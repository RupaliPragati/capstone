import sqlite3

# Connect to (or create) the database
conn = sqlite3.connect("data/data.db")
cursor = conn.cursor()

# Create the knowledge table
cursor.execute("""
CREATE TABLE IF NOT EXISTS knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT UNIQUE,
    answer TEXT
)
""")

# Optional: Initial seed data
qa_seed = [
    ("What is IIT Patna?", "IIT Patna is an Institute of National Importance located in Bihar, India."),
    ("Where is IIT Patna located?", "IIT Patna is located in Bihta, approximately 35 km from Patna city."),
    ("How can I reach IIT Patna?", "You can reach IIT Patna via train to Bihta station or from Patna airport."),
    ("What are the departments in IIT Patna?", "IIT Patna has departments like CSE, EE, ME, CE, Maths, Physics, Chemistry, and HSS."),
    ("Who is the director of IIT Patna?", "The current director of IIT Patna is Prof. T.N. Singh.")
]

for q, a in qa_seed:
    try:
        cursor.execute("INSERT INTO knowledge (question, answer) VALUES (?, ?)", (q, a))
    except:
        continue  # Skip if already exists

conn.commit()
conn.close()

print("✅ data.db created and initialized.")
