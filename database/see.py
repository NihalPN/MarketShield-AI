import sqlite3

con = sqlite3.connect("techpulsedb")
cursor = con.cursor()

cursor.execute("""
SELECT COUNT(*)
FROM documents
""")

print("Documents:", cursor.fetchone()[0])

con.close()