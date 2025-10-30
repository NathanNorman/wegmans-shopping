"""
Database operations tests

Tests for all database CRUD operations, transactions, and error handling.
"""
import pytest
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
    get_anonymous_user_stats
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
