import sqlite3
import os

os.makedirs("data", exist_ok=True)

conn = sqlite3.connect("data/data.db")
cursor = conn.cursor()

# Drop old table if exists
cursor.execute("DROP TABLE IF EXISTS qa")

# Create fresh table
cursor.execute('''
    CREATE TABLE qa (
        question TEXT PRIMARY KEY,
        answer   TEXT NOT NULL
    )
''')

# Add questions & answers
data = {
    "what is iit patna": "IIT Patna is one of the premier institutes of technology in India, located in Bihta, Bihar.",
    "what courses are offered": "IIT Patna offers B.Tech, M.Tech, M.Sc, and Ph.D programs in various disciplines including CSE, ECE, ME, CE, Chemical, Physics, Mathematics, and more.",
    "what is the fee structure": "The fee structure includes tuition fees, hostel charges, and other administrative fees. Visit the official IIT Patna website for the latest breakdown.",
    "where is the hostel located": "The hostels are located within the IIT Patna campus in Bihta with modern amenities for students.",
    "who is the director": "The current Director of IIT Patna is Prof. T.N. Singh.",
    "what are hybrid courses": "Hybrid courses at IIT Patna combine online and offline learning to provide flexibility and practical exposure.",
    "what is moodle": "Moodle is the learning management system (LMS) used by IIT Patna for course content, assignments, and interactions.",
    "how to reach iit patna": "IIT Patna is located about 35 km from Patna Junction. You can take a taxi, train to Bihta, or a direct bus service.",
    "what is the campus area": "The IIT Patna campus in Bihta spans over 500 acres and includes academic buildings, hostels, and labs."
}

for q, a in data.items():
    cursor.execute("INSERT INTO qa (question, answer) VALUES (?, ?)", (q.lower(), a))

conn.commit()
conn.close()

print("✅ Database created successfully.")
