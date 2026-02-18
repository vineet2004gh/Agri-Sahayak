
import sqlite3
import os

DB_PATH = "backend/documents.db"

def check_user():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT id, name, phone_number, state, district FROM users")
        users = cursor.fetchall()
        print(f"Found {len(users)} users:")
        for u in users:
            print(f"  ID: {u[0]}, Name: {u[1]}, Phone: {u[2]}, State: {u[3]}, District: {u[4]}")
            
    except Exception as e:
        print(f"Error querying database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_user()
