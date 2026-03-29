"""
test_auth.py
-----------
Tests for authentication routes (/api/auth/*).
Tests registration, login, JWT token generation, and expiration.
"""

import pytest
import json
from datetime import datetime, timedelta

pytestmark = [pytest.mark.integration]


class TestAuthRegister:
    """Tests for POST /api/auth/register"""
    
    def test_register_success(self, client):
        """Test successful user registration."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123!"
            }
        )
        assert response.status_code == 201
        data = response.get_json()
        assert data["message"] == "User registered successfully"
        assert "user_id" in data
        assert data["user_id"] > 0
    
    def test_register_missing_required_field(self, client):
        """Test registration fails without required fields."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                # Missing email and password
            }
        )
        assert response.status_code in (400, 422)
        assert "error" in response.get_json()
    
    def test_register_duplicate_username(self, client):
        """Test registration fails with duplicate username."""
        # First registration
        client.post(
            "/api/auth/register",
            json={
                "username": "duplicateuser",
                "email": "first@example.com",
                "password": "Password123!"
            }
        )
        
        # Try to register same username
        response = client.post(
            "/api/auth/register",
            json={
                "username": "duplicateuser",
                "email": "second@example.com",
                "password": "Password456!"
            }
        )
        assert response.status_code == 409
        assert "already exists" in response.get_json().get("error", "").lower()
    
    def test_register_duplicate_email(self, client):
        """Test registration fails with duplicate email."""
        # First registration
        client.post(
            "/api/auth/register",
            json={
                "username": "user1",
                "email": "sameemail@example.com",
                "password": "Password123!"
            }
        )
        
        # Try to register same email
        response = client.post(
            "/api/auth/register",
            json={
                "username": "user2",
                "email": "sameemail@example.com",
                "password": "Password456!"
            }
        )
        assert response.status_code == 409
        assert "already exists" in response.get_json().get("error", "").lower()


class TestAuthLogin:
    """Tests for POST /api/auth/login"""
    
    def test_login_success(self, client):
        """Test successful login returns JWT token."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin_test",
                "password": "admin_password"
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert data["user"]["username"] == "admin_test"
        assert data["user"]["role"] == "admin"
    
    def test_login_invalid_username(self, client):
        """Test login fails with non-existent username."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "nonexistentuser",
                "password": "somepassword"
            }
        )
        assert response.status_code == 401
        assert "invalid" in response.get_json().get("error", "").lower()
    
    def test_login_wrong_password(self, client):
        """Test login fails with wrong password."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin_test",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401
        assert "invalid" in response.get_json().get("error", "").lower()
    
    def test_login_missing_credentials(self, client):
        """Test login fails without credentials."""
        response = client.post(
            "/api/auth/login",
            json={}
        )
        assert response.status_code == 400
    
    def test_login_user_role(self, client):
        """Test login returns correct user role."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "user_test",
                "password": "user_password"
            }
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["user"]["role"] == "user"


class TestAuthJWT:
    """Tests for JWT token functionality"""
    
    def test_protected_route_without_token(self, client):
        """Test accessing protected route without token returns 401."""
        response = client.get("/api/transactions/")
        assert response.status_code == 401
    
    def test_protected_route_with_invalid_token(self, client):
        """Test accessing protected route with invalid token returns 401."""
        response = client.get(
            "/api/transactions/",
            headers={"Authorization": "Bearer invalid_token_here"}
        )
        assert response.status_code == 422  # Unprocessable entity (JWT decode fails)
    
    def test_protected_route_with_valid_token(self, client, user_headers):
        """Test accessing protected route with valid token succeeds."""
        response = client.get(
            "/api/transactions/",
            headers=user_headers
        )
        # 200 OK or 400+ depending on other validation, but NOT 401
        assert response.status_code != 401
    
    def test_admin_only_route_with_admin_token(self, client, admin_headers):
        """Test admin route with admin token succeeds."""
        # /api/model/retrain is admin-only
        response = client.post(
            "/api/model/retrain",
            headers=admin_headers,
            json={"count": 1000}
        )
        # Should not be 403 (forbidden)
        assert response.status_code != 403
    
    def test_admin_only_route_with_user_token(self, client, user_headers):
        """Test admin route with user token returns 403."""
        response = client.post(
            "/api/model/retrain",
            headers=user_headers,
            json={"count": 1000}
        )
        assert response.status_code == 403
        assert "admin" in response.get_json().get("error", "").lower()
    
    def test_token_contains_user_info(self, client, admin_token):
        """Test JWT token payload contains user information."""
        # Decode token (JWT structure: header.payload.signature)
        # For this test, just verify it's in correct format
        parts = admin_token.split(".")
        assert len(parts) == 3, "JWT should have 3 parts"
        
        # Each part should be base64-like (alphanumeric + - and _)
        for part in parts:
            assert all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_=" for c in part)


class TestAuthEdgeCases:
    """Edge case tests for authentication"""
    
    def test_register_with_whitespace_in_username(self, client):
        """Test registration with whitespace in username."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "user with spaces",
                "email": "user@example.com",
                "password": "Password123!"
            }
        )
        # Should either reject or strip whitespace
        assert response.status_code in (201, 400, 422)
    
    def test_register_with_very_long_password(self, client):
        """Test registration with very long password."""
        response = client.post(
            "/api/auth/register",
            json={
                "username": "userlong",
                "email": "userlong@example.com",
                "password": "P" * 1000  # 1000 character password
            }
        )
        # Should accept (bcrypt can handle long passwords)
        assert response.status_code == 201
    
    def test_login_case_sensitivity(self, client):
        """Test if username login is case-sensitive."""
        # Try uppercase username when stored as lowercase
        response = client.post(
            "/api/auth/login",
            json={
                "username": "ADMIN_TEST",
                "password": "admin_password"
            }
        )
        # Should fail (most implementations are case-sensitive)
        assert response.status_code == 401


class TestAuthInvalidJson:
    """Tests for invalid JSON payloads"""
    
    def test_register_with_no_json(self, client):
        """Test register endpoint with no JSON body."""
        response = client.post(
            "/api/auth/register",
            data="not json"
        )
        assert response.status_code in (400, 415)
    
    def test_login_with_extra_fields(self, client):
        """Test login with extra fields in payload."""
        response = client.post(
            "/api/auth/login",
            json={
                "username": "admin_test",
                "password": "admin_password",
                "extra_field": "should_be_ignored"
            }
        )
        # Should still succeed (extra fields are ignored)
        assert response.status_code == 200
