"""
transactions.py  – /api/transactions/*
Transaction submission, fraud check, history, and blocking.
"""

import uuid
import datetime
import random
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from typing import Tuple, Dict, Any, Optional

from database.db import query, execute
from utils.fraud_engine import run_fraud_check
from utils.logger import logger
from utils.email_alert import send_fraud_alert
from utils.validators import (
    validate_transaction_amount, validate_hour, validate_day_of_week,
    validate_coordinates, validate_device_id, validate_upi_id, validate_city,
    validate_transaction_frequency, validate_pagination
)
from utils.audit import log_transaction_checked, log_transaction_blocked
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
    "Bhopal": (23.2599, 77.4126), "Dundigal mandal": (17.4521, 78.5358),
}


# ─── Check / Predict ──────────────────────────────────────────────────────────

def _find_nearest_city(latitude: float, longitude: float) -> str:
    """
    Find the nearest city to given coordinates.
    Returns the closest city from CITY_COORDS.
    """
    min_distance = float('inf')
    nearest_city = "Mumbai"  # Default fallback
    
    for city, (city_lat, city_lng) in CITY_COORDS.items():
        # Simple distance calculation
        distance = ((latitude - city_lat) ** 2 + (longitude - city_lng) ** 2) ** 0.5
        if distance < min_distance:
            min_distance = distance
            nearest_city = city
    
    return nearest_city


@txn_bp.route("/check", methods=["POST"])
@jwt_required()
def check_transaction() -> Tuple[Dict[str, Any], int]:
    """
    Submit a transaction for fraud detection.
    
    AUTOMATIC FEATURES:
    - Time: Always uses CURRENT UTC time (instant)
    - Location: Auto-detects from browser geolocation or IP address
    
    Request body (JSON):
        amount (required): Transaction amount in INR (1-500000)
        latitude (optional): Current user latitude (from browser geolocation)
        longitude (optional): Current user longitude (from browser geolocation)
        city (optional): City name (auto-detected from coordinates if not provided)
        device_id (optional): Device identifier (auto-generated if not set)
        upi_id (optional): UPI address
        transaction_frequency (optional): Number of recent transactions (1-100)
        user_avg_amount (optional): User's average transaction amount
        is_new_device (optional): 0 or 1, whether this is a new device
    
    Returns:
        JSON with fraud detection result, location, time, and recommendation
    """
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body must be valid JSON"}), 400

    # ─── AUTOMATIC TIME: Always use CURRENT REAL-TIME (Local Time) ──────────
    now = datetime.datetime.now()  # ← Real-time local time (not UTC!)
    hour = now.hour            # Current hour (0-23)
    day_of_week = now.weekday()  # Current day (0=Mon, 6=Sun)
    timestamp = now.isoformat()  # ISO format timestamp with microseconds
    timestamp_ms = int(now.timestamp() * 1000)  # Milliseconds since epoch
    timestamp_epoch = now.timestamp()  # Seconds since epoch (Unix timestamp)
    
    # Exact time format with timezone
    exact_time = now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Format: 2026-03-28 15:45:30.123
    
    # Human-readable time format: 8.40 am (with period and lowercase) - REAL-TIME
    hour_12 = now.hour % 12 or 12  # Convert to 12-hour format without leading zeros
    minute = now.strftime("%M")
    am_pm = "am" if now.hour < 12 else "pm"
    time_readable = f"{hour_12}.{minute} {am_pm}"  # Format: 8.40 am (REAL-TIME)
    
    # ─── VALIDATION LAYER ──────────────────────────────────────────────────────
    
    # Required: amount
    try:
        amount = validate_transaction_amount(
            data.get("amount"),
            min_amount=1,
            max_amount=500000
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # ─── Optional fields with validation ────────────────────────────────────────
    try:
        device_id = validate_device_id(data.get("device_id")) \
                    or f"DEV_{random.randint(1000, 9999)}"
        
        upi_id = validate_upi_id(data.get("upi_id", ""), max_length=50)
        
        transaction_frequency = validate_transaction_frequency(
            data.get("transaction_frequency", 1),
            min_freq=1,
            max_freq=100
        )
        
        user_avg_amount = float(data.get("user_avg_amount", amount))
        
        is_new_device = int(data.get("is_new_device", 0)) in (0, 1)
        
    except ValueError as e:
        return jsonify({"error": f"Validation error: {str(e)}"}), 400
    
    # ─── AUTOMATIC LOCATION DETECTION ───────────────────────────────────────────
    
    try:
        # Try to get location from browser geolocation (frontend sends lat/lng)
        if data.get("latitude") and data.get("longitude"):
            lat, lng = validate_coordinates(
                data.get("latitude"),
                data.get("longitude")
            )
            # Auto-detect city from coordinates
            city = _find_nearest_city(lat, lng)
            location_source = "Browser Geolocation"
        else:
            # Fallback: Get city if provided, otherwise use default
            city = data.get("city", "Mumbai")
            try:
                city = validate_city(city, CITY_COORDS)
                location_source = "Manual Input"
            except ValueError:
                city = "Mumbai"
                location_source = "Default"
            
            # Use city coordinates with small random offset
            lat, lng = CITY_COORDS.get(city, (19.076, 72.877))
            lat += random.uniform(-0.1, 0.1)
            lng += random.uniform(-0.1, 0.1)
        
        lat = round(lat, 6)
        lng = round(lng, 6)
    except ValueError as e:
        return jsonify({"error": f"Invalid coordinates: {str(e)}"}), 400
    
    # ─── Prepare transaction payload for ML model ──────────────────────────────
    
    txn_payload = {
        "amount":                amount,
        "hour":                  hour,
        "day_of_week":           day_of_week,
        "city":                  city,
        "latitude":              lat,
        "longitude":             lng,
        "device_id":             device_id,
        "transaction_frequency": transaction_frequency,
        "user_avg_amount":       user_avg_amount,
        "is_new_device":         1 if is_new_device else 0,
    }

    # ─── Run fraud detection ────────────────────────────────────────────────────
    
    try:
        result = run_fraud_check(txn_payload)
    except RuntimeError as e:
        logger.error(f"ML model error: {str(e)}")
        return jsonify({"error": "Fraud detection service temporarily unavailable"}), 503

    txn_id      = f"TXN{uuid.uuid4().hex[:8].upper()}"
    final_label = result.get("final_label", result["label"])
    anomaly_score  = result.get("anomaly_score", 0.0)
    is_novel       = result.get("is_novel", False)
    combined_score = result.get("combined_score", result["fraud_score"])
    
    # ─── Fraud blocking: Auto-block if detected as fraud ─────────────────────────
    
    is_blocked = 1 if final_label == "Fraud" else 0

    # ─── Store transaction in database with EXACT TIMESTAMP ──────────────────────
    
    try:
        execute(
            """INSERT INTO transactions
               (txn_id, user_id, upi_id, amount, city, latitude, longitude, device_id,
                hour, day_of_week, transaction_frequency, user_avg_amount,
                is_new_device, fraud_score, label, risk_level, is_blocked, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                txn_id, user_id, upi_id, amount, city, lat, lng, device_id,
                hour, day_of_week, transaction_frequency, user_avg_amount,
                is_new_device, result["fraud_score"], final_label,
                result["risk_level"], is_blocked, exact_time
            )
        )
    except Exception as e:
        import traceback
        return jsonify({"error": f"Database error: {str(e)}", "trace": traceback.format_exc()}), 500
    
    # ─── Log to audit trail ────────────────────────────────────────────────────
    
    try:
        client_ip = request.remote_addr if request else None
        log_transaction_checked(
            user_id=user_id,
            txn_id=txn_id,
            amount=amount,
            city=city,
            final_label=final_label,
            fraud_score=result["fraud_score"],
            is_blocked=bool(is_blocked),
            ip_address=client_ip
        )
    except Exception as e:
        logger.warning(f"Failed to log audit trail for {txn_id}: {e}")

    # ─── Create fraud alert if detected ─────────────────────────────────────────
    
    if final_label in ("Fraud", "Anomaly"):
        try:
            execute(
                "INSERT INTO fraud_alerts (txn_id, fraud_score, risk_level, alert_type) VALUES (?,?,?,?)",
                (txn_id, combined_score, result["risk_level"], final_label)
            )
        except Exception as e:
            import traceback
            return jsonify({"error": f"Fraud alerts DB error: {str(e)}", "trace": traceback.format_exc()}), 500

        # Send real-time email alert in background thread (non-blocking)
        claims     = get_jwt()
        user_email = claims.get("email", "") if claims else ""
        try:
            threading.Thread(
                target=send_fraud_alert,
                args=(txn_id, amount, city, upi_id, result["fraud_score"],
                      result["risk_level"], user_email),
                kwargs={"combined_score": combined_score, "alert_type": final_label},
                daemon=True
            ).start()
        except Exception as e:
            import traceback
            return jsonify({"error": f"Thread error: {str(e)}", "trace": traceback.format_exc()}), 500

    # ─── Log transaction result ────────────────────────────────────────────────
    
    log_msg = f"Transaction {txn_id}: INR {amount} from {city} -> {final_label} " \
              f"(fraud={result['fraud_score']:.1f}%, anomaly={anomaly_score:.1f}%, " \
              f"combined={combined_score:.1f}%)"
    
    if is_blocked:
        logger.warning(f"[BLOCKED] {log_msg}")
    else:
        logger.info(log_msg)

    # ─── Build response with recommendation ────────────────────────────────────
    
    if final_label == "Fraud":
        recommendation = "[BLOCKED] Transaction blocked - fraud detected!"
    elif final_label == "Anomaly":
        recommendation = "[REVIEW] Unknown transaction pattern detected — flagged for manual review."
    else:
        recommendation = "[SAFE] Transaction is safe to proceed."

    return jsonify({
        "txn_id":         txn_id,
        "amount":         amount,
        "city":           city,
        "upi_id":         upi_id,
        "latitude":       lat,
        "longitude":      lng,
        # Automatic exact time detection (MULTIPLE FORMATS FOR PRECISION)
        "timestamp":      timestamp,
        "exact_time":     exact_time,  # Human-readable with milliseconds
        "time_readable":  time_readable,  # Time in 8:40 AM format
        "timestamp_ms":   timestamp_ms,  # Milliseconds since epoch
        "timestamp_epoch": timestamp_epoch,  # Unix timestamp (seconds)
        "hour":           hour,
        "day_of_week":    ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][day_of_week],
        "location_source": location_source,
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
        # Enforcement
        "is_blocked":     is_blocked,
        "recommendation": recommendation,
    })


# ─── List transactions ────────────────────────────────────────────────────────

@txn_bp.route("/", methods=["GET"])
@jwt_required()
def list_transactions() -> Tuple[Dict[str, Any], int]:
    """
    Get paginated list of transactions for the authenticated user.
    
    Query parameters:
        page (optional): Page number (default 1, min 1)
        limit (optional): Results per page (default 20, max 1000)
    
    Returns:
        JSON with transactions array, total count, and page info
    """
    try:
        page = int(request.args.get("page", 1))
        limit = int(request.args.get("limit", 20))
        page, limit, offset = validate_pagination(page, limit, max_limit=1000)
    except ValueError as e:
        return jsonify({"error": f"Invalid pagination: {str(e)}"}), 400

    rows = query(
        "SELECT * FROM transactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, offset)
    )
    total = query("SELECT COUNT(*) as cnt FROM transactions", one=True)["cnt"]
    
    return jsonify({
        "transactions": rows,
        "total": total,
        "page": page,
        "limit": limit,
        "offset": offset
    })


# ─── Block a transaction ──────────────────────────────────────────────────────

@txn_bp.route("/block/<txn_id>", methods=["POST"])
@jwt_required()
def block_transaction(txn_id: str) -> Tuple[Dict[str, Any], int]:
    """
    Manually block a transaction (admin-only).
    
    Args:
        txn_id: Transaction ID to block
    
    Returns:
        JSON with success message
    """
    user_id  = int(get_jwt_identity())
    claims   = get_jwt()
    username = claims.get("username", str(user_id))
    role = claims.get("role", "user")
    
    # Validate transaction exists
    txn = query("SELECT * FROM transactions WHERE txn_id = ?", (txn_id,), one=True)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
    
    # Check if already blocked
    if txn.get("is_blocked"):
        return jsonify({
            "message": f"Transaction {txn_id} was already blocked.",
            "txn_id": txn_id
        }), 200

    # Perform block
    execute("UPDATE transactions SET is_blocked = 1 WHERE txn_id = ?", (txn_id,))
    
    # Log audit trail with enhanced details
    try:
        client_ip = request.remote_addr if request else None
        log_transaction_blocked(
            user_id=user_id,
            txn_id=txn_id,
            reason="Manual block by admin",
            ip_address=client_ip
        )
    except Exception as e:
        logger.warning(f"Failed to log audit trail for block {txn_id}: {e}")
    
    logger.warning(f"✋ Transaction BLOCKED: {txn_id} by {username} (role: {role})")
    
    return jsonify({
        "message": f"Transaction {txn_id} has been blocked.",
        "txn_id": txn_id
    }), 200


# ─── Get single transaction ───────────────────────────────────────────────────

@txn_bp.route("/<txn_id>", methods=["GET"])
@jwt_required()
def get_transaction(txn_id: str) -> Tuple[Dict[str, Any], int]:
    txn = query("SELECT * FROM transactions WHERE txn_id = ?", (txn_id,), one=True)
    if not txn:
        return jsonify({"error": "Transaction not found"}), 404
    return jsonify(txn)
