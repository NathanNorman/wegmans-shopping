"""
Database module - PostgreSQL via Supabase

Uses connection pooling for improved performance and resource management.
"""
import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, List, Dict
import json
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

# Connection pool (initialized on first import)
_connection_pool = None

def get_connection_pool():
    """
    Get or create the connection pool (singleton pattern)

    Pool configuration:
    - minconn: 2 (always keep 2 connections ready)
    - maxconn: 10 (max 10 concurrent connections)
    - Connections auto-released after use
    """
    global _connection_pool

    if _connection_pool is None:
        try:
            _connection_pool = pool.ThreadedConnectionPool(
                minconn=2,
                maxconn=10,
                dsn=settings.DATABASE_URL
            )
            logger.info("✓ Database connection pool created (2-10 connections)")
        except Exception as e:
            logger.error(f"✗ Failed to create connection pool: {e}")
            raise

    return _connection_pool

@contextmanager
def get_db():
    """
    Context manager for database connections from pool

    Automatically:
    - Gets connection from pool
    - Returns connection to pool after use
    - Commits on success
    - Rolls back on error
    """
    conn_pool = get_connection_pool()
    conn = None
    cursor = None

    try:
        conn = conn_pool.getconn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        conn.commit()
    except Exception:
        if conn:
            conn.rollback()
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn_pool.putconn(conn)

# === Cart Operations ===

def get_user_cart(user_id: str, store_number: int) -> List[Dict]:
    """Get all items in user's cart for specific store"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT * FROM shopping_carts
            WHERE user_id = %s AND store_number = %s
            ORDER BY added_at DESC
        """, (user_id, store_number))
        return cursor.fetchall()

def add_to_cart(user_id: str, product: dict, quantity: float, store_number: int):
    """
    Add item to cart (or update quantity if exists) for specific store

    Supports weight-based items (quantity can be decimal like 1.5)
    """
    with get_db() as cursor:
        # Check if item already in cart FOR THIS STORE
        cursor.execute("""
            SELECT id, quantity FROM shopping_carts
            WHERE user_id = %s AND store_number = %s AND product_name = %s
        """, (user_id, store_number, product['name']))

        existing = cursor.fetchone()
        if existing:
            # Update quantity
            new_qty = float(existing['quantity']) + quantity
            cursor.execute("""
                UPDATE shopping_carts
                SET quantity = %s
                WHERE id = %s AND user_id = %s AND store_number = %s
            """, (new_qty, existing['id'], user_id, store_number))
        else:
            # Insert new item WITH store_number
            price_str = product['price'].replace('$', '') if isinstance(product['price'], str) else str(product['price'])

            cursor.execute("""
                INSERT INTO shopping_carts
                (user_id, store_number, product_name, price, quantity, aisle, image_url,
                 search_term, is_sold_by_weight, unit_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                store_number,
                product['name'],
                float(price_str),
                quantity,
                product.get('aisle'),
                product.get('image'),
                product.get('search_term', ''),
                product.get('is_sold_by_weight', False),
                product.get('unit_price')
            ))

def update_cart_quantity(user_id: str, cart_item_id: int, quantity: float, store_number: int):
    """Update item quantity for specific store (supports decimals for weight)"""
    with get_db() as cursor:
        cursor.execute("""
            UPDATE shopping_carts
            SET quantity = %s
            WHERE id = %s AND user_id = %s AND store_number = %s
        """, (quantity, cart_item_id, user_id, store_number))

def remove_from_cart(user_id: str, cart_item_id: int, store_number: int):
    """Remove item from cart for specific store"""
    with get_db() as cursor:
        cursor.execute("""
            DELETE FROM shopping_carts
            WHERE id = %s AND user_id = %s AND store_number = %s
        """, (cart_item_id, user_id, store_number))

def clear_cart(user_id: str, store_number: int):
    """Clear entire cart for specific store"""
    with get_db() as cursor:
        cursor.execute("""
            DELETE FROM shopping_carts
            WHERE user_id = %s AND store_number = %s
        """, (user_id, store_number))

# === Search Cache Operations ===

def get_cached_search(search_term: str, store_number: int) -> Optional[List]:
    """
    Get cached search results for specific store (if not expired)

    Returns None on cache miss OR error (fail gracefully)
    """
    try:
        with get_db() as cursor:
            cursor.execute("""
                SELECT results_json, cached_at
                FROM search_cache
                WHERE LOWER(search_term) = LOWER(%s)
                AND store_number = %s
                AND cached_at > NOW() - INTERVAL '7 days'
            """, (search_term, store_number))

            row = cursor.fetchone()
            if row:
                # Increment hit count (best effort - don't fail if this fails)
                try:
                    cursor.execute("""
                        UPDATE search_cache
                        SET hit_count = hit_count + 1
                        WHERE LOWER(search_term) = LOWER(%s)
                        AND store_number = %s
                    """, (search_term, store_number))
                except Exception as e:
                    logger.warning(f"Failed to update cache hit count: {e}")

                return row['results_json']  # JSONB type, returns as Python list
            return None
    except Exception as e:
        logger.error(f"Search cache read failed for '{search_term}' at store {store_number}: {e}")
        return None  # Cache miss on error - search will fetch fresh

def cache_search_results(search_term: str, results: List[Dict], store_number: int):
    """
    Cache search results for specific store

    Best effort - doesn't raise exceptions if caching fails
    """
    try:
        with get_db() as cursor:
            cursor.execute("""
                INSERT INTO search_cache (search_term, store_number, results_json, cached_at, hit_count)
                VALUES (LOWER(%s), %s, %s, CURRENT_TIMESTAMP, 0)
                ON CONFLICT (store_number, search_term) DO UPDATE SET
                    results_json = EXCLUDED.results_json,
                    cached_at = CURRENT_TIMESTAMP
            """, (search_term, store_number, json.dumps(results)))
            logger.debug(f"Cached search results for '{search_term}' at store {store_number} ({len(results)} items)")
    except Exception as e:
        logger.error(f"Search cache write failed for '{search_term}' at store {store_number}: {e}")
        # Don't raise - caching is optional optimization

# === Saved Lists Operations ===

def get_user_lists(user_id: str, store_number: int = None) -> List[Dict]:
    """Get all saved lists for user with their items (optionally filtered by store)"""
    with get_db() as cursor:
        # Get all lists (filtered by store if specified)
        if store_number is not None:
            cursor.execute("""
                SELECT l.id, l.name, l.created_at, l.is_auto_saved, l.store_number,
                       COUNT(li.id) as item_count,
                       COALESCE(SUM(li.quantity), 0) as total_quantity,
                       COALESCE(SUM(li.price * li.quantity), 0) as total_price
                FROM saved_lists l
                LEFT JOIN saved_list_items li ON l.id = li.list_id
                WHERE l.user_id = %s AND l.store_number = %s
                GROUP BY l.id, l.name, l.created_at, l.is_auto_saved, l.store_number
                ORDER BY l.created_at DESC
            """, (user_id, store_number))
        else:
            # Return all lists across all stores
            cursor.execute("""
                SELECT l.id, l.name, l.created_at, l.is_auto_saved, l.store_number,
                       COUNT(li.id) as item_count,
                       COALESCE(SUM(li.quantity), 0) as total_quantity,
                       COALESCE(SUM(li.price * li.quantity), 0) as total_price
                FROM saved_lists l
                LEFT JOIN saved_list_items li ON l.id = li.list_id
                WHERE l.user_id = %s
                GROUP BY l.id, l.name, l.created_at, l.is_auto_saved, l.store_number
                ORDER BY l.store_number, l.created_at DESC
            """, (user_id,))
        lists = cursor.fetchall()

        # For each list, fetch its items
        for list_obj in lists:
            cursor.execute("""
                SELECT product_name, price, quantity, aisle, is_sold_by_weight
                FROM saved_list_items
                WHERE list_id = %s
            """, (list_obj['id'],))
            list_obj['items'] = cursor.fetchall()

        return lists

def save_cart_as_list(user_id: str, list_name: str, store_number: int) -> int:
    """
    Save current cart as a list for specific store (atomic transaction)

    Transaction safety:
    - Both INSERT operations wrapped in single transaction
    - If cart copy fails, list creation is rolled back
    - get_db() context manager handles commit/rollback automatically
    """
    with get_db() as cursor:
        # Step 1: Create list WITH store_number
        cursor.execute("""
            INSERT INTO saved_lists (user_id, name, store_number)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, list_name, store_number))
        result = cursor.fetchone()

        if not result:
            raise ValueError("Failed to create saved list")

        list_id = result['id']

        # Step 2: Copy cart items to list (within same transaction)
        cursor.execute("""
            INSERT INTO saved_list_items
            (list_id, product_name, price, quantity, aisle, is_sold_by_weight)
            SELECT %s, product_name, price, quantity, aisle, is_sold_by_weight
            FROM shopping_carts
            WHERE user_id = %s AND store_number = %s
        """, (list_id, user_id, store_number))

        # Both operations commit together (or rollback together on error)
        return list_id

def load_list_to_cart(user_id: str, list_id: int, store_number: int):
    """
    Load a saved list into cart for specific store (atomic transaction)

    Transaction safety:
    - Verification, cart clear, and item load in single transaction
    - If any step fails, entire operation is rolled back
    - User's cart remains unchanged on error
    """
    with get_db() as cursor:
        # Step 1: Verify list belongs to user AND matches store
        cursor.execute("""
            SELECT id, store_number FROM saved_lists
            WHERE id = %s AND user_id = %s
        """, (list_id, user_id))

        list_info = cursor.fetchone()
        if not list_info:
            raise ValueError("List not found or access denied")

        if list_info['store_number'] != store_number:
            raise ValueError(f"List is for store {list_info['store_number']}, not store {store_number}")

        # Step 2: Clear current cart FOR THIS STORE (within transaction)
        cursor.execute("""
            DELETE FROM shopping_carts
            WHERE user_id = %s AND store_number = %s
        """, (user_id, store_number))

        # Step 3: Load list items into cart WITH store_number (within same transaction)
        cursor.execute("""
            INSERT INTO shopping_carts
            (user_id, store_number, product_name, price, quantity, aisle, search_term, is_sold_by_weight)
            SELECT %s, %s, product_name, price, quantity, aisle, '', is_sold_by_weight
            FROM saved_list_items
            WHERE list_id = %s
        """, (user_id, store_number, list_id))

        # All 3 operations commit together (or rollback together on error)

# === Frequent Items ===

def update_frequent_items(user_id: str, store_number: int):
    """Update frequent items from completed cart for specific store (user-specific)"""
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO frequent_items
            (user_id, store_number, product_name, price, aisle, image_url, purchase_count, is_sold_by_weight, last_purchased)
            SELECT
                %s,
                %s,
                product_name,
                price,
                aisle,
                image_url,
                1,
                is_sold_by_weight,
                CURRENT_TIMESTAMP
            FROM shopping_carts
            WHERE user_id = %s AND store_number = %s
            ON CONFLICT (user_id, store_number, product_name) DO UPDATE SET
                purchase_count = frequent_items.purchase_count + 1,
                last_purchased = CURRENT_TIMESTAMP,
                price = EXCLUDED.price,
                aisle = EXCLUDED.aisle,
                image_url = EXCLUDED.image_url
        """, (user_id, store_number, user_id, store_number))

def get_frequent_items(user_id: str, store_number: int, limit: int = 20) -> List[Dict]:
    """
    Get auto-learned frequently purchased items for specific store (excludes manual favorites)

    Only returns items where:
    - store_number matches
    - is_manual = FALSE (not manually starred)
    - purchase_count >= 2 (appeared in 2+ lists)
    """
    with get_db() as cursor:
        cursor.execute("""
            SELECT * FROM frequent_items
            WHERE user_id = %s
              AND store_number = %s
              AND is_manual = FALSE
              AND purchase_count >= 2
            ORDER BY purchase_count DESC, last_purchased DESC
            LIMIT %s
        """, (user_id, store_number, limit))
        return cursor.fetchall()

# === Favorites Operations ===

def add_favorite(user_id: str, product_name: str, price: str, aisle: str, image_url: str, is_sold_by_weight: bool, store_number: int):
    """
    Add item to favorites (manual) for specific store

    Sets is_manual=TRUE and purchase_count=999 to ensure it appears at top of frequent items
    """
    with get_db() as cursor:
        # Parse price (remove $ if present)
        price_float = float(price.replace('$', '')) if isinstance(price, str) and price.startswith('$') else float(price)

        cursor.execute("""
            INSERT INTO frequent_items
                (user_id, store_number, product_name, price, aisle, image_url, purchase_count, is_manual, is_sold_by_weight, last_purchased)
            VALUES (%s, %s, %s, %s, %s, %s, 999, TRUE, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id, store_number, product_name)
            DO UPDATE SET
                is_manual = TRUE,
                purchase_count = GREATEST(frequent_items.purchase_count, 999),
                last_purchased = CURRENT_TIMESTAMP,
                price = EXCLUDED.price,
                aisle = EXCLUDED.aisle,
                image_url = COALESCE(NULLIF(EXCLUDED.image_url, ''), frequent_items.image_url),
                is_sold_by_weight = EXCLUDED.is_sold_by_weight
        """, (user_id, store_number, product_name, price_float, aisle, image_url, is_sold_by_weight))

def remove_favorite(user_id: str, product_name: str, store_number: int):
    """
    Remove manual favorite for specific store (keep if auto-generated with count >= 2)

    Sets is_manual=FALSE. If item is not auto-frequent (count < 2), deletes it entirely.
    """
    with get_db() as cursor:
        # First, update is_manual to FALSE
        cursor.execute("""
            UPDATE frequent_items
            SET is_manual = FALSE,
                purchase_count = CASE
                    WHEN purchase_count >= 999 THEN 1  -- Reset manual favorites to 1
                    ELSE purchase_count  -- Keep actual purchase count
                END
            WHERE user_id = %s AND store_number = %s AND product_name = %s
        """, (user_id, store_number, product_name))

        # Then delete if it's not actually frequent (count < 2 and not manual)
        cursor.execute("""
            DELETE FROM frequent_items
            WHERE user_id = %s
              AND store_number = %s
              AND product_name = %s
              AND purchase_count < 2
              AND is_manual = FALSE
        """, (user_id, store_number, product_name))

def get_favorites(user_id: str, store_number: int) -> List[Dict]:
    """Get all manually favorited items for user at specific store"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT * FROM frequent_items
            WHERE user_id = %s AND store_number = %s AND is_manual = TRUE
            ORDER BY last_purchased DESC
        """, (user_id, store_number))
        return cursor.fetchall()

def check_if_favorited(user_id: str, product_name: str, store_number: int) -> bool:
    """Check if a specific product is manually favorited at specific store"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM frequent_items
                WHERE user_id = %s AND store_number = %s AND product_name = %s AND is_manual = TRUE
            )
        """, (user_id, store_number, product_name))
        result = cursor.fetchone()
        return result['exists'] if result else False

# === Recipe Operations ===

def get_user_recipes(user_id: str, store_number: int) -> List[Dict]:
    """Get all recipes for user at specific store with their items"""
    with get_db() as cursor:
        # Get all recipes FOR THIS STORE
        cursor.execute("""
            SELECT r.id, r.name, r.description, r.created_at, r.last_updated, r.store_number,
                   COUNT(ri.id) as item_count,
                   COALESCE(SUM(ri.quantity), 0) as total_quantity,
                   COALESCE(SUM(ri.price * ri.quantity), 0) as total_price
            FROM recipes r
            LEFT JOIN recipe_items ri ON r.id = ri.recipe_id
            WHERE r.user_id = %s AND r.store_number = %s
            GROUP BY r.id, r.name, r.description, r.created_at, r.last_updated, r.store_number
            ORDER BY r.last_updated DESC
        """, (user_id, store_number))
        recipes = cursor.fetchall()

        # For each recipe, fetch its items
        for recipe in recipes:
            cursor.execute("""
                SELECT product_name, price, quantity, aisle, image_url,
                       search_term, is_sold_by_weight, unit_price
                FROM recipe_items
                WHERE recipe_id = %s
                ORDER BY id
            """, (recipe['id'],))
            recipe['items'] = cursor.fetchall()

        return recipes

def create_recipe(user_id: str, name: str, store_number: int, description: str = None) -> int:
    """Create a new recipe for specific store"""
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO recipes (user_id, store_number, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, store_number, name, description))
        return cursor.fetchone()['id']

def save_cart_as_recipe(user_id: str, name: str, store_number: int, description: str = None) -> int:
    """
    Save current cart as a recipe for specific store (atomic transaction)

    Transaction safety:
    - Recipe creation and item copy in single transaction
    - If item copy fails, recipe creation is rolled back
    - Prevents orphaned recipes without items
    """
    with get_db() as cursor:
        # Step 1: Create recipe WITH store_number
        cursor.execute("""
            INSERT INTO recipes (user_id, store_number, name, description)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (user_id, store_number, name, description))
        result = cursor.fetchone()

        if not result:
            raise ValueError("Failed to create recipe")

        recipe_id = result['id']

        # Step 2: Copy cart items to recipe (within same transaction)
        cursor.execute("""
            INSERT INTO recipe_items
            (recipe_id, product_name, price, quantity, aisle, image_url,
             search_term, is_sold_by_weight, unit_price)
            SELECT %s, product_name, price, quantity, aisle, image_url,
                   search_term, is_sold_by_weight, unit_price
            FROM shopping_carts
            WHERE user_id = %s AND store_number = %s
        """, (recipe_id, user_id, store_number))

        # Both operations commit together (or rollback together on error)
        return recipe_id

def add_item_to_recipe(recipe_id: int, item: dict):
    """Add an item to a recipe"""
    with get_db() as cursor:
        price_str = item['price'].replace('$', '') if isinstance(item['price'], str) else str(item['price'])

        cursor.execute("""
            INSERT INTO recipe_items
            (recipe_id, product_name, price, quantity, aisle, image_url,
             search_term, is_sold_by_weight, unit_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            recipe_id,
            item['name'],
            float(price_str),
            item.get('quantity', 1),
            item.get('aisle'),
            item.get('image'),
            item.get('search_term', ''),
            item.get('is_sold_by_weight', False),
            item.get('unit_price')
        ))

def update_recipe_item_quantity(recipe_item_id: int, quantity: float):
    """Update item quantity in recipe"""
    with get_db() as cursor:
        cursor.execute("""
            UPDATE recipe_items
            SET quantity = %s
            WHERE id = %s
        """, (quantity, recipe_item_id))

def remove_item_from_recipe(recipe_item_id: int):
    """Remove item from recipe"""
    with get_db() as cursor:
        cursor.execute("""
            DELETE FROM recipe_items
            WHERE id = %s
        """, (recipe_item_id,))

def update_recipe(recipe_id: int, name: str = None, description: str = None):
    """Update recipe metadata"""
    with get_db() as cursor:
        if name:
            cursor.execute("""
                UPDATE recipes
                SET name = %s, last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (name, recipe_id))
        if description is not None:  # Allow empty string
            cursor.execute("""
                UPDATE recipes
                SET description = %s, last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (description, recipe_id))

def delete_recipe(user_id: str, recipe_id: int, store_number: int):
    """Delete a recipe for specific store (cascade deletes items)"""
    with get_db() as cursor:
        cursor.execute("""
            DELETE FROM recipes
            WHERE id = %s AND user_id = %s AND store_number = %s
        """, (recipe_id, user_id, store_number))

# === Anonymous User Cleanup ===

def cleanup_stale_anonymous_users(days_old: int = 30) -> int:
    """
    Remove stale anonymous users and their data.

    Removes anonymous users who:
    - Have is_anonymous=TRUE
    - Created more than `days_old` days ago
    - Have no activity (empty cart, no saved lists, no recipes)

    Args:
        days_old: Age threshold in days (default 30)

    Returns:
        Number of users deleted
    """
    with get_db() as cursor:
        # Find stale anonymous users with no activity
        cursor.execute("""
            SELECT u.id
            FROM users u
            WHERE u.is_anonymous = TRUE
            AND u.created_at < NOW() - INTERVAL '%s days'
            AND NOT EXISTS (
                SELECT 1 FROM shopping_carts sc WHERE sc.user_id = u.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM saved_lists sl WHERE sl.user_id = u.id
            )
            AND NOT EXISTS (
                SELECT 1 FROM recipes r WHERE r.user_id = u.id
            )
        """, (days_old,))

        stale_users = cursor.fetchall()
        user_ids = [user['id'] for user in stale_users]

        if not user_ids:
            return 0

        # Delete stale anonymous users (cascades to related data)
        placeholders = ','.join(['%s'] * len(user_ids))
        cursor.execute(f"""
            DELETE FROM users
            WHERE id IN ({placeholders})
        """, user_ids)

        return len(user_ids)

def get_anonymous_user_stats() -> Dict:
    """Get statistics about anonymous users"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT
                COUNT(*) as total_anonymous,
                COUNT(CASE WHEN created_at > NOW() - INTERVAL '7 days' THEN 1 END) as active_7d,
                COUNT(CASE WHEN created_at > NOW() - INTERVAL '30 days' THEN 1 END) as active_30d,
                COUNT(CASE WHEN created_at < NOW() - INTERVAL '30 days' THEN 1 END) as stale_30d
            FROM users
            WHERE is_anonymous = TRUE
        """)
        return cursor.fetchone()

def load_recipe_to_cart(user_id: str, recipe_id: int, store_number: int, item_ids: List[int] = None):
    """
    Load recipe items into cart for specific store

    Args:
        user_id: User ID
        recipe_id: Recipe ID
        store_number: Store number
        item_ids: Optional list of specific recipe_item IDs to add (for selective adding)
    """
    with get_db() as cursor:
        # Verify recipe belongs to user AND matches store
        cursor.execute("""
            SELECT id, store_number FROM recipes
            WHERE id = %s AND user_id = %s
        """, (recipe_id, user_id))

        recipe_info = cursor.fetchone()
        if not recipe_info:
            raise ValueError("Recipe not found")

        if recipe_info['store_number'] != store_number:
            raise ValueError(f"Recipe is for store {recipe_info['store_number']}, not store {store_number}")

        # Build query based on whether specific items are selected
        if item_ids:
            placeholders = ','.join(['%s'] * len(item_ids))
            cursor.execute(f"""
                INSERT INTO shopping_carts
                (user_id, store_number, product_name, price, quantity, aisle, image_url,
                 search_term, is_sold_by_weight, unit_price)
                SELECT %s, %s, product_name, price, quantity, aisle, image_url,
                       search_term, is_sold_by_weight, unit_price
                FROM recipe_items
                WHERE recipe_id = %s AND id IN ({placeholders})
                ON CONFLICT (user_id, store_number, product_name) DO UPDATE SET
                    quantity = shopping_carts.quantity + EXCLUDED.quantity
            """, (user_id, store_number, recipe_id, *item_ids))
        else:
            # Add all items
            cursor.execute("""
                INSERT INTO shopping_carts
                (user_id, store_number, product_name, price, quantity, aisle, image_url,
                 search_term, is_sold_by_weight, unit_price)
                SELECT %s, %s, product_name, price, quantity, aisle, image_url,
                       search_term, is_sold_by_weight, unit_price
                FROM recipe_items
                WHERE recipe_id = %s
                ON CONFLICT (user_id, store_number, product_name) DO UPDATE SET
                    quantity = shopping_carts.quantity + EXCLUDED.quantity
            """, (user_id, store_number, recipe_id))

# === User Store Operations ===

def get_user_store(user_id: str) -> int:
    """Get user's default store number"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT store_number FROM users WHERE id = %s
        """, (user_id,))
        result = cursor.fetchone()
        return result['store_number'] if result else 86  # Default to Raleigh

def update_user_store(user_id: str, store_number: int):
    """Update user's default store"""
    with get_db() as cursor:
        cursor.execute("""
            UPDATE users
            SET store_number = %s
            WHERE id = %s
        """, (store_number, user_id))

def clear_all_user_data(user_id: str, store_number: int):
    """Clear all store-specific data for user (for store switching)"""
    with get_db() as cursor:
        # Clear cart
        cursor.execute("DELETE FROM shopping_carts WHERE user_id = %s AND store_number = %s",
                      (user_id, store_number))

        # Clear favorites/frequent
        cursor.execute("DELETE FROM frequent_items WHERE user_id = %s AND store_number = %s",
                      (user_id, store_number))

        # Clear saved lists (cascades to list items)
        cursor.execute("DELETE FROM saved_lists WHERE user_id = %s AND store_number = %s",
                      (user_id, store_number))

        # Clear recipes (cascades to recipe items)
        cursor.execute("DELETE FROM recipes WHERE user_id = %s AND store_number = %s",
                      (user_id, store_number))
