import sqlite3
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import time

# Configuration
TARGET_DAYS = 14
cutoff_ts = datetime.now(timezone.utc).timestamp() - (TARGET_DAYS * 86400)

SITEMAPS = {
    "techcrunch": "https://techcrunch.com/sitemap.xml",
    "wired": "https://www.wired.com/sitemap.xml"
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Database Configuration
db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "database", "techpulse.db"))
os.makedirs(os.path.dirname(db_path), exist_ok=True)
con = sqlite3.connect(db_path)
cursor = con.cursor()

# Initialize Database Schema
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

def parse_date(date_str):
    try:
        clean_str = date_str.strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean_str)
        return dt.timestamp(), dt
    except Exception:
        return None, None

def process_sitemap(url, source_name):
    global total_inserted
    print(f"Scanning XML Index: {url}")
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            print(f"  Failed to fetch sitemap: HTTP {response.status_code}")
            return
            
        root = ET.fromstring(response.content)
        ns = root.tag.split("}")[0] + "}" if "}" in root.tag else ""
        tag_name = root.tag.replace(ns, "")

        # Handle nested Sitemap Index files
        if tag_name == "sitemapindex":
            for sitemap in root.findall(f".//{ns}sitemap"):
                loc_node = sitemap.find(f"{ns}loc")
                lastmod_node = sitemap.find(f"{ns}lastmod")
                if loc_node is None: 
                    continue
                
                if lastmod_node is not None:
                    lastmod_ts, _ = parse_date(lastmod_node.text)
                    if lastmod_ts and lastmod_ts < cutoff_ts:
                        continue # Skip sub-sitemaps older than our target window
                
                time.sleep(0.5)
                process_sitemap(loc_node.text, source_name)

        # Handle standard URL sets containing articles
        elif tag_name == "urlset":
            for url_node in root.findall(f".//{ns}url"):
                loc_node = url_node.find(f"{ns}loc")
                lastmod_node = url_node.find(f"{ns}lastmod")
                if loc_node is None or lastmod_node is None: 
                    continue
                    
                article_url = loc_node.text
                published_ts, published_dt = parse_date(lastmod_node.text)
                
                if not published_ts or published_ts < cutoff_ts:
                    continue

                slug = [part for part in article_url.split('/') if part][-1]
                doc_id = f"news_{source_name}_{slug}"

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO documents (
                        document_id, document_type, source, parent_document_id, 
                        title, content, author, url, published_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (doc_id, "article", source_name, None, "Pending Extraction", "", source_name, article_url, published_dt.isoformat())
                )
                total_inserted += cursor.rowcount
    except Exception as e:
        print(f"  Error parsing XML node {url}: {e}")

if __name__ == "__main__":
    print("--- Starting Single-Threaded Sitemap Scraper ---")
    for source, entry_url in SITEMAPS.items():
        total_inserted = 0
        process_sitemap(entry_url, source)
        con.commit()
        print(f"Finished {source.upper()}. Queued {total_inserted} new items.")
    con.close()