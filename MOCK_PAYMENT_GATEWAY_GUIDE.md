# 🏦 Mock Payment Gateway - Complete Guide

## Overview

The **Mock Payment Gateway** simulates real UPI transaction processing locally. It integrates fraud detection with payment processing to demonstrate a complete end-to-end workflow.

### What It Does

```
User submits transaction
         ↓
Fraud Detection (ML Model)
         ↓
If Legitimate → Process payment via mock gateway ✅
If Fraud/Anomaly → Block transaction + Send alert ❌
         ↓
Return status + receipt
```

---

## 🚀 Quick Start

### Step 1: Start Flask Server

```bash
cd backend
python app.py
```

You should see:
```
WARNING: This is a development server. Do not use it in production.
 * Running on http://127.0.0.1:5000
 * Press CTRL+C to quit
```

### Step 2: Run Payment Tests (In another terminal)

```bash
cd backend
python test_mock_payments.py
```

Output:
```
🚀 MOCK PAYMENT GATEWAY - COMPLETE TEST SUITE 🚀

==================================================================
Step 1: Register User
==================================================================

✅ PASS | Registration | Status: 409
  (User already exists - using existing account)

==================================================================
Step 2: Login & Get Token
==================================================================

✅ PASS | Login | Token: eyJ0eXAiOiJKV1Qi...

==================================================================
Test 1: Legitimate Transaction
==================================================================

✅ PASS | Legitimate Payment | Status: SUCCESS | Amount: ₹5000
  TXN ID: TXN_A1B2C3D4E5
  Fraud Score: 2.5%
  Risk Level: Low
  Gateway Status: MOCK_ABCD1234

==================================================================
Test 2: High Amount Transaction
==================================================================

✅ PASS | Fraud Detection Working | Blocked: Fraud detected
  Fraud Score: 95.8%
  Final Label: Fraud
  Message: Your transaction has been blocked for security...

✅ TEST SUITE COMPLETE
```

---

## 📋 API Endpoints

### 1. Process Payment (Main Endpoint)

```http
POST /api/payments/process
Authorization: Bearer JWT_TOKEN
Content-Type: application/json

{
  "amount": 5000,                      // Transaction amount (₹1-₹100,000)
  "payee_upi": "merchant@bank",        // Recipient UPI ID
  "payer_upi": "user@bank",            // Sender UPI ID (optional)
  "device_id": "DEV_PHONE_001",        // Device identifier (optional)
  "is_new_device": 0,                  // 0 = known, 1 = new device
  "city": "Mumbai",                    // Transaction location
  "transaction_frequency": 5,          // Number of recent transactions
  "user_avg_amount": 7500,             // User's average transaction
  "latitude": 19.076,                  // Geolocation
  "longitude": 72.877                  // Geolocation
}
```

**Response (Legitimate):**
```json
{
  "status": "SUCCESS",
  "txn_id": "TXN_A1B2C3D4E5",
  "gateway_txn_id": "MOCK_ABC123DEF456",
  "amount": 5000,
  "payee": "merchant@bank",
  "fraud_score": 2.5,
  "risk_level": "Low",
  "timestamp": "2026-03-28T15:45:30.123456",
  "message": "Payment successful",
  "success": true,
  "receipt_url": "https://mock-gateway.local/receipt/TXN_A1B2C3D4E5"
}
```

**Response (Fraud Blocked - 403):**
```json
{
  "status": "BLOCKED",
  "reason": "Fraud detected",
  "txn_id": "TXN_X1Y2Z3A4B5",
  "amount": 500000,
  "fraud_score": 100.0,
  "risk_level": "High",
  "message": "Your transaction has been blocked for security. Email alert sent to priya@gmail.com",
  "recommendation": "Please verify your account and try again"
}
```

### 2. Get Payment Status

```http
GET /api/payments/status/<txn_id>
Authorization: Bearer JWT_TOKEN
```

Response:
```json
{
  "txn_id": "TXN_A1B2C3D4E5",
  "amount": 5000,
  "status": "SUCCESS",
  "fraud_score": 2.5,
  "final_label": "Legitimate",
  "risk_level": "Low",
  "timestamp": "2026-03-28T15:45:30",
  "gateway_status": {
    "gateway_txn_id": "MOCK_ABC123",
    "status": "SUCCESS",
    "message": "Payment successful"
  }
}
```

### 3. Get Payment History

```http
GET /api/payments/history?limit=10
Authorization: Bearer JWT_TOKEN
```

Response:
```json
{
  "transactions": [
    {
      "txn_id": "TXN_A1B2C3D4E5",
      "amount": 5000,
      "final_label": "Legitimate",
      "fraud_score": 2.5,
      "created_at": "2026-03-28 15:45:30"
    },
    ...
  ],
  "count": 5
}
```

### 4. Get Gateway Statistics

```http
GET /api/payments/gateway/stats
Authorization: Bearer JWT_TOKEN
```

Response:
```json
{
  "total_transactions": 42,
  "successful": 38,
  "failed": 2,
  "fraud_blocked": 2,
  "success_rate": "90.5%",
  "total_amount": 185500,
  "gateway_name": "MockGateway v1.0"
}
```

### 5. Get All Gateway Transactions (Debug)

```http
GET /api/payments/gateway/transactions
Authorization: Bearer JWT_TOKEN
```

Response:
```json
{
  "transactions": [
    {
      "gateway_txn_id": "MOCK_ABC123",
      "payer_upi": "priya@bank",
      "payee_upi": "merchant@bank",
      "amount": 5000,
      "status": "SUCCESS",
      "fraud_label": "Legitimate",
      "created_at": "2026-03-28T15:45:30"
    },
    ...
  ],
  "count": 42
}
```

---

## 🧪 Test Scenarios

### Scenario 1: Normal Transaction

**Setup:**
- Amount: ₹5,000 (normal)
- Device: `is_new_device: 0` (known)
- Time: 2:30 PM (normal)
- Location: Mumbai (expected)

**Expected Result:**
```
Fraud Score: ~2-5%
Status: SUCCESS ✅
```

### Scenario 2: High Amount Alert

**Setup:**
- Amount: ₹50,000 (2x average)
- Device: `is_new_device: 0` (known)
- Time: 2:30 PM (normal)
- Location: Mumbai (expected)

**Expected Result:**
```
Fraud Score: ~35-50%
Status: SUCCESS (but flagged as Medium risk)
```

### Scenario 3: Fraud - New Device + High Amount

**Setup:**
- Amount: ₹100,000 (high)
- Device: `is_new_device: 1` (NEW!) 🚨
- Time: 3:15 AM (unusual)
- Location: Delhi (different)

**Expected Result:**
```
Fraud Score: ~95-100% 🚨
Status: BLOCKED
Email Alert: SENT ✅
```

### Scenario 4: Anomaly Detection

**Setup:**
- Amount: ₹75,000 (unusual pattern)
- Device: `is_new_device: 1` (new device)
- Transaction Frequency: 50 (very high!)
- User Avg Amount: ₹3,000 (25x difference)

**Expected Result:**
```
Fraud Score: ~90%
Anomaly Score: ~85%
Status: BLOCKED
Label: Fraud
```

---

## 🔧 Using via cURL/REST Client

### Register User

```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "priya",
    "email": "priya@gmail.com",
    "password": "test123"
  }'
```

### Login

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "priya",
    "password": "test123"
  }'
```

Save the `access_token` from response.

### Process Legitimate Payment

```bash
curl -X POST http://localhost:5000/api/payments/process \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 5000,
    "payee_upi": "merchant@paytm",
    "payer_upi": "priya@bank",
    "device_id": "PHONE_001",
    "is_new_device": 0,
    "city": "Mumbai",
    "transaction_frequency": 5,
    "user_avg_amount": 7500,
    "latitude": 19.076,
    "longitude": 72.877
  }'
```

### Process High-Risk Payment (Should be Blocked)

```bash
curl -X POST http://localhost:5000/api/payments/process \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 500000,
    "payee_upi": "attacker@bank",
    "payer_upi": "priya@bank",
    "device_id": "LAPTOP_001",
    "is_new_device": 1,
    "city": "Delhi",
    "transaction_frequency": 15,
    "user_avg_amount": 7500,
    "latitude": 28.6139,
    "longitude": 77.2090
  }'
```

Response (403 Forbidden):
```json
{
  "status": "BLOCKED",
  "reason": "Fraud detected",
  "fraud_score": 100.0,
  ...
}
```

---

## 📊 Complete Workflow Example

### Step 1: Register User

```bash
POST /api/auth/register
Body: {"username": "demo", "email": "demo@test.com", "password": "test"}
Response: 201 Created
```

### Step 2: Login

```bash
POST /api/auth/login
Body: {"username": "demo", "password": "test"}
Response: {"access_token": "eyJ0eXAi..."}
```

### Step 3: Submit Legitimate Transaction

```bash
POST /api/payments/process
Headers: Authorization: Bearer eyJ0eXAi...
Body: {
  "amount": 10000,
  "payee_upi": "friend@bank",
  "is_new_device": 0,
  "city": "Mumbai"
}

Response: {
  "status": "SUCCESS",
  "txn_id": "TXN_ABCD1234",
  "fraud_score": 5.2,
  "success": true
}
```

### Step 4: Submit Suspicious Transaction

```bash
POST /api/payments/process
Headers: Authorization: Bearer eyJ0eXAi...
Body: {
  "amount": 300000,
  "payee_upi": "unknown@bank",
  "is_new_device": 1,
  "city": "Delhi",
  "latitude": 28.6139,
  "longitude": 77.2090
}

Response (403): {
  "status": "BLOCKED",
  "reason": "Fraud detected",
  "fraud_score": 99.8,
  "message": "Email alert sent to demo@test.com"
}
```

### Step 5: Check History

```bash
GET /api/payments/history
Response: {
  "transactions": [
    {"txn_id": "TXN_ABCD1234", "amount": 10000, "fraud_score": 5.2, "final_label": "Legitimate"},
    ... (fraud blocked transaction)
  ],
  "count": 2
}
```

### Step 6: View Statistics

```bash
GET /api/payments/gateway/stats
Response: {
  "total_transactions": 2,
  "successful": 1,
  "fraud_blocked": 1,
  "success_rate": "50%"
}
```

---

## 🎯 Key Features

### ✅ Fraud Detection Integration
- Runs ML model on all transactions
- Blocks fraud before payment processing
- Sends email alerts for blocked transactions

### ✅ Mock Gateway Simulation
- Simulates real payment processing
- 90% success rate (like real gateways)
- Generates unique transaction IDs
- Tracks transaction status throughout lifecycle

### ✅ Complete Audit Trail
- All transactions logged to database
- Gateway statistics tracked
- Transaction history available

### ✅ Error Handling
- Invalid UPI ID validation
- Amount range validation (₹1-₹100,000)
- Duplicate payer/payee detection

---

## 🔐 Security Features

1. **JWT Authentication**
   - All endpoints require valid JWT token
   - Token includes user email for alerts

2. **Fraud Prevention**
   - ML model blocks fraudulent transactions
   - Email alerts for suspicious activity
   - Risk level classification

3. **Data Validation**
   - Input sanitization
   - Amount boundary checks
   - UPI format validation

---

## 📈 Production Readiness

### What's Production-Ready
✅ Fraud detection ML model  
✅ Email alert system  
✅ Database transaction logging  
✅ API structure and error handling  
✅ JWT authentication  

### What Needs Real Implementation
❌ Replace MockGateway with real payment provider (Razorpay, PayU, etc.)  
❌ Add PCI-DSS compliance  
❌ Integrate with actual UPI networks  
❌ Add refund/chargeback handling  
❌ Implement settlement process  

---

## 🆘 Troubleshooting

### Problem: "Cannot connect to Flask server"
**Solution:** Start Flask first
```bash
cd backend
python app.py
```

### Problem: "No email received"
**Solution:** Check configuration
```bash
cat backend/.env | grep ALERT
# Should show Gmail credentials configured
```

### Problem: "All transactions marked as fraud"
**Solution:** Check ML model is loaded
```bash
python backend/check_fraud_engine.py
# If fails, retrain: python backend/train_model.py
```

### Problem: "Transaction ID not found in history"
**Solution:** Verify transaction was created
```bash
GET /api/payments/gateway/transactions  # See all transactions
```

---

## 📞 Next Steps

1. **Customize fraud thresholds** in `/ml/fraud_predictor.py`
2. **Add real payment gateway** - Replace MockGateway with Razorpay API
3. **Setup webhook handlers** for payment callbacks
4. **Add refund processing** for failed/disputed transactions
5. **Implement settlement** with bank partners

---

**Your system is now fully capable of simulating real transaction flows with fraud detection!** 🚀
