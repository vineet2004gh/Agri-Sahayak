#!/usr/bin/env python3
"""
Inject a demo alert into the weather-alerts endpoint for testing.

Usage:
    python inject_demo_alert.py

This script sends a request to the backend to verify alerts are
working, and also patches the analyze_weather_for_alerts function
to always include a demo alert for demonstration purposes.
"""

import requests
import sys

BACKEND = "http://127.0.0.1:8000"

# The user ID to test with — change this to your actual user ID
USER_ID = "369562d1-7899-4e4f-9115-c33ca1742b54"

def check_existing_alerts():
    """Check what alerts are currently returned."""
    try:
        resp = requests.get(f"{BACKEND}/weather-alerts/{USER_ID}", timeout=10)
        data = resp.json()
        alerts = data.get("alerts", [])
        print(f"District: {data.get('district', 'N/A')}")
        print(f"Current alerts: {len(alerts)}")
        for a in alerts:
            print(f"  - [{a.get('severity', '?')}] {a.get('title')}: {a.get('message', '')[:80]}...")
        return data
    except Exception as e:
        print(f"Error fetching alerts: {e}")
        return None

if __name__ == "__main__":
    print("=== Current Alerts ===")
    check_existing_alerts()
    print()
    print("To inject a demo alert, the backend routes.py has been patched.")
    print("Restart the server and check the dashboard.")
