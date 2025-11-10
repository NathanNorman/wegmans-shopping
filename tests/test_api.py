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

    def test_get_lists_with_saved_lists(self, client):
        """Test GET /api/lists returns saved lists with details"""
        # Add items to cart
        client.post("/api/cart/add", json={"name": "Milk", "price": "$3.99", "quantity": 1})
        client.post("/api/cart/add", json={"name": "Bread", "price": "$2.49", "quantity": 2})

        # Save as list
        client.post("/api/lists/save", json={"name": "Grocery List"})

        # Get lists
        response = client.get("/api/lists")
        assert response.status_code == 200
        data = response.json()
        assert len(data["lists"]) >= 1

        # Verify list details
        saved_list = data["lists"][0]
        assert "id" in saved_list
        assert "name" in saved_list
        assert "item_count" in saved_list
        assert "total_quantity" in saved_list
        assert "total_price" in saved_list
        assert "items" in saved_list

    def test_save_list_success(self, client):
        """Test POST /api/lists/save creates new list"""
        # Add items to cart
        client.post("/api/cart/add", json={"name": "Apples", "price": "$4.99", "quantity": 3})

        # Save list
        response = client.post("/api/lists/save", json={"name": "Weekly Shopping"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "list_id" in data
        assert isinstance(data["list_id"], int)

    def test_save_list_empty_cart_fails(self, client):
        """Test POST /api/lists/save with empty cart returns error"""
        # Clear cart first
        client.delete("/api/cart")

        # Try to save empty cart
        response = client.post("/api/lists/save", json={"name": "Empty List"})

        assert response.status_code == 400
        assert "Cart is empty" in response.json()["detail"]

    def test_save_list_invalid_name_fails(self, client):
        """Test POST /api/lists/save with missing name returns validation error"""
        # Add item to cart
        client.post("/api/cart/add", json={"name": "Test", "price": "$1", "quantity": 1})

        # Try to save without name
        response = client.post("/api/lists/save", json={})

        assert response.status_code == 422  # Pydantic validation error

    def test_load_list_success(self, client):
        """Test POST /api/lists/{list_id}/load loads list to cart"""
        # Create a list
        client.post("/api/cart/add", json={"name": "Orange Juice", "price": "$5.99", "quantity": 1})
        save_response = client.post("/api/lists/save", json={"name": "Breakfast"})
        list_id = save_response.json()["list_id"]

        # Clear cart
        client.delete("/api/cart")

        # Load list
        response = client.post(f"/api/lists/{list_id}/load")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cart" in data
        assert len(data["cart"]) >= 1
        assert data["list_name"] == "Breakfast"

    def test_load_list_invalid_id_fails(self, client):
        """Test POST /api/lists/{list_id}/load with non-existent ID returns 404"""
        response = client.post("/api/lists/999999/load")

        assert response.status_code == 404
        assert "List not found" in response.json()["detail"]

    def test_load_list_replaces_cart_contents(self, client):
        """Test loading list clears existing cart contents"""
        # Create list 1
        client.post("/api/cart/add", json={"name": "Item A", "price": "$1", "quantity": 1})
        save_response = client.post("/api/lists/save", json={"name": "List 1"})
        list_id = save_response.json()["list_id"]

        # Add different items to cart
        client.delete("/api/cart")
        client.post("/api/cart/add", json={"name": "Item B", "price": "$2", "quantity": 1})
        client.post("/api/cart/add", json={"name": "Item C", "price": "$3", "quantity": 1})

        # Load list 1
        response = client.post(f"/api/lists/{list_id}/load")
        cart = response.json()["cart"]

        # Cart should only have Item A
        assert len(cart) == 1
        assert cart[0]["product_name"] == "Item A"

    def test_delete_list_success(self, client):
        """Test DELETE /api/lists/{list_id} removes list"""
        # Create list
        client.post("/api/cart/add", json={"name": "Coffee", "price": "$8.99", "quantity": 1})
        save_response = client.post("/api/lists/save", json={"name": "Morning"})
        list_id = save_response.json()["list_id"]

        # Delete list
        response = client.delete(f"/api/lists/{list_id}")

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify list is gone
        lists_response = client.get("/api/lists")
        list_ids = [lst["id"] for lst in lists_response.json()["lists"]]
        assert list_id not in list_ids

    def test_delete_list_invalid_id_fails(self, client):
        """Test DELETE /api/lists/{list_id} with non-existent ID returns 404"""
        response = client.delete("/api/lists/999999")

        assert response.status_code == 404
        assert "List not found" in response.json()["detail"]

    def test_delete_list_updates_frequent_items(self, client):
        """Test DELETE decrements frequent items purchase_count"""
        # Create list with items
        client.post("/api/cart/add", json={"name": "Bananas", "price": "$0.59", "quantity": 1})
        save_response = client.post("/api/lists/save", json={"name": "Fruit List"})
        list_id = save_response.json()["list_id"]

        # Delete list
        response = client.delete(f"/api/lists/{list_id}")
        assert response.status_code == 200

        # Note: We can't easily verify frequent_items count without direct DB access
        # This test verifies the endpoint executes without error

    def test_auto_save_list_creates_new(self, client):
        """Test POST /api/lists/auto-save creates new list"""
        # Add item to cart
        client.post("/api/cart/add", json={"name": "Test", "price": "$1", "quantity": 1})

        # Auto-save
        list_data = {"name": "Monday, January 30, 2025"}
        response = client.post("/api/lists/auto-save", json=list_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "list_id" in data
        assert data["updated"] is False  # New list

    def test_auto_save_list_updates_existing_today(self, client):
        """Test POST /api/lists/auto-save updates existing list from today

        NOTE: This test is skipped due to a bug in src/api/lists.py line 139-143.
        The code tries to update last_updated column which was removed in migration 009.
        Fix: Remove lines 139-143 from src/api/lists.py (UPDATE last_updated query).
        """
        # Create first auto-save
        client.post("/api/cart/add", json={"name": "Item 1", "price": "$1", "quantity": 1})
        response1 = client.post("/api/lists/auto-save", json={"name": "Tuesday, January 31, 2025"})
        list_id = response1.json()["list_id"]

        # Modify cart
        client.post("/api/cart/add", json={"name": "Item 2", "price": "$2", "quantity": 1})

        # Auto-save again with same name
        response2 = client.post("/api/lists/auto-save", json={"name": "Tuesday, January 31, 2025"})

        assert response2.status_code == 200
        data = response2.json()
        assert data["success"] is True
        assert data["list_id"] == list_id  # Same list ID
        assert data["updated"] is True  # Updated existing

    def test_auto_save_empty_cart_returns_message(self, client):
        """Test POST /api/lists/auto-save with empty cart returns success message"""
        # Clear cart
        client.delete("/api/cart")

        # Try auto-save
        response = client.post("/api/lists/auto-save", json={"name": "Wednesday, Feb 1, 2025"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "nothing to save" in data["message"].lower()

    def test_auto_save_marks_as_auto_saved(self, client):
        """Test POST /api/lists/auto-save sets is_auto_saved flag"""
        # Add item and auto-save
        client.post("/api/cart/add", json={"name": "Eggs", "price": "$3.49", "quantity": 1})
        response = client.post("/api/lists/auto-save", json={"name": "Thursday, Feb 2, 2025"})

        assert response.status_code == 200

        # Get lists and verify flag
        lists_response = client.get("/api/lists")
        lists = lists_response.json()["lists"]

        # Find our auto-saved list
        auto_saved = [lst for lst in lists if lst["name"] == "Thursday, Feb 2, 2025"]
        assert len(auto_saved) >= 1
        assert auto_saved[0]["is_auto_saved"] is True

    def test_get_todays_list_exists(self, client):
        """Test GET /api/lists/today returns today's list"""
        # Create today's auto-saved list
        client.post("/api/cart/add", json={"name": "Milk", "price": "$3.99", "quantity": 2})
        client.post("/api/lists/auto-save", json={"name": "Today's List"})

        # Get today's list
        response = client.get("/api/lists/today")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is True
        assert "list" in data
        assert data["list"]["name"] == "Today's List"
        assert "item_count" in data["list"]
        assert "total_quantity" in data["list"]
        assert "total_price" in data["list"]

    def test_get_todays_list_not_exists(self, client):
        """Test GET /api/lists/today returns exists=False when no list today"""
        # Don't create any auto-saved list

        response = client.get("/api/lists/today")

        assert response.status_code == 200
        data = response.json()
        assert data["exists"] is False
        assert "list" not in data

    def test_get_todays_list_excludes_old_auto_saved(self, client):
        """Test GET /api/lists/today only returns lists from current date"""
        # Note: This test assumes we can't easily mock dates in the test
        # It verifies the endpoint executes without checking date logic

        response = client.get("/api/lists/today")

        assert response.status_code == 200
        assert "exists" in response.json()

    def test_multiple_lists_workflow(self, client):
        """Test complete workflow: create, load, delete multiple lists"""
        # Create list 1
        client.post("/api/cart/add", json={"name": "Coffee", "price": "$10", "quantity": 1})
        list1_response = client.post("/api/lists/save", json={"name": "Drinks"})
        list1_id = list1_response.json()["list_id"]

        # Create list 2
        client.delete("/api/cart")
        client.post("/api/cart/add", json={"name": "Bread", "price": "$3", "quantity": 2})
        list2_response = client.post("/api/lists/save", json={"name": "Bakery"})
        list2_id = list2_response.json()["list_id"]

        # Verify both exist
        lists_response = client.get("/api/lists")
        list_ids = [lst["id"] for lst in lists_response.json()["lists"]]
        assert list1_id in list_ids
        assert list2_id in list_ids

        # Load list 1
        client.delete("/api/cart")
        load_response = client.post(f"/api/lists/{list1_id}/load")
        assert load_response.json()["cart"][0]["product_name"] == "Coffee"

        # Delete list 2
        delete_response = client.delete(f"/api/lists/{list2_id}")
        assert delete_response.json()["success"] is True

        # Verify list 2 is gone
        final_lists = client.get("/api/lists").json()["lists"]
        final_ids = [lst["id"] for lst in final_lists]
        assert list1_id in final_ids
        assert list2_id not in final_ids


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


class TestRecipeEndpoints:
    """Test recipe API endpoints"""

    def test_get_recipes_empty(self, client):
        """Test GET /api/recipes with no recipes"""
        response = client.get("/api/recipes")
        assert response.status_code == 200
        data = response.json()
        assert "recipes" in data
        assert isinstance(data["recipes"], list)

    def test_get_recipes_with_existing_recipes(self, client):
        """Test GET /api/recipes returns all user's recipes"""
        # Create a couple of recipes
        client.post("/api/recipes/create", json={"name": "Recipe 1", "description": "First recipe"})
        client.post("/api/recipes/create", json={"name": "Recipe 2"})

        response = client.get("/api/recipes")
        assert response.status_code == 200
        data = response.json()
        assert len(data["recipes"]) >= 2

        # Verify recipe structure
        recipe = data["recipes"][0]
        assert "id" in recipe
        assert "name" in recipe
        assert "description" in recipe
        assert "items" in recipe

    def test_create_recipe_success(self, client):
        """Test POST /api/recipes/create creates new empty recipe"""
        recipe_data = {"name": "My Recipe", "description": "Test description"}

        response = client.post("/api/recipes/create", json=recipe_data)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "recipe_id" in data
        assert isinstance(data["recipe_id"], int)

        # Verify recipe was created
        recipes_response = client.get("/api/recipes")
        recipes = recipes_response.json()["recipes"]
        assert any(r["name"] == "My Recipe" for r in recipes)

    def test_create_recipe_without_description(self, client):
        """Test POST /api/recipes/create with only name"""
        response = client.post("/api/recipes/create", json={"name": "Simple Recipe"})
        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_create_recipe_missing_name_fails(self, client):
        """Test POST /api/recipes/create without name returns validation error"""
        response = client.post("/api/recipes/create", json={})
        assert response.status_code == 422  # Pydantic validation error

    def test_save_cart_as_recipe_success(self, client):
        """Test POST /api/recipes/save-cart creates recipe from current cart"""
        # Add items to cart
        client.post("/api/cart/add", json={"name": "Chicken", "price": "$8.99", "quantity": 2})
        client.post("/api/cart/add", json={"name": "Rice", "price": "$4.50", "quantity": 1})

        # Save cart as recipe
        recipe_data = {"name": "Dinner Recipe", "description": "Weekly meal"}
        response = client.post("/api/recipes/save-cart", json=recipe_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "recipe_id" in data

        # Verify recipe has items
        recipes_response = client.get("/api/recipes")
        recipes = recipes_response.json()["recipes"]
        dinner_recipe = next(r for r in recipes if r["name"] == "Dinner Recipe")
        assert len(dinner_recipe["items"]) == 2

    def test_save_cart_as_recipe_empty_cart_fails(self, client):
        """Test POST /api/recipes/save-cart with empty cart returns 400"""
        # Clear cart
        client.delete("/api/cart")

        # Try to save empty cart
        response = client.post("/api/recipes/save-cart", json={"name": "Empty Recipe"})

        assert response.status_code == 400
        assert "Cart is empty" in response.json()["detail"]

    def test_save_cart_as_recipe_missing_name_fails(self, client):
        """Test POST /api/recipes/save-cart without name returns validation error"""
        # Add item to cart
        client.post("/api/cart/add", json={"name": "Bread", "price": "$2.99", "quantity": 1})

        # Try to save without name
        response = client.post("/api/recipes/save-cart", json={})
        assert response.status_code == 422

    def test_add_item_to_recipe_success(self, client):
        """Test POST /api/recipes/{recipe_id}/items adds item to recipe"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Test Recipe"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Add item
        item_data = {
            "name": "Tomatoes",
            "price": "$3.49",
            "quantity": 3,
            "aisle": "Produce",
            "image": "https://example.com/tomatoes.jpg",
            "search_term": "tomatoes",
            "is_sold_by_weight": False
        }
        response = client.post(f"/api/recipes/{recipe_id}/items", json=item_data)

        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify item was added
        recipes_response = client.get("/api/recipes")
        recipe = next(r for r in recipes_response.json()["recipes"] if r["id"] == recipe_id)
        assert len(recipe["items"]) == 1
        assert recipe["items"][0]["product_name"] == "Tomatoes"

    def test_add_item_to_recipe_minimal_fields(self, client):
        """Test POST /api/recipes/{recipe_id}/items with only required fields"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Minimal Recipe"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Add item with minimal fields
        item_data = {"name": "Carrots", "price": "$1.99"}
        response = client.post(f"/api/recipes/{recipe_id}/items", json=item_data)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_add_item_to_recipe_with_weight_item(self, client):
        """Test POST /api/recipes/{recipe_id}/items with weight-based item"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Deli Recipe"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Add weight-based item
        item_data = {
            "name": "Turkey Breast",
            "price": "$8.99",
            "quantity": 0.5,
            "is_sold_by_weight": True,
            "unit_price": "$17.98/lb"
        }
        response = client.post(f"/api/recipes/{recipe_id}/items", json=item_data)

        assert response.status_code == 200
        assert response.json()["success"] is True

    def test_add_item_to_nonexistent_recipe_fails(self, client):
        """Test POST /api/recipes/{recipe_id}/items with invalid recipe ID returns 404"""
        item_data = {"name": "Test Item", "price": "$1.00"}
        response = client.post("/api/recipes/999999/items", json=item_data)

        assert response.status_code == 404
        assert "Recipe not found" in response.json()["detail"]

    def test_add_item_missing_required_fields_fails(self, client):
        """Test POST /api/recipes/{recipe_id}/items without required fields returns 422"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Test"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Try to add item without name
        response = client.post(f"/api/recipes/{recipe_id}/items", json={"price": "$1.00"})
        assert response.status_code == 422

    def test_update_recipe_item_quantity_success(self, client):
        """Test PUT /api/recipes/items/{item_id}/quantity updates quantity"""
        # Create recipe with item via cart (to ensure we have item IDs)
        client.post("/api/cart/add", json={"name": "Apples", "price": "$4.99", "quantity": 1})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Test Recipe"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Get item ID directly from database (since items don't include id in API response)
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s", (recipe_id,))
            item_id = cursor.fetchone()["id"]

        # Update quantity
        response = client.put(f"/api/recipes/items/{item_id}/quantity", json={"quantity": 5})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify quantity was updated
        updated_recipes = client.get("/api/recipes")
        updated_recipe = next(r for r in updated_recipes.json()["recipes"] if r["id"] == recipe_id)
        assert updated_recipe["items"][0]["quantity"] == 5

    def test_update_recipe_item_quantity_decimal(self, client):
        """Test PUT /api/recipes/items/{item_id}/quantity with decimal quantity"""
        # Create recipe with item via cart
        client.post("/api/cart/add", json={"name": "Cheese", "price": "$6.99"})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Test"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Get item ID from database
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s", (recipe_id,))
            item_id = cursor.fetchone()["id"]

        # Update to decimal quantity
        response = client.put(f"/api/recipes/items/{item_id}/quantity", json={"quantity": 0.75})
        assert response.status_code == 200

    def test_update_recipe_item_quantity_missing_quantity_fails(self, client):
        """Test PUT /api/recipes/items/{item_id}/quantity without quantity returns 422"""
        response = client.put("/api/recipes/items/1/quantity", json={})
        assert response.status_code == 422

    def test_remove_item_from_recipe_success(self, client):
        """Test DELETE /api/recipes/items/{item_id} removes item"""
        # Create recipe with items via cart
        client.post("/api/cart/add", json={"name": "Item 1", "price": "$1.00"})
        client.post("/api/cart/add", json={"name": "Item 2", "price": "$2.00"})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Test Recipe"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Get first item ID from database
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s ORDER BY id LIMIT 1", (recipe_id,))
            item_id = cursor.fetchone()["id"]

        # Remove item
        response = client.delete(f"/api/recipes/items/{item_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify item was removed
        updated_recipe = client.get("/api/recipes").json()["recipes"][0]
        assert len(updated_recipe["items"]) == 1

    def test_remove_item_removes_last_item(self, client):
        """Test DELETE /api/recipes/items/{item_id} can remove last item"""
        # Create recipe with one item via cart
        client.post("/api/cart/add", json={"name": "Only Item", "price": "$1.00"})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Test"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Get item ID from database
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s", (recipe_id,))
            item_id = cursor.fetchone()["id"]

        response = client.delete(f"/api/recipes/items/{item_id}")
        assert response.status_code == 200

        # Recipe should still exist but have no items
        updated_recipe = client.get("/api/recipes").json()["recipes"][0]
        assert len(updated_recipe["items"]) == 0

    def test_update_recipe_name_success(self, client):
        """Test PUT /api/recipes/{recipe_id} updates recipe name"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Old Name"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Update name
        response = client.put(f"/api/recipes/{recipe_id}", json={"name": "New Name"})
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify name was updated
        recipe = client.get("/api/recipes").json()["recipes"][0]
        assert recipe["name"] == "New Name"

    def test_update_recipe_description_success(self, client):
        """Test PUT /api/recipes/{recipe_id} updates description"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Test", "description": "Old"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Update description
        response = client.put(f"/api/recipes/{recipe_id}", json={"description": "New Description"})
        assert response.status_code == 200

        # Verify description was updated
        recipe = client.get("/api/recipes").json()["recipes"][0]
        assert recipe["description"] == "New Description"

    def test_update_recipe_both_fields(self, client):
        """Test PUT /api/recipes/{recipe_id} updates both name and description"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Old", "description": "Old"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Update both fields
        response = client.put(
            f"/api/recipes/{recipe_id}",
            json={"name": "Updated Name", "description": "Updated Description"}
        )
        assert response.status_code == 200

        # Verify both fields were updated
        recipe = client.get("/api/recipes").json()["recipes"][0]
        assert recipe["name"] == "Updated Name"
        assert recipe["description"] == "Updated Description"

    def test_update_recipe_nonexistent_fails(self, client):
        """Test PUT /api/recipes/{recipe_id} with invalid ID returns 404"""
        response = client.put("/api/recipes/999999", json={"name": "New Name"})
        assert response.status_code == 404
        assert "Recipe not found" in response.json()["detail"]

    def test_update_recipe_no_fields_provided(self, client):
        """Test PUT /api/recipes/{recipe_id} with no fields still succeeds"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "Test"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Update with no fields (should succeed but not change anything)
        response = client.put(f"/api/recipes/{recipe_id}", json={})
        assert response.status_code == 200

    def test_delete_recipe_success(self, client):
        """Test DELETE /api/recipes/{recipe_id} removes recipe"""
        # Create recipe
        recipe_response = client.post("/api/recipes/create", json={"name": "To Delete"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Delete recipe
        response = client.delete(f"/api/recipes/{recipe_id}")
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify recipe is gone
        recipes = client.get("/api/recipes").json()["recipes"]
        assert not any(r["id"] == recipe_id for r in recipes)

    def test_delete_recipe_with_items(self, client):
        """Test DELETE /api/recipes/{recipe_id} removes recipe and all items"""
        # Create recipe with items
        recipe_response = client.post("/api/recipes/create", json={"name": "Recipe with Items"})
        recipe_id = recipe_response.json()["recipe_id"]

        client.post(f"/api/recipes/{recipe_id}/items", json={"name": "Item 1", "price": "$1.00"})
        client.post(f"/api/recipes/{recipe_id}/items", json={"name": "Item 2", "price": "$2.00"})

        # Delete recipe
        response = client.delete(f"/api/recipes/{recipe_id}")
        assert response.status_code == 200

        # Verify recipe and items are gone
        recipes = client.get("/api/recipes").json()["recipes"]
        assert not any(r["id"] == recipe_id for r in recipes)

    def test_delete_recipe_does_not_affect_others(self, client):
        """Test DELETE /api/recipes/{recipe_id} only deletes specified recipe"""
        # Create two recipes
        recipe1_response = client.post("/api/recipes/create", json={"name": "Recipe 1"})
        recipe1_id = recipe1_response.json()["recipe_id"]

        recipe2_response = client.post("/api/recipes/create", json={"name": "Recipe 2"})
        recipe2_id = recipe2_response.json()["recipe_id"]

        # Delete recipe 1
        client.delete(f"/api/recipes/{recipe1_id}")

        # Verify recipe 2 still exists
        recipes = client.get("/api/recipes").json()["recipes"]
        assert any(r["id"] == recipe2_id for r in recipes)
        assert not any(r["id"] == recipe1_id for r in recipes)

    def test_load_recipe_to_cart_all_items(self, client):
        """Test POST /api/recipes/{recipe_id}/add-to-cart loads all items"""
        # Create recipe with items
        client.post("/api/cart/add", json={"name": "Pasta", "price": "$2.99", "quantity": 2})
        client.post("/api/cart/add", json={"name": "Sauce", "price": "$3.49", "quantity": 1})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Pasta Night"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Clear cart
        client.delete("/api/cart")

        # Load recipe (all items)
        response = client.post(f"/api/recipes/{recipe_id}/add-to-cart", json={})
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cart" in data
        assert len(data["cart"]) == 2

    def test_load_recipe_to_cart_selective_items(self, client):
        """Test POST /api/recipes/{recipe_id}/add-to-cart with item_ids"""
        # Create recipe with multiple items via cart
        client.post("/api/cart/add", json={"name": "Item A", "price": "$1.00"})
        client.post("/api/cart/add", json={"name": "Item B", "price": "$2.00"})
        client.post("/api/cart/add", json={"name": "Item C", "price": "$3.00"})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Big Recipe"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Get item IDs from database (select first and third)
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s ORDER BY id", (recipe_id,))
            all_items = cursor.fetchall()
            item_ids = [all_items[0]["id"], all_items[2]["id"]]

        # Clear cart
        client.delete("/api/cart")

        # Load only selected items
        response = client.post(f"/api/recipes/{recipe_id}/add-to-cart", json={"item_ids": item_ids})
        assert response.status_code == 200
        cart = response.json()["cart"]
        assert len(cart) == 2
        cart_names = [item["product_name"] for item in cart]
        assert "Item A" in cart_names
        assert "Item C" in cart_names
        assert "Item B" not in cart_names

    def test_load_recipe_to_cart_adds_to_existing(self, client):
        """Test POST /api/recipes/{recipe_id}/add-to-cart adds to existing cart"""
        # Create recipe
        client.post("/api/cart/add", json={"name": "Recipe Item", "price": "$5.00"})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Test"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Add different items to cart
        client.delete("/api/cart")
        client.post("/api/cart/add", json={"name": "Different Item", "price": "$10.00"})

        # Load recipe (should add to cart, not replace)
        response = client.post(f"/api/recipes/{recipe_id}/add-to-cart", json={})
        cart = response.json()["cart"]
        assert len(cart) == 2  # Both items should be present
        cart_names = [item["product_name"] for item in cart]
        assert "Recipe Item" in cart_names
        assert "Different Item" in cart_names

    def test_load_recipe_nonexistent_fails(self, client):
        """Test POST /api/recipes/{recipe_id}/add-to-cart with invalid ID returns 404"""
        response = client.post("/api/recipes/999999/add-to-cart", json={})
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_load_recipe_with_invalid_item_ids_succeeds_empty(self, client):
        """Test POST /api/recipes/{recipe_id}/add-to-cart with non-existent item IDs succeeds but adds nothing"""
        # Create recipe with one item via cart
        client.post("/api/cart/add", json={"name": "Item", "price": "$1.00"})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Test"})
        recipe_id = recipe_response.json()["recipe_id"]

        # Clear cart
        client.delete("/api/cart")

        # Try to load with invalid item IDs (SQL will find no matching items, but succeeds)
        response = client.post(f"/api/recipes/{recipe_id}/add-to-cart", json={"item_ids": [999999]})
        assert response.status_code == 200  # Succeeds but adds nothing
        cart = response.json()["cart"]
        assert len(cart) == 0  # No items added

    def test_recipe_workflow_complete(self, client):
        """Test complete recipe workflow: create, add items, update, load, delete"""
        # 1. Create recipe via cart
        client.post("/api/cart/add", json={"name": "Flour", "price": "$3.99"})
        client.post("/api/cart/add", json={"name": "Sugar", "price": "$4.49"})
        recipe_response = client.post("/api/recipes/save-cart", json={"name": "Workflow Recipe"})
        recipe_id = recipe_response.json()["recipe_id"]

        # 2. Update recipe metadata
        client.put(f"/api/recipes/{recipe_id}", json={"description": "Baking essentials"})

        # 3. Update item quantity
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s ORDER BY id LIMIT 1", (recipe_id,))
            item_id = cursor.fetchone()["id"]
        client.put(f"/api/recipes/items/{item_id}/quantity", json={"quantity": 3})

        # 4. Load to cart (clear first to verify load works)
        client.delete("/api/cart")
        load_response = client.post(f"/api/recipes/{recipe_id}/add-to-cart", json={})
        assert load_response.status_code == 200
        assert len(load_response.json()["cart"]) == 2

        # 5. Delete recipe
        delete_response = client.delete(f"/api/recipes/{recipe_id}")
        assert delete_response.status_code == 200

        # Verify recipe is gone
        recipes = client.get("/api/recipes").json()["recipes"]
        assert not any(r["id"] == recipe_id for r in recipes)

    def test_multiple_users_recipes_isolation(self, client):
        """Test that recipes are isolated per user"""
        # User 1 creates recipe
        client.post("/api/recipes/create", json={"name": "User 1 Recipe"})

        # Create new client with different user ID (simulates different user)
        import uuid
        from fastapi.testclient import TestClient
        from app import app

        with TestClient(app) as client2:
            client2.headers = {"X-Anonymous-User-ID": str(uuid.uuid4())}

            # User 2 should not see User 1's recipe
            response = client2.get("/api/recipes")
            recipes = response.json()["recipes"]
            assert not any(r["name"] == "User 1 Recipe" for r in recipes)

            # User 2 creates their own recipe
            client2.post("/api/recipes/create", json={"name": "User 2 Recipe"})

        # User 1 should not see User 2's recipe
        recipes = client.get("/api/recipes").json()["recipes"]
        assert not any(r["name"] == "User 2 Recipe" for r in recipes)


class TestRecipeImportEndpoints:
    """Test recipe import and parser API endpoints"""

    def test_parse_recipe_simple(self, client):
        """Test POST /api/recipes/parse with simple text"""
        response = client.post('/api/recipes/parse', json={
            'text': '2 tablespoons olive oil\n1 onion\n3 cloves garlic'
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['count'] == 3
        assert len(data['ingredients']) == 3
        assert data['ingredients'][0]['name'] == 'olive oil'
        assert data['ingredients'][1]['name'] == 'onion'
        assert data['ingredients'][2]['name'] == 'garlic'

    def test_parse_recipe_with_checkboxes(self, client):
        """Test parsing with checkbox bullets"""
        response = client.post('/api/recipes/parse', json={
            'text': '▢2 tablespoons extra virgin olive oil\n▢1 medium sweet onion, chopped'
        })

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 2
        assert data['ingredients'][0]['name'] == 'olive oil'
        assert data['ingredients'][1]['name'] == 'onion'
        # Verify checkboxes removed
        assert '▢' not in data['ingredients'][0]['name']
        # Verify quality words removed
        assert 'extra virgin' not in data['ingredients'][0]['name']
        assert 'sweet' not in data['ingredients'][1]['name']

    def test_parse_recipe_empty_text(self, client):
        """Test parsing with empty text"""
        response = client.post('/api/recipes/parse', json={'text': ''})

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 0
        assert data['ingredients'] == []

    def test_parse_recipe_edge_cases(self, client):
        """Test parsing known edge cases"""
        text = """1 green bell pepper seeded and diced
14.5 ounces crushed tomatoes 1 can
2 pounds lean ground beef
1 jar (12 ounce) marinated, quartered artichokes, drained"""

        response = client.post('/api/recipes/parse', json={'text': text})

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 4

        # Verify edge cases parsed correctly
        names = [ing['name'] for ing in data['ingredients']]
        assert 'bell pepper' in names[0]
        assert 'crushed tomatoes' in names[1]
        assert 'ground beef' in names[2]
        assert 'marinated' in names[3] and 'artichokes' in names[3]

    def test_parse_recipe_with_sections(self, client):
        """Test multi-section recipe parsing"""
        text = """Sauce:
- 2 cups tomato sauce
- 1 onion

Toppings:
- 1 cup cheese"""

        response = client.post('/api/recipes/parse', json={'text': text})

        assert response.status_code == 200
        data = response.json()
        assert data['count'] == 3
        assert data['ingredients'][0]['section'] == 'Sauce'
        assert data['ingredients'][2]['section'] == 'Toppings'

    def test_import_search_batch(self, client):
        """Test POST /api/recipes/import-search"""
        response = client.post('/api/recipes/import-search', json={
            'ingredients': ['olive oil', 'chicken', 'onion'],
            'max_results_per_item': 3,
            'store_number': 86
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['total_ingredients'] == 3
        assert len(data['results']) == 3

        # Each result should have matches (or empty list if store doesn't have items)
        for result in data['results']:
            assert 'ingredient' in result
            assert 'matches' in result
            assert 'match_count' in result
            assert isinstance(result['matches'], list)

    def test_import_search_with_store_number(self, client):
        """Test that store_number parameter is respected"""
        response = client.post('/api/recipes/import-search', json={
            'ingredients': ['chicken'],
            'max_results_per_item': 3,
            'store_number': 86
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True

    def test_import_search_empty_ingredients(self, client):
        """Test with empty ingredient list"""
        response = client.post('/api/recipes/import-search', json={
            'ingredients': [],
            'max_results_per_item': 3,
            'store_number': 86
        })

        assert response.status_code == 200
        data = response.json()
        assert data['total_ingredients'] == 0
        assert data['results'] == []

    def test_import_search_no_matches(self, client):
        """Test searching for non-existent items"""
        response = client.post('/api/recipes/import-search', json={
            'ingredients': ['xyzabc123notarealproduct'],
            'max_results_per_item': 3,
            'store_number': 86
        })

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        # Should return result with empty matches
        assert len(data['results']) == 1
        assert data['results'][0]['match_count'] == 0
        assert data['results'][0]['matches'] == []

    def test_get_recipe_items(self, client):
        """Test GET /api/recipes/{id}/items endpoint"""
        # Create a recipe first
        create_response = client.post('/api/recipes/create', json={
            'name': 'Test Recipe for Items'
        })
        recipe_id = create_response.json()['recipe_id']

        # Add items to recipe
        client.post(f'/api/recipes/{recipe_id}/items', json={
            'name': 'Test Item',
            'price': '$5.99',
            'quantity': 1
        })

        # Get recipe items
        response = client.get(f'/api/recipes/{recipe_id}/items')

        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert 'items' in data
        assert len(data['items']) >= 1
        assert data['items'][0]['product_name'] == 'Test Item'

    def test_get_recipe_items_not_found(self, client):
        """Test getting items for non-existent recipe"""
        response = client.get('/api/recipes/99999/items')

        assert response.status_code == 404

    def test_parse_then_search_flow(self, client):
        """Test complete import flow: parse → search"""
        # Step 1: Parse recipe
        parse_response = client.post('/api/recipes/parse', json={
            'text': '2 tablespoons olive oil\n1 pound chicken\n1 onion, chopped'
        })

        assert parse_response.status_code == 200
        parse_data = parse_response.json()
        ingredient_names = [ing['name'] for ing in parse_data['ingredients']]

        # Step 2: Search for ingredients
        search_response = client.post('/api/recipes/import-search', json={
            'ingredients': ingredient_names,
            'max_results_per_item': 3,
            'store_number': 86
        })

        assert search_response.status_code == 200
        search_data = search_response.json()
        assert len(search_data['results']) == len(ingredient_names)
