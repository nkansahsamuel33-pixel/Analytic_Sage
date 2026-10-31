import os
from dotenv import load_dotenv
import pandas as pd
from sqlalchemy import create_engine

print("Step 1: Loading environment variables...")
load_dotenv()
POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
DB_HOST = os.getenv('DB_HOST', 'db')
DB_PORT = os.getenv('DB_PORT', '5432')
POSTGRES_DB = os.getenv('POSTGRES_DB')

print(f"Connecting to Postgres at {DB_HOST}:{DB_PORT} as {POSTGRES_USER}...")
engine = create_engine(f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{DB_HOST}:{DB_PORT}/{POSTGRES_DB}')

try:
    print("Step 2: Reading CSV file...")
    csv_path = 'SELECT-usd-max.csv'
    
    df = pd.read_csv(csv_path)
    print(f"CSV read successfully! Rows: {len(df)}")

    print("Step 3: Creating empty table schema...")
    df.head(0).to_sql(
        name="crypto_data", 
        con=engine, 
        if_exists="replace", 
        index=False
    )
    print("Empty table created with schema!")

    print("Step 4: Appending full data...")
    df.to_sql(
        name="crypto_data", 
        con=engine, 
        if_exists="append", 
        index=False
    )
    print("Data successfully appended to the table!")

except Exception as e:
    print(f" ERROR DURING INGESTION: {e}")
    raise e