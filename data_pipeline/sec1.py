import sqlite3
import os

# Define the database directory path
db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database"))

# Paths for the expected files
main_db_path = os.path.join(db_dir, "techpulse.db")
typo_db_raw = os.path.join(db_dir, "techpulsedb")
typo_db_ext = os.path.join(db_dir, "techpulzedb.db")

def get_db_stats(db_path):
    """Safely extracts row count and source breakdown from a given SQLite file."""
    if not os.path.exists(db_path):
        return None, "File does not exist"
    
    stats = {
        "file_size_kb": round(os.path.getsize(db_path) / 1024, 2),
        "total_rows": 0,
        "sources": {}
    }
    
    try:
        # Open in read-only mode to guarantee absolute safety
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = con.cursor()
        
        # Check if the core documents table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents';")
        if not cursor.fetchone():
            con.close()
            return stats, "Table 'documents' does not exist yet."
            
        # Get grand total
        cursor.execute("SELECT COUNT(*) FROM documents;")
        stats["total_rows"] = cursor.fetchone()[0]
        
        # Get source breakdown
        cursor.execute("SELECT source, COUNT(*) FROM documents GROUP BY source;")
        for source, count in cursor.fetchall():
            source_name = source if source else "Unknown/Null"
            stats["sources"][source_name] = count
            
        con.close()
        return stats, "Success"
    except Exception as e:
        return None, f"Error reading database: {e}"

def main():
    print("=" * 65)
    print("         TECHPULSE PIPELINE: PRE-MERGE INSPECTOR         ")
    print("=" * 65)
    print(f"Database Directory: {db_dir}\n")

    # 1. Inspect the Typo Database
    typo_path = typo_db_ext if os.path.exists(typo_db_ext) else typo_db_raw
    print("[1] CHECKING TYPO DATABASE (techpulzedb)")
    print("-" * 45)
    typo_stats, typo_status = get_db_stats(typo_path)
    
    if typo_stats:
        print(f"File Found at : {os.path.basename(typo_path)}")
        print(f"File Size     : {typo_stats['file_size_kb']} KB")
        print(f"Total Rows    : {typo_stats['total_rows']}")
        print("Source Breakdown:")
        for src, cnt in typo_stats["sources"].items():
            print(f"  - {src}: {cnt} rows")
    else:
        print(f"Status: {typo_status}")

    print("\n" + "-" * 45)

    # 2. Inspect the Main Database
    print("[2] CHECKING MAIN DATABASE (techpulse.db)")
    print("-" * 45)
    main_stats, main_status = get_db_stats(main_db_path)
    
    if main_stats:
        print(f"File Found at : {os.path.basename(main_db_path)}")
        print(f"File Size     : {main_stats['file_size_kb']} KB")
        print(f"Total Rows    : {main_stats['total_rows']}")
        print("Source Breakdown:")
        for src, cnt in main_stats["sources"].items():
            print(f"  - {src}: {cnt} rows")
    else:
        print(f"Status: {main_status}")

    print("=" * 65)
    
    # 3. Provide Actionable Guidance Contextually
    print("\n[3] NEXT STEPS SUGGESTION")
    print("-" * 45)
    if typo_stats and typo_stats["total_rows"] > 0:
        print("✔ Verified: Data exists in the typo database.")
        print("Action: Run your 'merge_pipelines.py' script to safety combine them.")
    elif main_stats and "reddit" in [s.lower() for s in main_stats["sources"].keys()]:
        print("✔ Verified: Reddit data is already sitting safely inside techpulse.db.")
        print("Action: You are clear to proceed directly to the NLP pipelines.")
    else:
        print("⚠ Notice: No mergeable rows found. Check your file locations.")
    print("=" * 65)

if __name__ == "__main__":
    main()