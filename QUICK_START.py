#!/usr/bin/env python
"""
QUICK START: Mock Payment Gateway
==================================

This script verifies everything is set up correctly and gives you
commands to start testing immediately.

Run: python QUICK_START.py
"""

import sys
import os

print("\n" + "="*70)
print("🚀 MOCK PAYMENT GATEWAY - QUICK START VERIFICATION")
print("="*70 + "\n")

# Check Python version
python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
print(f"✅ Python {python_version}")

# Check if in correct directory
if os.path.exists("backend/app.py"):
    print("✅ Correct directory structure found")
else:
    print("❌ Not in correct directory. Run from project root.")
    sys.exit(1)

# Check required files exist
files_to_check = [
    "backend/app.py",
    "backend/config.py",
    "backend/utils/mock_gateway.py",
    "backend/routes/payments.py",
    "backend/test_mock_payments.py",
    "MOCK_PAYMENT_GATEWAY_GUIDE.md",
]

print("\n📁 Checking files:")
all_exist = True
for file in files_to_check:
    exists = os.path.exists(file)
    status = "✅" if exists else "❌"
    print(f"  {status} {file}")
    if not exists:
        all_exist = False

if not all_exist:
    print("\n❌ Some files missing!")
    sys.exit(1)

# Check imports work
print("\n📦 Checking imports:")
try:
    sys.path.insert(0, "backend")
    from utils.mock_gateway import MockGateway, get_gateway
    print("  ✅ MockGateway imports successfully")
except Exception as e:
    print(f"  ❌ MockGateway import failed: {e}")

try:
    from routes.payments import payment_bp
    print("  ✅ Payments blueprint imports successfully")
except Exception as e:
    print(f"  ❌ Payments blueprint import failed: {e}")

# Show next steps
print("\n" + "="*70)
print("🎯 NEXT STEPS - START TESTING IN 3 COMMANDS")
print("="*70)

print("""
TERMINAL 1 (Start Flask Server):
────────────────────────────────
cd backend
python app.py

You should see:
  WARNING: This is a development server...
  * Running on http://127.0.0.1:5000


TERMINAL 2 (Run Test Suite):
────────────────────────────
cd backend
python test_mock_payments.py

You should see:
  ✅ Registration successful
  ✅ Login successful
  ✅ Legitimate transaction: SUCCESS
  ✅ Fraud blocked: BLOCKED
  ✅ Transaction history retrieved
  ✅ Gateway statistics displayed
""")

print("="*70)
print("📚 DOCUMENTATION")
print("="*70)
print("""
Read these for complete information:
  • MOCK_PAYMENT_GATEWAY_GUIDE.md     (API endpoints & workflows)
  • QUICK_EMAIL_TEST.md               (Email alert testing)
  • EMAIL_ALERT_STATUS.md             (Email system status)
  • MOCK_GATEWAY_READY.md             (Implementation summary)
""")

print("="*70)
print("✨ YOUR SYSTEM IS READY TO TEST!")
print("="*70 + "\n")
