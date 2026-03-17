"""
transactions.py  – /api/transactions/*
Transaction submission, fraud check, history, and blocking.
"""

import uuid
import datetime
import random
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt

from database.db import query, execute
from utils.fraud_engine import run_fraud_check
from utils.logger import logger
from utils.email_alert import send_fraud_alert
import threading

txn_bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")

CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777), "Delhi": (28.6139, 77.2090),
    "Bangalore": (12.9716, 77.5946), "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707), "Kolkata": (22.5726, 88.3639),
    "Pune": (18.5204, 73.8567), "Jaipur": (26.9124, 75.7873),
    "Ahmedabad": (23.0225, 72.5714), "Surat": (21.1702, 72.8311),
    "Lucknow": (26.8467, 80.9462), "Kanpur": (26.4499, 80.3319),
    "Nagpur": (21.1458, 79.0882), "Patna": (25.5941, 85.1376),
    "Bhopal": (23.2599, 77.4126),
}


# ─── Check / Predict ──────────────────────────────────────────────────────────

@txn_bp.route("/check", methods=["POST"])
@jwt_required()
def check_transaction():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    # Required field
    amount = data.get("amount")
    if amount is None:
        return jsonify({"error": "'amount' is required"}), 400

    upi_id = data.get("upi_id", "").strip()

    city   = data.get("city", "Mumbai")
    lat, lng = CITY_COORDS.get(city, (19.076, 72.877))
    lat += random.uniform(-0.2, 0.2)
    lng += random.uniform(-0.2, 0.2)

    now = datetime.datetime.utcnow()

    # Helper functions to avoid int(None) / float(None) crashes:
    def safe_int(val, default):
        try:
            return int(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    def safe_float(val, default):
        try:
            return float(val) if val is not None else default
        except (ValueError, TypeError):
            return default

    txn_payload = {
        "amount":                safe_float(amount, 0.0),
        "hour":                  safe_int(data.get("hour"), now.hour),
        "day_of_week":           safe_int(data.get("day_of_week"), now.weekday()),
        "city":                  city,
        "latitude":              round(lat, 6),
        "longitude":             round(lng, 6),
        "device_id":             data.get("device_id", "") or f"DEV_{random.randint(1000,9999)}",
        "transaction_frequency": safe_int(data.get("transaction_frequency"), 1),
        "user_avg_amount":       safe_float(data.get("user_avg_amount"), float(amount)),
        "is_new_device":         safe_int(data.get("is_new_device"), 0),
    }

    try:
        result = run_fraud_check(txn_payload)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    txn_id      = f"TXN{uuid.uuid4().hex[:8].upper()}"
    final_label = result.get("final_label", result["label"])
    anomaly_score  = result.get("anomaly_score", 0.0)
    is_novel       = result.get("is_novel", False)
    combined_score = result.get("combined_score", result["fraud_score"])

    # Store in DB
    execute(
        """INSERT INTO transactions
           (txn_id, user_id, upi_id, amount, city, latitude, longitude, device_id,
            hour, day_of_week, transaction_frequency, user_avg_amount,
            is_new_device, fraud_score, label, risk_level)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            txn_id, user_id, upi_id, txn_payload["amount"], txn_payload["city"],
            txn_payload["latitude"], txn_payload["longitude"],
            txn_payload["device_id"], txn_payload["hour"],
            txn_payload["day_of_week"], txn_payload["transaction_frequency"],
            txn_payload["user_avg_amount"], txn_payload["is_new_device"],
            result["fraud_score"], final_label, result["risk_level"]
        )
    )

    # Create alert for Fraud OR Anomaly transactions
    if final_label in ("Fraud", "Anomaly"):
        execute(
            "INSERT INTO fraud_alerts (txn_id, fraud_score, risk_level) VALUES (?,?,?)",
            (txn_id, combined_score, result["risk_level"])
        )
        # Send real-time email alert for both Fraud and Anomaly
        claims     = get_jwt()
        user_email = claims.get("email", "") if claims else ""
        
        # Send synchronously to prevent WSGI from killing the background thread
        send_fraud_alert(
            txn_id, txn_payload["amount"], txn_payload["city"],
            upi_id, result["fraud_score"], result["risk_level"],
            user_email,
            combined_score=combined_score,
            alert_type=final_label
        )


    logger.info(
        f"Transaction {txn_id}: INR {amount} from {city} -> "
        f"{final_label} (fraud={result['fraud_score']}%, "
        f"anomaly={anomaly_score}%, combined={combined_score}%)"
    )

    # Build recommendation message
    if final_label == "Fraud":
        recommendation = "[BLOCKED] Transaction blocked - fraud detected!"
    elif final_label == "Anomaly":
        recommendation = (
            "[REVIEW] Unknown transaction pattern detected — "
            "flagged for manual review."
        )
    else:
        recommendation = "[SAFE] Transaction is safe to proceed."

    return jsonify({
        "txn_id":         txn_id,
        "amount":         txn_payload["amount"],
        "city":           txn_payload["city"],
        # Supervised model output
        "fraud_score":    result["fraud_score"],
        "label":          result["label"],
        "risk_level":     result["risk_level"],
        # Anomaly detection output
        "anomaly_score":  anomaly_score,
        "is_novel":       is_novel,
        # Fused output
        "combined_score": combined_score,
        "final_label":    final_label,
        "recommendation": recommendation,
        "timestamp":      now.isoformat(),
    })


# ─── List transactions ────────────────────────────────────────────────────────

@txn_bp.route("/", methods=["GET"])
@jwt_required()
def list_transactions():
    page  = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))
    offset = (page - 1) * limit

    rows = query(
        "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    total = query("SELECT COUNT(*) as cnt FROM transactions", one=True)["cnt"]
    return jsonify({"transactions": rows, "total": total, "page": page})


# ─── Block a transaction ──────────────────────────────────────────────────────

@txn_bp.route("/block/<txn_id>", methods=["POST"])
@jwt_required()
def block_transaction(txn_id):
    user_id  = int(get_jwt_identity())
    claims   = get_jwt()
    username = claims.get("username", str(user_id))
    txn = query("SELECT * FROM transactions WHERE txn_id = ?", (txn_id,), one=True)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404

    execute("UPDATE transactions SET is_blocked = 1 WHERE txn_id = ?", (txn_id,))
    execute(
        "INSERT INTO audit_logs (user_id, action, details) VALUES (?,?,?)",
        (user_id, "block_transaction", f"Blocked txn {txn_id}")
    )
    logger.warning(f"Transaction BLOCKED: {txn_id} by user {username}")
    return jsonify({"message": f"Transaction {txn_id} has been blocked.", "txn_id": txn_id})


# ─── Get single transaction ───────────────────────────────────────────────────

@txn_bp.route("/<txn_id>", methods=["GET"])
@jwt_required()
def get_transaction(txn_id):
    txn = query("SELECT * FROM transactions WHERE txn_id = ?", (txn_id,), one=True)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify(txn)
