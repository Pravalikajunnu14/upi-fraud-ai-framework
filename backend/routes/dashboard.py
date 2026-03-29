"""
dashboard.py  – /api/dashboard/*
Returns summary stats, live feed, heatmap data, and feature importance.
"""

import json
import os
import time
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from typing import Tuple, Dict, Any

from database.db import query, execute
from utils.logger import logger
from utils.audit import log_audit

dash_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

METRICS_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "model_metrics.json")
)

# Simple time-based cache for dashboard stats (TTL: 30 seconds)
_cache = {}
_cache_ttl = {}
CACHE_TTL_SECONDS = 30


def _get_cached(key: str) -> Any:
    """Retrieve from cache if not expired."""
    if key in _cache and key in _cache_ttl:
        if time.time() - _cache_ttl[key] < CACHE_TTL_SECONDS:
            logger.debug(f"Cache HIT for {key}")
            return _cache[key]
    return None


def _set_cached(key: str, value: Any) -> None:
    """Store in cache with current timestamp."""
    _cache[key] = value
    _cache_ttl[key] = time.time()
    logger.debug(f"Cache SET for {key}")


# ─── Overall stats ────────────────────────────────────────────────────────────

@dash_bp.route("/stats", methods=["GET"])
@jwt_required()
def stats() -> Tuple[Dict[str, Any], int]:
    # Check cache first
    cached = _get_cached("dashboard_stats")
    if cached:
        return jsonify(cached)
    
    total   = query("SELECT COUNT(*) as cnt FROM transactions", one=True)["cnt"]
    fraud   = query("SELECT COUNT(*) as cnt FROM transactions WHERE label='Fraud'", one=True)["cnt"]
    blocked = query("SELECT COUNT(*) as cnt FROM transactions WHERE is_blocked=1", one=True)["cnt"]
    alerts  = query("SELECT COUNT(*) as cnt FROM fraud_alerts WHERE resolved=0", one=True)["cnt"]
    avg_score = query("SELECT AVG(fraud_score) as avg FROM transactions", one=True)["avg"] or 0
    
    # Count anomalies (novel transactions)
    anomalies = query(
        "SELECT COUNT(*) as cnt FROM transactions WHERE label IN ('Anomaly')",
        one=True
    )["cnt"] or 0

    fraud_rate = round((fraud / total * 100), 2) if total > 0 else 0

    # Risk breakdown
    low    = query("SELECT COUNT(*) as cnt FROM transactions WHERE risk_level='Low'",    one=True)["cnt"]
    medium = query("SELECT COUNT(*) as cnt FROM transactions WHERE risk_level='Medium'", one=True)["cnt"]
    high   = query("SELECT COUNT(*) as cnt FROM transactions WHERE risk_level='High'",   one=True)["cnt"]

    result = {
        "total_transactions":   total,
        "fraud_count":          fraud,          # Fixed: was "fraud_detected"
        "fraud_rate":           fraud_rate,
        "blocked_transactions": blocked,
        "anomaly_count":        anomalies,      # New: added
        "open_alerts":          alerts,
        "avg_fraud_score":      round(avg_score, 2),
        "high_risk_count":      high,           # New: added
        "risk_distribution":    {"Low": low, "Medium": medium, "High": high},
    }
    
    # Cache the result
    _set_cached("dashboard_stats", result)
    return jsonify(result)


# ─── Live transaction feed ────────────────────────────────────────────────────

@dash_bp.route("/feed", methods=["GET"])
@jwt_required()
def feed() -> Tuple[Dict[str, Any], int]:
    # Get page/limit from query params
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 25, type=int)
    
    # Validate pagination
    limit = min(limit, 1000)  # Max 1000 per page
    offset = (max(page, 1) - 1) * limit
    
    rows = query(
        """SELECT txn_id, amount, city, label, risk_level, fraud_score, is_blocked, created_at
           FROM transactions ORDER BY created_at DESC LIMIT ? OFFSET ?""",
        (limit, offset)
    )
    
    logger.debug(f"Feed: page={page}, limit={limit}, returned {len(rows)} transactions")
    return jsonify({"transactions": rows})  # Fixed: was "feed"


# ─── Fraud alerts with filtering ──────────────────────────────────────────────

@dash_bp.route("/alerts", methods=["GET"])
@jwt_required()
def alerts() -> Tuple[Dict[str, Any], int]:
    """
    Get paginated list of fraud alerts.
    
    Query parameters:
        resolved (optional): 0 (unresolved) or 1 (resolved), default returns all
        alert_type (optional): Filter by alert type
        page (optional): Page number (default 1)
        limit (optional): Results per page (default 50, max 1000)
    """
    resolved = request.args.get("resolved", None, type=int)
    alert_type = request.args.get("alert_type", None, type=str)
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", 50, type=int)
    
    # Validate pagination
    limit = min(limit, 1000)
    offset = (max(page, 1) - 1) * limit
    
    # Build query
    where_clauses = []
    params = []
    
    if resolved is not None:
        where_clauses.append("resolved = ?")
        params.append(resolved)
    
    if alert_type:
        where_clauses.append("alert_type = ?")
        params.append(alert_type)
    
    where_clause = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    
    sql = f"""
        SELECT id, txn_id, fraud_score, risk_level, alert_type, resolved, created_at
        FROM fraud_alerts
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    
    rows = query(sql, tuple(params))
    logger.debug(f"Alerts: resolved={resolved}, alert_type={alert_type}, returned {len(rows)}")
    
    return jsonify({"alerts": rows})


# ─── Resolve alert ────────────────────────────────────────────────────────────

@dash_bp.route("/alerts/<int:alert_id>", methods=["PATCH"])
@jwt_required()
def resolve_alert(alert_id: int) -> Tuple[Dict[str, Any], int]:
    """
    Mark an alert as resolved.
    
    Request body (JSON):
        resolved (required): 0 (unresolved) or 1 (resolved)
        notes (optional): Resolution notes/comments
    """
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    resolved = data.get("resolved", 0)
    notes = data.get("notes", "")
    
    # Validate
    if resolved not in (0, 1):
        return jsonify({"error": "resolved must be 0 or 1"}), 400
    
    # Check if alert exists
    alert = query("SELECT id, txn_id FROM fraud_alerts WHERE id = ?", (alert_id,), one=True)
    if not alert:
        return jsonify({"error": "Alert not found"}), 404
    
    # Update alert
    execute(
        "UPDATE fraud_alerts SET resolved = ? WHERE id = ?",
        (resolved, alert_id)
    )
    
    # Log audit trail
    try:
        client_ip = request.remote_addr if request else None
        log_audit(
            user_id=user_id,
            action="ALERT_RESOLVED",
            details={
                "alert_id": alert_id,
                "txn_id": alert["txn_id"],
                "resolved": resolved,
                "notes": notes
            },
            ip_address=client_ip
        )
    except Exception as e:
        logger.warning(f"Failed to log audit trail for alert {alert_id}: {e}")
    
    logger.info(f"Alert {alert_id} updated: resolved={resolved}, notes={notes}")
    
    return jsonify({
        "message": "Alert updated successfully",
        "alert_id": alert_id,
        "resolved": resolved
    })


# ─── Heatmap (fraud locations) ────────────────────────────────────────────────

@dash_bp.route("/heatmap", methods=["GET"])
@jwt_required()
def heatmap() -> Tuple[Dict[str, Any], int]:
    rows = query(
        """SELECT latitude, longitude, city, fraud_score, label
           FROM transactions WHERE label = 'Fraud' ORDER BY created_at DESC LIMIT 200"""
    )
    return jsonify({"heatmap": rows})


# ─── Fraud by hour of day ─────────────────────────────────────────────────────

@dash_bp.route("/hourly", methods=["GET"])
@jwt_required()
def hourly() -> Tuple[Dict[str, Any], int]:
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
def feature_importance() -> Tuple[Dict[str, Any], int]:
    if not os.path.exists(METRICS_PATH):
        return jsonify({"error": "Model not trained yet. Run train_model.py first."}), 404
    with open(METRICS_PATH) as f:
        metrics = json.load(f)
    fi = metrics.get("feature_importance", [])[:10]
    return jsonify({"feature_importance": fi})


# ─── Model metrics ────────────────────────────────────────────────────────────

@dash_bp.route("/model-metrics", methods=["GET"])
@jwt_required()
def model_metrics() -> Tuple[Dict[str, Any], int]:
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
