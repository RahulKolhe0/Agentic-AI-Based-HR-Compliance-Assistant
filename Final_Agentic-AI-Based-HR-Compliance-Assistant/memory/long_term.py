import sqlite3
import os

DB_PATH = "memory/chat_memory.db"

def init_db():
    os.makedirs("memory", exist_ok=True)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id TEXT PRIMARY KEY,
            question TEXT,
            answer TEXT
        )
    """)
    con.commit()
    con.close()


def save(entry):
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO memory VALUES (?,?,?)",
        (entry["id"], entry["question"], entry["answer"])
    )
    con.commit()
    con.close()


# ✅ ADD THIS FUNCTION
def search(query):
    """Search similar past questions from SQLite"""

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        SELECT question, answer
        FROM memory
        WHERE question LIKE ?
        ORDER BY rowid DESC
        LIMIT 3
    """, (f"%{query}%",))

    results = cur.fetchall()
    con.close()

    return results
