import os
import sys
import argparse
import datetime
from web3 import Web3
import psycopg
from dotenv import load_dotenv

load_dotenv()

RPC_URL = os.getenv("RPC_URL")
DATABASE_URL = os.getenv("DATABASE_URL")

# Uniswap V3 Swap Event ABI
SWAP_ABI = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "name": "sender", "type": "address"},
            {"indexed": True, "name": "recipient", "type": "address"},
            {"indexed": False, "name": "amount0", "type": "int256"},
            {"indexed": False, "name": "amount1", "type": "int256"},
            {"indexed": False, "name": "sqrtPriceX96", "type": "uint160"},
            {"indexed": False, "name": "liquidity", "type": "uint128"},
            {"indexed": False, "name": "tick", "type": "int24"}
        ],
        "name": "Swap",
        "type": "event"
    }
]

# Target Pools
POOLS = {
    "0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640": "ETH / USDC",
    "0x99ac8cA7087fAc4AEE841716da046925FF1EbCa8": "WBTC / USDC",
    "0x11b815efB8f5811c4ae790064f74d92330768266": "XDP / USDC"
}

def get_block_timestamp(w3, block_number, block_cache):
    if block_number in block_cache:
        return block_cache[block_number]
    
    block = w3.eth.get_block(block_number)
    timestamp = block["timestamp"]
    dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
    block_cache[block_number] = dt
    return dt

def main():
    try:
        parser = argparse.ArgumentParser(description="Extract Uniswap V3 Swaps into Postgres")
        parser.add_argument("--start_block", type=int, required=True, help="The starting block number to fetch swaps from.")
        parser.add_argument("--end_block", type=int, required=True, help="The ending block number to fetch swaps from.")
        parser.add_argument("--chunk", type=int, default=10, help="Block chunk size (default: 10)")
        args = parser.parse_args()

        print("DEBUG: Arguments parsed successfully.", flush=True)

        if not RPC_URL or not DATABASE_URL:
            print("ERROR: RPC_URL or DATABASE_URL is missing!", flush=True)
            sys.exit(1)

        w3 = Web3(Web3.HTTPProvider(RPC_URL))

        if not w3.is_connected():
            print(f"Error: Failed to connect to RPC endpoint: {RPC_URL}", file=sys.stderr, flush=True)
            sys.exit(1)
            
        print("DEBUG: Connected to Web3 successfully.", flush=True)

        with psycopg.connect(DATABASE_URL) as conn:
            print("DEBUG: Connected to PostgreSQL successfully.", flush=True)
            with conn.cursor() as cur:
                block_cache = {}
                total_inserted = 0

                swap_topic = "0x" + (w3.keccak(text="Swap(address,address,int256,int256,uint160,uint128,int24)")).hex()
                pool_addresses = [w3.to_checksum_address(addr) for addr in POOLS.keys()]
                contract = w3.eth.contract(abi=SWAP_ABI)

                for current_block in range(args.start_block, args.end_block + 1, args.chunk):
                    current_end = min(current_block + args.chunk - 1, args.end_block)
                    print(f"Fetching blocks {current_block} to {current_end}...", flush=True)

                    try:
                        logs = w3.eth.get_logs({
                            "fromBlock": hex(current_block),
                            "toBlock": hex(current_end),
                            "address": pool_addresses,
                            "topics": [swap_topic]
                        })
                    except Exception as e:
                        print(f"Error fetching logs for block range {current_block}-{current_end}: {e}", file=sys.stderr, flush=True)
                        continue

                    chunk_swaps = []
                    for log in logs:
                        try:
                            decoded = contract.events.Swap().process_log(log)
                            block_number = decoded["blockNumber"]
                            block_timestamp = get_block_timestamp(w3, block_number, block_cache)
                            event_args = decoded["args"]
                            pool_address = decoded["address"]
                            pool_name = POOLS.get(pool_address, POOLS.get(pool_address.lower(), "Unknown"))

                            swap_record = (
                                decoded["transactionHash"].hex(),
                                decoded["logIndex"],
                                block_number,
                                block_timestamp,
                                pool_address,
                                pool_name,
                                str(event_args["sender"]),
                                str(event_args["recipient"]),
                                str(event_args["amount0"]),
                                str(event_args["amount1"]),
                                str(event_args["sqrtPriceX96"]),
                                str(event_args["liquidity"]),
                                str(event_args["tick"])
                            )
                            chunk_swaps.append(swap_record)
                        except Exception as decode_err:
                            print(f"Error decoding log: {decode_err}", file=sys.stderr, flush=True)
                            continue

                    if chunk_swaps:
                        cur.executemany("""
                            INSERT INTO swaps (
                                tx_hash, log_index, block_number, block_timestamp, 
                                pool_address, pool_name, sender, recipient, 
                                amount0, amount1, sqrt_price_x96, liquidity, tick
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (tx_hash, log_index) DO NOTHING;
                        """, chunk_swaps)
                        
                        conn.commit()
                        total_inserted += len(chunk_swaps)
                        print(f"-> Inserted {len(chunk_swaps)} swaps. Total so far: {total_inserted}", flush=True)

        print(f"Extraction complete! Total new swaps inserted: {total_inserted}", flush=True)

    except Exception as e:
        print(f"CRITICAL ERROR: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()