#!/usr/bin/env python
"""
test_fraud_alert.py
===================
Tests fraud detection and email alerts with known fraud patterns.
Submit high-risk transactions to trigger fraud alerts.
"""

import sys
import requests
import json

sys.path.insert(0, ".")

# Server configuration
SERVER_URL = "http://localhost:5000"
TEST_USER = {
    "username": "testuser",
    "password": "test123"
}

def login():
    """Login and get JWT token"""
    print("\n[1] Logging in...")
    
    response = requests.post(
        f"{SERVER_URL}/api/auth/register",
        json={
            "username": TEST_USER["username"],
            "email": "test@example.com",
            "password": TEST_USER["password"]
        }
    )
    
    if response.status_code != 201 and "already exists" not in response.text:
        print(f"Register error: {response.text}")
    
    response = requests.post(
        f"{SERVER_URL}/api/auth/login",
        json=TEST_USER
    )
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.text}")
        return None
    
    data = response.json()
    token = data.get("access_token")
    print(f"✅ Logged in. Token: {token[:20]}...")
    return token

def submit_transaction(token, amount, upi_id, city, device_id, print_details=True):
    """Submit a transaction and return the result"""
    
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "amount": amount,
        "upi_id": upi_id,
        "city": city,
        "device_id": device_id,
        "is_new_device": 1,
        "transaction_frequency": 5,
        "user_avg_amount": 5000,
        "latitude": 19.0760,
        "longitude": 72.8777
    }
    
    response = requests.post(
        f"{SERVER_URL}/api/transactions/check",
        json=payload,
        headers=headers
    )
    
    if response.status_code != 200:
        print(f"❌ Transaction failed: {response.text}")
        return None
    
    data = response.json()
    
    if print_details:
        print(f"\n   Amount: ₹{amount}")
        print(f"   UPI: {upi_id}")
        print(f"   City: {city}")
        print(f"   Fraud Score: {data.get('fraud_score')}%")
        print(f"   Label: {data.get('final_label')}")
        print(f"   Risk: {data.get('risk_level')}")
        print(f"   TXN ID: {data.get('txn_id')}")
    
    return data

def test_fraud_scenarios():
    """Test multiple fraud scenarios"""
    
    print("\n" + "=" * 70)
    print("📧 FRAUD ALERT TEST - Testing Email Notifications")
    print("=" * 70)
    
    # Login
    token = login()
    if not token:
        return False
    
    # Test scenarios
    scenarios = [
        {
            "name": "Extremely High Amount",
            "amount": 500000,
            "upi_id": "fraudster@bank",
            "city": "Mumbai",
            "device_id": "DEV_FRAUD_001"
        },
        {
            "name": "Suspicious Pattern (New Device + High Freq)",
            "amount": 50000,
            "upi_id": "suspicious@upi",
            "city": "Delhi",
            "device_id": "DEV_NEW_DEVICE_123"
        },
        {
            "name": "Unusual Location + Different Device",
            "amount": 100000,
            "upi_id": "anomaly@bank",
            "city": "Bangalore",
            "device_id": "DEV_UNKNOWN_789"
        }
    ]
    
    print("\n[2] Submitting Test Transactions...")
    print("=" * 70)
    
    fraud_detected = False
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n[Test {i}] {scenario['name']}")
        print("-" * 70)
        
        result = submit_transaction(
            token,
            scenario["amount"],
            scenario["upi_id"],
            scenario["city"],
            scenario["device_id"],
            print_details=True
        )
        
        if result:
            if result.get("final_label") in ("Fraud", "Anomaly"):
                print(f"✅ {result.get('final_label')} detected!")
                print(f"🔔 Email alert should be sent to: pravalikajunnu14@gmail.com")
                fraud_detected = True
            else:
                print(f"⚠️  Transaction classified as: {result.get('final_label')}")
    
    print("\n" + "=" * 70)
    if fraud_detected:
        print("✅ Fraud/Anomaly detected! Checking for email alerts...")
        print("\n📧 Email alerts should have been sent:")
        print("   → Check your inbox for UPI Shield alerts")
        print("   → Check spam/promotions folder")
        print("   → Wait 1-2 minutes for delivery")
    else:
        print("⚠️  No fraud/anomaly detected in test scenarios")
        print("   Try:")
        print("   - Submit transaction with even higher amount (₹1000000+)")
        print("   - Check ML model is loaded correctly")
        print("   → python backend/train_model.py  (to retrain model)")
    
    print("\n" + "=" * 70 + "\n")
    
    return fraud_detected

if __name__ == "__main__":
    try:
        test_fraud_scenarios()
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to Flask server")
        print("   Start it first: python backend/app.py")
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
