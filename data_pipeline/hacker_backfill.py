import sqlite3
import requests
import os
import time
from datetime import datetime, timezone

# =====================================================
# CONFIGURATION
# =====================================================

TARGET_DAYS = 14
cutoff_ts = int(datetime.now(timezone.utc).timestamp() - (TARGET_DAYS * 86400))

# API Endpoints
ALGOLIA_BASE = "https://hn.algolia.com/api/v1"
FIREBASE_BASE = "https://hacker-news.firebaseio.com/v0"

HEADERS = {
    "User-Agent": "TechPulse_Data_Engine/1.0 (Research Project)"
}

# =====================================================
# DATABASE SETUP
# =====================================================

db_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db")
)
os.makedirs(os.path.dirname(db_path), exist_ok=True)

con = sqlite3.connect(db_path)
cursor = con.cursor()

# Ensure schema matches our multi-source design
cursor.execute('''
    CREATE TABLE IF NOT EXISTS documents (
        document_id TEXT PRIMARY KEY,
        document_type TEXT,
        source TEXT,
        parent_document_id TEXT,
        title TEXT,
        content TEXT,
        author TEXT,
        url TEXT,
        published_at TEXT,
        scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
''')
con.commit()

# =====================================================
# ENGINE 1: ALGOLIA BULK BACKFILLER
# =====================================================

def run_algolia_backfill():
    print(f"--- Starting Algolia Bulk Backfill (Last {TARGET_DAYS} Days) ---")
    
    page = 0
    total_inserted = 0
    reached_limit = False
    
    # We loop through Algolia's pages until we hit our timestamp cutoff
    while not reached_limit:
        print(f"Fetching Algolia Page {page}...")
        
        # search_by_date sorts strictly chronological (newest first)
        url = f"{ALGOLIA_BASE}/search_by_date?tags=story&hitsPerPage=100&page={page}"
        
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"Algolia API Error: {response.status_code}")
            break
            
        data = response.json()
        hits = data.get("hits", [])
        
        if not hits:
            break
            
        for hit in hits:
            created_at_ts = hit.get("created_at_i")
            
            if created_at_ts < cutoff_ts:
                print("\nReached timestamp cutoff. Backfill complete.")
                reached_limit = True
                break
                
            doc_id = f"hn_{hit.get('objectID')}"
            title = hit.get("title", "")
            author = hit.get("author", "")
            url_link = hit.get("url", f"https://news.ycombinator.com/item?id={hit.get('objectID')}")
            published_at = hit.get("created_at") # ISO8601 string
            
            cursor.execute(
                """
                INSERT OR IGNORE INTO documents (
                    document_id, document_type, source, parent_document_id, 
                    title, content, author, url, published_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (doc_id, "submission", "hackernews", None, title, "", author, url_link, published_at)
            )
            total_inserted += cursor.rowcount
            
        con.commit()
        
        # Algolia caps standard pagination at 1000 items (10 pages of 100)
        # To bypass this for massive datasets, you dynamically change the cutoff_ts 
        # based on the last item, but for a standard 14-day portfolio pull, this is sufficient.
        if data.get("nbPages") <= page + 1:
            break
            
        page += 1
        time.sleep(1) # Polite rate limiting
        
    print(f"Algolia Backfill complete. Inserted {total_inserted} historical stories.")

# =====================================================
# ENGINE 2: FIREBASE REALTIME LISTENER
# =====================================================

def run_firebase_realtime(poll_interval_seconds=60):
    print("--- Starting Firebase Real-time Poller ---")
    print("Press Ctrl+C to stop.\n")
    
    # We track the last max item to only fetch strictly new nodes
    last_max_item = None
    
    try:
        while True:
            # 1. Get the absolute latest ID generated on Hacker News
            max_resp = requests.get(f"{FIREBASE_BASE}/maxitem.json", timeout=10)
            current_max_item = max_resp.json()
            
            if last_max_item is None:
                # First run, establish baseline, jump back 50 items to prime the pump
                last_max_item = current_max_item - 50 
                
            if current_max_item > last_max_item:
                print(f"Found new items: {last_max_item + 1} to {current_max_item}")
                
                # Fetch every new item sequentially
                for item_id in range(last_max_item + 1, current_max_item + 1):
                    item_resp = requests.get(f"{FIREBASE_BASE}/item/{item_id}.json", timeout=10)
                    
                    if item_resp.status_code != 200:
                        continue
                        
                    item = item_resp.json()
                    
                    # Some items are deleted or dead; ignore them
                    if not item or item.get("deleted") or item.get("dead"):
                        continue
                        
                    # Normalize HN schema to TechPulse schema
                    doc_id = f"hn_{item.get('id')}"
                    item_type = item.get("type") # 'story', 'comment', 'poll'
                    author = item.get("by", "[deleted]")
                    published_at = datetime.fromtimestamp(item.get("time"), tz=timezone.utc).isoformat()
                    content = item.get("text", "")
                    
                    parent_id = f"hn_{item.get('parent')}" if item.get("parent") else None
                    
                    # If it's a story, it has a title and a url
                    title = item.get("title", "Comment")
                    url_link = item.get("url", f"https://news.ycombinator.com/item?id={item.get('id')}")
                    
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO documents (
                            document_id, document_type, source, parent_document_id, 
                            title, content, author, url, published_at
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (doc_id, item_type, "hackernews", parent_id, title, content, author, url_link, published_at)
                    )
                
                con.commit()
                last_max_item = current_max_item
                
            # Sleep until the next polling cycle
            time.sleep(poll_interval_seconds)
            
    except KeyboardInterrupt:
        print("\nReal-time polling stopped by user.")

# =====================================================
# EXECUTION ROUTER
# =====================================================

if __name__ == "__main__":
    print("Select Mode:")
    print("1: Bulk Backfill (Algolia API)")
    print("2: Real-time Live Stream (Firebase API)")
    
    choice = input("\nEnter 1 or 2: ")
    
    if choice == "1":
        run_algolia_backfill()
    elif choice == "2":
        run_firebase_realtime(poll_interval_seconds=30)
    else:
        print("Invalid choice.")
        
    con.close()