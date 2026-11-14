import sys
sys.path.insert(0, "backend")

from app.db import connect

conn = connect()
cur = conn.cursor()

cur.execute("""
    SELECT
        current_database(),
        current_schema(),
        inet_server_addr(),
        inet_server_port()
""")

print("\nDATABASE CONNECTION:")
print(cur.fetchone())

cur.execute("""
    SELECT table_name
    FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name
""")

print("\nDATABASE TABLES:")
for row in cur.fetchall():
    print(row["table_name"])

conn.close()
