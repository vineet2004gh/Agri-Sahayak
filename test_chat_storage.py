
import requests
import sqlite3
import time

BASE_URL = "http://localhost:8000"
DB_PATH = "backend/documents.db"
USER_ID = "369562d1-7899-4e4f-9115-c33ca1742b54"

def get_chat_count():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM conversations WHERE user_id = ?", (USER_ID,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def test_chat_storage():
    print(f"Testing Chat Storage for user {USER_ID}...")
    
    initial_count = get_chat_count()
    print(f"Initial chat count: {initial_count}")
    
    url = f"{BASE_URL}/ask"
    payload = {
        "user_id": USER_ID,
        "question": "TEST_STORAGE_QUESTION: How do I store chat history?"
    }
    
    try:
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            print("Chat request successful")
            time.sleep(1) # Wait for potential async write if any (though it's sync in code)
            final_count = get_chat_count()
            print(f"Final chat count: {final_count}")
            
            if final_count > initial_count:
                print("SUCCESS: Chat history stored!")
            else:
                print("FAILURE: Chat history count did not increase.")
        else:
            print(f"Request failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat_storage()
