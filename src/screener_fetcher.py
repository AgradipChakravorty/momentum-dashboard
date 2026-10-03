import requests
from bs4 import BeautifulSoup
import re
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.data_fetcher import fetch_and_calculate_metrics
from src.database import get_db_connection

# Known REITs and InvITs keywords/symbols to filter out
REIT_INVIT_KEYWORDS = ["REIT", "INVIT", "EMBASSY", "MINDSPACE", "NEXUS", "BIRET", "PGINVIT", "IRBINVIT"]

def fetch_screener_tickers():
    """Scrapes Screener.in for stocks with Market Cap between 20,000 Cr and 3,50,000 Cr."""
    url = "https://www.screener.in/api/company/search/"
    # Alternative direct screen query URL
    screen_url = "https://www.screener.in/screen/raw/?query=Market+Capitalization+%3E+20000+AND+Market+Capitalization+%3C+350000"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    response = requests.get(screen_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch Screener data. Status code: {response.status_code}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    rows = soup.find_all("tr")
    
    extracted_tickers = []
    
    for row in rows:
        link = row.find("a", href=True)
        if link and "/company/" in link["href"]:
            company_name = link.text.strip()
            # Extract ticker symbol from URL or text
            symbol_match = re.search(r"/company/([^/]+)/", link["href"])
            if symbol_match:
                raw_symbol = symbol_match.group(1).upper()
                
                # Check REIT / InvIT exclusion
                if any(keyword in company_name.upper() or keyword in raw_symbol for keyword in REIT_INVIT_KEYWORDS):
                    print(f"Skipping REIT/InvIT: {company_name} ({raw_symbol})")
                    continue
                
                ticker = f"{raw_symbol}.NS"
                extracted_tickers.append((ticker, company_name))
                
    return extracted_tickers

def sync_screener_universe():
    print("🔍 Fetching universe from Screener.in (Market Cap: 20,000 Cr - 350,000 Cr)...")
    tickers = fetch_screener_tickers()
    print(f"Found {len(tickers)} potential tickers matching criteria.")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    added_count = 0
    for ticker, name in tickers:
        print(f"Processing: {ticker} ({name})...")
        metrics = fetch_and_calculate_metrics(ticker)
        
        # Filters out companies traded for less than 1 year (fetch_and_calculate_metrics returns None if history < required days)
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
            added_count += 1
        else:
            print(f"Skipped {ticker}: Insufficient trading history (< 1 year / 180 days).")
            
    conn.commit()
    cursor.close()
    conn.close()
    print(f"✅ Finished! Successfully stored and calculated metrics for {added_count} stocks.")

if __name__ == "__main__":
    sync_screener_universe()
