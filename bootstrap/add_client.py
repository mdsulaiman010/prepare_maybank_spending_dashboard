import sqlite3


conn = sqlite3.connect("secrets.db")
cursor = conn.cursor()

cursor.execute("""
INSERT INTO oauth_clients (id, client_id, client_secret, provider)
VALUES (?, ?, ?, ?)
""", (
    "ms_graph_prod",
    "YOUR_CLIENT_ID",
    "YOUR_CLIENT_SECRET",
    "microsoft"
))

conn.commit()
conn.close()

print("✅ OAuth client added")