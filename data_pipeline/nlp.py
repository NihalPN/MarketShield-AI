import sqlite3
import os
import spacy
import time

# =====================================================
# CONFIGURATION
# =====================================================
BATCH_SIZE = 500  # Number of rows to process in memory at once

print("Loading spaCy NLP Model (en_core_web_sm)...")
nlp = spacy.load("en_core_web_sm")

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

def setup_database():
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    cursor = con.cursor()
    
    # Create the junction table to map documents to the companies mentioned
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS document_entities (
            document_id TEXT,
            entity_name TEXT,
            entity_type TEXT,
            PRIMARY KEY (document_id, entity_name)
        );
    ''')
    
    # Add a tracking column to the main table so we can resume if we stop the script
    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN nlp_processed INTEGER DEFAULT 0;")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    con.commit()
    con.close()

def run_ner_pipeline():
    setup_database()
    
    con = sqlite3.connect(db_path, timeout=30.0)
    cursor = con.cursor()
    
    while True:
        # 1. Grab an unprocessed batch of documents
        cursor.execute("""
            SELECT document_id, title, content 
            FROM documents 
            WHERE nlp_processed = 0 AND content != '' AND content != 'Empty or minimal body content extracted.'
            LIMIT ?
        """, (BATCH_SIZE,))
        
        batch = cursor.fetchall()
        
        if not batch:
            print("All documents have been successfully processed by the NLP engine.")
            break
            
        print(f"\nProcessing new batch of {len(batch)} documents...")
        
        # Prepare the text for spaCy's optimized batch processor
        doc_ids = [row[0] for row in batch]
        texts = [f"{row[1]}. {row[2]}" for row in batch] # Combine title and content
        
        entities_to_insert = []
        
        # 2. nlp.pipe() is highly optimized in C under the hood
        for doc_id, doc in zip(doc_ids, nlp.pipe(texts, disable=["tagger", "parser", "attribute_ruler", "lemmatizer"])):
            
            # We only care about ORG (Organizations) and PRODUCT (Products)
            # We use a set to ensure we don't insert duplicate tags for the same document
            unique_entities = set()
            for ent in doc.ents:
                if ent.label_ in ["ORG", "PRODUCT"]:
                    # Clean up the string (e.g., remove trailing punctuation or whitespace)
                    clean_name = ent.text.strip().upper()
                    if len(clean_name) > 1:
                        unique_entities.add((doc_id, clean_name, ent.label_))
                        
            entities_to_insert.extend(list(unique_entities))
            
        # 3. Write the extracted entities to the database
        cursor.execute("BEGIN IMMEDIATE")
        try:
            cursor.executemany("""
                INSERT OR IGNORE INTO document_entities (document_id, entity_name, entity_type)
                VALUES (?, ?, ?)
            """, entities_to_insert)
            
            # 4. Mark this batch as processed
            cursor.executemany("""
                UPDATE documents SET nlp_processed = 1 WHERE document_id = ?
            """, [(doc_id,) for doc_id in doc_ids])
            
            con.commit()
            print(f"Extracted {len(entities_to_insert)} entities. Saved and checkpointed.")
            
        except Exception as e:
            con.rollback()
            print(f"Failed to save batch: {e}")
            time.sleep(5)
            
    con.close()

if __name__ == "__main__":
    print("--- Starting Local NLP Named Entity Recognition ---")
    run_ner_pipeline()