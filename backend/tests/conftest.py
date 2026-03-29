"""
conftest.py
-----------
Pytest configuration and shared fixtures for all backend tests.
Provides Flask app, database, JWT tokens, and sample data.
"""

import pytest
import os
import sqlite3
import tempfile
import bcrypt
import sys
from datetime import datetime, timedelta

# Setup path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session")
def temp_db_dir():
    """Create a temporary directory for test databases."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir


@pytest.fixture
def app(temp_db_dir, monkeypatch):
    """
    Create Flask app with test database.
    Each test gets a fresh database.
    """
    # Use temporary database for tests
    test_db_path = os.path.join(temp_db_dir, f"test_{os.getpid()}_{id(monkeypatch)}.db")
    
    # Set env vars FIRST, before any imports that use config
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-12345")
    monkeypatch.setenv("JWT_SECRET_KEY", "test-jwt-key-67890")
    monkeypatch.setenv("DB_PATH", test_db_path)
    monkeypatch.setenv("FLASK_ENV", "testing")
    monkeypatch.setenv("DEBUG", "False")
    monkeypatch.setenv("SETUP_MODE", "0")
    
    # Clear any cached modules so they reload with new env vars
    modules_to_clear = [k for k in sys.modules.keys() if 'backend' in k or k == 'config' or k == 'app']
    for module in modules_to_clear:
        del sys.modules[module]
    
    # Now import with fresh env vars
    from app import create_app
    from database.db import get_db
    
    app = create_app()
    app.config["TESTING"] = True
    
    # Create test database and schema
    with app.app_context():
        conn = get_db()
        
        # Load and execute schema
        schema_path = os.path.join(os.path.dirname(__file__), "..", "database", "schema.sql")
        with open(schema_path, "r") as f:
            schema = f.read()
        conn.executescript(schema)
        conn.commit()
        
        # Seed test users (check if they don't exist first)
        admin_exists = conn.execute("SELECT id FROM users WHERE username = ?", ("admin_test",)).fetchone()
        if not admin_exists:
            admin_hash = bcrypt.hashpw(b"admin_password", bcrypt.gensalt()).decode()
            user_hash = bcrypt.hashpw(b"user_password", bcrypt.gensalt()).decode()
            
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?,?,?,?)",
                ("admin_test", "admin@test.com", admin_hash, "admin")
            )
            conn.execute(
                "INSERT INTO users (username, email, password, role) VALUES (?,?,?,?)",
                ("user_test", "user@test.com", user_hash, "user")
            )
            conn.commit()
        conn.close()
    
    yield app
    
    # Cleanup
    if os.path.exists(test_db_path):
        try:
            os.remove(test_db_path)
        except OSError:
            pass  # File already deleted or in use


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Flask CLI test runner."""
    return app.test_cli_runner()


@pytest.fixture
def admin_token(client):
    """
    Create JWT token for admin user.
    Returns the token string for use in Authorization headers.
    """
    response = client.post(
        "/api/auth/login",
        json={
            "username": "admin_test",
            "password": "admin_password"
        }
    )
    assert response.status_code == 200
    data = response.get_json()
    return data["access_token"]


@pytest.fixture
def user_token(client):
    """
    Create JWT token for regular user.
    Returns the token string for use in Authorization headers.
    """
    response = client.post(
        "/api/auth/login",
        json={
            "username": "user_test",
            "password": "user_password"
        }
    )
    assert response.status_code == 200
    data = response.get_json()
    return data["access_token"]


@pytest.fixture
def admin_headers(admin_token):
    """HTTP headers with admin JWT token."""
    return {
        "Authorization": f"Bearer {admin_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def user_headers(user_token):
    """HTTP headers with user JWT token."""
    return {
        "Authorization": f"Bearer {user_token}",
        "Content-Type": "application/json"
    }


@pytest.fixture
def sample_transaction():
    """Sample valid transaction data for testing."""
    return {
        "amount": 5000,
        "city": "Mumbai",
        "hour": 14,
        "day_of_week": 3,
        "device_id": "DEV_1234",
        "upi_id": "user@okhdfcbank",
        "transaction_frequency": 5,
        "user_avg_amount": 4500,
        "is_new_device": 0
    }


@pytest.fixture
def suspicious_transaction():
    """Transaction with fraud red flags."""
    return {
        "amount": 200000,  # Very high amount
        "city": "Delhi",
        "hour": 3,  # Late night
        "day_of_week": 5,
        "device_id": "DEV_NEW_9999",
        "upi_id": "attacker@bank",
        "transaction_frequency": 20,  # Very high frequency
        "user_avg_amount": 5000,  # Extreme ratio
        "is_new_device": 1  # New device
    }


@pytest.fixture
def invalid_transaction_negative_amount():
    """Transaction with invalid (negative) amount."""
    return {
        "amount": -1000,
        "city": "Mumbai"
    }


@pytest.fixture
def invalid_transaction_no_amount():
    """Transaction without required amount field."""
    return {
        "city": "Mumbai"
    }


@pytest.fixture
def invalid_transaction_invalid_hour():
    """Transaction with invalid hour."""
    return {
        "amount": 5000,
        "hour": 25  # Invalid hour
    }


@pytest.fixture
def invalid_transaction_invalid_city():
    """Transaction with city not in whitelist."""
    return {
        "amount": 5000,
        "city": "InvalidCityName"
    }


# ─── Pytest Configuration ──────────────────────────────────────────────────────

def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (fast, no DB)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
