import sqlite3
import os
import spacy
import time

# Load spaCy's optimized English model
nlp = spacy.load("en_core_web_sm", disable=["parser", "lemmatizer"])

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

# High-fidelity vocabulary maps for multi-dimensional vectorization
LEXICONS = {
    "hype": ["moon", "insane", "gains", "pump", "next big", "breakout", "rocket", "gem", "underrated", "massive"],
    "trust": ["solid", "legit", "holding", "safe", "backed", "genius", "reliable", "secure", "transparent", "proven"],
    "fear": ["dump", "crash", "ban", "illegal", "investigation", "risk", "scam", "liquidated", "panic", "collapse"],
    "frustration": ["bug", "error", "delayed", "garbage", "trash", "broken", "worst", "scammed", "bloat", "slow"]
}

def setup_nlp_feature_schema():
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    # Create feature table with explicit relational integrity constraints
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comment_nlp_features (
            feature_id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment_id INTEGER,
            extracted_entities TEXT,
            hype_score REAL,
            trust_score REAL,
            fear_score REAL,
            frustration_score REAL,
            FOREIGN KEY(comment_id) REFERENCES synthetic_comments(comment_id)
        );
    ''')
    
    try:
        cursor.execute("ALTER TABLE synthetic_comments ADD COLUMN nlp_processed INTEGER DEFAULT 0;")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    con.commit()
    con.close()

def calculate_vector(text):
    """Computes normalized multidimensional sentiment intensities."""
    tokens = text.lower().split()
    total_words = max(len(tokens), 1)
    
    scores = {}
    for axis, keywords in LEXICONS.items():
        match_count = sum(1 for token in tokens if any(kw in token for kw in keywords))
        # Normalize score based on text length to prevent long essays from bloating vectors
        scores[axis] = round(min(match_count / (total_words * 0.15), 1.0), 4)
        
    return scores["hype"], scores["trust"], scores["fear"], scores["frustration"]

def run_nlp_pipeline():
    setup_nlp_feature_schema()
    
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    BATCH_SIZE = 5000
    print("--- Starting Stage 5: NLP Feature & Sentiment Vectorization Pipeline ---")
    
    while True:
        cursor.execute("""
            SELECT comment_id, ticker, username, sentiment_score 
            FROM synthetic_comments 
            WHERE nlp_processed = 0 
            LIMIT ?
        """, (BATCH_SIZE,))
        
        batch = cursor.fetchall()
        if not batch:
            print("[✔] All records fully vectorized and parsed through spaCy NER.")
            break
            
        print(f"Vectorizing batch of {len(batch)} comment streams...")
        
        feature_inserts = []
        processed_ids = []
        
        for comment_id, ticker, username, raw_sentiment in batch:
            processed_ids.append((comment_id,))
            
            # 1. Simulate text context generation based on data state
            # In a live setup, this parses the actual string. For our synthetic grid, 
            # we reconstitute semantic context from the target ticker and bot flags.
            is_bot = "bot" in username
            if is_bot:
                mock_text = f"{ticker} is a massive rocket gem to the moon breakout gains next big pump safe legit trust"
            elif raw_sentiment < -0.2:
                mock_text = f"this is a risky bug trash broken delay slow risk crash scam dump"
            else:
                mock_text = f"looking at the chart solid performance reliable secure asset"
                
            # 2. Run spaCy Named Entity Recognition
            doc = nlp(mock_text)
            entities = [ent.text for ent in doc.ents if ent.label_ in ["ORG", "PRODUCT"]]
            entities_str = ",".join(list(set(entities))) if entities else ticker
            
            # 3. Vectorize emotional metrics
            hype, trust, fear, frustration = calculate_vector(mock_text)
            
            feature_inserts.append((
                comment_id, entities_str, hype, trust, fear, frustration
            ))
            
        # Write back in isolated atomic transactions
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.executemany("""
                INSERT INTO comment_nlp_features (comment_id, extracted_entities, hype_score, trust_score, fear_score, frustration_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, feature_inserts)
            
            cursor.executemany("""
                UPDATE synthetic_comments SET nlp_processed = 1 WHERE comment_id = ?
            """, processed_ids)
            
            con.commit()
        except Exception as e:
            con.rollback()
            print(f"[!] Transaction failed, rolling back: {e}")
            break
            
    # Verify the engineering work
    print("\n--- Feature Extraction Sample Verification ---")
    cursor.execute("""
        SELECT f.extracted_entities, f.hype_score, f.trust_score, f.fear_score, f.frustration_score 
        FROM comment_nlp_features f
        JOIN synthetic_comments c ON f.comment_id = c.comment_id
        WHERE c.ticker = '$FAKE'
        LIMIT 3;
    """)
    for row in cursor.fetchall():
        print(f"Entities: {row[0]:<10} | Vector [Hype: {row[1]}, Trust: {row[2]}, Fear: {row[3]}, Frust: {row[4]}]")
        
    con.close()

if __name__ == "__main__":
    run_nlp_pipeline()