CREATE DATABASE IF NOT EXISTS investing_db;
USE investing_db;

CREATE TABLE IF NOT EXISTS stock_metrics (
    ticker VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    current_price DECIMAL(10, 2) NOT NULL,
    market_cap BIGINT,
    return_1m FLOAT,
    return_3m FLOAT,
    last_updated DATETIME NOT NULL,
    INDEX idx_last_updated (last_updated),
    INDEX idx_market_cap (market_cap)
);
