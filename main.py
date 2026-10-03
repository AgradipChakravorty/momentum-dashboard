import sys
import os

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from src.config import WATCHLIST
from src.database import initialize_database, save_stock_metrics
from src.data_fetcher import fetch_and_calculate_metrics

def run_pipeline():
    print("--- Starting Stock Metrics Pipeline ---")
    initialize_database()
    
    for ticker in WATCHLIST:
        print(f"Processing: {ticker}...")
        metrics = fetch_and_calculate_metrics(ticker)
        if metrics:
            save_stock_metrics(metrics)
            print(f"Saved: {ticker}")
        else:
            print(f"Skipped: {ticker}")
            
    print("--- Pipeline Execution Complete ---")

if __name__ == "__main__":
    run_pipeline()
