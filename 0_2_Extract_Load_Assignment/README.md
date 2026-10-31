# Uniswap V3 Swap Extractor

This assignment extracts `Swap` events from selected Uniswap V3 pools on an
Ethereum-compatible JSON-RPC endpoint and loads them into PostgreSQL. It uses
`web3.py` to query logs and `psycopg` to insert the decoded events.

## Pipeline

![Uniswap V3 swap extraction pipeline](./swap-pipeline.svg)

## What it does

- Queries the configured pools over an inclusive block range.
- Fetches logs in configurable block chunks (10 blocks by default).
- Decodes each event and records its block timestamp in UTC.
- Inserts records into the PostgreSQL `swaps` table.
- Skips duplicate events using the `(tx_hash, log_index)` conflict key.

The pool addresses and labels are defined in [`swap.py`](./swap.py):

| Pool address | Label |
| --- | --- |
| `0x88e6A0c2dDD26FEEb64F039a2c41296FcB3f5640` | ETH / USDC |
| `0x99ac8cA7087fAc4AEE841716da046925FF1EbCa8` | WBTC / USDC |
| `0x11b815efB8f5811c4ae790064f74d92330768266` | XDP / USDC |

## Requirements

- Python 3.14 or newer
- [`uv`](https://docs.astral.sh/uv/)
- A PostgreSQL database
- An Ethereum JSON-RPC endpoint with access to the block range you want to query

## Configuration

From this directory, create a `.env` file with the endpoint and PostgreSQL
connection string:

```env
RPC_URL=https://your-ethereum-rpc-endpoint
DATABASE_URL=postgresql://username:password@localhost:5432/database_name
```

Keep the `.env` file private; do not commit credentials or API keys.

## Prepare the database

The extractor does not create its destination table. Create `swaps` in the
database named by `DATABASE_URL` before running it:

```sql
CREATE TABLE swaps (
    tx_hash         TEXT NOT NULL,
    log_index       BIGINT NOT NULL,
    block_number    BIGINT NOT NULL,
    block_timestamp TIMESTAMPTZ NOT NULL,
    pool_address    TEXT NOT NULL,
    pool_name       TEXT NOT NULL,
    sender          TEXT NOT NULL,
    recipient       TEXT NOT NULL,
    amount0         NUMERIC NOT NULL,
    amount1         NUMERIC NOT NULL,
    sqrt_price_x96  NUMERIC NOT NULL,
    liquidity       NUMERIC NOT NULL,
    tick            INTEGER NOT NULL,
    PRIMARY KEY (tx_hash, log_index)
);
```

The numeric columns preserve the large integer values from the event without
requiring them to fit in PostgreSQL's fixed-width integer types.

## Install dependencies

```powershell
uv sync
```

## Run the extractor

Provide the start and end block numbers. The range includes both endpoints:

```powershell
uv run python swap.py --start_block 20000000 --end_block 20000020
```

To change the number of blocks requested per RPC call, provide `--chunk`:

```powershell
uv run python swap.py --start_block 20000000 --end_block 20000100 --chunk 100
```

Use a chunk size supported by your RPC provider; providers may limit the
maximum block span for `eth_getLogs`. The script reports progress and logs
fetch or decode errors to standard error. A failed block-range request is
skipped, so check the output and rerun any ranges that were not fetched.

## Docker

A Dockerfile is included, but it currently uses Python 3.13 while
`pyproject.toml` requires Python 3.14 or newer. The image's Python version must
be updated to meet the project requirement before the Docker build can run
successfully. For now, use the local `uv` workflow above.