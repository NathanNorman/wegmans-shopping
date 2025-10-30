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
            SELECT l.id, l.name, l.created_at, l.is_auto_saved, l.custom_name,
                   COUNT(li.id) as item_count,
                   COALESCE(SUM(li.quantity), 0) as total_quantity,
                   COALESCE(SUM(li.price * li.quantity), 0) as total_price
            FROM saved_lists l
            LEFT JOIN saved_list_items li ON l.id = li.list_id
            WHERE l.user_id = %s
            GROUP BY l.id, l.name, l.created_at, l.is_auto_saved, l.custom_name
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

def update_frequent_items(user_id: str):
    """Update frequent items from completed cart (user-specific)"""
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO frequent_items
            (user_id, product_name, price, aisle, image_url, purchase_count, is_sold_by_weight, last_purchased)
            SELECT
                %s,
                product_name,
                price,
                aisle,
                image_url,
                1,
                is_sold_by_weight,
                CURRENT_TIMESTAMP
            FROM shopping_carts
            WHERE user_id = %s
            ON CONFLICT (user_id, product_name) DO UPDATE SET
                purchase_count = frequent_items.purchase_count + 1,
                last_purchased = CURRENT_TIMESTAMP,
                price = EXCLUDED.price,
                aisle = EXCLUDED.aisle,
                image_url = EXCLUDED.image_url
        """, (user_id, user_id))

def get_frequent_items(user_id: str, limit: int = 20) -> List[Dict]:
    """Get most frequently purchased items for specific user"""
    with get_db() as cursor:
        cursor.execute("""
            SELECT * FROM frequent_items
            WHERE user_id = %s
            ORDER BY purchase_count DESC, last_purchased DESC
            LIMIT %s
        """, (user_id, limit))
        return cursor.fetchall()

# === Recipe Operations ===

def get_user_recipes(user_id: int) -> List[Dict]:
    """Get all recipes for user with their items"""
    with get_db() as cursor:
        # Get all recipes
        cursor.execute("""
            SELECT r.id, r.name, r.description, r.created_at, r.last_updated,
                   COUNT(ri.id) as item_count,
                   COALESCE(SUM(ri.quantity), 0) as total_quantity,
                   COALESCE(SUM(ri.price * ri.quantity), 0) as total_price
            FROM recipes r
            LEFT JOIN recipe_items ri ON r.id = ri.recipe_id
            WHERE r.user_id = %s
            GROUP BY r.id, r.name, r.description, r.created_at, r.last_updated
            ORDER BY r.last_updated DESC
        """, (user_id,))
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

def create_recipe(user_id: int, name: str, description: str = None) -> int:
    """Create a new recipe"""
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO recipes (user_id, name, description)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, name, description))
        return cursor.fetchone()['id']

def save_cart_as_recipe(user_id: int, name: str, description: str = None) -> int:
    """Save current cart as a recipe"""
    with get_db() as cursor:
        # Create recipe
        cursor.execute("""
            INSERT INTO recipes (user_id, name, description)
            VALUES (%s, %s, %s)
            RETURNING id
        """, (user_id, name, description))
        recipe_id = cursor.fetchone()['id']

        # Copy cart items to recipe
        cursor.execute("""
            INSERT INTO recipe_items
            (recipe_id, product_name, price, quantity, aisle, image_url,
             search_term, is_sold_by_weight, unit_price)
            SELECT %s, product_name, price, quantity, aisle, image_url,
                   search_term, is_sold_by_weight, unit_price
            FROM shopping_carts
            WHERE user_id = %s
        """, (recipe_id, user_id))

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

def delete_recipe(user_id: int, recipe_id: int):
    """Delete a recipe (cascade deletes items)"""
    with get_db() as cursor:
        cursor.execute("""
            DELETE FROM recipes
            WHERE id = %s AND user_id = %s
        """, (recipe_id, user_id))

def load_recipe_to_cart(user_id: int, recipe_id: int, item_ids: List[int] = None):
    """
    Load recipe items into cart

    Args:
        user_id: User ID
        recipe_id: Recipe ID
        item_ids: Optional list of specific recipe_item IDs to add (for selective adding)
    """
    with get_db() as cursor:
        # Verify recipe belongs to user
        cursor.execute("""
            SELECT id FROM recipes WHERE id = %s AND user_id = %s
        """, (recipe_id, user_id))

        if not cursor.fetchone():
            raise ValueError("Recipe not found")

        # Build query based on whether specific items are selected
        if item_ids:
            placeholders = ','.join(['%s'] * len(item_ids))
            cursor.execute(f"""
                INSERT INTO shopping_carts
                (user_id, product_name, price, quantity, aisle, image_url,
                 search_term, is_sold_by_weight, unit_price)
                SELECT %s, product_name, price, quantity, aisle, image_url,
                       search_term, is_sold_by_weight, unit_price
                FROM recipe_items
                WHERE recipe_id = %s AND id IN ({placeholders})
                ON CONFLICT (user_id, product_name) DO UPDATE SET
                    quantity = shopping_carts.quantity + EXCLUDED.quantity
            """, (user_id, recipe_id, *item_ids))
        else:
            # Add all items
            cursor.execute("""
                INSERT INTO shopping_carts
                (user_id, product_name, price, quantity, aisle, image_url,
                 search_term, is_sold_by_weight, unit_price)
                SELECT %s, product_name, price, quantity, aisle, image_url,
                       search_term, is_sold_by_weight, unit_price
                FROM recipe_items
                WHERE recipe_id = %s
                ON CONFLICT (user_id, product_name) DO UPDATE SET
                    quantity = shopping_carts.quantity + EXCLUDED.quantity
            """, (user_id, recipe_id))
