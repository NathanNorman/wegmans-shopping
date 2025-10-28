from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional
from src.database import (
    get_user_cart,
    add_to_cart,
    update_cart_quantity,
    remove_from_cart,
    clear_cart,
    update_frequent_items
)

router = APIRouter()

class AddToCartRequest(BaseModel):
    name: str
    price: str
    quantity: float = 1.0  # Supports decimals for weight
    aisle: Optional[str] = None
    image: Optional[str] = None
    search_term: Optional[str] = None
    is_sold_by_weight: bool = False
    unit_price: Optional[str] = None

class UpdateQuantityRequest(BaseModel):
    cart_item_id: int
    quantity: float

@router.get("/cart")
async def get_cart(request: Request):
    """Get user's shopping cart"""
    user_id = request.state.user_id
    cart_items = get_user_cart(user_id)
    return {"cart": cart_items}

@router.post("/cart/add")
async def add_item(item: AddToCartRequest, request: Request):
    """Add item to cart"""
    user_id = request.state.user_id
    
    product = {
        'name': item.name,
        'price': item.price,
        'aisle': item.aisle,
        'image': item.image,
        'search_term': item.search_term,
        'is_sold_by_weight': item.is_sold_by_weight,
        'unit_price': item.unit_price
    }
    
    add_to_cart(user_id, product, item.quantity)
    cart_items = get_user_cart(user_id)
    
    return {"success": True, "cart": cart_items}

@router.put("/cart/quantity")
async def update_quantity(update: UpdateQuantityRequest, request: Request):
    """Update item quantity in cart"""
    user_id = request.state.user_id
    update_cart_quantity(user_id, update.cart_item_id, update.quantity)
    cart_items = get_user_cart(user_id)
    
    return {"success": True, "cart": cart_items}

@router.delete("/cart/{cart_item_id}")
async def remove_item(cart_item_id: int, request: Request):
    """Remove item from cart"""
    user_id = request.state.user_id
    remove_from_cart(user_id, cart_item_id)
    cart_items = get_user_cart(user_id)
    
    return {"success": True, "cart": cart_items}

@router.delete("/cart")
async def clear_user_cart(request: Request):
    """Clear entire cart"""
    user_id = request.state.user_id
    clear_cart(user_id)
    
    return {"success": True, "cart": []}

@router.post("/cart/complete")
async def complete_shopping(request: Request):
    """Mark shopping complete and update frequent items"""
    user_id = request.state.user_id
    update_frequent_items(user_id)
    clear_cart(user_id)

    return {"success": True, "message": "Shopping completed!"}

@router.post("/cart/update-frequent")
async def update_frequent(request: Request):
    """Update frequent items from cart WITHOUT clearing cart"""
    user_id = request.state.user_id
    update_frequent_items(user_id)

    return {"success": True, "message": "Frequent items updated!"}
