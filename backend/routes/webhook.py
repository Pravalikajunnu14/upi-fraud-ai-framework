"""
webhook.py  – /api/webhook/*
Razorpay-compatible webhook endpoint for real-time UPI fraud detection.
Accepts transaction payloads from payment gateways, runs fraud check, returns result.
"""

import hmac
import hashlib
import datetime
import random
from flask import Blueprint, request, jsonify
from typing import Tuple, Dict, Any
from config import Config
from utils.fraud_engine import run_fraud_check
from utils.logger import logger

webhook_bp = Blueprint("webhook", __name__, url_prefix="/api/webhook")

CITY_COORDS = {
    "Mumbai": (19.0760, 72.8777), "Delhi": (28.6139, 77.2090),
    "Bangalore": (12.9716, 77.5946), "Hyderabad": (17.3850, 78.4867),
    "Chennai": (13.0827, 80.2707), "Kolkata": (22.5726, 88.3639),
    "Pune": (18.5204, 73.8567), "Jaipur": (26.9124, 75.7873),
    "Ahmedabad": (23.0225, 72.5714), "Surat": (21.1702, 72.8311),
}


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify Razorpay HMAC-SHA256 webhook signature."""
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


@webhook_bp.route("/transaction", methods=["POST"])
def transaction_webhook() -> Tuple[Dict[str, Any], int]:
    """
    Accepts real Razorpay / bank webhook payload and runs fraud detection.

    Expected JSON body (Razorpay payment.captured format or custom):
    {
        "payment_id": "pay_xxx",
        "amount": 50000,          # in paise (Razorpay) OR rupees
        "currency": "INR",
        "contact": "+91xxxxxxxxxx",
        "email": "user@example.com",
        "description": "UPI payment",
        "upi_id": "merchant@okhdfc",     # optional
        "city": "Mumbai",                 # optional
        "device_id": "DEV_1234"          # optional
    }

    Razorpay webhook signature passed as header:
        X-Razorpay-Signature: <hmac-sha256>
    """
    raw_body  = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature", "")

    # Verify signature if secret is configured (skip in dev mode)
    webhook_secret = getattr(Config, "RAZORPAY_WEBHOOK_SECRET", "")
    if webhook_secret and not _verify_signature(raw_body, signature, webhook_secret):
        logger.warning("Webhook: invalid signature rejected")
        return jsonify({"error": "Invalid webhook signature"}), 401

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    # Normalise amount: Razorpay sends in paise (÷100 → rupees)
    raw_amount = data.get("amount", 0)
    amount     = float(raw_amount) / 100 if raw_amount > 1000 else float(raw_amount)
    amount     = max(1.0, amount)

    city = data.get("city", "Mumbai")
    lat, lng = CITY_COORDS.get(city, (19.076, 72.877))
    now  = datetime.datetime.utcnow()

    txn_payload = {
        "amount":                amount,
        "hour":                  now.hour,
        "day_of_week":           now.weekday(),
        "city":                  city,
        "latitude":              round(lat + random.uniform(-0.2, 0.2), 6),
        "longitude":             round(lng + random.uniform(-0.2, 0.2), 6),
        "device_id":             data.get("device_id", f"DEV_{random.randint(1000,9999)}"),
        "transaction_frequency": int(data.get("transaction_frequency", 1)),
        "user_avg_amount":       float(data.get("user_avg_amount", amount)),
        "is_new_device":         int(data.get("is_new_device", 0)),
    }

    try:
        result = run_fraud_check(txn_payload)
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 503

    upi_id    = data.get("upi_id", "")
    payment_id = data.get("payment_id", f"PAY_{random.randint(100000,999999)}")

    logger.info(
        f"Webhook TXN {payment_id}: INR {amount} from {city} -> "
        f"{result['label']} (score={result['fraud_score']}%)"
    )

    return jsonify({
        "payment_id":   payment_id,
        "upi_id":       upi_id,
        "amount":       amount,
        "city":         city,
        "fraud_score":  result["fraud_score"],
        "label":        result["label"],
        "risk_level":   result["risk_level"],
        "action":       "block" if result["label"] == "Fraud" else "allow",
        "timestamp":    now.isoformat(),
    })


@webhook_bp.route("/health", methods=["GET"])
def webhook_health() -> Tuple[Dict[str, Any], int]:
    """Webhook endpoint health check — no auth required."""
    from utils.fraud_engine import cache_stats
    return jsonify({
        "status":      "ok",
        "endpoint":    "/api/webhook/transaction",
        "cache":       cache_stats(),
        "timestamp":   datetime.datetime.utcnow().isoformat(),
    })
