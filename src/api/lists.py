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
