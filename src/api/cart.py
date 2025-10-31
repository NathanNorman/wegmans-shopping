from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from src.database import (
    get_user_cart,
    add_to_cart,
    update_cart_quantity,
    remove_from_cart,
    clear_cart,
    update_frequent_items,
    get_user_store
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
    sell_by_unit: str = "Each"  # Unit name for display (lb, oz, pkg, Each, etc.)

class UpdateQuantityRequest(BaseModel):
    cart_item_id: int
    quantity: float

@router.get("/cart")
async def get_cart(user: AuthUser = Depends(get_current_user_optional)):
    """Get user's shopping cart for their default store"""
    store_number = get_user_store(str(user.id))
    cart_items = get_user_cart(str(user.id), store_number)
    return {"cart": cart_items}

@router.post("/cart/add")
async def add_item(item: AddToCartRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Add item to cart for user's default store"""
    store_number = get_user_store(str(user.id))

    product = {
        'name': item.name,
        'price': item.price,
        'aisle': item.aisle,
        'image': item.image,
        'search_term': item.search_term,
        'is_sold_by_weight': item.is_sold_by_weight,
        'unit_price': item.unit_price,
        'sell_by_unit': item.sell_by_unit
    }

    add_to_cart(str(user.id), product, item.quantity, store_number)
    cart_items = get_user_cart(str(user.id), store_number)

    return {"success": True, "cart": cart_items}

@router.put("/cart/quantity")
async def update_quantity(update: UpdateQuantityRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Update item quantity in cart for user's default store"""
    store_number = get_user_store(str(user.id))
    update_cart_quantity(str(user.id), update.cart_item_id, update.quantity, store_number)
    cart_items = get_user_cart(str(user.id), store_number)

    return {"success": True, "cart": cart_items}

@router.delete("/cart/{cart_item_id}")
async def remove_item(cart_item_id: int, user: AuthUser = Depends(get_current_user_optional)):
    """Remove item from cart for user's default store"""
    store_number = get_user_store(str(user.id))
    remove_from_cart(str(user.id), cart_item_id, store_number)
    cart_items = get_user_cart(str(user.id), store_number)

    return {"success": True, "cart": cart_items}

@router.delete("/cart")
async def clear_user_cart(user: AuthUser = Depends(get_current_user_optional)):
    """Clear entire cart for user's default store"""
    store_number = get_user_store(str(user.id))
    clear_cart(str(user.id), store_number)

    return {"success": True, "cart": []}

@router.post("/cart/complete")
async def complete_shopping(user: AuthUser = Depends(get_current_user_optional)):
    """Mark shopping complete and update frequent items for user's default store"""
    store_number = get_user_store(str(user.id))
    update_frequent_items(str(user.id), store_number)
    clear_cart(str(user.id), store_number)

    return {"success": True, "message": "Shopping completed!"}

@router.post("/cart/update-frequent")
async def update_frequent(user: AuthUser = Depends(get_current_user_optional)):
    """Update frequent items from cart WITHOUT clearing cart for user's default store"""
    store_number = get_user_store(str(user.id))
    update_frequent_items(str(user.id), store_number)

    return {"success": True, "message": "Frequent items updated!"}
