"""
Database module - PostgreSQL via Supabase
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Optional, List, Dict
import json
from config.settings import settings

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = psycopg2.connect(settings.DATABASE_URL)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

# === Cart Operations ===

def get_user_cart(user_id: int) -> List[Dict]:
    """Get all items in user's cart"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT * FROM shopping_carts
            WHERE user_id = %s
            ORDER BY added_at DESC
        """, (user_id,))
        return cursor.fetchall()

def add_to_cart(user_id: int, product: dict, quantity: float = 1):
    """
    Add item to cart (or update quantity if exists)
    
    Supports weight-based items (quantity can be decimal like 1.5)
    """
    with get_db() as cursor:
        # Check if item already in cart
        cursor.execute("""
            SELECT id, quantity FROM shopping_carts
            WHERE user_id = %s AND product_name = %s
        """, (user_id, product['name']))
        
        existing = cursor.fetchone()
        if existing:
            # Update quantity
            new_qty = float(existing['quantity']) + quantity
            cursor.execute("""
                UPDATE shopping_carts
                SET quantity = %s
                WHERE id = %s
            """, (new_qty, existing['id']))
        else:
            # Insert new item
            price_str = product['price'].replace('$', '') if isinstance(product['price'], str) else str(product['price'])
            
            cursor.execute("""
                INSERT INTO shopping_carts
                (user_id, product_name, price, quantity, aisle, image_url,
                 search_term, is_sold_by_weight, unit_price)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                product['name'],
                float(price_str),
                quantity,
                product.get('aisle'),
                product.get('image'),
                product.get('search_term', ''),
                product.get('is_sold_by_weight', False),
                product.get('unit_price')
            ))

def update_cart_quantity(user_id: int, cart_item_id: int, quantity: float):
    """Update item quantity (supports decimals for weight)"""
    with get_db() as cursor:
        cursor.execute("""
            UPDATE shopping_carts
            SET quantity = %s
            WHERE id = %s AND user_id = %s
        """, (quantity, cart_item_id, user_id))

def remove_from_cart(user_id: int, cart_item_id: int):
    """Remove item from cart"""
    with get_db() as cursor:
        cursor.execute("""
            DELETE FROM shopping_carts
            WHERE id = %s AND user_id = %s
        """, (cart_item_id, user_id))

def clear_cart(user_id: int):
    """Clear entire cart"""
    with get_db() as cursor:
        cursor.execute("DELETE FROM shopping_carts WHERE user_id = %s", (user_id,))

# === Search Cache Operations ===

def get_cached_search(search_term: str) -> Optional[List]:
    """Get cached search results (if not expired)"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT results_json, cached_at
            FROM search_cache
            WHERE LOWER(search_term) = LOWER(%s)
            AND cached_at > NOW() - INTERVAL '7 days'
        """, (search_term,))
        
        row = cursor.fetchone()
        if row:
            # Increment hit count
            cursor.execute("""
                UPDATE search_cache
                SET hit_count = hit_count + 1
                WHERE LOWER(search_term) = LOWER(%s)
            """, (search_term,))
            
            return row['results_json']  # JSONB type, returns as Python list
        return None

def cache_search_results(search_term: str, results: List[Dict]):
    """Cache search results"""
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO search_cache (search_term, results_json, cached_at, hit_count)
            VALUES (LOWER(%s), %s, CURRENT_TIMESTAMP, 0)
            ON CONFLICT (search_term) DO UPDATE SET
                results_json = EXCLUDED.results_json,
                cached_at = CURRENT_TIMESTAMP
        """, (search_term, json.dumps(results)))

# === Saved Lists Operations ===

def get_user_lists(user_id: int) -> List[Dict]:
    """Get all saved lists for user with their items"""
    with get_db() as cursor:
        # Get all lists
        cursor.execute("""
            SELECT l.id, l.name, l.created_at,
                   COUNT(li.id) as item_count,
                   COALESCE(SUM(li.quantity), 0) as total_quantity,
                   COALESCE(SUM(li.price * li.quantity), 0) as total_price
            FROM saved_lists l
            LEFT JOIN saved_list_items li ON l.id = li.list_id
            WHERE l.user_id = %s
            GROUP BY l.id, l.name, l.created_at
            ORDER BY l.created_at DESC
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

def save_cart_as_list(user_id: int, list_name: str) -> int:
    """Save current cart as a list"""
    with get_db() as cursor:
        # Create list
        cursor.execute("""
            INSERT INTO saved_lists (user_id, name)
            VALUES (%s, %s)
            RETURNING id
        """, (user_id, list_name))
        list_id = cursor.fetchone()['id']
        
        # Copy cart items to list
        cursor.execute("""
            INSERT INTO saved_list_items
            (list_id, product_name, price, quantity, aisle, is_sold_by_weight)
            SELECT %s, product_name, price, quantity, aisle, is_sold_by_weight
            FROM shopping_carts
            WHERE user_id = %s
        """, (list_id, user_id))
        
        return list_id

def load_list_to_cart(user_id: int, list_id: int):
    """Load a saved list into cart"""
    with get_db() as cursor:
        # Verify list belongs to user
        cursor.execute("""
            SELECT id FROM saved_lists WHERE id = %s AND user_id = %s
        """, (list_id, user_id))
        
        if not cursor.fetchone():
            raise ValueError("List not found")
        
        # Clear current cart
        clear_cart(user_id)
        
        # Load list items into cart
        cursor.execute("""
            INSERT INTO shopping_carts
            (user_id, product_name, price, quantity, aisle, search_term, is_sold_by_weight)
            SELECT %s, product_name, price, quantity, aisle, '', is_sold_by_weight
            FROM saved_list_items
            WHERE list_id = %s
        """, (user_id, list_id))

# === Frequent Items ===

def update_frequent_items(user_id: int):
    """Update frequent items from completed cart"""
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO frequent_items
            (product_name, price, aisle, image_url, purchase_count, is_sold_by_weight, last_purchased)
            SELECT
                product_name,
                price,
                aisle,
                image_url,
                1,
                is_sold_by_weight,
                CURRENT_TIMESTAMP
            FROM shopping_carts
            WHERE user_id = %s
            ON CONFLICT (product_name) DO UPDATE SET
                purchase_count = frequent_items.purchase_count + 1,
                last_purchased = CURRENT_TIMESTAMP,
                price = EXCLUDED.price,
                aisle = EXCLUDED.aisle
        """, (user_id,))

def get_frequent_items(limit: int = 20) -> List[Dict]:
    """Get most frequently purchased items"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT * FROM frequent_items
            ORDER BY purchase_count DESC, last_purchased DESC
            LIMIT %s
        """, (limit,))
        return cursor.fetchall()
