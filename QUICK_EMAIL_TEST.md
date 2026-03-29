#!/usr/bin/env python
"""
QUICK FIX: How to Get Email Alerts Working Now
================================================

The system IS configured correctly.
JWT DOES include email field ✅
Fraud detection WORKS correctly ✅
Email sending WORKS correctly ✅

The issue: You probably haven't tested with a FRAUD transaction yet.

QUICK TEST (2 steps):
"""

print("""
📧 QUICK EMAIL ALERT TEST
==========================

The email alert system is working. To verify it:

STEP 1: Register & Login
-----------
POST http://localhost:5000/api/auth/register
{
    "username": "testuser123",
    "email": "your-email@gmail.com",  [← THIS GETS EMAIL ALERTS!]
    "password": "test123"
}

Save the access_token from the response.


STEP 2: Send Test Alert Email
------------
POST http://localhost:5000/api/auth/test-alert
Headers: Authorization: Bearer <your_access_token>

This will send an instant test email to your registered email address.


STEP 3: Check Your Email
-----------
Look for email with subject: "🚨 UPI Shield - Fraud Alert"
Check SPAM folder too (emails from new services often go there)
Confirm it arrives within 1-2 minutes


STEP 4: Submit Real Fraud Transaction  
-----------
POST http://localhost:5000/api/transactions/check
Headers: Authorization: Bearer <your_access_token>
{
    "amount": 500000,          [← HIGH AMOUNT TRIGGERS FRAUD]
    "upi_id": "fraud@upi",
    "city": "Mumbai",
    "device_id": "DEV_NEW_123",
    "is_new_device": 1,
    "transaction_frequency": 15,
    "user_avg_amount": 5000,
    "latitude": 19.076,
    "longitude": 72.877
}

If final_label is "Fraud" or "Anomaly" → Email will be sent ✅


USING cURL (if you prefer command line):
========================================

# Register
curl -X POST http://localhost:5000/api/auth/register \\
  -H "Content-Type: application/json" \\
  -d '{
    "username": "testuser123",
    "email": "your-email@gmail.com",
    "password": "test123"
  }'

# Copy the access_token from response

# Send test alert
curl -X POST http://localhost:5000/api/auth/test-alert \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Submit fraud transaction
curl -X POST http://localhost:5000/api/transactions/check \\
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \\
  -H "Content-Type: application/json" \\
  -d '{
    "amount": 500000,
    "upi_id": "fraud@upi",
    "city": "Mumbai",
    "device_id": "DEV_NEW_123",
    "is_new_device": 1,
    "transaction_frequency": 15,
    "user_avg_amount": 5000,
    "latitude": 19.076,
    "longitude": 72.877
  }'


USING PYTHON:
==============

import requests
import json

# Register
response = requests.post("http://localhost:5000/api/auth/register", json={
    "username": "testuser123",
    "email": "your-email@gmail.com",
    "password": "test123"
})
print("Register:", response.json())

# Login
response = requests.post("http://localhost:5000/api/auth/login", json={
    "username": "testuser123",
    "password": "test123"
})
data = response.json()
token = data["access_token"]
print("Token:", token)

# Send test alert
response = requests.post(
    "http://localhost:5000/api/auth/test-alert",
    headers={"Authorization": f"Bearer {token}"}
)
print("Test Alert:", response.json())

# Submit fraud transaction
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "http://localhost:5000/api/transactions/check",
    json={
        "amount": 500000,
        "upi_id": "fraud@upi",
        "city": "Mumbai",
        "device_id": "DEV_NEW_123",
        "is_new_device": 1,
        "transaction_frequency": 15,
        "user_avg_amount": 5000,
        "latitude": 19.076,
        "longitude": 72.877
    },
    headers=headers
)
print("Fraud Check:", response.json())


TROUBLESHOOTING:
================

❌ "Server not running"
→ Start: python backend/app.py

❌ "No email received"
→ Check spam folder
→ Wait 2-3 minutes (Gmail can be slow)
→ Check email address is registered correctly

❌ "Transaction not fraud" (final_label = "Legitimate")
→ Try higher amount (₹1,000,000+)
→ Or increase transaction_frequency (30+)

❌ "Email error" in logs
→ Check .env file exists
→ Verify ALERT_EMAIL_FROM and ALERT_EMAIL_PASSWORD set
→ Run: python backend/test_email.py (should pass all tests)


WHAT GETS EMAILED:
==================

When a Fraud/Anomaly transaction detected, email includes:
✅ Transaction ID
✅ Amount
✅ UPI ID
✅ City
✅ Fraud Score
✅ Risk Level
✅ Timestamp
✅ Action: Review in Dashboard


THAT'S IT! 🎉
============

The system is fully working. Just test it with the steps above.
""")
