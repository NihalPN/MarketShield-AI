import sqlite3
import pandas as pd
import numpy as np
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

def detect_anomalies():
    print("--- Stage 6: Statistical Anomaly Engine (V2 - Cold Start Fix) ---")
    
    con = sqlite3.connect(db_path)
    query = """
        SELECT ticker, metric_hour, hourly_volume, rolling_24h_volume, rolling_24h_sentiment 
        FROM hourly_ticker_metrics
    """
    df = pd.read_sql_query(query, con)
    df['metric_hour'] = pd.to_datetime(df['metric_hour'])
    
    # Create a master timeline of every single hour in the 6-month window
    full_timeline = pd.date_range(start=df['metric_hour'].min(), end=df['metric_hour'].max(), freq='h')
    
    BASELINE_WINDOW_HOURS = 24 * 7 
    Z_SCORE_THRESHOLD = 5.0 # Raised to 5.0 to filter out standard noise
    anomalies = []
    
    print("[*] Reindexing timelines and calculating fixed Z-Scores...")
    
    for ticker, group in df.groupby('ticker'):
        # 1. THE FIX: Reindex the data against the master timeline, filling missing hours with 0
        group = group.set_index('metric_hour').reindex(full_timeline).fillna(0)
        group['ticker'] = ticker
        
        # 2. Calculate baseline with min_periods=1 so brand new tickers get evaluated instantly
        group['baseline_mean'] = group['rolling_24h_volume'].rolling(window=BASELINE_WINDOW_HOURS, min_periods=1).mean()
        group['baseline_std'] = group['rolling_24h_volume'].rolling(window=BASELINE_WINDOW_HOURS, min_periods=1).std()
        
        group['volume_z_score'] = (group['rolling_24h_volume'] - group['baseline_mean']) / (group['baseline_std'] + 1e-9)
        
        ticker_anomalies = group[group['volume_z_score'] > Z_SCORE_THRESHOLD]
        
        for timestamp, row in ticker_anomalies.iterrows():
            if row['rolling_24h_volume'] > 0: # Only log active hours
                anomalies.append({
                    'ticker': ticker,
                    'timestamp': timestamp,
                    'volume_z_score': round(row['volume_z_score'], 2),
                    'rolling_volume': row['rolling_24h_volume'],
                    # TYPO FIXED HERE: 'sentiment' -> 'rolling_24h_sentiment'
                    'sentiment': round(row['rolling_24h_sentiment'], 4)
                })

    con.close()
    
    print("\n==================================================")
    print("             Z-SCORE ANOMALY REPORT               ")
    print("==================================================")
    
    if not anomalies:
        print("[!] No anomalies detected above threshold.")
    else:
        anomalies_df = pd.DataFrame(anomalies).sort_values('volume_z_score', ascending=False)
        print(f"Found {len(anomalies_df)} extreme hourly triggers (Top 15 shown).")
        print(f"{'Timestamp':<20} | {'Ticker':<8} | {'Z-Score':<10} | {'Rolling Vol':<12} | {'Sentiment'}")
        print("-" * 65)
        
        for _, row in anomalies_df.head(15).iterrows():
            print(f"{row['timestamp'].strftime('%Y-%m-%d %H:%M'):<20} | {row['ticker']:<8} | {row['volume_z_score']:<10} | {row['rolling_volume']:<12} | {row['sentiment']}")

if __name__ == "__main__":
    detect_anomalies()