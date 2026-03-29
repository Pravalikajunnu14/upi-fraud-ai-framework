#!/usr/bin/env python
"""
Test real-time format - verify hour matches system time
"""
import requests
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Current system time
now = datetime.now()
current_hour = now.hour
current_hour_12 = current_hour % 12 or 12
current_minute = now.strftime("%M")
current_am_pm = "am" if current_hour < 12 else "pm"

print("=" * 70)
print("🕐 REAL-TIME FORMAT - INSTANT CHECK")
print("=" * 70)
print()
print(f"📱 SYSTEM TIME: {current_hour_12}.{current_minute} {current_am_pm} (24-hr: {current_hour}:{current_minute})")
print()

# Login
print("[1] Logging in...")
login_res = requests.post(
    f"{BASE_URL}/api/auth/login",
    json={"username": "timetest", "password": "test123"}
)
token = login_res.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}
print("✅ Logged in\n")

# Submit transaction
print("[2] Submitting transaction...")
res = requests.post(
    f"{BASE_URL}/api/transactions/check",
    json={"amount": 5000},
    headers=headers
)
data = res.json()

time_readable = data.get("time_readable", "")
hour_response = data.get("hour", -1)

print()
print(f"🔔 API RESPONSE:")
print(f"   time_readable: {time_readable}")
print(f"   hour (24-hr): {hour_response}")
print()

# Verify
if hour_response == current_hour:
    print(f"✅ PERFECT! Hour matches: {hour_response} = {current_hour}")
else:
    print(f"❌ MISMATCH! Response hour {hour_response} vs System hour {current_hour}")
    print(f"   (System is 3 hours ahead: {current_hour} - 3 = {current_hour - 3 if current_hour >= 3 else 24 + current_hour - 3})")

print()
print("=" * 70)
