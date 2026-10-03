import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

from src.database import get_db_connection
from src.data_fetcher import fetch_and_calculate_metrics
from src.config import WATCHLIST

st.set_page_config(page_title="Risk-Adjusted Momentum Dashboard", layout="wide")

# Auto-refresh trigger (60s)
count = st_autorefresh(interval=60000, limit=1000, key="momentum_model_autorefresh")

st.title("📊 Risk-Adjusted Momentum Screening Model")
st.write("Screening stocks via Sharpe-style returns, period volatility ($\sigma \cdot \sqrt{N}$), cross-sectional Z-Scores, and Positivity Adjustments.")

# --- Sidebar Parameters ---
st.sidebar.header("⚙️ Model Parameters")
rf_annual_1m = st.sidebar.number_input("1-Month Risk-Free Rate (% p.a.)", value=5.20, step=0.1)
rf_annual_3m = st.sidebar.number_input("3-Month Risk-Free Rate (% p.a.)", value=5.25, step=0.1)

rf_1m = rf_annual_1m / 12.0
rf_3m = rf_annual_3m / 4.0

def sync_market_data():
    conn = get_db_connection()
    cursor = conn.cursor()
    for ticker in WATCHLIST:
        metrics = fetch_and_calculate_metrics(ticker)
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
    cursor.close()
    conn.close()

if count > 0:
    sync_market_data()

# --- Model Calculations ---
def compute_momentum_model(rf_1m_rate, rf_3m_rate):
    conn = get_db_connection()
    query = "SELECT ticker, company_name, current_price, return_1m, return_3m, std_1m, std_3m, last_updated FROM stock_metrics;"
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        return df

    # Risk-Adjusted Returns
    df["risk_adj_1m"] = (df["return_1m"] - rf_1m_rate) / df["std_1m"].replace(0, np.nan)
    df["risk_adj_3m"] = (df["return_3m"] - rf_3m_rate) / df["std_3m"].replace(0, np.nan)

    std_adj_1m = df["risk_adj_1m"].std()
    std_adj_3m = df["risk_adj_3m"].std()

    if len(df) > 1 and pd.notnull(std_adj_1m) and std_adj_1m != 0:
        df["z_1m"] = (df["risk_adj_1m"] - df["risk_adj_1m"].mean()) / std_adj_1m
    else:
        df["z_1m"] = 0.0

    if len(df) > 1 and pd.notnull(std_adj_3m) and std_adj_3m != 0:
        df["z_3m"] = (df["risk_adj_3m"] - df["risk_adj_3m"].mean()) / std_adj_3m
    else:
        df["z_3m"] = 0.0

    # Intermediate Average Z-Score (used internally only)
    z_avg = (df["z_1m"] + df["z_3m"]) / 2.0

    # Piecewise Adjusted Z-Score: z >= 0 -> 1 + z | z < 0 -> 1 / (1 - z)
    df["adj_z_score"] = np.where(z_avg >= 0, 1.0 + z_avg, 1.0 / (1.0 - z_avg))

    # Rank based on Adjusted Z-Score
    df["momentum_rank"] = df["adj_z_score"].rank(ascending=False, method="min").astype(int)

    return df.sort_values("momentum_rank").reset_index(drop=True)

df_model = compute_momentum_model(rf_1m, rf_3m)

if not df_model.empty:
    col_a, col_b = st.columns(2)
    with col_a:
        st.metric("Total Stocks Screened", len(df_model))
    with col_b:
        latest_ts = df_model["last_updated"].max()
        st.metric("Last Full Universe Sync", str(latest_ts))

    st.markdown("---")

    # --- Search Bar & Live Inspection ---
    st.subheader("🔍 Search & Inspect Stock in Universe")
    search_col1, search_col2 = st.columns([2, 2])

    with search_col1:
        search_query = st.text_input("Filter table by symbol/name:", placeholder="e.g. SANSERA, HCLTECH, PATANJALI").strip().upper()

    with search_col2:
        all_symbols = sorted(df_model["ticker"].tolist())
        selected_stock = st.selectbox("Pick exact stock for LIVE inspection:", options=["None"] + all_symbols)

    if selected_stock != "None":
        stock_row = df_model[df_model["ticker"] == selected_stock].iloc[0]
        
        # On-demand live fetch for the individual target stock
        with st.spinner(f"Fetching live real-time metrics for {selected_stock}..."):
            live_metrics = fetch_and_calculate_metrics(selected_stock)

        live_price = live_metrics['current_price'] if live_metrics else stock_row['current_price']
        live_1m_ret = live_metrics['return_1m'] if live_metrics else stock_row['return_1m']
        live_3m_ret = live_metrics['return_3m'] if live_metrics else stock_row['return_3m']

        price_diff = live_price - stock_row['current_price']
        price_diff_pct = (price_diff / stock_row['current_price']) * 100 if stock_row['current_price'] != 0 else 0.0

        st.info(f"📍 **{stock_row['company_name']} ({stock_row['ticker']})** | **Rank #{stock_row['momentum_rank']}** of {len(df_model)}")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Live Price", f"₹{live_price:,.2f}", f"{price_diff_pct:+.2f}% vs DB")
        m2.metric("1M Return (Live)", f"{live_1m_ret:+.2f}%")
        m3.metric("3M Return (Live)", f"{live_3m_ret:+.2f}%")
        m4.metric("Z (1M)", f"{stock_row['z_1m']:.2f}")
        m5.metric("Adj Z-Score", f"{stock_row['adj_z_score']:.2f}")

    st.markdown("---")

    # --- Table Display ---
    df_filtered = df_model.copy()
    if search_query:
        df_filtered = df_filtered[
            df_filtered["ticker"].str.contains(search_query, case=False, na=False) |
            df_filtered["company_name"].str.contains(search_query, case=False, na=False)
        ]

    df_display = df_filtered.copy()
    df_display["current_price"] = df_display["current_price"].apply(lambda x: f"₹{x:,.2f}")
    df_display["return_1m"] = df_display["return_1m"].apply(lambda x: f"{x:+.2f}%")
    df_display["return_3m"] = df_display["return_3m"].apply(lambda x: f"{x:+.2f}%")
    df_display["std_1m"] = df_display["std_1m"].apply(lambda x: f"{x:.2f}%")
    df_display["std_3m"] = df_display["std_3m"].apply(lambda x: f"{x:.2f}%")
    df_display["risk_adj_1m"] = df_display["risk_adj_1m"].apply(lambda x: f"{x:.2f}")
    df_display["risk_adj_3m"] = df_display["risk_adj_3m"].apply(lambda x: f"{x:.2f}")
    df_display["z_1m"] = df_display["z_1m"].apply(lambda x: f"{x:.2f}")
    df_display["z_3m"] = df_display["z_3m"].apply(lambda x: f"{x:.2f}")
    df_display["adj_z_score"] = df_display["adj_z_score"].apply(lambda x: f"{x:.2f}")

    rename_map = {
        "momentum_rank": "Rank",
        "ticker": "Ticker",
        "company_name": "Company",
        "current_price": "Price (₹)",
        "return_1m": "1M Ret (%)",
        "return_3m": "3M Ret (%)",
        "std_1m": "1M SD (% * √N)",
        "std_3m": "3M SD (% * √N)",
        "risk_adj_1m": "1M Risk-Adj",
        "risk_adj_3m": "3M Risk-Adj",
        "z_1m": "Z (1M)",
        "z_3m": "Z (3M)",
        "adj_z_score": "Adj Z-Score"
    }
    
    st.dataframe(
        df_display[[
            "momentum_rank", "ticker", "company_name", "current_price", 
            "return_1m", "std_1m", "return_3m", "std_3m",
            "risk_adj_1m", "risk_adj_3m", "z_1m", "z_3m", "adj_z_score"
        ]].rename(columns=rename_map),
        use_container_width=True
    )
else:
    st.warning("No stocks available in database yet.")
