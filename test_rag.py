
import sys
import os
import asyncio
from dotenv import load_dotenv

# Add current dir to path
sys.path.append(os.getcwd())
load_dotenv()

# Set env vars if missing (mocking provided ones to ensuring they are present)
# But valid ones are needed for actual API calls.

try:
    from backend.voice import _answer_with_rag
    # Mock database fetching if needed, but let's try direct import first 
    # assuming backend.database connects to sqlite:///backend/documents.db
    # We might need to adjust DB path in backend/database.py if it uses relative path.
    # backend/voice.py:32 -> DATABASE_URL = "sqlite:///backend/documents.db" (in alerter)
    # let's check backend/database.py if we can (I haven't read it yet, but it's imported)
    
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

USER_ID = "369562d1-7899-4e4f-9115-c33ca1742b54" # Vineet Jain
QUESTION = "What is the best time to sow wheat?"

import time

def test_rag():
    print(f"Testing RAG for user {USER_ID}...")
    
    # Run 1: Cold start
    start = time.time()
    try:
        print("\n--- Run 1 (Cold Start) ---")
        answer = _answer_with_rag(USER_ID, QUESTION)
        print(f"Answer: {answer[:100]}...")
        print(f"Time taken: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"Run 1 Failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # Run 2: Warm start
    start = time.time()
    try:
        print("\n--- Run 2 (Warm Start) ---")
        answer = _answer_with_rag(USER_ID, "How much fertilizer?")
        print(f"Answer: {answer[:100]}...")
        print(f"Time taken: {time.time() - start:.2f}s")
    except Exception as e:
        print(f"Run 2 Failed: {e}")

if __name__ == "__main__":
    test_rag()
