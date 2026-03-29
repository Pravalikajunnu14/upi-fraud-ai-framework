"""
payments.py – /api/payments/*
Mock payment processing routes.

This demonstrates how to integrate the fraud detection system with a real gateway.
Currently uses MockGateway for testing local transactions end-to-end.
"""

from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from typing import Tuple, Dict, Any

from database.db import query, execute
from utils.fraud_engine import run_fraud_check
from utils.mock_gateway import get_gateway
from utils.logger import logger
from utils.email_alert import send_fraud_alert
import threading
import datetime

payment_bp = Blueprint("payments", __name__, url_prefix="/api/payments")


@payment_bp.route("/process", methods=["POST"])
@jwt_required()
def process_payment() -> Tuple[Dict[str, Any], int]:
    """
    Process a complete payment transaction with fraud detection.
    
    This endpoint:
    1. Checks transaction for fraud
    2. Blocks if fraud detected
    3. Processes payment via mock gateway if legitimate
    4. Sends confirmation/alert emails
    5. Logs everything
    
    Request body:
        amount (required): Transaction amount in INR
        payee_upi (required): Recipient's UPI ID
        payer_upi (required): Sender's UPI ID (from user)
        device_id (optional): Device identifier
        is_new_device (optional): 0 or 1
        city (optional): Transaction location
        
    Returns:
        JSON with payment status and details
    """
    
    user_id = int(get_jwt_identity())
    claims = get_jwt()
    user_email = claims.get("email", "")
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400
    
    # ─── Parse request ────────────────────────────────────────────────────
    amount = float(data.get("amount", 0))
    payee_upi = data.get("payee_upi", "").strip()
    payer_upi = data.get("payer_upi", "").strip() or f"user_{user_id}@bank"
    device_id = data.get("device_id", "")
    is_new_device = int(data.get("is_new_device", 0))
    city = data.get("city", "Mumbai")
    
    # Validate
    if amount <= 0 or amount > 100000:
        return jsonify({
            "error": "Invalid amount",
            "details": "Amount must be between ₹1 and ₹100,000"
        }), 400
    
    if not payee_upi or "@" not in payee_upi:
        return jsonify({"error": "Invalid payee UPI ID"}), 400
    
    # ─── Get CURRENT REAL-TIME (Local Time) ─────────────────────────────
    now = datetime.datetime.now()  # ← Real-time local time (not UTC!)
    hour = now.hour
    day_of_week = now.weekday()
    timestamp = now.isoformat()
    # Time format: 8.40 am (with period and lowercase) - REAL-TIME
    hour_12 = now.hour % 12 or 12
    minute = now.strftime("%M")
    am_pm = "am" if now.hour < 12 else "pm"
    time_readable = f"{hour_12}.{minute} {am_pm}"  # Format: 8.40 am (REAL-TIME)
    
    # ─── Run fraud detection ──────────────────────────────────────────────
    fraud_check = run_fraud_check({
        "amount": amount,
        "hour": hour,
        "day_of_week": day_of_week,
        "city": city,
        "is_new_device": is_new_device,
        "transaction_frequency": data.get("transaction_frequency", 1),
        "user_avg_amount": data.get("user_avg_amount", amount),
        "latitude": data.get("latitude", 19.076),
        "longitude": data.get("longitude", 72.877),
    })
    
    fraud_score = fraud_check["fraud_score"]
    final_label = fraud_check["final_label"]
    risk_level = fraud_check["risk_level"]
    
    # ─── Generate transaction ID ─────────────────────────────────────────
    import uuid
    txn_id = f"TXN_{uuid.uuid4().hex[:10].upper()}"
    
    # ─── Log to database ─────────────────────────────────────────────────
    try:
        execute(
            """
            INSERT INTO transactions (
                user_id, txn_id, amount, upi_id, city,
                fraud_score, final_label, risk_level, is_new_device,
                device_id, timestamp, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id, txn_id, amount, payee_upi, city,
                fraud_score, final_label, risk_level, is_new_device,
                device_id, timestamp, now.strftime("%Y-%m-%d %H:%M:%S")
            )
        )
    except Exception as e:
        logger.error(f"Failed to log transaction: {e}")
    
    # ─── Step 1: Check if fraud ───────────────────────────────────────
    if final_label in ("Fraud", "Anomaly"):
        logger.warning(f"[FRAUD_BLOCKED] {final_label} transaction: {txn_id}")
        
        # Send alert email
        if user_email:
            threading.Thread(
                target=send_fraud_alert,
                args=(txn_id, amount, city, payee_upi, fraud_score, risk_level, user_email),
                kwargs={"combined_score": fraud_check.get("combined_score", fraud_score), "alert_type": final_label}
            ).start()
        
        return jsonify({
            "status": "BLOCKED",
            "reason": f"{final_label} detected",
            "txn_id": txn_id,
            "amount": amount,
            "fraud_score": fraud_score,
            "risk_level": risk_level,
            "timestamp": timestamp,
            "time_readable": time_readable,  # Time in 8:40 AM format
            "message": f"Your transaction has been blocked for security. We detected {final_label.lower()} patterns. Email alert sent to {user_email}",
            "recommendation": "Please verify your account and try again"
        }), 403
    
    # ─── Step 2: Process with mock gateway ────────────────────────────
    gateway = get_gateway()
    
    gateway_result = gateway.process_payment(
        payer_upi=payer_upi,
        payee_upi=payee_upi,
        amount=amount,
        fraud_label=final_label,
        transaction_id=txn_id,
        metadata={
            "device_id": device_id,
            "is_new_device": is_new_device,
            "city": city,
            "fraud_score": fraud_score,
            "risk_level": risk_level
        }
    )
    
    # ─── Step 3: Update transaction status ────────────────────────────
    try:
        execute(
            "UPDATE transactions SET status = ? WHERE txn_id = ?",
            (gateway_result["status"], txn_id)
        )
    except Exception as e:
        logger.error(f"Failed to update transaction status: {e}")
    
    # ─── Step 4: Send confirmation email ──────────────────────────────
    if gateway_result["success"] and user_email:
        logger.info(f"[PAYMENT_SUCCESS] {txn_id}: {amount} to {payee_upi}")
        
        # Could send success email here
        # threading.Thread(
        #     target=send_success_email,
        #     args=(txn_id, amount, payee_upi, user_email)
        # ).start()
    
    # ─── Return response ──────────────────────────────────────────────
    return jsonify({
        "status": gateway_result["status"],
        "txn_id": txn_id,
        "gateway_txn_id": gateway_result["gateway_txn_id"],
        "amount": amount,
        "payee": payee_upi,
        "fraud_score": fraud_score,
        "risk_level": risk_level,
        "timestamp": timestamp,
        "time_readable": time_readable,  # Time in 8:40 AM format
        "message": gateway_result["message"],
        "success": gateway_result.get("success", False),
        "receipt_url": gateway_result.get("receipt_url")
    }), 200


@payment_bp.route("/status/<txn_id>", methods=["GET"])
@jwt_required()
def get_payment_status(txn_id: str) -> Tuple[Dict[str, Any], int]:
    """Get payment transaction status"""
    
    user_id = int(get_jwt_identity())
    
    # Check if transaction belongs to user
    txn = query(
        "SELECT * FROM transactions WHERE txn_id = ? AND user_id = ?",
        (txn_id, user_id),
        one=True
    )
    
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
    
    # Get gateway status
    gateway = get_gateway()
    gateway_status = gateway.get_transaction_status(txn_id)
    
    return jsonify({
        "txn_id": txn_id,
        "amount": txn["amount"],
        "status": txn.get("status", "UNKNOWN"),
        "fraud_score": txn["fraud_score"],
        "final_label": txn["final_label"],
        "risk_level": txn["risk_level"],
        "timestamp": txn["timestamp"],
        "gateway_status": gateway_status["status"],
        "message": gateway_status["message"]
    }), 200


@payment_bp.route("/history", methods=["GET"])
@jwt_required()
def get_payment_history() -> Tuple[Dict[str, Any], int]:
    """Get user's payment history"""
    
    user_id = int(get_jwt_identity())
    limit = request.args.get("limit", 10, type=int)
    
    transactions = query(
        "SELECT * FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
        (user_id, limit)
    )
    
    return jsonify({
        "transactions": [dict(t) for t in transactions],
        "count": len(transactions)
    }), 200


@payment_bp.route("/gateway/stats", methods=["GET"])
@jwt_required()
def get_gateway_stats() -> Tuple[Dict[str, Any], int]:
    """Get mock gateway statistics (for testing/debugging)"""
    
    gateway = get_gateway()
    stats = gateway.get_statistics()
    
    return jsonify(stats), 200


@payment_bp.route("/gateway/transactions", methods=["GET"])
@jwt_required()
def get_gateway_transactions() -> Tuple[Dict[str, Any], int]:
    """Get all transactions from mock gateway (for testing/debugging)"""
    
    gateway = get_gateway()
    all_txns = gateway.get_all_transactions(limit=50)
    
    return jsonify({
        "transactions": all_txns,
        "count": len(all_txns)
    }), 200
