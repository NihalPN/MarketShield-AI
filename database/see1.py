import sqlite3

con = sqlite3.connect("techpulsedb")
cursor = con.cursor()

cursor.execute("""
SELECT
    parent_document_id,
    COUNT(*) as comments
FROM documents
WHERE document_type='comment'
GROUP BY parent_document_id
ORDER BY comments DESC
LIMIT 25
""")

for row in cursor.fetchall():
    print(row)

con.close()