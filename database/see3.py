import sqlite3
import os

# Dynamically locate the database file relative to this script
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

def run_query(cursor, query, params=()):
    """Helper function to execute a query safely."""
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"\n[!] Database Error: {e}")
        return []

def main():
    if not os.path.exists(db_path):
        print(f"[!] Error: Database not found at {db_path}")
        print("Please ensure your sitemap scraper or harvester has run at least once.")
        return

    # Connect with a generous timeout in case the NLP pipeline is actively writing
    con = sqlite3.connect(db_path, timeout=30.0)
    cursor = con.cursor()
    
    print("=" * 60)
    print("          TECHPULSE DATA PIPELINE INSIGHTS          ")
    print("=" * 60)

    # -------------------------------------------------
    # METRIC 1: Pipeline Processing Progress
    # -------------------------------------------------
    print("\n[1] PIPELINE PROCESSING PROGRESS")
    print("-" * 40)
    progress_query = """
        SELECT nlp_processed, COUNT(*) as total_documents
        FROM documents 
        GROUP BY nlp_processed;
    """
    progress_rows = run_query(cursor, progress_query)
    
    if progress_rows:
        print(f"{'Status':<15} | {'Article Count':<15}")
        print("-" * 35)
        for row in progress_rows:
            status = "Processed (1)" if row[0] == 1 else "Pending (0)"
            print(f"{status:<15} | {row[1]:<15}")
    else:
        print("No documents found in the database.")

    # -------------------------------------------------
    # METRIC 2: Top 20 Most Mentioned Companies (ORG)
    # -------------------------------------------------
    print("\n[2] TOP 20 MOST MENTIONED COMPANIES (ORG)")
    print("-" * 50)
    org_query = """
        SELECT entity_name, COUNT(*) as mention_count
        FROM document_entities
        WHERE entity_type = 'ORG'
        GROUP BY entity_name
        ORDER BY mention_count DESC
        LIMIT 20;
    """
    org_rows = run_query(cursor, org_query)
    
    if org_rows:
        print(f"{'Rank':<5} | {'Company Name':<30} | {'Mentions':<10}")
        print("-" * 52)
        for idx, row in enumerate(org_rows, 1):
            print(f"{idx:<5} | {row[0]:<30} | {row[1]:<10}")
    else:
        print("No organization entities found yet. Run nlp_pipeline.py to extract data.")

    # -------------------------------------------------
    # METRIC 3: Top 15 Trending Products (PRODUCT)
    # -------------------------------------------------
    print("\n[3] TOP 15 TRENDING PRODUCTS")
    print("-" * 50)
    product_query = """
        SELECT entity_name, COUNT(*) as mention_count
        FROM document_entities
        WHERE entity_type = 'PRODUCT'
        GROUP BY entity_name
        ORDER BY mention_count DESC
        LIMIT 15;
    """
    product_rows = run_query(cursor, product_query)
    
    if product_rows:
        print(f"{'Rank':<5} | {'Product Name':<30} | {'Mentions':<10}")
        print("-" * 52)
        for idx, row in enumerate(product_rows, 1):
            print(f"{idx:<5} | {row[0]:<30} | {row[1]:<10}")
    else:
        print("No product entities found yet. Run nlp_pipeline.py to extract data.")

    # -------------------------------------------------
    # METRIC 4: Real-Time Data Density & Source Breakdown
    # -------------------------------------------------
    print("\n[4] DATA CORAL DISTRIBUTION (BY SOURCE)")
    print("-" * 50)
    source_query = """
        SELECT source, COUNT(*) as total, 
               SUM(CASE WHEN nlp_processed = 1 THEN 1 ELSE 0 END) as processed
        FROM documents
        GROUP BY source;
    """
    source_rows = run_query(cursor, source_query)
    
    if source_rows:
        print(f"{'Source':<15} | {'Total Extracted':<15} | {'NLP Completed':<15}")
        print("-" * 51)
        for row in source_rows:
            source_name = row[0] if row[0] else "Unknown"
            print(f"{source_name:<15} | {row[1]:<15} | {row[2]:<15}")
    else:
        print("No source breakdown metadata available.")

    print("\n" + "=" * 60)
    con.close()

if __name__ == "__main__":
    main()