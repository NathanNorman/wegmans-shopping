from fastapi import APIRouter, HTTPException, Depends
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
from src.auth import get_current_user_optional, AuthUser

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
async def get_cart(user: AuthUser = Depends(get_current_user_optional)):
    """Get user's shopping cart"""
    cart_items = get_user_cart(user.id)
    return {"cart": cart_items}

@router.post("/cart/add")
async def add_item(item: AddToCartRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Add item to cart"""
    product = {
        'name': item.name,
        'price': item.price,
        'aisle': item.aisle,
        'image': item.image,
        'search_term': item.search_term,
        'is_sold_by_weight': item.is_sold_by_weight,
        'unit_price': item.unit_price
    }

    add_to_cart(user.id, product, item.quantity)
    cart_items = get_user_cart(user.id)

    return {"success": True, "cart": cart_items}

@router.put("/cart/quantity")
async def update_quantity(update: UpdateQuantityRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Update item quantity in cart"""
    update_cart_quantity(user.id, update.cart_item_id, update.quantity)
    cart_items = get_user_cart(user.id)

    return {"success": True, "cart": cart_items}

@router.delete("/cart/{cart_item_id}")
async def remove_item(cart_item_id: int, user: AuthUser = Depends(get_current_user_optional)):
    """Remove item from cart"""
    remove_from_cart(user.id, cart_item_id)
    cart_items = get_user_cart(user.id)

    return {"success": True, "cart": cart_items}

@router.delete("/cart")
async def clear_user_cart(user: AuthUser = Depends(get_current_user_optional)):
    """Clear entire cart"""
    clear_cart(user.id)

    return {"success": True, "cart": []}

@router.post("/cart/complete")
async def complete_shopping(user: AuthUser = Depends(get_current_user_optional)):
    """Mark shopping complete and update frequent items"""
    update_frequent_items(user.id)
    clear_cart(user.id)

    return {"success": True, "message": "Shopping completed!"}

@router.post("/cart/update-frequent")
async def update_frequent(user: AuthUser = Depends(get_current_user_optional)):
    """Update frequent items from cart WITHOUT clearing cart"""
    update_frequent_items(user.id)

    return {"success": True, "message": "Frequent items updated!"}
