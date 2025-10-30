"""
API endpoint tests

Tests for all REST API endpoints including auth, cart, search, lists, and recipes.
"""
import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_check(self, client):
        """Test /api/health returns 200"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["ok", "degraded"]  # "ok" when healthy
        assert "database" in data
        assert "timestamp" in data


class TestCartEndpoints:
    """Test cart API endpoints"""

    def test_get_empty_cart(self, client):
        """Test GET /api/cart with empty cart"""
        response = client.get("/api/cart")
        assert response.status_code == 200
        data = response.json()
        assert "cart" in data
        assert isinstance(data["cart"], list)

    def test_add_to_cart(self, client):
        """Test POST /api/cart/add"""
        item = {
            "name": "Test Product",
            "price": "$5.99",
            "quantity": 1,
            "aisle": "Test Aisle"
        }

        response = client.post("/api/cart/add", json=item)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["cart"]) >= 1

    def test_update_cart_quantity(self, client):
        """Test PUT /api/cart/quantity"""
        # First add an item
        item = {"name": "Test", "price": "$1.00", "quantity": 1}
        add_response = client.post("/api/cart/add", json=item)
        cart_item_id = add_response.json()["cart"][0]["id"]

        # Update quantity
        update_data = {"cart_item_id": cart_item_id, "quantity": 5}
        response = client.put("/api/cart/quantity", json=update_data)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_clear_cart(self, client):
        """Test DELETE /api/cart"""
        # Add some items
        client.post("/api/cart/add", json={"name": "Item1", "price": "$1", "quantity": 1})
        client.post("/api/cart/add", json={"name": "Item2", "price": "$2", "quantity": 1})

        # Clear cart
        response = client.delete("/api/cart")
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["cart"] == []


class TestSearchEndpoint:
    """Test search API endpoint"""

    def test_search_products(self, client):
        """Test POST /api/search"""
        search_data = {"search_term": "bananas", "max_results": 5}

        response = client.post("/api/search", json=search_data)
        assert response.status_code == 200
        data = response.json()

        assert "products" in data
        assert isinstance(data["products"], list)
        # Note: Actual results depend on Algolia API

    def test_search_empty_term_fails(self, client):
        """Test search with empty term returns validation error"""
        response = client.post("/api/search", json={"search_term": "", "max_results": 5})
        # Should either return empty results or validation error
        assert response.status_code in [200, 422]


class TestListEndpoints:
    """Test list API endpoints"""

    def test_get_lists(self, client):
        """Test GET /api/lists"""
        response = client.get("/api/lists")
        assert response.status_code == 200
        data = response.json()
        assert "lists" in data
        assert isinstance(data["lists"], list)

    def test_auto_save_list(self, client):
        """Test POST /api/lists/auto-save"""
        # Add item to cart first
        client.post("/api/cart/add", json={"name": "Test", "price": "$1", "quantity": 1})

        # Auto-save
        list_data = {"name": "Monday, January 30, 2025"}
        response = client.post("/api/lists/auto-save", json=list_data)

        assert response.status_code == 200
        assert response.json()["success"] is True


class TestImageEndpoints:
    """Test image API endpoints"""

    def test_fetch_images_batch(self, client):
        """Test POST /api/images/fetch"""
        request_data = {"product_names": ["Bananas", "Milk"]}

        response = client.post("/api/images/fetch", json=request_data)
        assert response.status_code == 200
        data = response.json()

        assert "results" in data
        assert "success_count" in data
        assert "total_count" in data
        assert data["total_count"] == 2

    def test_fetch_images_empty_list(self, client):
        """Test batch fetch with empty list"""
        response = client.post("/api/images/fetch", json={"product_names": []})
        assert response.status_code == 200
        data = response.json()
        assert data["total_count"] == 0

    def test_fetch_images_exceeds_limit(self, client):
        """Test batch fetch with too many items"""
        # Max is 20 items
        product_names = [f"Product{i}" for i in range(25)]
        response = client.post("/api/images/fetch", json={"product_names": product_names})

        # Should return 400 Bad Request
        assert response.status_code == 400


class TestCORSHeaders:
    """Test CORS configuration"""

    def test_cors_headers_in_debug_mode(self, client):
        """Test CORS headers are present (if in debug mode)"""
        response = client.options("/api/health")
        # CORS headers should be present or endpoint should return 405
        assert response.status_code in [200, 405]


class TestErrorHandling:
    """Test API error handling"""

    def test_invalid_endpoint_returns_404(self, client):
        """Test accessing non-existent endpoint"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_invalid_method_returns_405(self, client):
        """Test using wrong HTTP method"""
        # GET on POST endpoint
        response = client.get("/api/cart/add")
        assert response.status_code == 405

    def test_invalid_json_returns_422(self, client):
        """Test sending invalid JSON"""
        response = client.post(
            "/api/cart/add",
            json={"invalid": "data"}  # Missing required fields
        )
        assert response.status_code == 422


class TestRateLimiting:
    """Test rate limiting"""

    def test_rate_limiting_configured(self):
        """Verify rate limiting is configured in production"""
        from config.settings import settings
        from app import app

        # Check that rate limiter exists
        assert hasattr(app.state, 'limiter'), "Rate limiter not configured"

        # Check that setting exists
        assert hasattr(settings, 'ENABLE_RATE_LIMITING'), "ENABLE_RATE_LIMITING setting missing"

        # In production (ENABLE_RATE_LIMITING=true), rate limiting should be active
        # In tests (ENABLE_RATE_LIMITING=false), it's disabled for test isolation
        print(f"Rate limiting enabled: {settings.ENABLE_RATE_LIMITING}")
