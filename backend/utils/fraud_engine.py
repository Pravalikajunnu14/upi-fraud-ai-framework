"""
fraud_engine.py
---------------
Singleton wrapper around FraudPredictor with LRU prediction cache.
Imported once on app startup; used by transaction routes.

Returns extended result dict including anomaly detection fields:
  fraud_score, label, risk_level, anomaly_score, is_novel,
  combined_score, final_label
"""

import sys
import os
import hashlib
import json
import threading
from collections import OrderedDict
from typing import Dict

# Allow importing from ml/ folder (two levels up from backend/utils/)
ML_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml"))
if ML_DIR not in sys.path:
    sys.path.insert(0, ML_DIR)

from fraud_predictor import FraudPredictor  # noqa: E402

# Single shared instance — loaded lazily on first .predict() call
predictor = FraudPredictor()

# ── Simple LRU prediction cache with thread-safety ────────────────────────────────
CACHE_MAX_SIZE = 256
_cache: OrderedDict = OrderedDict()
_cache_lock = threading.Lock()  # Protect cache from race conditions
_cache_hits   = 0
_cache_misses = 0


def _cache_key(txn: Dict) -> str:
    """Create a stable hash key from transaction features."""
    key_fields = {
        k: round(v, 2) if isinstance(v, float) else v
        for k, v in txn.items()
        if k in ("amount", "hour", "day_of_week", "city",
                  "transaction_frequency", "user_avg_amount",
                  "is_new_device")
    }
    return hashlib.md5(json.dumps(key_fields, sort_keys=True).encode()).hexdigest()


def run_fraud_check(txn: Dict) -> Dict:
    """
    Run fraud detection on a transaction dict with LRU cache.

    Returns
    -------
    {
        "fraud_score":    float,   # supervised model P(fraud) × 100
        "label":          str,     # "Fraud" | "Legitimate"
        "risk_level":     str,     # "Low" | "Medium" | "High"
        "anomaly_score":  float,   # Isolation Forest novelty score 0–100
        "is_novel":       bool,    # True when anomaly_score > 65
        "combined_score": float,   # 0.7·fraud_score + 0.3·anomaly_score
        "final_label":    str,     # "Fraud" | "Anomaly" | "Legitimate"
    }

    Raises RuntimeError if model is not trained yet.
    """
    global _cache_hits, _cache_misses

    if not predictor.is_ready():
        raise RuntimeError(
            "Fraud model is not loaded. "
            "Run `python ml/train_model.py` to train it first."
        )

    key = _cache_key(txn)
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            _cache_hits += 1
            return _cache[key]

        result = predictor.predict(txn)
        _cache[key] = result
        if len(_cache) > CACHE_MAX_SIZE:
            _cache.popitem(last=False)
        _cache_misses += 1
        return result


def cache_stats() -> Dict:
    """Return current cache statistics (thread-safe)."""
    with _cache_lock:
        return {"hits": _cache_hits, "misses": _cache_misses, "size": len(_cache)}
