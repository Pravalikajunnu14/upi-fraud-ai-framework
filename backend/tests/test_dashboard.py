"""
test_dashboard.py
-----------------
Tests for dashboard routes (/api/dashboard/*).
Tests statistics, fraud feed, heatmap data, and fraud alerts.
"""

import pytest
from datetime import datetime

pytestmark = [pytest.mark.integration]


class TestDashboardStats:
    """Tests for GET /api/dashboard/stats"""
    
    def test_get_stats_success(self, client, user_headers):
        """Test retrieving dashboard statistics."""
        response = client.get(
            "/api/dashboard/stats",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Verify expected fields
        assert "total_transactions" in data
        assert "fraud_count" in data
        assert "fraud_rate" in data
        assert "anomaly_count" in data
        assert "avg_fraud_score" in data
        assert "high_risk_count" in data
    
    def test_get_stats_without_auth(self, client):
        """Test stats endpoint without authentication returns 401."""
        response = client.get("/api/dashboard/stats")
        assert response.status_code == 401
    
    def test_stats_values_are_numeric(self, client, user_headers):
        """Test that all stats values are numeric."""
        response = client.get(
            "/api/dashboard/stats",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Check numeric types
        assert isinstance(data["total_transactions"], (int, float))
        assert isinstance(data["fraud_count"], (int, float))
        assert isinstance(data["fraud_rate"], (int, float))
        assert 0 <= data["fraud_rate"] <= 100  # Fraud rate as percentage


class TestDashboardFeed:
    """Tests for GET /api/dashboard/feed"""
    
    def test_get_feed_empty(self, client, user_headers):
        """Test retrieving feed when no transactions exist."""
        response = client.get(
            "/api/dashboard/feed",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert "transactions" in data
        assert isinstance(data["transactions"], list)
        assert len(data["transactions"]) == 0
    
    def test_get_feed_with_data(self, client, user_headers, sample_transaction):
        """Test retrieving feed with transactions."""
        # Create a few transactions
        for _ in range(3):
            client.post(
                "/api/transactions/check",
                headers=user_headers,
                json=sample_transaction
            )
        
        response = client.get(
            "/api/dashboard/feed",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data["transactions"]) > 0
    
    def test_get_feed_pagination(self, client, user_headers, sample_transaction):
        """Test feed pagination."""
        # Create multiple transactions
        for _ in range(15):
            client.post(
                "/api/transactions/check",
                headers=user_headers,
                json=sample_transaction
            )
        
        response = client.get(
            "/api/dashboard/feed?limit=5",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert len(data["transactions"]) <= 5
    
    def test_get_feed_without_auth(self, client):
        """Test feed without authentication returns 401."""
        response = client.get("/api/dashboard/feed")
        assert response.status_code == 401


class TestDashboardHeatmap:
    """Tests for GET /api/dashboard/heatmap"""
    
    def test_get_heatmap_success(self, client, user_headers):
        """Test retrieving heatmap data."""
        response = client.get(
            "/api/dashboard/heatmap",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Heatmap should have geographic fraud data
        assert isinstance(data, (dict, list))
    
    def test_get_heatmap_without_auth(self, client):
        """Test heatmap without authentication returns 401."""
        response = client.get("/api/dashboard/heatmap")
        assert response.status_code == 401
    
    def test_get_heatmap_with_fraud_data(self, client, user_headers, suspicious_transaction):
        """Test heatmap with fraud transactions."""
        # Create suspicious transaction
        client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=suspicious_transaction
        )
        
        response = client.get(
            "/api/dashboard/heatmap",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        # Should return some data structure
        assert data is not None


class TestDashboardAlerts:
    """Tests for GET /api/dashboard/alerts"""
    
    def test_get_alerts_empty(self, client, user_headers):
        """Test retrieving alerts when none exist."""
        response = client.get(
            "/api/dashboard/alerts",
            headers=user_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        
        assert "alerts" in data or isinstance(data, list)
    
    def test_get_alerts_unresolved(self, client, user_headers, suspicious_transaction):
        """Test retrieving unresolved alerts."""
        # Create a suspicious transaction (should generate alert)
        client.post(
            "/api/transactions/check",
            headers=user_headers,
            json=suspicious_transaction
        )
        
        response = client.get(
            "/api/dashboard/alerts?resolved=0",
            headers=user_headers
        )
        assert response.status_code == 200
    
    def test_get_alerts_without_auth(self, client):
        """Test alerts without authentication returns 401."""
        response = client.get("/api/dashboard/alerts")
        assert response.status_code == 401


class TestDashboardCityStats:
    """Tests for GET /api/dashboard/stats-by-city"""
    
    def test_get_city_stats(self, client, user_headers):
        """Test retrieving statistics by city."""
        response = client.get(
            "/api/dashboard/stats-by-city",
            headers=user_headers
        )
        # Endpoint may or may not exist, but if it does:
        if response.status_code != 404:
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, (dict, list))


class TestDashboardHourlyStats:
    """Tests for GET /api/dashboard/stats-by-hour"""
    
    def test_get_hourly_stats(self, client, user_headers):
        """Test retrieving hourly fraud patterns."""
        response = client.get(
            "/api/dashboard/stats-by-hour",
            headers=user_headers
        )
        # Endpoint may or may not exist
        if response.status_code != 404:
            assert response.status_code == 200
            data = response.get_json()
            assert isinstance(data, (dict, list))


class TestDashboardErrorCases:
    """Tests for error conditions in dashboard"""
    
    def test_invalid_query_parameter(self, client, user_headers):
        """Test dashboard endpoints with invalid query parameters."""
        response = client.get(
            "/api/dashboard/stats?invalid_param=123",
            headers=user_headers
        )
        # Should ignore invalid params and return success
        assert response.status_code == 200
    
    def test_feed_with_very_large_limit(self, client, user_headers):
        """Test feed with extremely large limit."""
        response = client.get(
            "/api/dashboard/feed?limit=100000",
            headers=user_headers
        )
        # Should either cap limit or return 400
        assert response.status_code in (200, 400)
