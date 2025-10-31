from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.database import (
    get_user_lists,
    save_cart_as_list,
    load_list_to_cart,
    get_user_cart,
    get_user_store,
    get_db
)
from src.auth import get_current_user_optional, AuthUser

router = APIRouter()

class SaveListRequest(BaseModel):
    name: str

@router.get("/lists")
async def get_lists(user: AuthUser = Depends(get_current_user_optional)):
    """Get all saved lists for user at their default store"""
    store_number = get_user_store(str(user.id))
    lists = get_user_lists(str(user.id), store_number)
    return {"lists": lists}

@router.post("/lists/save")
async def save_list(save_req: SaveListRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Save current cart as a list for user's default store"""
    store_number = get_user_store(str(user.id))

    # Check cart isn't empty
    cart = get_user_cart(str(user.id), store_number)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    list_id = save_cart_as_list(str(user.id), save_req.name, store_number)

    return {"success": True, "list_id": list_id}

@router.post("/lists/{list_id}/load")
async def load_list(list_id: int, user: AuthUser = Depends(get_current_user_optional)):
    """Load a saved list into cart for user's default store"""
    store_number = get_user_store(str(user.id))

    try:
        # Get list name before loading
        with get_db() as cursor:
            cursor.execute("""
                SELECT name, store_number FROM saved_lists
                WHERE id = %s AND user_id = %s
            """, (list_id, str(user.id)))
            list_row = cursor.fetchone()

            if not list_row:
                raise ValueError("List not found")

            list_name = list_row['name']

        load_list_to_cart(str(user.id), list_id, store_number)
        cart = get_user_cart(str(user.id), store_number)
        return {"success": True, "cart": cart, "list_name": list_name}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/lists/{list_id}")
async def delete_list(list_id: int, user: AuthUser = Depends(get_current_user_optional)):
    """Delete a saved list and update frequent items counts for user's default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)

    with get_db() as cursor:
        # Verify list belongs to user AND store
        cursor.execute("""
            SELECT id, store_number FROM saved_lists
            WHERE id = %s AND user_id = %s
        """, (list_id, user_id))

        list_row = cursor.fetchone()
        if not list_row:
            raise HTTPException(status_code=404, detail="List not found")

        # Get items in this list before deleting
        cursor.execute("""
            SELECT DISTINCT product_name
            FROM saved_list_items
            WHERE list_id = %s
        """, (list_id,))
        products_in_list = [row['product_name'] for row in cursor.fetchall()]

        # Delete list (cascade deletes items)
        cursor.execute("DELETE FROM saved_lists WHERE id = %s", (list_id,))

        # Decrement frequent items counts FOR THIS STORE (or delete if count reaches 0)
        for product_name in products_in_list:
            cursor.execute("""
                UPDATE frequent_items
                SET purchase_count = purchase_count - 1
                WHERE user_id = %s AND store_number = %s AND product_name = %s
            """, (user_id, store_number, product_name))

            # Delete if count is now 0 or less
            cursor.execute("""
                DELETE FROM frequent_items
                WHERE user_id = %s AND store_number = %s AND product_name = %s
                  AND purchase_count <= 0
            """, (user_id, store_number, product_name))

    return {"success": True}

@router.post("/lists/auto-save")
async def auto_save_list(save_req: SaveListRequest, user: AuthUser = Depends(get_current_user_optional)):
    """
    Auto-save cart to date-based list for user's default store (create or update today's list)

    If list with same name exists from today, update it.
    Otherwise create new list.
    """
    user_id = str(user.id)
    store_number = get_user_store(user_id)
    list_name = save_req.name

    # Check cart isn't empty
    cart = get_user_cart(user_id, store_number)
    if not cart:
        return {"success": True, "message": "Cart is empty, nothing to save"}

    # Check if list with this name already exists from today FOR THIS STORE
    with get_db() as cursor:
        cursor.execute("""
            SELECT id FROM saved_lists
            WHERE user_id = %s AND store_number = %s AND name = %s
            AND DATE(created_at) = CURRENT_DATE
        """, (user_id, store_number, list_name))

        existing = cursor.fetchone()

        if existing:
            # Update existing list - delete old items, insert new ones
            list_id = existing['id']

            cursor.execute("DELETE FROM saved_list_items WHERE list_id = %s", (list_id,))

            cursor.execute("""
                INSERT INTO saved_list_items
                (list_id, product_name, price, quantity, aisle, is_sold_by_weight)
                SELECT %s, product_name, price, quantity, aisle, is_sold_by_weight
                FROM shopping_carts
                WHERE user_id = %s AND store_number = %s
            """, (list_id, user_id, store_number))

            # Note: last_updated column was removed in migration 009
            # No need to update timestamp - created_at is sufficient

            return {"success": True, "list_id": list_id, "updated": True}
        else:
            # Create new list
            list_id = save_cart_as_list(user_id, list_name, store_number)

            # Mark as auto-saved
            cursor.execute("""
                UPDATE saved_lists
                SET is_auto_saved = TRUE
                WHERE id = %s
            """, (list_id,))

            return {"success": True, "list_id": list_id, "updated": False}

@router.get("/lists/today")
async def get_todays_list(user: AuthUser = Depends(get_current_user_optional)):
    """Get summary of today's auto-saved list for user's default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)

    with get_db() as cursor:
        cursor.execute("""
            SELECT l.id, l.name, l.created_at,
                   COUNT(li.id) as item_count,
                   COALESCE(SUM(li.quantity), 0) as total_quantity,
                   COALESCE(SUM(li.price * li.quantity), 0) as total_price
            FROM saved_lists l
            LEFT JOIN saved_list_items li ON l.id = li.list_id
            WHERE l.user_id = %s
            AND l.store_number = %s
            AND l.is_auto_saved = TRUE
            AND DATE(l.created_at) = CURRENT_DATE
            GROUP BY l.id, l.name, l.created_at
        """, (user_id, store_number))

        today = cursor.fetchone()

        if today:
            return {"exists": True, "list": dict(today)}
        else:
            return {"exists": False}

# REMOVED: /lists/tag endpoint
# Custom lists now use /lists/save to create NEW lists (not tag existing)
# This allows multiple custom lists per day
