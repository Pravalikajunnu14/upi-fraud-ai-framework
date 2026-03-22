"""
db.py
-----
SQLite connection helpers for the UPI Fraud Detection backend.
"""

import sqlite3
import os
import bcrypt
from config import Config

DB_PATH = Config.DB_PATH
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_db():
    """Return a new SQLite connection with row_factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Create all tables from schema.sql if they don't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    with open(SCHEMA_PATH, "r") as f:
        sql = f.read()
    conn.executescript(sql)
    conn.commit()
    conn.close()
    print(f"[OK] Database initialised at: {DB_PATH}")
    _seed_default_users()


def _seed_default_users():
    """Create default admin and user accounts if no users exist."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if count == 0:
        defaults = [
            ("admin", "admin123", "junnupravalika59@gmail.com", "admin"),
            ("user",  "user123",  "junnupravalika59@gmail.com",  "user"),
        ]
        for username, password, email, role in defaults:
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?, ?, ?, ?)",
                (username, hashed, email, role)
            )
        conn.commit()
        print("[OK] Default accounts created: admin/admin123  and  user/user123")
    conn.close()


def query(sql, params=(), one=False):
    """Execute a SELECT query. Returns one row or a list of rows."""
    conn = get_db()
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    if one:
        return dict(rows[0]) if rows else None
    return [dict(r) for r in rows]


def execute(sql, params=()):
    """Execute INSERT / UPDATE / DELETE. Returns lastrowid."""
    conn = get_db()
    cur = conn.execute(sql, params)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id
