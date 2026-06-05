import sqlite3
import requests
import feedparser
import os
import time
from datetime import datetime, timezone

# =====================================================
# CONFIGURATION
# =====================================================

SUBREDDIT = "technology"

# The base URL for strictly chronological posts
BASE_RSS_URL = f"https://www.reddit.com/r/{SUBREDDIT}/new/.rss"
TARGET_DAYS = 30

# A custom User-Agent to avoid the generic bot filter
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 TechPulse/1.0"
}

cutoff_date = datetime.now(timezone.utc).timestamp() - (TARGET_DAYS * 86400)

# =====================================================
# DATABASE SETUP
# =====================================================

db_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "database", "techpulsedb")
)
os.makedirs(os.path.dirname(db_path), exist_ok=True)

con = sqlite3.connect(db_path)
cursor = con.cursor()

# Ensure tables exist
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
# PAGINATION ENGINE
# =====================================================

# We start with the base URL for Page 1
next_url = BASE_RSS_URL
page_number = 1
total_posts = 0
total_comments = 0
reached_cutoff = False

while next_url and not reached_cutoff:
    
    print(f"\n--- Fetching Page {page_number} ---")
    print(f"URL: {next_url}")

    try:
        response = requests.get(next_url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Network error on main feed: {e}")
        break

    feed = feedparser.parse(response.content)

    if not feed.entries:
        print("No more entries found. (Feed is empty or Reddit soft-blocked the request).")
        break

    for submission in feed.entries:
        
        # 1. Date Check
        published = submission.get("published_parsed")
        if published is None:
            continue
            
        published_ts = datetime(*published[:6], tzinfo=timezone.utc).timestamp()
        
        if published_ts < cutoff_date:
            print("\nReached 30-day cutoff date. Stopping pagination.")
            reached_cutoff = True
            break

        # 2. Extract and Store Main Post
        submission_id = submission.get("id") # This looks like 't3_xyz123'
        title = submission.get("title", "")
        author = submission.get("author", "")
        url = submission.get("link", "")
        published_at = submission.get("published", "")
        
        content = ""
        if "content" in submission:
            content = submission.content[0]["value"]
        elif "summary" in submission:
            content = submission.summary

        cursor.execute(
            """
            INSERT OR IGNORE INTO documents (
                document_id, document_type, source, parent_document_id, 
                title, content, author, url, published_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (submission_id, "submission", "reddit", None, title, content, author, url, published_at)
        )
        total_posts += cursor.rowcount

        # 3. Extract and Store Comments for this Post
        comment_rss_url = url.rstrip("/") + "/.rss"
        
        try:
            comment_response = requests.get(comment_rss_url, headers=HEADERS, timeout=30)
            comment_response.raise_for_status()
            comment_feed = feedparser.parse(comment_response.content)

            for entry in comment_feed.entries:
                comment_id = entry.get("id", "")
                
                # Filter out the main post duplicate
                if not comment_id.startswith("t1_"):
                    continue

                comment_author = entry.get("author", "")
                comment_title = entry.get("title", "Comment")
                comment_published = entry.get("updated", "")
                
                comment_content = ""
                if "content" in entry:
                    comment_content = entry.content[0]["value"]
                elif "summary" in entry:
                    comment_content = entry.summary

                comment_url = entry.links[0].get("href", "") if entry.get("links") else ""

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO documents (
                        document_id, document_type, source, parent_document_id, 
                        title, content, author, url, published_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (comment_id, "comment", "reddit", submission_id, comment_title, 
                     comment_content, comment_author, comment_url, comment_published)
                )
                total_comments += cursor.rowcount

            print(f"Stored post {submission_id} and its comments.")
            
            # MANDATORY PAUSE: If you do not pause here, Reddit will ban your IP.
            time.sleep(2)

        except Exception as e:
            print(f"Comment fetch failed for {submission_id}: {e}")

    con.commit()

    # =====================================================
    # BUILD THE NEXT PAGE URL
    # =====================================================
    if not reached_cutoff:
        # Get the ID of the very last post on this page (e.g., 't3_1tu7q5z')
        last_id = feed.entries[-1].get("id")
        
        if not last_id:
            break
            
        # Append ?after=t3_xxx to the base RSS URL to get the next page
        next_url = f"{BASE_RSS_URL}?after={last_id}"
        page_number += 1
        
        # Extra pause before turning the page
        time.sleep(3)

con.close()
print(f"\nFetch complete! Stored {total_posts} posts and {total_comments} comments.")