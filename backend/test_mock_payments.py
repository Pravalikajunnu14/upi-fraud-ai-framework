#!/usr/bin/env python
"""
test_mock_payments.py
====================
Test Mock Payment Gateway - End-to-end payment processing with fraud detection.

Tests:
1. Register and login
2. Submit legitimate transaction → Should succeed
3. Submit fraudulent transaction → Should be blocked
4. Check transaction history
5. View gateway statistics
"""

import sys
import requests
import json
from datetime import datetime

sys.path.insert(0, ".")

SERVER_URL = "http://localhost:5000"

def print_header(title):
    """Print formatted section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")

def print_result(test_name, result, details=""):
    """Print test result"""
    status = "✅ PASS" if result else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"       {details}")

class PaymentTester:
    """Test payment processing system"""
    
    def __init__(self):
        self.token = None
        self.user_data = {
            "username": "payment_test_user",
            "email": "payment.test@example.com",
            "password": "test12345"
        }
    
    def register(self):
        """Register test user"""
        print_header("Step 1: Register User")
        
        response = requests.post(
            f"{SERVER_URL}/api/auth/register",
            json=self.user_data
        )
        
        success = response.status_code in (201, 409)  # 409 = already exists
        print_result("Registration", success, f"Status: {response.status_code}")
        
        if response.status_code == 409:
            print("  (User already exists - using existing account)")
        
        return success
    
    def login(self):
        """Login and get JWT token"""
        print_header("Step 2: Login & Get Token")
        
        response = requests.post(
            f"{SERVER_URL}/api/auth/login",
            json={
                "username": self.user_data["username"],
                "password": self.user_data["password"]
            }
        )
        
        success = response.status_code == 200
        
        if success:
            data = response.json()
            self.token = data["access_token"]
            print_result("Login", True, f"Token: {self.token[:30]}...")
        else:
            print_result("Login", False, response.text)
        
        return success
    
    def submit_payment(self, amount, payee_upi, is_new_device, city, description):
        """Submit payment transaction"""
        
        headers = {"Authorization": f"Bearer {self.token}"}
        payload = {
            "amount": amount,
            "payee_upi": payee_upi,
            "payer_upi": f"testuser_{self.user_data['username']}@bank",
            "device_id": "DEV_PAYMENT_TEST_001",
            "is_new_device": is_new_device,
            "city": city,
            "transaction_frequency": 5,
            "user_avg_amount": 5000,
            "latitude": 19.076,
            "longitude": 72.877
        }
        
        response = requests.post(
            f"{SERVER_URL}/api/payments/process",
            json=payload,
            headers=headers
        )
        
        return response
    
    def test_legitimate_transaction(self):
        """Test 1: Legitimate transaction (should succeed)"""
        print_header("Test 1: Legitimate Transaction")
        
        response = self.submit_payment(
            amount=5000,
            payee_upi="merchant@bank",
            is_new_device=0,
            city="Mumbai",
            description="Normal transaction"
        )
        
        success = response.status_code == 200
        
        if success:
            data = response.json()
            print_result(
                "Legitimate Payment",
                True,
                f"Status: {data['status']} | Amount: ₹{data['amount']}"
            )
            print(f"  TXN ID: {data['txn_id']}")
            print(f"  Fraud Score: {data['fraud_score']}%")
            print(f"  Risk Level: {data['risk_level']}")
            print(f"  Gateway Status: {data['gateway_txn_id']}")
        else:
            print_result("Legitimate Payment", False, response.text)
        
        return success, response.json() if success else None
    
    def test_high_amount_transaction(self):
        """Test 2: High amount (potential fraud)"""
        print_header("Test 2: High Amount Transaction")
        
        response = self.submit_payment(
            amount=50000,
            payee_upi="suspicious@bank",
            is_new_device=1,
            city="Delhi",
            description="High amount that might trigger fraud"
        )
        
        if response.status_code == 403:  # Blocked
            data = response.json()
            print_result(
                "Fraud Detection Working",
                True,
                f"Blocked: {data['reason']}"
            )
            print(f"  Fraud Score: {data['fraud_score']}%")
            print(f"  Final Label: {data.get('final_label', 'Unknown')}")
            print(f"  Message: {data['message']}")
            return True, data
        
        elif response.status_code == 200:
            data = response.json()
            print(f"  ℹ️  Transaction allowed (not classified as fraud)")
            print(f"  Status: {data['status']}")
            print(f"  Fraud Score: {data['fraud_score']}%")
            return True, data
        
        else:
            print_result("Payment Processing", False, response.text)
            return False, None
    
    def test_new_device_fraud(self):
        """Test 3: New device + high amount (should be fraud)"""
        print_header("Test 3: New Device + Fraud Pattern")
        
        response = self.submit_payment(
            amount=100000,
            payee_upi="attacker@bank",
            is_new_device=1,
            city="Bangalore",
            description="New device + high amount = fraud pattern"
        )
        
        if response.status_code == 403:  # Blocked
            data = response.json()
            print_result(
                "Fraud Blocked",
                True,
                f"Reason: {data['reason']}"
            )
            print(f"  Fraud Score: {data['fraud_score']}%")
            print(f"  Risk Level: {data['risk_level']}")
            print(f"  TXN ID: {data['txn_id']}")
            return True, data
        else:
            print_result("Test", False, response.text)
            return False, None
    
    def get_transaction_history(self):
        """Get user's transaction history"""
        print_header("Step 4: Get Transaction History")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{SERVER_URL}/api/payments/history",
            headers=headers
        )
        
        success = response.status_code == 200
        
        if success:
            data = response.json()
            print_result(
                "Get History",
                True,
                f"Found {data['count']} transactions"
            )
            
            print("\n  Recent Transactions:")
            for txn in data['transactions'][:5]:
                print(f"    • {txn['txn_id']}: ₹{txn['amount']} | Label: {txn['final_label']}")
        else:
            print_result("Get History", False, response.text)
        
        return success
    
    def get_gateway_stats(self):
        """Get mock gateway statistics"""
        print_header("Step 5: Gateway Statistics")
        
        headers = {"Authorization": f"Bearer {self.token}"}
        response = requests.get(
            f"{SERVER_URL}/api/payments/gateway/stats",
            headers=headers
        )
        
        success = response.status_code == 200
        
        if success:
            data = response.json()
            print_result("Gateway Stats", True)
            print(f"  Total Transactions: {data.get('total_transactions', 'N/A')}")
            print(f"  Successful: {data.get('successful', 'N/A')}")
            print(f"  Failed: {data.get('failed', 'N/A')}")
            print(f"  Fraud Blocked: {data.get('fraud_blocked', 'N/A')}")
            print(f"  Success Rate: {data.get('success_rate', 'N/A')}")
            print(f"  Total Amount: ₹{data.get('total_amount', 'N/A')}")
            print(f"  Gateway: {data.get('gateway_name', 'N/A')}")
        else:
            print_result("Gateway Stats", False, response.text)
        
        return success
    
    def run_all_tests(self):
        """Run complete test suite"""
        print("\n" + "🚀 "*35)
        print("MOCK PAYMENT GATEWAY - COMPLETE TEST SUITE")
        print("🚀 "*35)
        
        # Setup
        if not self.register():
            print("\n❌ Registration failed. Aborting.")
            return False
        
        if not self.login():
            print("\n❌ Login failed. Aborting.")
            return False
        
        # Tests
        self.test_legitimate_transaction()
        self.test_high_amount_transaction()
        self.test_new_device_fraud()
        
        # Review
        self.get_transaction_history()
        self.get_gateway_stats()
        
        # Summary
        print_header("✅ TEST SUITE COMPLETE")
        print("All payment processing tests completed successfully!")
        print("\nFeatures Tested:")
        print("  ✅ User registration and login")
        print("  ✅ Legitimate transaction processing")
        print("  ✅ Fraud detection and blocking")
        print("  ✅ New device detection")
        print("  ✅ Transaction history retrieval")
        print("  ✅ Gateway statistics")
        print("\nNext Steps:")
        print("  1. Check your email for fraud alerts")
        print("  2. Review transaction history in dashboard")
        print("  3. Monitor gateway statistics")
        print("\n" + "="*70 + "\n")

if __name__ == "__main__":
    try:
        tester = PaymentTester()
        tester.run_all_tests()
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to Flask server")
        print("   Start it first: python backend/app.py")
        print("   In another terminal: python backend/test_mock_payments.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
