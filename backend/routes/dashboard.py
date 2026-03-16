"""
dashboard.py  – /api/dashboard/*
Returns summary stats, live feed, heatmap data, and feature importance.
"""

import json
import os
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required

from database.db import query

dash_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

METRICS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "model_metrics.json")
)


# ─── Overall stats ────────────────────────────────────────────────────────────

@dash_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats():
    total   = query("SELECT COUNT(*) as cnt FROM transactions", one=True)["cnt"]
    fraud   = query("SELECT COUNT(*) as cnt FROM transactions WHERE label='Fraud'", one=True)["cnt"]
    blocked = query("SELECT COUNT(*) as cnt FROM transactions WHERE is_blocked=1", one=True)["cnt"]
    alerts  = query("SELECT COUNT(*) as cnt FROM fraud_alerts WHERE resolved=0", one=True)["cnt"]
    avg_score = query("SELECT AVG(fraud_score) as avg FROM transactions", one=True)["avg"] or 0

    fraud_rate = round((fraud / total * 100), 2) if total > 0 else 0

    # Risk breakdown
    low    = query("SELECT COUNT(*) as cnt FROM transactions WHERE risk_level='Low'",    one=True)["cnt"]
    medium = query("SELECT COUNT(*) as cnt FROM transactions WHERE risk_level='Medium'", one=True)["cnt"]
    high   = query("SELECT COUNT(*) as cnt FROM transactions WHERE risk_level='High'",   one=True)["cnt"]

    return jsonify({
        "total_transactions":  total,
        "fraud_detected":      fraud,
        "fraud_rate":          fraud_rate,
        "blocked_transactions": blocked,
        "open_alerts":         alerts,
        "avg_fraud_score":     round(avg_score, 2),
        "risk_distribution":   {"Low": low, "Medium": medium, "High": high},
    })


# ─── Live transaction feed ────────────────────────────────────────────────────

@dash_bp.route("/feed", methods=["GET"])
@jwt_required()
def feed():
    rows = query(
        """SELECT txn_id, amount, city, label, risk_level, fraud_score, is_blocked, created_at
           FROM transactions ORDER BY created_at DESC LIMIT 25"""
    )
    return jsonify({"feed": rows})


# ─── Heatmap (fraud locations) ────────────────────────────────────────────────

@dash_bp.route("/heatmap", methods=["GET"])
@jwt_required()
def heatmap():
    rows = query(
        """SELECT latitude, longitude, city, fraud_score, label
           FROM transactions WHERE label = 'Fraud' ORDER BY created_at DESC LIMIT 200"""
    )
    return jsonify({"heatmap": rows})


# ─── Fraud by hour of day ─────────────────────────────────────────────────────

@dash_bp.route("/hourly", methods=["GET"])
@jwt_required()
def hourly():
    rows = query(
        """SELECT hour, COUNT(*) as count
           FROM transactions WHERE label='Fraud'
           GROUP BY hour ORDER BY hour"""
    )
    hourly_map = {r["hour"]: r["count"] for r in rows}
    data = [hourly_map.get(h, 0) for h in range(24)]
    return jsonify({"hourly_fraud": data})


# ─── Feature importance ───────────────────────────────────────────────────────

@dash_bp.route("/feature-importance", methods=["GET"])
@jwt_required()
def feature_importance():
    if not os.path.exists(METRICS_PATH):
        return jsonify({"error": "Model not trained yet. Run train_model.py first."}), 404
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    fi = metrics.get("feature_importance", [])[:10]
    return jsonify({"feature_importance": fi})


# ─── Model metrics ────────────────────────────────────────────────────────────

@dash_bp.route("/model-metrics", methods=["GET"])
@jwt_required()
def model_metrics():
    if not os.path.exists(METRICS_PATH):
        return jsonify({"error": "Model not trained yet."}), 404
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    return jsonify({
        "accuracy":  metrics.get("accuracy"),
        "precision": metrics.get("precision"),
        "recall":    metrics.get("recall"),
        "f1_score":  metrics.get("f1_score"),
        "roc_auc":   metrics.get("roc_auc"),
    })
