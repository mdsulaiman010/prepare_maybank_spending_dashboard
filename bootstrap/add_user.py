import sqlite3

# Connect to DB
conn = sqlite3.connect("secrets.db")
cursor = conn.cursor()

# Insert new 
cursor.execute("""
INSERT INTO user_tokens (username, client_id, refresh_token)
VALUES (?, ?, ?)
""", (
    "user@email.com",
    "ms_graph_prod",
    "USER_REFRESH_TOKEN"
))

conn.commit()
conn.close()

print("✅ User token added")