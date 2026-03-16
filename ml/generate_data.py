"""
generate_data.py
----------------
Maps the REAL Kaggle creditcard.csv dataset to UPI transaction features.
creditcard.csv has 284,807 rows: V1-V28 (PCA), Amount, Class (0=legit, 1=fraud).

We sample and enrich it with realistic UPI-specific fields (city, hour, device,
frequency, etc.) based on the fraud label -> producing a production-grade dataset.

Usage:
    python generate_data.py
Output:
    ml/data/upi_transactions.csv
"""

import numpy as np
import pandas as pd
import random
import os

np.random.seed(42)
random.seed(42)

REAL_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "..", "dataset", "creditcard.csv"
)

CITIES = [
    "Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai",
    "Kolkata", "Pune", "Jaipur", "Ahmedabad", "Surat",
    "Lucknow", "Kanpur", "Nagpur", "Patna", "Bhopal"
]

CITY_COORDS = {
    "Mumbai":    (19.0760, 72.8777), "Delhi":     (28.6139, 77.2090),
    "Bangalore": (12.9716, 77.5946), "Hyderabad": (17.3850, 78.4867),
    "Chennai":   (13.0827, 80.2707), "Kolkata":   (22.5726, 88.3639),
    "Pune":      (18.5204, 73.8567), "Jaipur":    (26.9124, 75.7873),
    "Ahmedabad": (23.0225, 72.5714), "Surat":     (21.1702, 72.8311),
    "Lucknow":   (26.8467, 80.9462), "Kanpur":    (26.4499, 80.3319),
    "Nagpur":    (21.1458, 79.0882), "Patna":     (25.5941, 85.1376),
    "Bhopal":    (23.2599, 77.4126),
}

# Target dataset size – large enough for a good model, fast enough to train
N_SAMPLES  = 50_000
FRAUD_RATE = 0.15     # 15% fraud rate


def jitter(coord, scale=0.3):
    return round(coord + np.random.uniform(-scale, scale), 6)


def enrich_row(row, is_fraud: bool) -> dict:
    """Convert a real creditcard.csv row into a UPI transaction dict."""
    city = random.choice(CITIES)
    lat, lng = CITY_COORDS[city]

    # Amount: use real Amount scaled to INR (×80 ≈ USD→INR), clamp
    amount = round(float(row["Amount"]) * 80 + 50, 2)
    amount = max(10.0, min(amount, 500_000.0))

    if is_fraud:
        # Fraud patterns: late night, rapid frequency, new device, large amount
        fraud_type = random.choice(["late_night", "high_amount", "new_device", "combo"])
        hour       = random.randint(0, 4) if "night" in fraud_type or "combo" == fraud_type else random.randint(0, 23)
        freq       = random.randint(8, 25)   if "combo" == fraud_type else random.randint(5, 15)
        is_new_dev = 1 if fraud_type in ("new_device", "combo") else random.choice([0, 0, 1])
        if fraud_type in ("high_amount", "combo"):
            amount = round(np.random.uniform(40_000, 200_000), 2)
        user_avg   = round(amount * np.random.uniform(0.05, 0.35), 2)
        device_id  = f"DEV_NEW_{random.randint(10000, 99999)}" if is_new_dev else f"DEV_{random.randint(1000, 9999)}"
        lat_j, lng_j = jitter(lat, 1.0), jitter(lng, 1.0)
    else:
        hour       = int(np.random.choice(range(24), p=_hour_weights()))
        freq       = random.randint(1, 5)
        is_new_dev = random.choice([0, 0, 0, 1])
        user_avg   = round(amount * np.random.uniform(0.8, 1.3), 2)
        device_id  = f"DEV_{random.randint(1000, 9999)}"
        lat_j, lng_j = jitter(lat, 0.3), jitter(lng, 0.3)

    amt_ratio = round(amount / (user_avg + 1), 4)
    is_night  = 1 if (hour <= 5 or hour >= 22) else 0

    return {
        "amount":                amount,
        "hour":                  hour,
        "day_of_week":           random.randint(0, 6),
        "latitude":              lat_j,
        "longitude":             lng_j,
        "city":                  city,
        "device_id":             device_id,
        "transaction_frequency": freq,
        "user_avg_amount":       user_avg,
        "is_new_device":         is_new_dev,
        "amount_to_avg_ratio":   amt_ratio,
        "is_night":              is_night,
        "is_fraud":              int(is_fraud),
    }


def _hour_weights():
    """Business-hours weighted distribution for legitimate txns (sums to 1)."""
    raw = [0.010, 0.005, 0.005, 0.005, 0.005, 0.010,
           0.030, 0.060, 0.080, 0.080, 0.080, 0.070,
           0.070, 0.070, 0.070, 0.070, 0.070, 0.060,
           0.060, 0.050, 0.040, 0.030, 0.020, 0.015]
    total = sum(raw)
    return [w / total for w in raw]


def main():
    print(f"Loading real dataset from: {REAL_DATA_PATH}")
    df_real = pd.read_csv(REAL_DATA_PATH)
    print(f"  Real dataset shape : {df_real.shape}")
    print(f"  Real fraud rate    : {df_real['Class'].mean()*100:.2f}%")

    n_fraud = int(N_SAMPLES * FRAUD_RATE)
    n_legit = N_SAMPLES - n_fraud

    # Sample from each class in the real dataset
    legit_rows = df_real[df_real["Class"] == 0].sample(n=n_legit, random_state=42)
    fraud_rows = df_real[df_real["Class"] == 1].sample(
        n=min(n_fraud, len(df_real[df_real["Class"] == 1])),
        replace=(n_fraud > len(df_real[df_real["Class"] == 1])),
        random_state=42
    )

    print(f"\nEnriching {n_legit:,} legitimate + {n_fraud:,} fraud rows with UPI features...")
    records = []
    for _, row in legit_rows.iterrows():
        records.append(enrich_row(row, is_fraud=False))
    for _, row in fraud_rows.iterrows():
        records.append(enrich_row(row, is_fraud=True))

    df = pd.DataFrame(records).sample(frac=1, random_state=42).reset_index(drop=True)
    df.insert(0, "txn_id", [f"TXN{str(i).zfill(6)}" for i in range(len(df))])

    os.makedirs("data", exist_ok=True)
    out_path = os.path.join("data", "upi_transactions.csv")
    df.to_csv(out_path, index=False)

    total = len(df)
    fraud_count = df["is_fraud"].sum()
    print(f"\n✅ Dataset saved to : {out_path}")
    print(f"   Total records    : {total:,}")
    print(f"   Legitimate       : {total - fraud_count:,}  ({(total-fraud_count)/total*100:.1f}%)")
    print(f"   Fraud            : {fraud_count:,}  ({fraud_count/total*100:.1f}%)")
    print(f"   Features         : {[c for c in df.columns if c not in ('txn_id',)]}")


if __name__ == "__main__":
    main()
