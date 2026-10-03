import sys
import os

# Add root directory to sys.path to resolve 'src' imports cleanly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector
from src.config import DB_CONFIG

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def initialize_database():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_metrics (
            ticker VARCHAR(20) PRIMARY KEY,
            company_name VARCHAR(100),
            current_price DECIMAL(10, 2),
            return_1m DECIMAL(6, 2),
            return_3m DECIMAL(6, 2),
            std_1m DECIMAL(6, 2),
            std_3m DECIMAL(6, 2),
            risk_adj_1m DECIMAL(8, 4),
            risk_adj_3m DECIMAL(8, 4),
            z_score_1m DECIMAL(8, 4),
            z_score_3m DECIMAL(8, 4),
            z_avg DECIMAL(8, 4),
            adj_z_score DECIMAL(8, 4),
            momentum_rank INT,
            last_updated DATETIME
        );
    """)
    conn.commit()
    cursor.close()
    conn.close()

def save_stock_metrics(metrics: dict):
    if not metrics:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO stock_metrics (
        ticker, company_name, current_price, return_1m, return_3m, std_1m, std_3m, last_updated
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        current_price = VALUES(current_price),
        return_1m = VALUES(return_1m),
        return_3m = VALUES(return_3m),
        std_1m = VALUES(std_1m),
        std_3m = VALUES(std_3m),
        last_updated = VALUES(last_updated);
    """
    cursor.execute(query, (
        metrics['ticker'],
        metrics['company_name'],
        metrics['current_price'],
        metrics['return_1m'],
        metrics['return_3m'],
        metrics['std_1m'],
        metrics['std_3m'],
        metrics['last_updated']
    ))
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    initialize_database()
