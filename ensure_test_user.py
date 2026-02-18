
import sqlite3
import uuid

DB_PATH = "backend/documents.db"
USER_ID = "test_user_english_v1"

def ensure_user():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE id = ?", (USER_ID,))
    if cursor.fetchone():
        print(f"User {USER_ID} already exists. Updating language to English.")
        cursor.execute("UPDATE users SET language = 'en' WHERE id = ?", (USER_ID,))
    else:
        print(f"Creating user {USER_ID}...")
        cursor.execute(
            "INSERT INTO users (id, name, email, phone_number, language, crop, district, state) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (USER_ID, "Test User", "test@example.com", "9999999999", "en", "Wheat", "Test District", "Test State")
        )
    
    conn.commit()
    conn.close()
    print("User ensured.")

if __name__ == "__main__":
    ensure_user()
