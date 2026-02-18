
import requests
import json
import time

BASE_URL = "http://localhost:8000"
USER_ID = "369562d1-7899-4e4f-9115-c33ca1742b54" 

def test_chat():
    print(f"Testing Chat RAG for user {USER_ID}...")
    
    url = f"{BASE_URL}/ask"
    # Ask a question likely to trigger the policy/structured response format
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
            print(answer)
            print("="*40)
            print(f"Time taken: {time.time() - start:.2f}s")
        else:
            print(f"Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_chat()
