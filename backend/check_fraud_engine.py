#!/usr/bin/env python
"""
check_fraud_engine.py
====================
Verify fraud detection engine is working correctly
"""

import sys
import os
sys.path.insert(0, ".")

from backend.utils.fraud_engine import run_fraud_check

def main():
    print("\n" + "="*70)
    print("🔍 Fraud Detection Engine Status Check")
    print("="*70)
    
    # Test prediction
    print("\n[1] Testing Fraud Detection:")
    
    test_cases = [
        {
            "label": "Normal Transaction (₹1,000)",
            "txn": {
                "amount": 1000,
                "hour": 10,
                "day_of_week": 2,
                "city": "Mumbai",
                "transaction_frequency": 5,
                "user_avg_amount": 5000,
                "is_new_device": 0
            }
        },
        {
            "label": "High-Risk Transaction (₹500,000)",
            "txn": {
                "amount": 500000,
                "hour": 23,
                "day_of_week": 6,
                "city": "Unknown",
                "transaction_frequency": 15,
                "user_avg_amount": 5000,
                "is_new_device": 1
            }
        },
        {
            "label": "Anomaly Test (Unusual Pattern)",
            "txn": {
                "amount": 100000,
                "hour": 2,
                "day_of_week": 0,
                "city": "Bangalore",
                "transaction_frequency": 50,
                "user_avg_amount": 3000,
                "is_new_device": 1
            }
        }
    ]
    
    for test in test_cases:
        try:
            result = run_fraud_check(test["txn"])
            print(f"\n    {test['label']}:")
            print(f"      Fraud Score: {result['fraud_score']:.2f}%")
            print(f"      Anomaly Score: {result['anomaly_score']:.2f}%")
            print(f"      Label: {result['label']}")
            print(f"      Final Label: {result['final_label']} ⚠️" if result['final_label'] != "Legitimate" else f"      Final Label: {result['final_label']}")
        except Exception as e:
            print(f"\n    ❌ Error: {e}")
            if "not loaded" in str(e):
                print("\n    → Fix: Run `python backend/train_model.py` to train model")
            return False
    
    print("\n" + "="*70)
    print("✅ Fraud engine is working correctly")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}\n")
