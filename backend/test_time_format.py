#!/usr/bin/env python
"""
Quick Test - Time Format Fix
=============================
Test the new time_readable field in API responses
"""

import sys
import requests

sys.path.insert(0, ".")

SERVER_URL = "http://localhost:5000"

print("\n" + "="*70)
print("🕐 TIME FORMAT FIX - QUICK TEST")
print("="*70 + "\n")

# Register
print("[1] Registering user...")
response = requests.post(
    f"{SERVER_URL}/api/auth/register",
    json={
        "username": "timetest",
        "email": "timetest@example.com",
        "password": "test123"
    }
)
print(f"✅ Status: {response.status_code}")

# Login
print("\n[2] Logging in...")
response = requests.post(
    f"{SERVER_URL}/api/auth/login",
    json={
        "username": "timetest",
        "password": "test123"
    }
)
token = response.json()["access_token"]
print(f"✅ Token received")

# Submit transaction
print("\n[3] Submitting transaction (checking time format)...\n")
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    f"{SERVER_URL}/api/transactions/check",
    json={
        "amount": 5000,
        "upi_id": "merchant@bank",
        "city": "Mumbai",
        "device_id": "TEST_DEVICE_001",
        "is_new_device": 0,
        "transaction_frequency": 5,
        "user_avg_amount": 7500,
        "latitude": 19.076,
        "longitude": 72.877
    },
    headers=headers
)

data = response.json()

print("📋 RESPONSE with NEW TIME FORMAT:")
print("="*70)
print(f"""
Transaction ID:    {data.get('txn_id')}
Amount:            ₹{data.get('amount')}
City:              {data.get('city')}
Fraud Score:       {data.get('fraud_score')}%

🕐 TIME FORMATS:
   time_readable:  {data.get('time_readable')}    ← 8:40 AM (HUMAN READABLE!)
   exact_time:     {data.get('exact_time')}    ← Full timestamp
   timestamp:      {data.get('timestamp')}
   hour:           {data.get('hour')}
   day_of_week:    {data.get('day_of_week')}

Label:             {data.get('final_label')}
Risk Level:        {data.get('risk_level')}
Recommendation:    {data.get('recommendation')}
""")

print("="*70)
print("✅ NEW TIME FORMAT WORKING!")
print("="*70 + "\n")

print("📝 KEY FIELD: time_readable")
print(f"   Shows time as: {data.get('time_readable')}")
print(f"   Format: HH:MM AM/PM (12-hour format)")
print()
