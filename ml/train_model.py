"""
train_model.py
--------------
Trains Random Forest AND XGBoost on the UPI transaction dataset.
Auto-selects the model with the higher ROC-AUC score and saves it.

NEW (Anomaly Detection): Also trains an Isolation Forest on legitimate-only
transactions, saved to ml/models/anomaly_model.pkl. This lets the system detect
unknown / novel transaction patterns that the supervised model may miss.

Usage:
    python train_model.py
Output:
    ml/models/fraud_model.pkl
    ml/models/anomaly_model.pkl   ← NEW
    ml/models/feature_columns.pkl
    ml/models/model_metrics.json
"""

import os
import json
import joblib
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestClassifier, IsolationForest
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score,
    f1_score, roc_auc_score, confusion_matrix, classification_report
)

try:
    from xgboost import XGBClassifier
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False

# ─── Paths ────────────────────────────────────────────────────────────────────
DATA_PATH    = os.path.join("data", "upi_transactions.csv")
MODEL_DIR    = "models"
MODEL_PATH   = os.path.join(MODEL_DIR, "fraud_model.pkl")
ANOMALY_PATH = os.path.join(MODEL_DIR, "anomaly_model.pkl")
FEATS_PATH   = os.path.join(MODEL_DIR, "feature_columns.pkl")
METRICS_PATH = os.path.join(MODEL_DIR, "model_metrics.json")

NUMERIC_FEATURES = [
    "amount", "hour", "day_of_week", "latitude", "longitude",
    "transaction_frequency", "user_avg_amount",
    "is_new_device", "amount_to_avg_ratio", "is_night"
]
TARGET = "is_fraud"


# ─── Load & preprocess ────────────────────────────────────────────────────────

def load_data(path):
    print(f"Loading dataset: {path}")
    df = pd.read_csv(path)
    le = LabelEncoder()
    df["city_encoded"] = le.fit_transform(df["city"])
    feature_cols = NUMERIC_FEATURES + ["city_encoded"]
    X = df[feature_cols]
    y = df[TARGET]
    print(f"  Rows: {len(df):,}  |  Fraud rate: {y.mean()*100:.2f}%")
    return X, y, feature_cols, le, df


# ─── Supervised model trainers ────────────────────────────────────────────────

def train_random_forest(X_train, y_train):
    print("\n[1/3] Training Random Forest (200 trees) …")
    clf = RandomForestClassifier(
        n_estimators=200,
        max_depth=14,
        min_samples_split=4,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    return clf


def train_xgboost(X_train, y_train):
    print("[2/3] Training XGBoost (300 trees) …")
    pos   = int((y_train == 0).sum())
    neg   = int((y_train == 1).sum())
    scale = pos / max(neg, 1)
    clf = XGBClassifier(
        n_estimators=300,
        max_depth=7,
        learning_rate=0.08,
        subsample=0.85,
        colsample_bytree=0.85,
        scale_pos_weight=scale,
        random_state=42,
        eval_metric="logloss",
        verbosity=0,
        n_jobs=-1,
    )
    clf.fit(X_train, y_train)
    return clf


# ─── Anomaly Detection (Isolation Forest) ─────────────────────────────────────

def train_anomaly_model(df_full, feature_cols):
    """
    Train Isolation Forest on LEGITIMATE transactions only.

    By fitting exclusively on normal data, the model learns what 'normal'
    looks like. At inference time, any transaction whose feature vector is
    highly isolated (i.e., unlike the training data) receives a high
    anomaly_score — even if the supervised classifier labels it 'Legitimate'.

    This gives the system the ability to flag genuinely novel attack patterns
    that were never present in training data (zero-day fraud behaviour).
    """
    print("[3/3] Training Isolation Forest anomaly detector on legitimate transactions …")

    df_legit   = df_full[df_full[TARGET] == 0]
    fraud_rate = float((df_full[TARGET] == 1).mean())
    # Contamination = expected % of outliers in the TRAINING set (capped at 10 %)
    contam     = min(fraud_rate, 0.10)

    X_legit = df_legit[feature_cols]

    iso = IsolationForest(
        n_estimators=200,
        contamination=contam,
        max_samples="auto",
        random_state=42,
        n_jobs=-1,
    )
    iso.fit(X_legit)
    print(f"  Trained on {len(X_legit):,} legitimate rows  "
          f"|  contamination={contam*100:.2f}%")
    return iso, fraud_rate


# ─── Evaluate ─────────────────────────────────────────────────────────────────

def evaluate(clf, X_test, y_test, feature_cols):
    y_pred = clf.predict(X_test)
    y_prob = clf.predict_proba(X_test)[:, 1]

    acc  = accuracy_score(y_test, y_pred)
    prec = precision_score(y_test, y_pred, zero_division=0)
    rec  = recall_score(y_test, y_pred, zero_division=0)
    f1   = f1_score(y_test, y_pred, zero_division=0)
    auc  = roc_auc_score(y_test, y_prob)

    importances = getattr(clf, "feature_importances_", np.zeros(len(feature_cols)))
    feat_imp    = sorted(zip(feature_cols, importances),
                         key=lambda x: x[1], reverse=True)

    return {
        "accuracy":  round(acc, 4),
        "precision": round(prec, 4),
        "recall":    round(rec, 4),
        "f1_score":  round(f1, 4),
        "roc_auc":   round(auc, 4),
        "feature_importance": [
            {"feature": n, "importance": round(float(i), 4)} for n, i in feat_imp
        ],
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
    }


def print_report(name, metrics):
    print(f"\n{'='*55}")
    print(f"  {name} — Evaluation")
    print(f"{'='*55}")
    print(f"  Accuracy  : {metrics['accuracy']*100:.2f}%")
    print(f"  Precision : {metrics['precision']*100:.2f}%")
    print(f"  Recall    : {metrics['recall']*100:.2f}%")
    print(f"  F1-Score  : {metrics['f1_score']*100:.2f}%")
    print(f"  ROC-AUC   : {metrics['roc_auc']*100:.2f}%")


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    os.makedirs(MODEL_DIR, exist_ok=True)

    X, y, feature_cols, city_encoder, df_full = load_data(DATA_PATH)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    # ── Train supervised classifiers ──────────────────────────────────────────
    rf         = train_random_forest(X_train, y_train)
    rf_metrics = evaluate(rf, X_test, y_test, feature_cols)
    print_report("Random Forest", rf_metrics)

    best_clf     = rf
    best_metrics = rf_metrics
    best_name    = "Random Forest"

    if XGBOOST_AVAILABLE:
        xgb         = train_xgboost(X_train, y_train)
        xgb_metrics = evaluate(xgb, X_test, y_test, feature_cols)
        print_report("XGBoost", xgb_metrics)

        # Auto-select winner by ROC-AUC
        if xgb_metrics["roc_auc"] >= rf_metrics["roc_auc"]:
            best_clf     = xgb
            best_metrics = xgb_metrics
            best_name    = "XGBoost"

        best_metrics["vs_random_forest"] = {
            "accuracy": rf_metrics["accuracy"],
            "roc_auc":  rf_metrics["roc_auc"],
        }
        best_metrics["vs_xgboost"] = {
            "accuracy": xgb_metrics["accuracy"],
            "roc_auc":  xgb_metrics["roc_auc"],
        }
    else:
        print("\nXGBoost not installed — using Random Forest only.")

    print(f"\n🏆 Winner: {best_name} (ROC-AUC={best_metrics['roc_auc']*100:.2f}%)")
    best_metrics["model_type"] = best_name

    # ── Train anomaly detection model ─────────────────────────────────────────
    anomaly_model, fraud_rate = train_anomaly_model(df_full, feature_cols)
    best_metrics["anomaly_detection"] = {
        "algorithm":         "IsolationForest",
        "trained_on":        "legitimate_only",
        "contamination":     round(fraud_rate, 4),
        "novelty_threshold": 65,
        "description": (
            "Scores 0-100. Values >65 indicate a novel/unknown "
            "transaction pattern not seen during training."
        ),
    }

    # ── Save artefacts ────────────────────────────────────────────────────────
    joblib.dump({"model": best_clf, "city_encoder": city_encoder}, MODEL_PATH)
    joblib.dump(feature_cols, FEATS_PATH)
    joblib.dump(anomaly_model, ANOMALY_PATH)

    with open(METRICS_PATH, "w") as f:
        json.dump(best_metrics, f, indent=2)

    print(f"\n✅ Model saved        : {MODEL_PATH}")
    print(f"✅ Anomaly model saved: {ANOMALY_PATH}")
    print(f"✅ Feature cols saved : {FEATS_PATH}")
    print(f"✅ Metrics saved      : {METRICS_PATH}")
    print(f"\n  Final model   : {best_name}")
    print(f"  Accuracy      : {best_metrics['accuracy']*100:.2f}%")
    print(f"  ROC-AUC       : {best_metrics['roc_auc']*100:.2f}%")
    print(f"  Anomaly model : IsolationForest  "
          f"(contamination={fraud_rate*100:.2f}%, novelty_threshold=65)")


if __name__ == "__main__":
    main()
