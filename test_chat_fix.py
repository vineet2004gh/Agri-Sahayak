
import requests
import json
import time

BASE_URL = "http://localhost:8000"
# Use a new user ID to ensure default settings (English)
USER_ID = "test_user_english_v1" 

def test_chat():
    print(f"Testing Chat RAG for user {USER_ID}...")
    
    url = f"{BASE_URL}/ask"
    payload = {
        "user_id": USER_ID,
        "question": "What are the key policies for rice farming?"
    }
    
    start = time.time()
    try:
        print("\n--- Sending Request ---")
        resp = requests.post(url, json=payload)
        if resp.status_code == 200:
            data = resp.json()
            print("\n--- Response Received ---")
            answer = data.get('answer', '')
            print("Full Answer:\n" + "="*40)
            print(answer[:500] + "..." if len(answer) > 500 else answer)
            print("="*40)
            
            # Verification check
            if "[{'type': 'text'" in answer:
                print("FAILURE: Raw JSON still present!")
            else:
                print("SUCCESS: Clean text received.")
                
            print(f"Time taken: {time.time() - start:.2f}s")
        else:
            print(f"Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat()
