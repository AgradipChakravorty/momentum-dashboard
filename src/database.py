import sys
import os

# Add root directory to sys.path to resolve 'src' imports cleanly
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector

def get_db_connection():
    """Establish connection using Environment Variables (Render/Aiven compatible)."""
    return mysql.connector.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASS", ""),
        database=os.getenv("DB_NAME", "defaultdb"),
        ssl_disabled=False
    )

def initialize_database():
    """Create table if it does not exist on remote cloud database."""
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
    """Insert or update stock ranking metrics."""
    if not metrics:
        return
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    INSERT INTO stock_metrics (
        ticker, company_name, current_price, return_1m, return_3m, 
        std_1m, std_3m, risk_adj_1m, risk_adj_3m, z_score_1m, 
        z_score_3m, z_avg, adj_z_score, momentum_rank, last_updated
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        company_name = VALUES(company_name),
        current_price = VALUES(current_price),
        return_1m = VALUES(return_1m),
        return_3m = VALUES(return_3m),
        std_1m = VALUES(std_1m),
        std_3m = VALUES(std_3m),
        risk_adj_1m = VALUES(risk_adj_1m),
        risk_adj_3m = VALUES(risk_adj_3m),
        z_score_1m = VALUES(z_score_1m),
        z_score_3m = VALUES(z_score_3m),
        z_avg = VALUES(z_avg),
        adj_z_score = VALUES(adj_z_score),
        momentum_rank = VALUES(momentum_rank),
        last_updated = VALUES(last_updated);
    """
    cursor.execute(query, (
        metrics.get('ticker'),
        metrics.get('company_name'),
        metrics.get('current_price'),
        metrics.get('return_1m'),
        metrics.get('return_3m'),
        metrics.get('std_1m'),
        metrics.get('std_3m'),
        metrics.get('risk_adj_1m'),
        metrics.get('risk_adj_3m'),
        metrics.get('z_score_1m'),
        metrics.get('z_score_3m'),
        metrics.get('z_avg'),
        metrics.get('adj_z_score'),
        metrics.get('momentum_rank'),
        metrics.get('last_updated')
    ))
    conn.commit()
    cursor.close()
    conn.close()

if __name__ == "__main__":
    initialize_database()