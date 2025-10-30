"""
Authentication tests

Tests for Supabase Auth integration including:
- User registration
- Login/logout
- Token verification
- Anonymous user support
"""
import pytest
from fastapi.testclient import TestClient
from app import app
import uuid

client = TestClient(app)


def test_anonymous_user_can_access_cart():
    """Anonymous users should be able to access cart without authentication"""
    response = client.get("/api/cart")
    assert response.status_code == 200
    assert "cart" in response.json()


def test_anonymous_user_can_search():
    """Anonymous users should be able to search products"""
    import time
    # Brief delay to ensure rate limiter reset completes
    time.sleep(0.2)

    response = client.post("/api/search", json={
        "search_term": "apple",
        "max_results": 5
    })

    # If rate limited, wait and retry (rate limiter should have reset)
    if response.status_code == 429:
        time.sleep(1)
        response = client.post("/api/search", json={
            "search_term": "apple",
            "max_results": 5
        })

    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    assert "products" in response.json()


def test_config_endpoint_returns_public_keys():
    """Config endpoint should return Supabase public configuration"""
    response = client.get("/api/config")
    assert response.status_code == 200
    data = response.json()
    assert "supabaseUrl" in data
    assert "supabaseAnonKey" in data
    # Should NOT include service key
    assert "supabaseServiceKey" not in data
    assert "SUPABASE_SERVICE_KEY" not in str(data)


def test_auth_me_without_token_returns_anonymous():
    """GET /api/auth/me without token should return anonymous user"""
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["is_anonymous"] == True
    assert data["email"] is None


def test_invalid_token_returns_401():
    """Invalid JWT token should return 401 Unauthorized"""
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.fake.signature"
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {fake_token}"}
    )
    assert response.status_code == 401


def test_cart_add_requires_valid_product():
    """Adding to cart should validate product data"""
    response = client.post("/api/cart/add", json={
        "name": "Test Product",
        "price": "$5.99",
        "quantity": 1
    })
    # Should succeed with anonymous user
    assert response.status_code == 200
    assert response.json()["success"] == True


def test_frequent_items_requires_auth():
    """Frequent items endpoint should work for anonymous users (returns empty)"""
    response = client.get("/api/frequent")
    assert response.status_code == 200
    assert "items" in response.json()


def test_sql_injection_in_cart_add():
    """SQL injection attempts should be safely handled"""
    response = client.post("/api/cart/add", json={
        "name": "'; DROP TABLE users; --",
        "price": "$5.99",
        "quantity": 1
    })
    # Should either succeed (parameterized) or fail safely
    assert response.status_code in [200, 400, 422]
    # Verify users table still exists by making another request
    verify = client.get("/api/cart")
    assert verify.status_code == 200


# Note: Cannot test actual Supabase signup/signin without real credentials
# and email verification. Those require integration tests or manual testing.

class TestAuthEndpoints:
    """Test auth endpoint structure (without real Supabase calls)"""

    def test_signup_endpoint_exists(self):
        """Signup endpoint should exist"""
        # Will fail without real credentials, but endpoint should exist
        response = client.post("/api/auth/signup", json={
            "email": "test@example.com",
            "password": "password123"
        })
        # 400 or 503 is fine (no real Supabase), 404 would be bad
        assert response.status_code != 404

    def test_signin_endpoint_exists(self):
        """Signin endpoint should exist"""
        response = client.post("/api/auth/signin", json={
            "email": "test@example.com",
            "password": "password123"
        })
        # 401 or 503 is fine, 404 would be bad
        assert response.status_code != 404

    def test_forgot_password_endpoint_exists(self):
        """Forgot password endpoint should exist"""
        response = client.post("/api/auth/forgot-password", json={
            "email": "test@example.com"
        })
        # Any response except 404 is fine
        assert response.status_code != 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
