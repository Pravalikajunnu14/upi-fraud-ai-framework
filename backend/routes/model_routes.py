"""
model_routes.py  – /api/model/*
Admin-only: retrain the model, view metrics, view feature importance.
"""

import os
import sys
import json
import subprocess
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from typing import Tuple, Dict, Any, Optional

model_bp = Blueprint("model", __name__, url_prefix="/api/model")

ML_DIR       = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml"))
METRICS_PATH = os.path.join(ML_DIR, "models", "model_metrics.json")


def _require_admin() -> Optional[Tuple[Dict[str, Any], int]]:
    claims = get_jwt()
    if claims.get("role") != "admin":
        return jsonify({"error": "Admin access required"}), 403
    return None


# ─── Retrain model ────────────────────────────────────────────────────────────

@model_bp.route("/retrain", methods=["POST"])
@jwt_required()
def retrain() -> Tuple[Dict[str, Any], int]:
    err = _require_admin()
    if err:
        return err

    try:
        # Step 1: generate fresh data
        gen_result = subprocess.run(
            [sys.executable, "generate_data.py"],
            cwd=ML_DIR, capture_output=True, text=True, timeout=120
        )
        # Step 2: train model
        train_result = subprocess.run(
            [sys.executable, "train_model.py"],
            cwd=ML_DIR, capture_output=True, text=True, timeout=300
        )

        if train_result.returncode != 0:
            return jsonify({
                "error":  "Training failed",
                "stderr": train_result.stderr[-2000:]
            }), 500

        # Reload predictor and anomaly detector
        from utils.fraud_engine import predictor
        from anomaly_detector import AnomalyDetector
        predictor._loaded = False
        AnomalyDetector().reset()

        # Return new metrics
        metrics = {}
        if os.path.exists(METRICS_PATH):
            with open(METRICS_PATH) as f:
                metrics = json.load(f)

        return jsonify({
            "message": "Model retrained successfully!",
            "metrics": {
                "accuracy":  metrics.get("accuracy"),
                "precision": metrics.get("precision"),
                "recall":    metrics.get("recall"),
                "f1_score":  metrics.get("f1_score"),
                "roc_auc":   metrics.get("roc_auc"),
            }
        })

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Training timed out (> 5 min)"}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─── Get current metrics ──────────────────────────────────────────────────────

@model_bp.route("/metrics", methods=["GET"])
@jwt_required()
def metrics() -> Tuple[Dict[str, Any], int]:
    if not os.path.exists(METRICS_PATH):
        return jsonify({"error": "Model not trained yet."}), 404
    with open(METRICS_PATH) as f:
        data = json.load(f)
    return jsonify(data)


# ─── Feature importance ───────────────────────────────────────────────────────

@model_bp.route("/feature-importance", methods=["GET"])
@jwt_required()
def feature_importance() -> Tuple[Dict[str, Any], int]:
    if not os.path.exists(METRICS_PATH):
        return jsonify({"error": "Model not trained yet."}), 404
    with open(METRICS_PATH) as f:
        data = json.load(f)
    return jsonify({"feature_importance": data.get("feature_importance", [])[:10]})
