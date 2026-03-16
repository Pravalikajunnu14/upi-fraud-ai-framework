-- UPI Fraud Detection Framework - Database Schema
-- SQLite compatible

PRAGMA foreign_keys = ON;

-- ─── Users table ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT    NOT NULL UNIQUE,
    email       TEXT,
    password    TEXT    NOT NULL,       -- bcrypt hashed
    role        TEXT    NOT NULL DEFAULT 'user',  -- 'admin' | 'user'
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    last_login  TEXT
);

-- ─── Transactions table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS transactions (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id                 TEXT    NOT NULL UNIQUE,
    user_id                INTEGER REFERENCES users(id),
    upi_id                 TEXT,
    amount                 REAL    NOT NULL,
    city                   TEXT    NOT NULL,
    latitude               REAL,
    longitude              REAL,
    device_id              TEXT,
    hour                   INTEGER,
    day_of_week            INTEGER,
    transaction_frequency  INTEGER,
    user_avg_amount        REAL,
    is_new_device          INTEGER DEFAULT 0,
    fraud_score            REAL,
    label                  TEXT,   -- 'Fraud' | 'Legitimate'
    risk_level             TEXT,   -- 'Low' | 'Medium' | 'High'
    is_blocked             INTEGER DEFAULT 0,
    created_at             TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ─── Fraud alerts table ───────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    txn_id      TEXT    NOT NULL,
    fraud_score REAL    NOT NULL,
    risk_level  TEXT    NOT NULL,
    alert_type  TEXT,                -- 'high_amount' | 'new_device' | 'late_night' etc.
    resolved    INTEGER DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ─── Audit logs table ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER REFERENCES users(id),
    action      TEXT    NOT NULL,
    details     TEXT,
    ip_address  TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- ─── Indexes ──────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_txn_created  ON transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_txn_label    ON transactions(label);
CREATE INDEX IF NOT EXISTS idx_txn_city     ON transactions(city);
CREATE INDEX IF NOT EXISTS idx_alerts_txn   ON fraud_alerts(txn_id);
