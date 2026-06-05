import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

def build_analytical_layer():
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    print("--- Initiating Deep SQL Optimization Engine ---")
    
    # 1. Drop the table if it exists so we can rerun this cleanly during testing
    cursor.execute("DROP TABLE IF EXISTS hourly_ticker_metrics;")
    
    # 2. The Master SQL Query (CTEs + Window Functions)
    print("[*] Executing CTEs and Window Functions to calculate rolling metrics...")
    
    advanced_sql = """
    CREATE TABLE hourly_ticker_metrics AS
    
    -- CTE 1: Group raw data into hourly buckets per ticker
    WITH HourlyBase AS (
        SELECT 
            ticker,
            strftime('%Y-%m-%d %H:00:00', created_at) AS metric_hour,
            COUNT(*) AS hourly_volume,
            AVG(sentiment_score) AS hourly_sentiment
        FROM synthetic_comments
        GROUP BY ticker, metric_hour
    ),
    
    -- CTE 2: Apply Window Functions for 24-hour rolling math
    RollingMetrics AS (
        SELECT 
            ticker,
            metric_hour,
            hourly_volume,
            ROUND(hourly_sentiment, 4) AS hourly_sentiment,
            
            -- Calculate 24-hour moving sum of volume
            SUM(hourly_volume) OVER (
                PARTITION BY ticker 
                ORDER BY metric_hour 
                ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
            ) AS rolling_24h_volume,
            
            -- Calculate 24-hour moving average of sentiment
            ROUND(AVG(hourly_sentiment) OVER (
                PARTITION BY ticker 
                ORDER BY metric_hour 
                ROWS BETWEEN 23 PRECEDING AND CURRENT ROW
            ), 4) AS rolling_24h_sentiment
            
        FROM HourlyBase
    )
    
    SELECT * FROM RollingMetrics;
    """
    
    cursor.execute(advanced_sql)
    con.commit()
    print("[✔] Analytical table 'hourly_ticker_metrics' created successfully.")
    
    # 3. Add Composite Indexes for lightning-fast queries in Stage 6 & 8
    print("[*] Building composite B-Tree indexes for visualization optimization...")
    cursor.execute("CREATE INDEX idx_ticker_hour ON hourly_ticker_metrics(ticker, metric_hour);")
    con.commit()
    
    # 4. Verify the Anomaly (The $FAKE bot attack)
    print("\n--- SQL Verification: Inspecting the $FAKE Anomaly ---")
    cursor.execute("""
        SELECT metric_hour, hourly_volume, rolling_24h_volume, rolling_24h_sentiment 
        FROM hourly_ticker_metrics 
        WHERE ticker = '$FAKE' 
        ORDER BY hourly_volume DESC 
        LIMIT 5;
    """)
    
    results = cursor.fetchall()
    print(f"{'Timestamp (Peak Hour)':<25} | {'Hourly Vol':<12} | {'24h Rolling Vol':<17} | {'24h Sentiment Avg':<15}")
    print("-" * 75)
    for row in results:
        print(f"{row[0]:<25} | {row[1]:<12} | {row[2]:<17} | {row[3]:<15}")

    con.close()
    print("\n[✔] Stage 3 Complete. Database is mathematically optimized.")

if __name__ == "__main__":
    build_analytical_layer()