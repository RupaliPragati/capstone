import sqlite3

# Connect to (or create) the database
conn = sqlite3.connect("data/data.db")
cursor = conn.cursor()

# Create table if it doesn't exist
cursor.execute("""
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print(" Database and table created successfully.")
