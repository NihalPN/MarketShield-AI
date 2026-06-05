import sqlite3
import os

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

def run_graph_inference():
    print("--- Initializing Stage 4: Probabilistic Graph Inference Engine ---")
    
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    
    # 1. Recreate clean tables for network topology
    cursor.execute("DROP TABLE IF EXISTS inferred_edges;")
    cursor.execute('''
        CREATE TABLE inferred_edges (
            edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_ticker TEXT,
            target_ticker TEXT,
            weight REAL,
            edge_type TEXT,
            inferred_at TIMESTAMP
        );
    ''')
    con.commit()
    
    # 2. Master Graph Inference Query using native SQL Self-Joins
    print("[*] Calculating conversational edges using cross-ticker time-decay joins...")
    
    inference_sql = """
    INSERT INTO inferred_edges (source_ticker, target_ticker, weight, edge_type, inferred_at)
    
    -- Connection Type A: Co-occurrence in the exact same hour (Delta_t = 0, Weight = 1.0)
    SELECT 
        a.ticker AS source_ticker,
        b.ticker AS target_ticker,
        ROUND(AVG((a.hourly_volume + b.hourly_volume) * 1.0), 4) AS weight,
        'CO_OCCURRENCE' AS edge_type,
        a.metric_hour AS inferred_at
    FROM hourly_ticker_metrics a
    JOIN hourly_ticker_metrics b ON a.metric_hour = b.metric_hour AND a.ticker < b.ticker
    GROUP BY source_ticker, target_ticker, inferred_at
    
    UNION ALL
    
    -- Connection Type B: Sequential hour trailing lag (Delta_t = 1 hour, Weight decayed by e^-0.5 ~ 0.606)
    SELECT 
        a.ticker AS source_ticker,
        b.ticker AS target_ticker,
        ROUND(AVG((a.hourly_volume + b.hourly_volume) * 0.6065), 4) AS weight,
        'SEQUENTIAL_LAG' AS edge_type,
        b.metric_hour AS inferred_at
    FROM hourly_ticker_metrics a
    JOIN hourly_ticker_metrics b ON b.metric_hour = datetime(a.metric_hour, '+1 hour') AND a.ticker != b.ticker
    GROUP BY source_ticker, target_ticker, inferred_at;
    """
    
    cursor.execute(inference_sql)
    con.commit()
    print("[✔] Network topology mapped into 'inferred_edges' table.")
    
    # 3. Optimize the Graph Table for downstream metrics
    cursor.execute("CREATE INDEX idx_edges_topology ON inferred_edges(source_ticker, target_ticker, weight);")
    con.commit()
    
    # 4. Verification: Look at the highest weighted network connections
    print("\n--- Network Verification: Top Inferred Conversational Edges ---")
    cursor.execute("""
        SELECT source_ticker, target_ticker, MAX(weight), edge_type, count(*) 
        FROM inferred_edges 
        GROUP BY source_ticker, target_ticker 
        ORDER BY MAX(weight) DESC 
        LIMIT 5;
    """)
    
    results = cursor.fetchall()
    print(f"{'Source':<8} | {'Target':<8} | {'Peak Link Weight':<18} | {'Edge Type':<15} | {'Occurrences'}")
    print("-" * 65)
    for row in results:
        print(f"{row[0]:<8} | {row[1]:<8} | {row[2]:<18} | {row[3]:<15} | {row[4]}")
        
    con.close()
    print("\n[✔] Stage 4 Complete. Network topology successfully generated.")

if __name__ == "__main__":
    run_graph_inference()