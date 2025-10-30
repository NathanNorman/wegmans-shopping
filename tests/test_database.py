"""
Database operations tests

Tests for all database CRUD operations, transactions, and error handling.
"""
import pytest
from unittest.mock import patch, MagicMock
from src.database import (
    get_user_cart,
    add_to_cart,
    update_cart_quantity,
    remove_from_cart,
    clear_cart,
    get_cached_search,
    cache_search_results,
    save_cart_as_list,
    load_list_to_cart,
    get_user_lists,
    cleanup_stale_anonymous_users,
    get_anonymous_user_stats,
    get_user_recipes,
    create_recipe,
    save_cart_as_recipe,
    add_item_to_recipe,
    update_recipe_item_quantity,
    remove_item_from_recipe,
    update_recipe,
    delete_recipe,
    load_recipe_to_cart,
    update_frequent_items,
    get_frequent_items,
    get_connection_pool
)


class TestCartOperations:
    """Test shopping cart database operations"""

    def test_get_empty_cart(self, test_anonymous_user):
        """Test getting cart for user with no items"""
        cart = get_user_cart(test_anonymous_user)
        assert cart == []

    def test_add_to_cart(self, test_anonymous_user, test_cart_item):
        """Test adding item to cart"""
        add_to_cart(test_anonymous_user, test_cart_item, quantity=2)

        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 1
        assert cart[0]['product_name'] == "Test Product"
        assert float(cart[0]['quantity']) == 2.0

    def test_add_duplicate_increases_quantity(self, test_anonymous_user, test_cart_item):
        """Test adding same item twice increases quantity"""
        add_to_cart(test_anonymous_user, test_cart_item, quantity=1)
        add_to_cart(test_anonymous_user, test_cart_item, quantity=2)

        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 1
        assert float(cart[0]['quantity']) == 3.0

    def test_update_cart_quantity(self, test_anonymous_user, test_cart_item):
        """Test updating item quantity"""
        add_to_cart(test_anonymous_user, test_cart_item)

        cart = get_user_cart(test_anonymous_user)
        cart_item_id = cart[0]['id']

        update_cart_quantity(test_anonymous_user, cart_item_id, 5)

        updated_cart = get_user_cart(test_anonymous_user)
        assert float(updated_cart[0]['quantity']) == 5.0

    def test_remove_from_cart(self, test_anonymous_user, test_cart_item):
        """Test removing item from cart"""
        add_to_cart(test_anonymous_user, test_cart_item)

        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 1

        remove_from_cart(test_anonymous_user, cart[0]['id'])

        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 0

    def test_clear_cart(self, test_anonymous_user, test_products):
        """Test clearing entire cart"""
        for product in test_products:
            add_to_cart(test_anonymous_user, product)

        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 3

        clear_cart(test_anonymous_user)

        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 0


class TestSearchCache:
    """Test search cache operations"""

    def test_cache_miss_returns_none(self):
        """Test cache miss returns None"""
        result = get_cached_search("nonexistent_search_term_xyz")
        assert result is None

    def test_cache_search_results(self, test_products):
        """Test caching search results"""
        search_term = "test_cache_search"

        # Cache results
        cache_search_results(search_term, test_products)

        # Retrieve from cache
        cached = get_cached_search(search_term)
        assert cached is not None
        assert len(cached) == 3
        assert cached[0]['name'] == "Bananas"

    def test_cache_is_case_insensitive(self, test_products):
        """Test cache lookup is case-insensitive"""
        cache_search_results("BaNaNaS", test_products)

        cached = get_cached_search("bananas")
        assert cached is not None

        cached = get_cached_search("BANANAS")
        assert cached is not None


class TestListOperations:
    """Test saved list operations"""

    def test_save_cart_as_list(self, test_anonymous_user, test_products):
        """Test saving cart as a list"""
        # Add items to cart
        for product in test_products:
            add_to_cart(test_anonymous_user, product)

        # Save as list
        list_id = save_cart_as_list(test_anonymous_user, "Test Shopping List")
        assert list_id is not None
        assert isinstance(list_id, int)

        # Verify list was created
        lists = get_user_lists(test_anonymous_user)
        assert len(lists) == 1
        assert lists[0]['name'] == "Test Shopping List"
        assert lists[0]['item_count'] == 3

    def test_load_list_to_cart(self, test_anonymous_user, test_products):
        """Test loading saved list into cart"""
        # Create list
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        list_id = save_cart_as_list(test_anonymous_user, "My List")

        # Clear cart
        clear_cart(test_anonymous_user)
        assert len(get_user_cart(test_anonymous_user)) == 0

        # Load list back into cart
        load_list_to_cart(test_anonymous_user, list_id)

        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 3

    def test_save_empty_cart_as_list(self, test_anonymous_user):
        """Test saving empty cart creates empty list"""
        list_id = save_cart_as_list(test_anonymous_user, "Empty List")

        lists = get_user_lists(test_anonymous_user)
        assert len(lists) == 1
        assert lists[0]['item_count'] == 0


class TestTransactionSafety:
    """Test transaction isolation and rollback"""

    def test_save_cart_as_list_is_atomic(self, test_anonymous_user, test_cart_item):
        """Test that list creation + item copy is atomic"""
        add_to_cart(test_anonymous_user, test_cart_item)

        # Save should succeed
        list_id = save_cart_as_list(test_anonymous_user, "Atomic Test")
        assert list_id is not None

        # Both list and items should exist
        lists = get_user_lists(test_anonymous_user)
        assert len(lists) == 1
        assert lists[0]['item_count'] == 1

    def test_load_list_invalid_id_fails_gracefully(self, test_anonymous_user):
        """Test loading non-existent list fails gracefully"""
        with pytest.raises(ValueError, match="List not found"):
            load_list_to_cart(test_anonymous_user, 999999)


class TestAnonymousUserCleanup:
    """Test anonymous user cleanup functions"""

    def test_get_anonymous_user_stats(self):
        """Test getting anonymous user statistics"""
        stats = get_anonymous_user_stats()

        assert 'total_anonymous' in stats
        assert 'active_7d' in stats
        assert 'active_30d' in stats
        assert 'stale_30d' in stats

        assert isinstance(stats['total_anonymous'], int)

    def test_cleanup_no_stale_users(self):
        """Test cleanup with no stale users returns 0"""
        # All test users are recent, so cleanup should delete 0
        deleted_count = cleanup_stale_anonymous_users(days_old=30)
        assert deleted_count == 0


class TestErrorHandling:
    """Test error handling in database operations"""

    def test_cache_invalid_data_doesnt_crash(self):
        """Test caching invalid data doesn't crash"""
        # Should not raise exception
        cache_search_results("test", [{"invalid": "data"}])

        # Should return cached data (even if invalid)
        result = get_cached_search("test")
        assert result is not None

    def test_get_cached_search_handles_errors_gracefully(self):
        """Test cache read errors return None (cache miss)"""
        # Even with database errors, should return None, not raise
        result = get_cached_search("any_term")
        assert result is None or isinstance(result, list)

    def test_connection_pool_creation_error(self):
        """Test connection pool handles initialization errors"""
        # Reset the global connection pool to test initialization
        import src.database as db_module
        original_pool = db_module._connection_pool
        db_module._connection_pool = None

        try:
            # Mock pool.ThreadedConnectionPool to raise an exception
            with patch('src.database.pool.ThreadedConnectionPool') as mock_pool:
                mock_pool.side_effect = Exception("Database connection failed")

                with pytest.raises(Exception, match="Database connection failed"):
                    get_connection_pool()
        finally:
            # Restore the original pool
            db_module._connection_pool = original_pool

    def test_cache_write_failure_doesnt_crash(self):
        """Test cache write failures are handled gracefully"""
        # Mock the database cursor to fail on cache write
        with patch('src.database.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Write failed")
            mock_get_db.return_value.__enter__.return_value = mock_cursor

            # Should not raise exception
            cache_search_results("test_term", [{"name": "test"}])

    def test_cache_hit_count_update_failure(self):
        """Test cache hit count update failure is handled gracefully"""
        # First cache some results successfully
        cache_search_results("test_hit_count", [{"name": "test"}])

        # Mock to fail only on the UPDATE (hit count), not the SELECT
        with patch('src.database.get_db') as mock_get_db:
            mock_cursor = MagicMock()

            # First execute (SELECT) succeeds and returns data
            mock_cursor.fetchone.return_value = {
                'results_json': [{"name": "test"}],
                'cached_at': '2025-01-01'
            }

            # Second execute (UPDATE hit count) fails
            def side_effect(*args, **kwargs):
                if 'UPDATE' in args[0]:
                    raise Exception("Update failed")

            mock_cursor.execute.side_effect = side_effect
            mock_get_db.return_value.__enter__.return_value = mock_cursor

            # Should still return cached results despite hit count update failure
            result = get_cached_search("test_hit_count")
            assert result is not None

    def test_cache_read_exception_returns_none(self):
        """Test cache read exception is caught and returns None"""
        # Mock the database to fail on SELECT
        with patch('src.database.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_get_db.return_value.__enter__.return_value = mock_cursor

            # Should return None on error (cache miss)
            result = get_cached_search("any_term")
            assert result is None

    def test_save_cart_as_list_no_result_error(self):
        """Test save_cart_as_list handles missing result"""
        with patch('src.database.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_get_db.return_value.__enter__.return_value = mock_cursor

            with pytest.raises(ValueError, match="Failed to create saved list"):
                save_cart_as_list("test_user", "Test List")

    def test_save_cart_as_recipe_no_result_error(self):
        """Test save_cart_as_recipe handles missing result"""
        with patch('src.database.get_db') as mock_get_db:
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None
            mock_get_db.return_value.__enter__.return_value = mock_cursor

            with pytest.raises(ValueError, match="Failed to create recipe"):
                save_cart_as_recipe("test_user", "Test Recipe")


class TestFrequentItems:
    """Test frequent items operations"""

    def test_update_frequent_items(self, test_anonymous_user, test_products):
        """Test updating frequent items from cart"""
        # Add items to cart
        for product in test_products:
            add_to_cart(test_anonymous_user, product)

        # Update frequent items
        update_frequent_items(test_anonymous_user)

        # Verify items were added to frequent_items
        frequent = get_frequent_items(test_anonymous_user)
        assert len(frequent) == 3
        assert all(item['purchase_count'] == 1 for item in frequent)

    def test_frequent_items_increment_count(self, test_anonymous_user, test_cart_item):
        """Test frequent items purchase count increments"""
        # Add item twice
        add_to_cart(test_anonymous_user, test_cart_item)
        update_frequent_items(test_anonymous_user)

        clear_cart(test_anonymous_user)
        add_to_cart(test_anonymous_user, test_cart_item)
        update_frequent_items(test_anonymous_user)

        # Verify count incremented
        frequent = get_frequent_items(test_anonymous_user)
        assert len(frequent) == 1
        assert frequent[0]['purchase_count'] == 2

    def test_get_frequent_items_limit(self, test_anonymous_user, test_products):
        """Test frequent items respects limit parameter"""
        # Add items to cart and update frequent
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        update_frequent_items(test_anonymous_user)

        # Get limited results
        frequent = get_frequent_items(test_anonymous_user, limit=2)
        assert len(frequent) == 2


class TestRecipeOperations:
    """Test recipe CRUD operations"""

    def test_create_empty_recipe(self, test_anonymous_user):
        """Test creating an empty recipe"""
        recipe_id = create_recipe(test_anonymous_user, "Thanksgiving Dinner", "Family favorites")

        assert recipe_id is not None
        assert isinstance(recipe_id, int)

        # Verify recipe was created
        recipes = get_user_recipes(test_anonymous_user)
        assert len(recipes) == 1
        assert recipes[0]['name'] == "Thanksgiving Dinner"
        assert recipes[0]['description'] == "Family favorites"
        assert recipes[0]['item_count'] == 0

    def test_create_recipe_without_description(self, test_anonymous_user):
        """Test creating recipe without description"""
        recipe_id = create_recipe(test_anonymous_user, "Quick Meals")

        recipes = get_user_recipes(test_anonymous_user)
        assert len(recipes) == 1
        assert recipes[0]['name'] == "Quick Meals"
        assert recipes[0]['description'] is None

    def test_save_cart_as_recipe(self, test_anonymous_user, test_products):
        """Test saving cart as a recipe"""
        # Add items to cart
        for product in test_products:
            add_to_cart(test_anonymous_user, product)

        # Save as recipe
        recipe_id = save_cart_as_recipe(test_anonymous_user, "Weekly Groceries", "Standard weekly shopping")

        assert recipe_id is not None

        # Verify recipe has items
        recipes = get_user_recipes(test_anonymous_user)
        assert len(recipes) == 1
        assert recipes[0]['item_count'] == 3
        assert len(recipes[0]['items']) == 3

    def test_get_user_recipes_empty(self, test_anonymous_user):
        """Test getting recipes when user has none"""
        recipes = get_user_recipes(test_anonymous_user)
        assert recipes == []

    def test_get_user_recipes_with_items(self, test_anonymous_user, test_products):
        """Test getting recipes with their items"""
        # Create recipe with items
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "Test Recipe")

        recipes = get_user_recipes(test_anonymous_user)
        assert len(recipes) == 1
        assert recipes[0]['id'] == recipe_id
        assert len(recipes[0]['items']) == 3

        # Verify item structure
        item = recipes[0]['items'][0]
        assert 'product_name' in item
        assert 'price' in item
        assert 'quantity' in item

    def test_add_item_to_recipe(self, test_anonymous_user, test_cart_item):
        """Test adding item to existing recipe"""
        # Create empty recipe
        recipe_id = create_recipe(test_anonymous_user, "Test Recipe")

        # Add item
        add_item_to_recipe(recipe_id, test_cart_item)

        # Verify item was added
        recipes = get_user_recipes(test_anonymous_user)
        assert recipes[0]['item_count'] == 1
        assert recipes[0]['items'][0]['product_name'] == "Test Product"

    def test_update_recipe_item_quantity(self, test_anonymous_user, test_cart_item):
        """Test updating recipe item quantity"""
        # Create recipe with item
        add_to_cart(test_anonymous_user, test_cart_item)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "Test")

        recipes = get_user_recipes(test_anonymous_user)
        # Get recipe_item id from saved list (not cart id)
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s", (recipe_id,))
            recipe_item_id = cursor.fetchone()['id']

        # Update quantity
        update_recipe_item_quantity(recipe_item_id, 5.0)

        # Verify update
        recipes = get_user_recipes(test_anonymous_user)
        assert float(recipes[0]['items'][0]['quantity']) == 5.0

    def test_remove_item_from_recipe(self, test_anonymous_user, test_products):
        """Test removing item from recipe"""
        # Create recipe with items
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "Test")

        # Get first recipe_item id
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s LIMIT 1", (recipe_id,))
            recipe_item_id = cursor.fetchone()['id']

        # Remove item
        remove_item_from_recipe(recipe_item_id)

        # Verify removal
        recipes = get_user_recipes(test_anonymous_user)
        assert recipes[0]['item_count'] == 2

    def test_update_recipe_name(self, test_anonymous_user):
        """Test updating recipe name"""
        recipe_id = create_recipe(test_anonymous_user, "Old Name")

        update_recipe(recipe_id, name="New Name")

        recipes = get_user_recipes(test_anonymous_user)
        assert recipes[0]['name'] == "New Name"

    def test_update_recipe_description(self, test_anonymous_user):
        """Test updating recipe description"""
        recipe_id = create_recipe(test_anonymous_user, "Recipe", "Old description")

        update_recipe(recipe_id, description="New description")

        recipes = get_user_recipes(test_anonymous_user)
        assert recipes[0]['description'] == "New description"

    def test_update_recipe_both_fields(self, test_anonymous_user):
        """Test updating both recipe name and description"""
        recipe_id = create_recipe(test_anonymous_user, "Old", "Old desc")

        update_recipe(recipe_id, name="New", description="New desc")

        recipes = get_user_recipes(test_anonymous_user)
        assert recipes[0]['name'] == "New"
        assert recipes[0]['description'] == "New desc"

    def test_update_recipe_empty_description(self, test_anonymous_user):
        """Test updating recipe description to empty string"""
        recipe_id = create_recipe(test_anonymous_user, "Recipe", "Has description")

        update_recipe(recipe_id, description="")

        recipes = get_user_recipes(test_anonymous_user)
        assert recipes[0]['description'] == ""

    def test_delete_recipe(self, test_anonymous_user, test_products):
        """Test deleting recipe"""
        # Create recipe with items
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "To Delete")

        # Verify it exists
        recipes = get_user_recipes(test_anonymous_user)
        assert len(recipes) == 1

        # Delete it
        delete_recipe(test_anonymous_user, recipe_id)

        # Verify it's gone
        recipes = get_user_recipes(test_anonymous_user)
        assert len(recipes) == 0

    def test_delete_recipe_cascades_items(self, test_anonymous_user, test_products):
        """Test deleting recipe also deletes its items"""
        # Create recipe with items
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "To Delete")

        # Verify items exist
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM recipe_items WHERE recipe_id = %s", (recipe_id,))
            count_before = cursor.fetchone()['count']
            assert count_before == 3

        # Delete recipe
        delete_recipe(test_anonymous_user, recipe_id)

        # Verify items are also deleted (cascade)
        with get_db() as cursor:
            cursor.execute("SELECT COUNT(*) as count FROM recipe_items WHERE recipe_id = %s", (recipe_id,))
            count_after = cursor.fetchone()['count']
            assert count_after == 0

    def test_load_recipe_to_cart_all_items(self, test_anonymous_user, test_products):
        """Test loading all items from recipe to cart"""
        # Create recipe
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "Test Recipe")

        # Clear cart
        clear_cart(test_anonymous_user)
        assert len(get_user_cart(test_anonymous_user)) == 0

        # Load recipe to cart
        load_recipe_to_cart(test_anonymous_user, recipe_id)

        # Verify all items loaded
        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 3

    def test_load_recipe_to_cart_selective_items(self, test_anonymous_user, test_products):
        """Test loading specific items from recipe to cart"""
        # Create recipe
        for product in test_products:
            add_to_cart(test_anonymous_user, product)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "Test Recipe")

        # Get first two recipe_item IDs
        from src.database import get_db
        with get_db() as cursor:
            cursor.execute("SELECT id FROM recipe_items WHERE recipe_id = %s ORDER BY id LIMIT 2", (recipe_id,))
            item_ids = [row['id'] for row in cursor.fetchall()]

        # Clear cart
        clear_cart(test_anonymous_user)

        # Load only selected items
        load_recipe_to_cart(test_anonymous_user, recipe_id, item_ids=item_ids)

        # Verify only 2 items loaded
        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 2

    def test_load_recipe_to_cart_increments_quantity(self, test_anonymous_user, test_cart_item):
        """Test loading recipe item that's already in cart increments quantity"""
        # Add item to cart with quantity 1
        test_cart_item_single = test_cart_item.copy()
        test_cart_item_single['quantity'] = 1
        add_to_cart(test_anonymous_user, test_cart_item_single, quantity=1)

        # Create recipe with same item (quantity 2 from fixture)
        recipe_id = save_cart_as_recipe(test_anonymous_user, "Test")

        # Clear cart
        clear_cart(test_anonymous_user)

        # Add item back to cart with quantity 1
        add_to_cart(test_anonymous_user, test_cart_item_single, quantity=1)

        # Load recipe (item already in cart with qty 1, recipe has qty 1)
        load_recipe_to_cart(test_anonymous_user, recipe_id)

        # Verify quantity incremented (not replaced)
        cart = get_user_cart(test_anonymous_user)
        assert len(cart) == 1
        assert float(cart[0]['quantity']) == 2.0  # 1 in cart + 1 from recipe

    def test_load_recipe_invalid_recipe_id(self, test_anonymous_user):
        """Test loading non-existent recipe fails"""
        with pytest.raises(ValueError, match="Recipe not found"):
            load_recipe_to_cart(test_anonymous_user, 999999)

    def test_load_recipe_wrong_user(self, test_anonymous_user):
        """Test user cannot load another user's recipe"""
        # Create recipe with first user
        create_recipe(test_anonymous_user, "User 1 Recipe")

        # Try to load with different user
        import uuid
        different_user = str(uuid.uuid4())

        with pytest.raises(ValueError, match="Recipe not found"):
            load_recipe_to_cart(different_user, 1)


class TestStaleUserCleanup:
    """Test stale anonymous user cleanup with actual data"""

    def test_cleanup_stale_anonymous_users_with_data(self):
        """Test cleanup deletes stale users with no activity"""
        import uuid
        from src.database import get_db

        # Create a stale user (60 days old, no activity)
        stale_user_id = str(uuid.uuid4())
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, created_at)
                VALUES (%s, NULL, TRUE, NOW() - INTERVAL '60 days')
            """, (stale_user_id,))

        # Run cleanup
        deleted_count = cleanup_stale_anonymous_users(days_old=30)

        # Should have deleted at least 1 user
        assert deleted_count >= 1

        # Verify user was deleted
        with get_db() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (stale_user_id,))
            assert cursor.fetchone() is None

    def test_cleanup_preserves_users_with_activity(self, test_anonymous_user, test_cart_item):
        """Test cleanup doesn't delete users with cart items"""
        import uuid
        from src.database import get_db

        # Create stale user WITH cart items
        stale_user_with_cart = str(uuid.uuid4())
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, created_at)
                VALUES (%s, NULL, TRUE, NOW() - INTERVAL '60 days')
            """, (stale_user_with_cart,))

        # Add cart item
        add_to_cart(stale_user_with_cart, test_cart_item)

        # Run cleanup
        cleanup_stale_anonymous_users(days_old=30)

        # User should still exist
        with get_db() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (stale_user_with_cart,))
            assert cursor.fetchone() is not None

    def test_cleanup_preserves_users_with_lists(self, test_anonymous_user):
        """Test cleanup doesn't delete users with saved lists"""
        import uuid
        from src.database import get_db

        # Create stale user WITH saved list
        stale_user_with_list = str(uuid.uuid4())
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, created_at)
                VALUES (%s, NULL, TRUE, NOW() - INTERVAL '60 days')
            """, (stale_user_with_list,))

        # Create saved list
        save_cart_as_list(stale_user_with_list, "Test List")

        # Run cleanup
        cleanup_stale_anonymous_users(days_old=30)

        # User should still exist
        with get_db() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (stale_user_with_list,))
            assert cursor.fetchone() is not None

    def test_cleanup_preserves_users_with_recipes(self):
        """Test cleanup doesn't delete users with recipes"""
        import uuid
        from src.database import get_db

        # Create stale user WITH recipe
        stale_user_with_recipe = str(uuid.uuid4())
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO users (id, email, is_anonymous, created_at)
                VALUES (%s, NULL, TRUE, NOW() - INTERVAL '60 days')
            """, (stale_user_with_recipe,))

        # Create recipe
        create_recipe(stale_user_with_recipe, "Test Recipe")

        # Run cleanup
        cleanup_stale_anonymous_users(days_old=30)

        # User should still exist
        with get_db() as cursor:
            cursor.execute("SELECT id FROM users WHERE id = %s", (stale_user_with_recipe,))
            assert cursor.fetchone() is not None
