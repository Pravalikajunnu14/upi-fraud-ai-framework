"""
auth.py  – /api/auth/*
JWT-based authentication: register, login, me.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
import bcrypt
import datetime

from database.db import query, execute
from utils.logger import logger
from utils.email_alert import send_fraud_alert
import threading

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# ─── Register ─────────────────────────────────────────────────────────────────

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")
    email    = data.get("email", "").strip().lower()
    role     = data.get("role", "user")

    if not username or not password:
        return jsonify({"error": "username and password are required"}), 400
    if not email or "@" not in email:
        return jsonify({"error": "a valid email is required"}), 400
    if role not in ("admin", "user"):
        role = "user"

    existing = query("SELECT id FROM users WHERE username = ?", (username,), one=True)
    if existing:
        return jsonify({"error": "Username already taken"}), 409
    email_exists = query("SELECT id FROM users WHERE email = ?", (email,), one=True)
    if email_exists:
        return jsonify({"error": "Email already registered"}), 409

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    uid = execute(
        "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
        (username, email, hashed, role)
    )
    logger.info(f"New user registered: {username} ({email}) role={role} id={uid}")
    return jsonify({"message": "User registered successfully", "user_id": uid}), 201


# ─── Login ────────────────────────────────────────────────────────────────────

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data:
        return jsonify({"error": "No JSON body"}), 400

    username = data.get("username", "").strip()
    password = data.get("password", "")

    user = query("SELECT * FROM users WHERE username = ?", (username,), one=True)
    if not user or not bcrypt.checkpw(password.encode(), user["password"].encode()):
        logger.warning(f"Failed login attempt for: {username}")
        return jsonify({"error": "Invalid username or password"}), 401

    # Update last login timestamp
    execute("UPDATE users SET last_login = ? WHERE id = ?",
            (datetime.datetime.utcnow().isoformat(), user["id"]))

    token = create_access_token(
        identity=str(user["id"]),
        additional_claims={
            "username": user["username"],
            "role":     user["role"],
            "email":    user["email"] or "",
        }
    )
    logger.info(f"User logged in: {username}")
    return jsonify({
        "access_token": token,
        "user": {"id": user["id"], "username": user["username"],
                  "role": user["role"], "email": user["email"] or ""}
    })


# ─── Get current user ─────────────────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = get_jwt_identity()
    user = query("SELECT id, username, email, role, created_at, last_login FROM users WHERE id = ?",
                 (user_id,), one=True)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))


# ─── Test alert email ─────────────────────────────────────────────────────────

@auth_bp.route("/test-alert", methods=["POST"])
@jwt_required()
def test_alert():
    """
    POST /api/auth/test-alert
    Sends a test fraud alert email to the currently logged-in user's email.
    No transaction is created. Use this to verify your email setup works.
    """
    claims     = get_jwt()
    user_email = claims.get("email", "")
    username   = claims.get("username", "User")

    if not user_email or "@" not in user_email:
        return jsonify({"error": "No valid email found in your account. Please register with a valid email."}), 400

    threading.Thread(
        target=send_fraud_alert,
        args=("TEST-TXN001", 99999.00, "Mumbai", "testpayee@upi",
              92.5, "High", user_email),
        kwargs={"combined_score": 88.0, "alert_type": "Fraud"}
    ).start()

    logger.info(f"[TestAlert] Test fraud alert email triggered for user '{username}' → {user_email}")
    return jsonify({
        "message": f"✅ Test alert email sent to {user_email}. Check your inbox (and spam folder).",
        "recipient": user_email
    })
