# 🛡️ UPI Shield — AI-Driven UPI Fraud Detection Framework

A production-structured, full-stack web application for real-time UPI transaction fraud detection using Machine Learning.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Browser (Frontend)                          │
│  index.html (Login) → dashboard.html + transactions.html    │
│  Chart.js + Leaflet.js + Socket.IO client                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP + WebSocket
┌──────────────────────▼──────────────────────────────────────┐
│              Flask Backend (backend/app.py)                  │
│  JWT Auth │ REST API │ Flask-SocketIO (live feed)           │
│  Routes: /api/auth/* /api/transactions/* /api/dashboard/*    │
└──────────────────────┬──────────────────────────────────────┘
                       │
          ┌────────────┴─────────────┐
          │                          │
┌─────────▼──────────┐    ┌──────────▼────────┐
│  SQLite Database    │    │   ML Model (pkl)   │
│  users, txns,       │    │  Random Forest     │
│  alerts, audit_logs │    │  (scikit-learn)    │
└────────────────────┘    └───────────────────┘
```

---

## 📁 Project Structure

```
upi_fraud_ai_framework/
├── backend/
│   ├── app.py              ← Main Flask entry point
│   ├── config.py           ← Environment config
│   ├── requirements.txt    ← Python dependencies
│   ├── .env                ← Environment variables
│   ├── database/
│   │   ├── db.py           ← SQLite helpers
│   │   └── schema.sql      ← Table definitions
│   ├── routes/
│   │   ├── auth.py         ← /api/auth/* (register, login)
│   │   ├── transactions.py ← /api/transactions/*
│   │   ├── dashboard.py    ← /api/dashboard/*
│   │   └── model_routes.py ← /api/model/* (retrain)
│   └── utils/
│       ├── fraud_engine.py ← ML model wrapper
│       └── logger.py       ← Rotating file logger
├── ml/
│   ├── generate_data.py    ← Synthetic data generator
│   ├── train_model.py      ← Model training script
│   ├── fraud_predictor.py  ← Prediction class
│   └── models/             ← Saved .pkl files (auto-created)
└── frontend/
    ├── index.html          ← Login page
    ├── dashboard.html      ← Main dashboard
    ├── transactions.html   ← Transaction simulator
    ├── css/style.css       ← Dark-mode premium styles
    └── js/
        ├── auth.js         ← JWT auth + route guard
        ├── charts.js       ← Chart.js configurations
        ├── dashboard.js    ← Stats, live feed, heatmap
        └── transactions.js ← Form submit, gauge, history
```

---

## 🚀 Quick Start (Step-by-Step)

### Step 1 — Install Python dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Step 2 — Train the ML model

```bash
# Generate 10,000 synthetic UPI transactions
cd ../ml
python generate_data.py

# Train the Random Forest model (~30 seconds)
python train_model.py
```

Expected output:
```
✅ MODEL EVALUATION REPORT
  Accuracy  : 94.xx%
  F1-Score  : 91.xx%
  ROC-AUC   : 97.xx%
✅ Model saved to: ml/models/fraud_model.pkl
```

### Step 3 — Start the Flask backend

```bash
cd ../backend
python app.py
```

Server starts at: **http://localhost:5000**

### Step 4 — Open the app

Open your browser and go to: **http://localhost:5000**

1. Click **Register** → create an account (choose **Admin** for full access)
2. Login → you're redirected to the Dashboard
3. Click **Check Transaction** in the sidebar to test fraud detection

---

## 🤖 AI/ML Model Details

| Property | Value |
|---|---|
| Algorithm | Random Forest Classifier (200 trees) |
| Training data | 10,000 synthetic UPI transactions |
| Fraud rate | ~12% (class-balanced training) |
| Features | Amount, Hour, Day, City, Device, Frequency, Avg Amount, Is Night, Amount Ratio |
| Output | Fraud score (0–100%), Label (Fraud/Legitimate), Risk (Low/Medium/High) |
| Accuracy | ~94% | F1-Score | ~91% |

### Fraud Detection Rules (used in data generation)
- 🌙 **Late night** (12am–5am): higher fraud risk
- 💰 **High amount** (> ₹30,000): higher fraud risk  
- 📱 **New device**: higher fraud risk
- ⚡ **High frequency** (> 8 txns/hour): higher fraud risk
- 🔀 **Combo** of the above: very high risk

---

## 🔐 API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login → returns JWT |
| GET  | `/api/auth/me` | Current user info |

### Transactions (JWT required)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/transactions/check` | Fraud check on a transaction |
| GET  | `/api/transactions/` | Transaction history |
| POST | `/api/transactions/block/<id>` | Block a transaction |

### Dashboard (JWT required)
| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/dashboard/stats` | Summary stats |
| GET | `/api/dashboard/feed` | Last 25 transactions |
| GET | `/api/dashboard/heatmap` | Fraud location data |
| GET | `/api/dashboard/hourly` | Fraud by hour |
| GET | `/api/dashboard/feature-importance` | ML feature importance |

### Model (Admin JWT required)
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/model/retrain` | Retrain model (admin only) |
| GET  | `/api/model/metrics` | Model accuracy metrics |

---

## 🔐 Security Features

- **JWT tokens** — expire after 1 hour, stored in `localStorage`
- **bcrypt password hashing** — industry-standard salted hashing
- **Role-based access** — Admin-only endpoints for model retraining
- **CORS** — configured for `localhost` development
- **Audit logging** — all block actions are logged to `audit_logs` table
- **Rotating file logger** — 5MB × 3 backup log files

---

## 🧑‍💻 For B.Tech Students — How it all works

1. **Frontend** sends an HTTP POST to `/api/transactions/check` with transaction data
2. **Flask backend** receives the request, validates the JWT token
3. **`fraud_engine.py`** passes the data to the trained **Random Forest model**
4. The model outputs a **fraud probability** (0.0 to 1.0), which is scaled to 0–100%
5. The result is **stored in SQLite** and returned as JSON
6. **Socket.IO** broadcasts simulated live transactions every 4 seconds
7. The **dashboard** charts auto-update every 8 seconds via polling

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---|---|
| `Model not found` error | Run `python ml/train_model.py` first |
| `ModuleNotFoundError` | Run `pip install -r backend/requirements.txt` |
| Port 5000 in use | Kill the old process or change port in `app.py` |
| Login page doesn't redirect | Check browser console — is Flask running? |
| Charts don't appear | Make sure you've submitted some transactions first |
