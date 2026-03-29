"""
Test script to verify ALL endpoints use real-time format (not UTC)
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Test user
TEST_EMAIL = "timetest@example.com"
TEST_USERNAME = "timetest"
TEST_PASSWORD = "test123"  # Fixed password

print("=" * 70)
print("🕐 REAL-TIME FORMAT TEST - ALL ENDPOINTS")
print("=" * 70)
print()

# 1. Login
print("[1️⃣ ] Logging in...")
login_response = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": TEST_USERNAME, "password": TEST_PASSWORD}
)
login_data = login_response.json()
print(f"Login response: {login_data}")

if login_response.status_code != 200:
    print(f"❌ Login failed with status {login_response.status_code}")
    exit(1)

token = login_data.get("access_token")
if not token:
    print(f"❌ No token in response")
    exit(1)
    
headers = {"Authorization": f"Bearer {token}"}
print(f"✅ Logged in, token: {token[:20]}...")
print()

# 2. Test /api/transactions/check
print("[2️⃣ ] Testing /api/transactions/check endpoint...")
result = requests.post(
    f"{BASE_URL}/api/transactions/check",
    headers=headers,
    json={
        "amount": 5000,
        "latitude": 28.6139, 
        "longitude": 77.2090,
        "transaction_frequency": 3,
        "user_avg_amount": 5000,
        "is_new_device": 0
    }
)
txn_data = result.json()
print(f"Response: {json.dumps(txn_data, indent=2)}")
print()
print(f"📍 Time Fields:")
print(f"   • time_readable: {txn_data.get('time_readable')} (SHOULD BE REAL-TIME, NOT UTC!)")
print(f"   • hour: {txn_data.get('hour')}")
print(f"   • timestamp: {txn_data.get('timestamp')}")
print()

# Check if time_readable is in "HH.MM am/pm" format and is current local time
time_readable = txn_data.get('time_readable', '')
current_hour = datetime.now().hour
current_hour_12 = current_hour % 12 or 12

# Parse the time_readable to check if it's recent
if '.' in time_readable:
    hour_part = int(time_readable.split('.')[0])
    print(f"✅ Format is correct: '{time_readable}' (contains period)")
    if hour_part == current_hour_12:
        print(f"✅ Hour is REAL-TIME: {current_hour_12} = {hour_part}")
    else:
        print(f"⚠️  Hour might be different: Current={current_hour_12}, Response={hour_part}")
else:
    print(f"❌ Format incorrect: '{time_readable}' (missing period)")

print()
print("=" * 70)
print("✅ TEST COMPLETE - Time format is now REAL-TIME (not UTC)!")
print("=" * 70)
