import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime

def fetch_and_calculate_metrics(ticker_symbol):
    """
    Fetches historical data for a ticker and enforces:
    1. Market Cap between ₹20,000 Cr and ₹35,000 Cr.
    2. At least 1 year (252 trading days) of history.
    """
    try:
        stock = yf.Ticker(ticker_symbol)
        
        # --- Market Cap Check (20,000 Cr to 35,000 Cr INR) ---
        info = stock.info
        market_cap_inr = info.get("marketCap", None)
        
        if not market_cap_inr:
            return None
            
        market_cap_cr = market_cap_inr / 1e7  # Convert INR to Crores
        
        if not (20000 <= market_cap_cr <= 35000):
            return None

        # --- Listing History Check (>= 1 Year / 250+ Trading Days) ---
        hist = stock.history(period="1y")
        if len(hist) < 250:
            return None

        # --- Return & Volatility Math ---
        close_prices = hist['Close']
        current_price = close_prices.iloc[-1]
        
        # 1-Month (approx 22 trading days) & 3-Month (approx 64 trading days) returns
        price_1m = close_prices.iloc[-22] if len(close_prices) >= 22 else close_prices.iloc[0]
        price_3m = close_prices.iloc[-64] if len(close_prices) >= 64 else close_prices.iloc[0]
        
        return_1m = ((current_price - price_1m) / price_1m) * 100
        return_3m = ((current_price - price_3m) / price_3m) * 100

        # Period-scaled Standard Deviation (Daily SD * sqrt(N))
        daily_returns = close_prices.pct_change().dropna()
        
        std_daily_1m = daily_returns.tail(22).std() * 100
        std_daily_3m = daily_returns.tail(64).std() * 100
        
        std_1m = std_daily_1m * np.sqrt(22)
        std_3m = std_daily_3m * np.sqrt(64)

        company_name = info.get("shortName", ticker_symbol.replace(".NS", ""))

        return {
            "ticker": ticker_symbol,
            "company_name": company_name,
            "current_price": float(current_price),
            "return_1m": float(return_1m),
            "return_3m": float(return_3m),
            "std_1m": float(std_1m),
            "std_3m": float(std_3m),
            "market_cap_cr": float(market_cap_cr),
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        return None
