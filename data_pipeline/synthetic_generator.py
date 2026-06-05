import sqlite3
import os
import random
from datetime import datetime, timedelta
import numpy as np
from faker import Faker

fake = Faker()

# =====================================================
# CONFIGURATION
# =====================================================
DAYS_TO_SIMULATE = 180
BASELINE_RECORDS_PER_DAY = 500  # Normal noise
REAL_TICKERS = ["$AAPL", "$MSFT", "$NVDA", "$GOOG", "$META"]

# The Anomaly Variables (The Market Manipulation)
FAKE_TICKER = "$FAKE"
ANOMALY_START_DAY = 45  # Day 45 of our 180 day window
ANOMALY_DURATION_HOURS = 48
ANOMALY_VOLUME = 5000  # Massive spike in comments
ANOMALY_SENTIMENT_MEAN = 0.9  # Unnaturally positive (0.0 to 1.0 scale)

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

def setup_synthetic_schema():
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS synthetic_comments (
            comment_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ticker TEXT,
            sentiment_score REAL,
            comment_length INTEGER,
            is_bot INTEGER DEFAULT 0,
            created_at TIMESTAMP
        );
    ''')
    con.commit()
    con.close()

def generate_baseline_data(start_date):
    """Generates the normal, everyday noise of the market."""
    records = []
    print(f"[*] Generating {DAYS_TO_SIMULATE} days of baseline noise...")
    
    for day in range(DAYS_TO_SIMULATE):
        current_date = start_date + timedelta(days=day)
        
        # Add some daily random variance to the volume
        daily_volume = int(np.random.normal(BASELINE_RECORDS_PER_DAY, 50))
        
        for _ in range(daily_volume):
            # Spread comments randomly throughout the 24-hour day
            second_offset = random.randint(0, 86400)
            timestamp = current_date + timedelta(seconds=second_offset)
            
            records.append((
                fake.user_name(),
                random.choice(REAL_TICKERS),
                np.random.normal(0.2, 0.4), # Slightly positive average sentiment, high variance
                random.randint(20, 500), # Comment length
                0, # Not a bot
                timestamp.strftime('%Y-%m-%d %H:%M:%S')
            ))
            
    return records

def inject_bot_attack(start_date):
    """Injects the coordinated market manipulation anomaly."""
    records = []
    anomaly_start_time = start_date + timedelta(days=ANOMALY_START_DAY)
    print(f"[*] INJECTING BOT ATTACK: {ANOMALY_VOLUME} records for {FAKE_TICKER} starting at {anomaly_start_time}")
    
    for _ in range(ANOMALY_VOLUME):
        # Compress all these comments into a tight 48-hour window
        second_offset = random.randint(0, ANOMALY_DURATION_HOURS * 3600)
        timestamp = anomaly_start_time + timedelta(seconds=second_offset)
        
        records.append((
            f"bot_{fake.word()}{random.randint(100,999)}", # Suspicious usernames
            FAKE_TICKER,
            np.random.normal(ANOMALY_SENTIMENT_MEAN, 0.05), # Artificially high, low variance sentiment
            random.randint(10, 50), # Short, spammy comments
            1, # Flagged as bot (our ground truth for testing later)
            timestamp.strftime('%Y-%m-%d %H:%M:%S')
        ))
        
    return records

def populate_database():
    setup_synthetic_schema()
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    # Start the simulation exactly 6 months ago from today
    start_date = datetime.now() - timedelta(days=DAYS_TO_SIMULATE)
    
    all_records = generate_baseline_data(start_date)
    all_records.extend(inject_bot_attack(start_date))
    
    # Shuffle so the bot attack is interspersed organically with the real comments on those days
    random.shuffle(all_records)
    
    print(f"[*] Committing {len(all_records)} synthetic rows to the database...")
    
    cursor.execute("BEGIN IMMEDIATE")
    cursor.executemany("""
        INSERT INTO synthetic_comments (username, ticker, sentiment_score, comment_length, is_bot, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, all_records)
    
    con.commit()
    con.close()
    print("[✔] Synthetic generation complete.")

if __name__ == "__main__":
    print("==================================================")
    print("   TECHPULSE SYNTHETIC DATA ENGINE INITIALIZED")
    print("==================================================")
    populate_database()