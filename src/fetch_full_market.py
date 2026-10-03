import sys
import os
import io
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_and_calculate_metrics
from src.database import get_db_connection

REIT_INVIT_KEYWORDS = ["REIT", "INVIT", "EMBASSY", "MINDSPACE", "NEXUS", "BIRET", "PGINVIT", "IRBINVIT"]

def download_nse_universe():
    """Downloads official listed equity universe from NSE India."""
    url = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    print("📥 Downloading official NSE equity master list...")
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        df = pd.read_csv(io.StringIO(response.text))
        # Keep active Equity series ('EQ')
        df_eq = df[df[' SERIES'].str.strip() == 'EQ']
        symbols = df_eq['SYMBOL'].str.strip().tolist()
        print(f"✅ Loaded {len(symbols)} active NSE symbols.")
        return symbols
    else:
        print(f"❌ Failed to download NSE equity list (Status: {response.status_code}).")
        return []

def run_full_market_ingestion():
    symbols = download_nse_universe()
    if not symbols:
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    success_count = 0
    skipped_count = 0

    print(f"🚀 Starting full market ingestion & metric calculations ({len(symbols)} stocks)...")

    for idx, sym in enumerate(symbols, 1):
        # 1. Filter out REITs & InvITs
        if any(keyword in sym.upper() for keyword in REIT_INVIT_KEYWORDS):
            print(f"[{idx}/{len(symbols)}] Skipping REIT/InvIT: {sym}")
            skipped_count += 1
            continue

        ticker = f"{sym}.NS"
        metrics = fetch_and_calculate_metrics(ticker)

        # 2. Filter out companies with <1 year trading history (fetch_and_calculate_metrics returns None)
        if metrics:
            query = """
            INSERT INTO stock_metrics (ticker, company_name, current_price, return_1m, return_3m, std_1m, std_3m, last_updated)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                current_price = VALUES(current_price),
                return_1m = VALUES(return_1m),
                return_3m = VALUES(return_3m),
                std_1m = VALUES(std_1m),
                std_3m = VALUES(std_3m),
                last_updated = VALUES(last_updated);
            """
            cursor.execute(query, (
                metrics['ticker'], metrics['company_name'], metrics['current_price'],
                metrics['return_1m'], metrics['return_3m'], metrics['std_1m'],
                metrics['std_3m'], metrics['last_updated']
            ))
            conn.commit()
            success_count += 1
            print(f"[{idx}/{len(symbols)}] ✅ Processed {sym}")
        else:
            skipped_count += 1
            print(f"[{idx}/{len(symbols)}] ⚠️ Skipped {sym} (History < 1 year or fetch limit)")

        time.sleep(0.05)  # Rate limiting protection

    cursor.close()
    conn.close()
    print(f"\n🎉 Finished! Processed: {success_count} | Skipped: {skipped_count}")

if __name__ == "__main__":
    run_full_market_ingestion()
