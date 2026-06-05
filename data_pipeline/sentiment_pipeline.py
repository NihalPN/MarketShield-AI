import sqlite3
import os
import time
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# =====================================================
# CONFIGURATION & RESOLUTION MAPPING
# =====================================================
BATCH_SIZE = 2000

# Standardizing common tech aliases to single clean names
RESOLUTION_MAP = {
    "GOOGLE INC.": "GOOGLE", "ALPHABET INC.": "GOOGLE", "ALPHABET": "GOOGLE", "GOOG": "GOOGLE", "GOOGL": "GOOGLE",
    "APPLE INC.": "APPLE", "AAPL": "APPLE",
    "MICROSOFT CORP.": "MICROSOFT", "MICROSOFT CORPORATION": "MICROSOFT", "MSFT": "MICROSOFT",
    "TESLA INC.": "TESLA", "TESLA MOTORS": "TESLA", "TSLA": "TESLA",
    "NVIDIA CORP.": "NVIDIA", "NVDA": "NVIDIA",
    "META PLATFORMS": "META", "FACEBOOK": "META", "FACEBOOK INC.": "META",
    "OPENAI INC": "OPENAI",
    "AMAZON.COM": "AMAZON", "AWS": "AMAZON", "AMZN": "AMAZON"
}

# Entities to completely drop because they are usually NLP noise/misclassifications
NOISE_FILTER = {"CEO", "AI", "APP", "TECH", "CLOUD", "API", "INTERNET", "SOURCE", "SYSTEM"}

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))
analyzer = SentimentIntensityAnalyzer()

def setup_sentiment_schema():
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    # Add sentiment and resolved columns to your existing entity table safely
    try:
        cursor.execute("ALTER TABLE document_entities ADD COLUMN resolved_name TEXT;")
        cursor.execute("ALTER TABLE document_entities ADD COLUMN sentiment_score REAL;")
        cursor.execute("ALTER TABLE document_entities ADD COLUMN sentiment_processed INTEGER DEFAULT 0;")
        # Create an index to make our metric queries run instantly later
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_resolved_sentiment ON document_entities(resolved_name, sentiment_score);")
        con.commit()
        print("[*] Database schema upgraded for Sentiment Analysis.")
    except sqlite3.OperationalError:
        pass # Columns already exist
    finally:
        con.close()

def process_sentiment():
    setup_sentiment_schema()
    
    con = sqlite3.connect(db_path, timeout=60.0)
    cursor = con.cursor()
    
    print("--- Starting High-Speed Sentiment Analysis Pipeline ---")
    
    while True:
        # Join tables to analyze the entity context directly against the original text
        cursor.execute("""
            SELECT de.document_id, de.entity_name, d.content 
            FROM document_entities de
            JOIN documents d ON de.document_id = d.document_id
            WHERE de.sentiment_processed = 0
            LIMIT ?
        """, (BATCH_SIZE,))
        
        batch = cursor.fetchall()
        if not batch:
            print("[✔] All entity mentions have been successfully resolved and scored!")
            break
            
        print(f"Processing batch of {len(batch)} mentions...")
        
        updates = []
        deletes = []
        
        for doc_id, entity_name, content in batch:
            # 1. Clean up entity resolution
            clean_name = entity_name.strip().upper()
            
            if clean_name in NOISE_FILTER or len(clean_name) <= 1:
                deletes.append((doc_id, entity_name))
                continue
                
            resolved_name = RESOLUTION_MAP.get(clean_name, clean_name)
            
            # 2. Calculate Sentiment Score
            # We score the actual document content where this entity was discovered
            scores = analyzer.polarity_scores(content[:4000]) # Cap text length slightly to optimize speed
            compound_score = scores['compound']
            
            updates.append((resolved_name, compound_score, doc_id, entity_name))
            
        # 3. Write updates back to database in a clean transaction
        cursor.execute("BEGIN IMMEDIATE")
        try:
            if updates:
                cursor.executemany("""
                    UPDATE document_entities 
                    SET resolved_name = ?, sentiment_score = ?, sentiment_processed = 1
                    WHERE document_id = ? AND entity_name = ?
                """, updates)
                
            if deletes:
                cursor.executemany("""
                    DELETE FROM document_entities WHERE document_id = ? AND entity_name = ?
                """, deletes)
                
            con.commit()
            print(f"  Saved {len(updates)} scores. Cleaned {len(deletes)} noise rows.")
        except Exception as e:
            con.rollback()
            print(f"[!] Batch write failed, rolling back: {e}")
            time.sleep(2)
            
    con.close()

if __name__ == "__main__":
    process_sentiment()