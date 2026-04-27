import sys
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

from backend.yield_prediction import run_yield_prediction

result = run_yield_prediction(
    crop="rice",
    season="kharif",
    state="Karnataka",
    district="Bengaluru Urban",
    google_api_key=api_key
)
print("RESULT:", result)
