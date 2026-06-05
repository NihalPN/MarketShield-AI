import sqlite3
import requests
import feedparser
import os
import time

# ==========================
# DATABASE
# ==========================

db_path = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "database",
        "techpulsedb"
    )
)

con = sqlite3.connect(db_path)
cursor = con.cursor()

# ==========================
# HEADERS
# ==========================

headers = {
    "User-Agent": "TechPulseBot/1.0"
}

# ==========================
# SUBREDDIT RSS
# ==========================

rss_url = "https://old.reddit.com/r/technology/.rss"

response = requests.get(
    rss_url,
    headers=headers,
    timeout=30
)

response.raise_for_status()

feed = feedparser.parse(response.content)

print(f"Found {len(feed.entries)} submissions")

# ==========================
# PROCESS SUBMISSIONS
# ==========================

for submission in feed.entries:

    submission_id = submission.get("id")

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
            document_id,
            document_type,
            source,
            parent_document_id,
            title,
            content,
            author,
            url,
            published_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            submission_id,
            "submission",
            "reddit",
            None,
            title,
            content,
            author,
            url,
            published_at
        )
    )

    print(f"Stored submission: {submission_id}")

    # ====================================
    # FETCH COMMENT RSS
    # ====================================

    comment_rss_url = url.rstrip("/") + "/.rss"

    try:

        comment_response = requests.get(
            comment_rss_url,
            headers=headers,
            timeout=30
        )

        comment_response.raise_for_status()

        comment_feed = feedparser.parse(
            comment_response.content
        )

        # Skip first entry (submission)
        for entry in comment_feed.entries:

            comment_id = entry.get("id", "")

            # Only comments
            if not comment_id.startswith("t1_"):
                continue

            comment_author = entry.get(
                "author",
                ""
            )

            comment_title = entry.get(
                "title",
                ""
            )

            comment_content = ""

            if "content" in entry:
                comment_content = (
                    entry.content[0]["value"]
                )

            elif "summary" in entry:
                comment_content = (
                    entry.summary
                )

            comment_url = ""

            if entry.get("links"):
                comment_url = (
                    entry.links[0].get(
                        "href",
                        ""
                    )
                )

            comment_published = entry.get(
                "updated",
                ""
            )

            cursor.execute(
                """
                INSERT OR IGNORE INTO documents (
                    document_id,
                    document_type,
                    source,
                    parent_document_id,
                    title,
                    content,
                    author,
                    url,
                    published_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    comment_id,
                    "comment",
                    "reddit",
                    submission_id,
                    comment_title,
                    comment_content,
                    comment_author,
                    comment_url,
                    comment_published
                )
            )

        print(
            f"Stored comments for {submission_id}"
        )

        time.sleep(1)

    except Exception as e:

        print(
            f"Comment fetch failed for "
            f"{submission_id}: {e}"
        )

# ==========================
# FINISH
# ==========================

con.commit()
con.close()

print("Reddit fetch complete")