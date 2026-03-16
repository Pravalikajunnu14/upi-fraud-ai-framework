"""
anomaly_detector.py
--------------------
Unsupervised anomaly detection layer using Isolation Forest.
Trained on LEGITIMATE transactions only — learns "what normal looks like".
Any transaction that deviates significantly from normal gets a high anomaly_score.

This complements the supervised fraud classifier:
  - Supervised (RF/XGBoost)  → detects KNOWN fraud patterns
  - Isolation Forest          → detects UNKNOWN / novel patterns

Saved model: ml/models/anomaly_model.pkl
"""

import os
import joblib
import numpy as np
import pandas as pd

BASE_DIR    = os.path.dirname(__file__)
ANOMALY_PATH = os.path.join(BASE_DIR, "models", "anomaly_model.pkl")

# Features used by the anomaly model (matches train_model.py)
ANOMALY_FEATURES = [
    "amount", "hour", "day_of_week", "latitude", "longitude",
    "transaction_frequency", "user_avg_amount",
    "is_new_device", "amount_to_avg_ratio", "is_night",
    "city_encoded",
]

# Threshold above which a transaction is flagged as "novel / anomalous"
NOVELTY_THRESHOLD = 65.0


def _isolation_score_to_0_100(raw_scores: np.ndarray) -> np.ndarray:
    """
    Convert Isolation Forest decision_function output to a 0-100 novelty score.

    decision_function returns negative scores for anomalies and positive for
    normal points.  We invert and normalise to [0, 100]:
        0   = perfectly normal
        100 = most anomalous
    """
    # raw_scores range roughly [-0.5, 0.5]; anything <0 is anomalous
    clipped = np.clip(raw_scores, -0.5, 0.5)
    # invert so "more anomalous → higher value", scale to [0,100]
    novelty = (0.5 - clipped) / 1.0 * 100.0
    return np.clip(novelty, 0.0, 100.0)


class AnomalyDetector:
    """
    Singleton anomaly detector backed by a pre-trained Isolation Forest.

    Usage
    -----
    detector = AnomalyDetector()
    result   = detector.score({
        "amount": 5_000_000, "hour": 3, "day_of_week": 6,
        "latitude": 19.076, "longitude": 72.877,
        "transaction_frequency": 50, "user_avg_amount": 500,
        "is_new_device": 1, "amount_to_avg_ratio": 10000,
        "is_night": 1,
    })
    # result → {"anomaly_score": 91.2, "is_novel": True}
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._loaded = False
        return cls._instance

    # ── Internal ─────────────────────────────────────────────────────────────

    def _load(self):
        if self._loaded:
            return
        if not os.path.exists(ANOMALY_PATH):
            # Graceful degradation: return neutral score when model not trained
            self._model = None
            self._loaded = True
            return
        self._model = joblib.load(ANOMALY_PATH)
        self._loaded = True

    # ── Public API ────────────────────────────────────────────────────────────

    def is_ready(self) -> bool:
        self._load()
        return self._model is not None

    def score(self, txn: dict) -> dict:
        """
        Parameters
        ----------
        txn : dict
            Must contain all ANOMALY_FEATURES keys.

        Returns
        -------
        dict:
            anomaly_score – float 0–100 (higher = more anomalous / novel)
            is_novel      – bool, True when anomaly_score > NOVELTY_THRESHOLD
        """
        self._load()

        if not self.is_ready():
            # Model not trained yet — return neutral response
            return {"anomaly_score": 0.0, "is_novel": False}

        row = {f: txn.get(f, 0) for f in ANOMALY_FEATURES}
        X   = pd.DataFrame([row])[ANOMALY_FEATURES]

        raw   = self._model.decision_function(X)          # shape (1,)
        score = float(_isolation_score_to_0_100(raw)[0])
        score = round(score, 2)

        return {
            "anomaly_score": score,
            "is_novel":      score > NOVELTY_THRESHOLD,
        }

    def reset(self):
        """Force a reload on the next call (used after retraining)."""
        self._loaded = False
        self._model  = None
        AnomalyDetector._instance = None
