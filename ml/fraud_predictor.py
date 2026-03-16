"""
fraud_predictor.py
------------------
Prediction interface class used by the Flask backend.
Loads the trained supervised model + Isolation Forest anomaly detector once
and exposes a .predict() method that fuses both scores.

Usage (from backend):
    from ml.fraud_predictor import FraudPredictor
    predictor = FraudPredictor()
    result = predictor.predict({
        "amount": 45000,
        "hour": 2,
        "day_of_week": 5,
        "city": "Mumbai",
        "is_new_device": 1,
        "transaction_frequency": 12,
        "user_avg_amount": 5000,
        "latitude": 19.076,
        "longitude": 72.877,
    })
    # result →
    # {
    #   "fraud_score":    87.4,
    #   "label":          "Fraud",
    #   "risk_level":     "High",
    #   "anomaly_score":  72.1,   ← NEW: 0-100, how novel/unknown the txn is
    #   "is_novel":       True,   ← NEW: True if anomaly_score > 65
    #   "combined_score": 83.8,   ← NEW: weighted fusion 0.7*fraud + 0.3*anomaly
    #   "final_label":    "Fraud" ← NEW: may be "Anomaly" for novel legit txns
    # }
"""

import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR     = os.path.dirname(__file__)
MODEL_PATH   = os.path.join(BASE_DIR, "models", "fraud_model.pkl")
FEATS_PATH   = os.path.join(BASE_DIR, "models", "feature_columns.pkl")

NUMERIC_FEATURES = [
    "amount", "hour", "day_of_week", "latitude", "longitude",
    "transaction_frequency", "user_avg_amount",
    "is_new_device", "amount_to_avg_ratio", "is_night"
]

# Weights for the combined risk score
W_FRAUD   = 0.70   # weight of supervised fraud_score
W_ANOMALY = 0.30   # weight of anomaly_score


def _risk_level(score: float) -> str:
    """Convert 0–100 fraud probability to Low / Medium / High."""
    if score < 30:
        return "Low"
    elif score < 65:
        return "Medium"
    else:
        return "High"


class FraudPredictor:
    """Singleton-friendly fraud prediction class with anomaly detection layer."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    def _load(self):
        if self._loaded:
            return
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(
                f"Model not found at {MODEL_PATH}. "
                "Run `python ml/train_model.py` first."
            )
        artefact       = joblib.load(MODEL_PATH)
        self.model     = artefact["model"]
        self.city_enc  = artefact["city_encoder"]
        self.feat_cols = joblib.load(FEATS_PATH)
        self._loaded   = True

        # Load anomaly detector (lazy, no error if not yet trained)
        from anomaly_detector import AnomalyDetector
        self.anomaly = AnomalyDetector()

    # ─── Public API ──────────────────────────────────────────────────────────

    def predict(self, txn: dict) -> dict:
        """
        Parameters
        ----------
        txn : dict with keys:
            amount, hour, day_of_week, city, is_new_device,
            transaction_frequency, user_avg_amount,
            latitude, longitude

        Returns
        -------
        dict:
            fraud_score    – float 0–100  (supervised model confidence)
            label          – "Fraud" | "Legitimate"
            risk_level     – "Low" | "Medium" | "High"
            anomaly_score  – float 0–100  (Isolation Forest novelty score)
            is_novel       – bool  (True when anomaly_score > 65)
            combined_score – float 0–100  (weighted blend of both scores)
            final_label    – "Fraud" | "Anomaly" | "Legitimate"
        """
        self._load()

        amount   = float(txn.get("amount", 0))
        user_avg = float(txn.get("user_avg_amount", amount))
        hour     = int(txn.get("hour", 12))
        city     = txn.get("city", "Mumbai")

        # Derived features
        amt_ratio = amount / (user_avg + 1)
        is_night  = 1 if (hour <= 5 or hour >= 22) else 0

        # Encode city
        known_cities = list(self.city_enc.classes_)
        city_enc_val = (
            self.city_enc.transform([city])[0]
            if city in known_cities
            else 0          # fallback to first city label
        )

        row = {
            "amount":                amount,
            "hour":                  hour,
            "day_of_week":           int(txn.get("day_of_week", 0)),
            "latitude":              float(txn.get("latitude", 19.076)),
            "longitude":             float(txn.get("longitude", 72.877)),
            "transaction_frequency": int(txn.get("transaction_frequency", 1)),
            "user_avg_amount":       user_avg,
            "is_new_device":         int(txn.get("is_new_device", 0)),
            "amount_to_avg_ratio":   round(amt_ratio, 4),
            "is_night":              is_night,
            "city_encoded":          city_enc_val,
        }

        # ── Supervised prediction ─────────────────────────────────────────────
        X      = pd.DataFrame([{f: row[f] for f in self.feat_cols}])
        prob   = self.model.predict_proba(X)[0][1]   # P(fraud)
        score  = round(prob * 100, 2)
        label  = "Fraud" if prob >= 0.5 else "Legitimate"

        # ── Anomaly / novelty detection ───────────────────────────────────────
        anomaly_result = self.anomaly.score(row)
        anomaly_score  = anomaly_result["anomaly_score"]
        is_novel       = anomaly_result["is_novel"]

        # ── Fused risk score ──────────────────────────────────────────────────
        combined_score = round(W_FRAUD * score + W_ANOMALY * anomaly_score, 2)

        # Determine final label:
        #   • If supervised says Fraud → "Fraud" (known pattern)
        #   • If supervised says Legitimate but anomaly is high → "Anomaly"
        #     (unknown/novel pattern — flag for manual review)
        #   • Otherwise → "Legitimate"
        if label == "Fraud":
            final_label = "Fraud"
        elif is_novel:
            final_label = "Anomaly"
        else:
            final_label = "Legitimate"

        return {
            "fraud_score":    score,
            "label":          label,
            "risk_level":     _risk_level(combined_score),
            "anomaly_score":  anomaly_score,
            "is_novel":       is_novel,
            "combined_score": combined_score,
            "final_label":    final_label,
        }

    def is_ready(self) -> bool:
        try:
            self._load()
            return True
        except FileNotFoundError:
            return False
