import sqlite3
import os
import time
from bs4 import BeautifulSoup
from curl_cffi import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# =====================================================
# CONFIGURATION
# =====================================================
# Number of simultaneous scraping threads. 
# 10 is the sweet spot. Higher risks triggering Cloudflare IP bans.
MAX_WORKERS = 10 

db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))

def enable_wal_mode():
    """Switches SQLite to Write-Ahead Logging for better concurrency."""
    con = sqlite3.connect(db_path)
    con.execute("PRAGMA journal_mode=WAL;")
    con.close()

def fetch_and_update(item):
    """The task executed by each individual thread."""
    doc_id, url, source_name = item
    
    # Each thread needs its own database connection to avoid thread-safety crashes
    # timeout=30 tells SQLite to patiently wait in line if another thread is currently saving data
    con = sqlite3.connect(db_path, timeout=30.0)
    cursor = con.cursor()
    
    try:
        response = requests.get(url, impersonate="chrome", timeout=15)
        
        if response.status_code != 200:
            cursor.execute("""
                UPDATE documents SET title = ?, content = ? WHERE document_id = ?
            """, (f"Failed Status {response.status_code}", "Extraction Failure", doc_id))
            con.commit()
            return f"Failed: HTTP {response.status_code} -> {url}"

        soup = BeautifulSoup(response.text, 'html.parser')
        
        og_title = soup.find("meta", property="og:title")
        true_title = og_title["content"] if og_title else (soup.title.string if soup.title else "Untitled Article")
        
        article_body = soup.find("article")
        paragraphs = article_body.find_all("p") if article_body else soup.find_all("p")
        clean_content = " ".join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])

        if not clean_content or len(clean_content) < 50:
            clean_content = "Empty or minimal body content extracted."

        cursor.execute("""
            UPDATE documents SET title = ?, content = ? WHERE document_id = ?
        """, (true_title, clean_content, doc_id))
        con.commit()
        
        # A tiny delay prevents us from hammering the server too aggressively
        time.sleep(0.5)
        
        return f"Success: {true_title[:40]}..."
        
    except Exception as e:
        cursor.execute("""
            UPDATE documents SET title = ?, content = ? WHERE document_id = ?
        """, ("Error Handling Request", str(e), doc_id))
        con.commit()
        return f"Error on {url}: {e}"
        
    finally:
        con.close()

def run_multithreaded_harvester():
    enable_wal_mode()
    
    # Grab only the remaining items
    con = sqlite3.connect(db_path)
    cursor = con.cursor()
    cursor.execute("""
        SELECT document_id, url, source FROM documents 
        WHERE document_type = 'article' 
        AND (content = '' OR title = 'Pending Extraction')
    """)
    pending_items = cursor.fetchall()
    con.close()
    
    total_remaining = len(pending_items)
    if total_remaining == 0:
        print("No pending articles found. Database is fully populated.")
        return

    print(f"--- Resuming Harvester: {total_remaining} items remaining ---")
    print(f"--- Booting up {MAX_WORKERS} simultaneous threads ---")
    
    completed_count = 0
    
    # Launch the thread pool
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submit all tasks to the queue
        future_to_item = {executor.submit(fetch_and_update, item): item for item in pending_items}
        
        # Process them as they finish, regardless of order
        for future in as_completed(future_to_item):
            completed_count += 1
            try:
                result_message = future.result()
                print(f"[{completed_count}/{total_remaining}] {result_message}")
            except Exception as exc:
                print(f"[{completed_count}/{total_remaining}] Thread generated an exception: {exc}")

    print("\n--- Multithreaded Pipeline Complete ---")

if __name__ == "__main__":
    run_multithreaded_harvester()