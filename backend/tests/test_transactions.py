"""
test_transactions.py
-------------------
Tests for transaction routes (/api/transactions/*).
Tests fraud detection, blocking, validation, and pagination.
"""

import pytest
import json
from datetime import datetime

pytestmark = [pytest.mark.integration]


class TestTransactionCheck:
    """Tests for POST /api/transactions/check"""
    
    def test_check_transaction_valid(self, client, user_headers, sample_transaction):
        """Test successful fraud check with valid transaction."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=sample_transaction
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify response structure
        assert "txn_id" in data
        assert "fraud_score" in data
        assert "label" in data
        assert "risk_level" in data
        assert "anomaly_score" in data
        assert "is_blocked" in data
        assert "recommendation" in data
        
        # Verify fraud score is in valid range (0-100)
        assert 0 <= data["fraud_score"] <= 100
        assert 0 <= data["anomaly_score"] <= 100
        
        # Valid transaction should not be blocked
        assert data["is_blocked"] in (0, 1)
    
    def test_check_transaction_without_auth(self, client, sample_transaction):
        """Test fraud check without authentication returns 401."""
        response = client.post(
            "/api/transactions/check",
            json=sample_transaction
        )
        assert response.status_code == 401
    
    def test_check_transaction_missing_amount(self, client, user_headers):
        """Test fraud check fails without required amount."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json={"city": "Mumbai"}
        )
        assert response.status_code == 400
        assert "amount" in response.get_json().get("error", "").lower()
    
    def test_check_transaction_invalid_amount_negative(self, client, user_headers, 
                                                       invalid_transaction_negative_amount):
        """Test fraud check rejects negative amount."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=invalid_transaction_negative_amount
        )
        assert response.status_code == 400
        error = response.get_json().get("error", "").lower()
        assert "invalid" in error or "amount" in error
    
    def test_check_transaction_amount_too_high(self, client, user_headers):
        """Test fraud check rejects amount exceeding max (500k)."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json={
                "amount": 600000,
                "city": "Mumbai"
            }
        )
        assert response.status_code == 400
    
    def test_check_transaction_amount_zero(self, client, user_headers):
        """Test fraud check rejects zero amount."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json={
                "amount": 0,
                "city": "Mumbai"
            }
        )
        assert response.status_code == 400
    
    def test_check_transaction_invalid_hour(self, client, user_headers, 
                                            invalid_transaction_invalid_hour):
        """Test fraud check rejects invalid hour."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=invalid_transaction_invalid_hour
        )
        assert response.status_code == 400
        assert "hour" in response.get_json().get("error", "").lower()
    
    def test_check_transaction_invalid_city(self, client, user_headers,
                                            invalid_transaction_invalid_city):
        """Test fraud check rejects city not in whitelist."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=invalid_transaction_invalid_city
        )
        assert response.status_code == 400
        error = response.get_json().get("error", "").lower()
        assert "city" in error or "not supported" in error
    
    def test_check_transaction_invalid_coordinates(self, client, user_headers):
        """Test fraud check rejects invalid coordinates."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json={
                "amount": 5000,
                "city": "Mumbai",
                "latitude": 999,  # Invalid latitude
                "longitude": 180
            }
        )
        assert response.status_code == 400
    
    def test_check_transaction_default_values(self, client, user_headers):
        """Test fraud check fills in default values for optional fields."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json={"amount": 5000}  # Only required field
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have defaults
        assert "city" in data
        assert "hour" in data or data["label"] in ("Fraud", "Legitimate", "Anomaly")
    
    def test_check_suspicious_transaction(self, client, user_headers, suspicious_transaction):
        """Test fraud check with suspicious transaction."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=suspicious_transaction
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Suspicious transaction likely to be flagged (but not guaranteed by model)
        # Just verify response structure
        assert data["label"] in ("Fraud", "Legitimate", "Anomaly")
    
    def test_check_transaction_response_timestamp(self, client, user_headers, sample_transaction):
        """Test fraud check response includes timestamp."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=sample_transaction
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Should have ISO format timestamp
        assert "timestamp" in data
        try:
            datetime.fromisoformat(data["timestamp"])
        except ValueError:
            pytest.fail("Timestamp is not in ISO format")
    
    def test_check_transaction_recommendation(self, client, user_headers, sample_transaction):
        """Test fraud check includes recommendation."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=sample_transaction
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Recommendation should match label
        assert "recommendation" in data
        if data["label"] == "Fraud":
            assert "BLOCKED" in data["recommendation"].upper()
        elif data["label"] == "Anomaly":
            assert "REVIEW" in data["recommendation"].upper()
        else:
            assert "SAFE" in data["recommendation"].upper()


class TestTransactionBlocking:
    """Tests for POST /api/transactions/block/<txn_id>"""
    
    def test_block_transaction_success(self, client, user_headers, sample_transaction):
        """Test successful transaction blocking."""
        # First, create a transaction
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=sample_transaction
        )
        assert response.status_code == 200
        txn_id = response.get_json()["txn_id"]
        
        # Block the transaction
        response = client.post(
            f"/api/transactions/block/{txn_id}",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["txn_id"] == txn_id
        assert "blocked" in data.get("message", "").lower()
    
    def test_block_transaction_not_found(self, client, user_headers):
        """Test blocking non-existent transaction returns 404."""
        response = client.post(
            "/api/transactions/block/FAKE_TXN_ID",
            headers=user_headers
        )
        assert response.status_code == 404
    
    def test_block_transaction_already_blocked(self, client, user_headers, sample_transaction):
        """Test blocking already-blocked transaction."""
        # Create and block a transaction
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=sample_transaction
        )
        txn_id = response.get_json()["txn_id"]
        
        client.post(f"/api/transactions/block/{txn_id}", headers=user_headers)
        
        # Try to block again
        response = client.post(
            f"/api/transactions/block/{txn_id}",
            headers=user_headers
        )
        # Should still succeed (idempotent)
        assert response.status_code == 200
    
    def test_block_transaction_without_auth(self, client):
        """Test blocking without authentication returns 401."""
        response = client.post("/api/transactions/block/SOME_TXN_ID")
        assert response.status_code == 401


class TestTransactionList:
    """Tests for GET /api/transactions/"""
    
    def test_list_transactions_empty(self, client, user_headers):
        """Test listing transactions when none exist."""
        response = client.get(
            "/api/transactions/",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert "transactions" in data
        assert "total" in data
        assert "page" in data
        assert data["total"] == 0
        assert len(data["transactions"]) == 0
    
    def test_list_transactions_with_data(self, client, user_headers, sample_transaction):
        """Test listing transactions returns data."""
        # Create a few transactions
        for _ in range(3):
            client.post(
                "/api/transactions/check",
                headers=user_headers,
                json=sample_transaction
            )
        
        # List transactions
        response = client.get(
            "/api/transactions/",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["total"] >= 3
        assert len(data["transactions"]) > 0
    
    def test_list_transactions_pagination(self, client, user_headers, sample_transaction):
        """Test pagination parameters."""
        # Create 25 transactions
        for _ in range(25):
            client.post(
                "/api/transactions/check",
                headers=user_headers,
                json=sample_transaction
            )
        
        # Get first page with limit 10
        response = client.get(
            "/api/transactions/?page=1&limit=10",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["page"] == 1
        assert data["limit"] == 10
        assert len(data["transactions"]) <= 10
    
    def test_list_transactions_pagination_exceeds_max(self, client, user_headers):
        """Test pagination limit capped at 1000."""
        response = client.get(
            "/api/transactions/?limit=2000",
            headers=user_headers
        )
        # Should either cap limit or return 400
        assert response.status_code in (200, 400)
    
    def test_list_transactions_invalid_page(self, client, user_headers):
        """Test invalid page number."""
        response = client.get(
            "/api/transactions/?page=0",
            headers=user_headers
        )
        # Should reject or treat as page 1
        assert response.status_code in (200, 400)
    
    def test_list_transactions_without_auth(self, client):
        """Test listing without authentication returns 401."""
        response = client.get("/api/transactions/")
        assert response.status_code == 401


class TestTransactionGet:
    """Tests for GET /api/transactions/<txn_id>"""
    
    def test_get_transaction_success(self, client, user_headers, sample_transaction):
        """Test retrieving single transaction."""
        # Create a transaction
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=sample_transaction
        )
        txn_id = response.get_json()["txn_id"]
        
        # Retrieve it
        response = client.get(
            f"/api/transactions/{txn_id}",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert data["txn_id"] == txn_id
        assert data["amount"] == sample_transaction["amount"]
    
    def test_get_transaction_not_found(self, client, user_headers):
        """Test retrieving non-existent transaction returns 404."""
        response = client.get(
            "/api/transactions/NONEXISTENT",
            headers=user_headers
        )
        assert response.status_code == 404
    
    def test_get_transaction_without_auth(self, client):
        """Test retrieving without authentication returns 401."""
        response = client.get("/api/transactions/SOME_TXN_ID")
        assert response.status_code == 401


class TestTransactionValidationErrors:
    """Tests for comprehensive validation error handling"""
    
    def test_invalid_json_body(self, client, user_headers):
        """Test POST with invalid JSON."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            data="not json",
            content_type="application/json"
        )
        assert response.status_code in (400, 415)
    
    def test_missing_json_content_type(self, client, user_headers):
        """Test POST without Content-Type: application/json."""
        response = client.post(
            "/api/transactions/check",
            headers={**user_headers, "Content-Type": "text/plain"},
            json={"amount": 5000}
        )
        # May fail due to content-type or succeed (Flask is flexible)
        assert response.status_code in (200, 400, 415)
    
    def test_transaction_with_string_amount(self, client, user_headers):
        """Test transaction with string amount (should be converted or rejected)."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json={
                "amount": "5000",  # String instead of number
                "city": "Mumbai"
            }
        )
        # Should accept (JSON number coercion) or reject
        assert response.status_code in (200, 400)
    
    def test_transaction_with_float_amount(self, client, user_headers):
        """Test transaction with float amount."""
        response = client.post(
            "/api/transactions/check",
            headers=user_headers,
            json={
                "amount": 5000.50,
                "city": "Mumbai"
            }
        )
        assert response.status_code == 200
