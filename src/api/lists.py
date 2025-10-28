from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.database import (
    get_user_lists,
    save_cart_as_list,
    load_list_to_cart,
    get_user_cart,
    get_db
)

router = APIRouter()

class SaveListRequest(BaseModel):
    name: str

@router.get("/lists")
async def get_lists(request: Request):
    """Get all saved lists for user"""
    user_id = request.state.user_id
    lists = get_user_lists(user_id)
    return {"lists": lists}

@router.post("/lists/save")
async def save_list(save_req: SaveListRequest, request: Request):
    """Save current cart as a list"""
    user_id = request.state.user_id
    
    # Check cart isn't empty
    cart = get_user_cart(user_id)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    list_id = save_cart_as_list(user_id, save_req.name)
    
    return {"success": True, "list_id": list_id}

@router.post("/lists/{list_id}/load")
async def load_list(list_id: int, request: Request):
    """Load a saved list into cart"""
    user_id = request.state.user_id
    
    try:
        load_list_to_cart(user_id, list_id)
        cart = get_user_cart(user_id)
        return {"success": True, "cart": cart}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.delete("/lists/{list_id}")
async def delete_list(list_id: int, request: Request):
    """Delete a saved list"""
    user_id = request.state.user_id

    with get_db() as cursor:
        # Verify list belongs to user
        cursor.execute("""
            SELECT id FROM saved_lists WHERE id = %s AND user_id = %s
        """, (list_id, user_id))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="List not found")

        # Delete list (cascade deletes items)
        cursor.execute("DELETE FROM saved_lists WHERE id = %s", (list_id,))

    return {"success": True}

@router.post("/lists/auto-save")
async def auto_save_list(save_req: SaveListRequest, request: Request):
    """
    Auto-save cart to date-based list (create or update today's list)

    If list with same name exists from today, update it.
    Otherwise create new list.
    """
    user_id = request.state.user_id
    list_name = save_req.name

    # Check cart isn't empty
    cart = get_user_cart(user_id)
    if not cart:
        return {"success": True, "message": "Cart is empty, nothing to save"}

    # Check if list with this name already exists from today
    with get_db() as cursor:
        cursor.execute("""
            SELECT id FROM saved_lists
            WHERE user_id = %s AND name = %s
            AND DATE(created_at) = CURRENT_DATE
        """, (user_id, list_name))

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
                WHERE user_id = %s
            """, (list_id, user_id))

            cursor.execute("""
                UPDATE saved_lists
                SET last_updated = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (list_id,))

            return {"success": True, "list_id": list_id, "updated": True}
        else:
            # Create new list
            list_id = save_cart_as_list(user_id, list_name)

            # Mark as auto-saved
            cursor.execute("""
                UPDATE saved_lists
                SET is_auto_saved = TRUE
                WHERE id = %s
            """, (list_id,))

            return {"success": True, "list_id": list_id, "updated": False}

@router.get("/lists/today")
async def get_todays_list(request: Request):
    """Get summary of today's auto-saved list"""
    user_id = request.state.user_id

    with get_db() as cursor:
        cursor.execute("""
            SELECT l.id, l.name, l.created_at,
                   COUNT(li.id) as item_count,
                   COALESCE(SUM(li.quantity), 0) as total_quantity,
                   COALESCE(SUM(li.price * li.quantity), 0) as total_price
            FROM saved_lists l
            LEFT JOIN saved_list_items li ON l.id = li.list_id
            WHERE l.user_id = %s
            AND l.is_auto_saved = TRUE
            AND DATE(l.created_at) = CURRENT_DATE
            GROUP BY l.id, l.name, l.created_at
        """, (user_id,))

        today = cursor.fetchone()

        if today:
            return {"exists": True, "list": dict(today)}
        else:
            return {"exists": False}
