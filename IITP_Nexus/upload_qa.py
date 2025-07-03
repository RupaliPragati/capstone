import pandas as pd
import sqlite3

# Load and clean the CSV
df = pd.read_csv("data/qa.csv")
df["question"] = df["question"].str.strip()
df["answer"] = df["answer"].str.strip()

# Connect to DB and insert
conn = sqlite3.connect("data/data.db")
cursor = conn.cursor()
for _, row in df.iterrows():
    try:
        cursor.execute("INSERT INTO knowledge (question, answer) VALUES (?, ?)", (row["question"], row["answer"]))
    except:
        continue
conn.commit()
conn.close()
