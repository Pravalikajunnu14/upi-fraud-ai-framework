"""
app.py
------
Main Flask application entry point for the UPI Fraud Detection Framework.
Initialises Flask + CORS + JWT + Flask-SocketIO + all route blueprints.

Run with:
    python app.py
"""

import eventlet
eventlet.monkey_patch()

import os
import sys
import datetime
import random
import threading
import time

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO

# ─── Path fixup: allow importing from /ml/ ────────────────────────────────────
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from config import Config

# ─── App factory ──────────────────────────────────────────────────────────────

def create_app():
    app = Flask(
        __name__,
        static_folder=os.path.join(ROOT_DIR, "frontend"),
        static_url_path="",
    )

    # Load config
    app.config["SECRET_KEY"]               = Config.SECRET_KEY
    app.config["JWT_SECRET_KEY"]           = Config.JWT_SECRET_KEY
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = datetime.timedelta(seconds=Config.JWT_ACCESS_TOKEN_EXPIRES)
    app.config["DEBUG"]                    = Config.DEBUG

    # Extensions
    CORS(app, resources={r"/*": {"origins": "*"}})
    JWTManager(app)

    # ─── Register blueprints ──────────────────────────────────────────────────
    from routes.auth         import auth_bp
    from routes.transactions import txn_bp
    from routes.dashboard    import dash_bp
    from routes.model_routes import model_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(txn_bp)
    app.register_blueprint(dash_bp)
    app.register_blueprint(model_bp)

    from routes.webhook import webhook_bp
    app.register_blueprint(webhook_bp)

    # ─── Initialise database ──────────────────────────────────────────────────
    from database.db import init_db
    with app.app_context():
        init_db()

    # ─── Health check ─────────────────────────────────────────────────────────
    @app.route("/api/health", methods=["GET"])
    def health():
        from utils.fraud_engine import predictor
        return jsonify({
            "status":      "ok",
            "model_ready": predictor.is_ready(),
            "timestamp":   datetime.datetime.utcnow().isoformat(),
        })

    # ─── Frontend page serving ────────────────────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(os.path.join(ROOT_DIR, "frontend"), "index.html")

    @app.route("/<path:path>")
    def static_files(path):
        frontend_dir = os.path.join(ROOT_DIR, "frontend")
        full_path    = os.path.join(frontend_dir, path)
        if os.path.isfile(full_path):
            return send_from_directory(frontend_dir, path)
        return send_from_directory(frontend_dir, "index.html")

    # ─── JWT / HTTP error handlers ────────────────────────────────────────────
    @app.errorhandler(401)
    def unauthorized(e):
        return jsonify({"error": "Unauthorized – please log in"}), 401

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return app


# ─── Initialise app + SocketIO ────────────────────────────────────────────────

app      = create_app()
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Jaipur", "Ahmedabad", "Surat",
]


def _live_feed_broadcaster():
    """Background thread: push a simulated transaction every 4 seconds."""
    from utils.fraud_engine import predictor
    while True:
        time.sleep(4)
        if not predictor.is_ready():
            continue
        try:
            city   = random.choice(CITIES)
            amount = round(random.uniform(500, 80_000), 2)
            hour   = datetime.datetime.utcnow().hour
            txn    = {
                "amount":                amount,
                "hour":                  hour,
                "day_of_week":           datetime.datetime.utcnow().weekday(),
                "city":                  city,
                "device_id":             f"DEV_{random.randint(1000, 9999)}",
                "transaction_frequency": random.randint(1, 10),
                "user_avg_amount":       round(amount * random.uniform(0.5, 1.5), 2),
                "is_new_device":         random.choice([0, 0, 0, 1]),
                "latitude":              0,
                "longitude":             0,
            }
            result = predictor.predict(txn)
            payload = {
                "txn_id":     f"TXN{random.randint(100_000, 999_999)}",
                "amount":     amount,
                "city":       city,
                "label":      result["label"],
                "risk_level": result["risk_level"],
                "fraud_score": result["fraud_score"],
                "timestamp":  datetime.datetime.utcnow().isoformat(),
            }
            socketio.emit("live_transaction", payload, namespace="/")
        except Exception:
            pass


_t = threading.Thread(target=_live_feed_broadcaster, daemon=True)
_t.start()


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    from utils.logger import logger
    from utils.fraud_engine import cache_stats

    if Config.DEBUG:
        # Development mode — Flask dev server with SocketIO
        logger.info("[DEV] Starting Flask dev server on http://localhost:5000")
        socketio.run(app, host="0.0.0.0", port=5000, debug=True,
                     use_reloader=False, allow_unsafe_werkzeug=True)
    else:
        # Production mode — Waitress WSGI (Windows-compatible)
        try:
            from waitress import serve
            logger.info("[PROD] Starting Waitress server on http://0.0.0.0:5000")
            logger.info(f"[PROD] Prediction cache: {cache_stats()}")
            serve(app, host="0.0.0.0", port=5000, threads=8)
        except ImportError:
            logger.warning("Waitress not installed. Run: pip install waitress")
            logger.info("Falling back to Flask dev server")
            socketio.run(app, host="0.0.0.0", port=5000, debug=False,
                         use_reloader=False, allow_unsafe_werkzeug=True)
