from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import List, Optional
from src.database import (
    get_user_recipes,
    create_recipe,
    save_cart_as_recipe,
    add_item_to_recipe,
    update_recipe_item_quantity,
    remove_item_from_recipe,
    update_recipe,
    delete_recipe,
    load_recipe_to_cart,
    get_user_cart
)

router = APIRouter()

class CreateRecipeRequest(BaseModel):
    name: str
    description: Optional[str] = None

class SaveCartAsRecipeRequest(BaseModel):
    name: str
    description: Optional[str] = None

class AddItemToRecipeRequest(BaseModel):
    name: str
    price: str
    quantity: float = 1
    aisle: Optional[str] = None
    image: Optional[str] = None
    search_term: Optional[str] = None
    is_sold_by_weight: bool = False
    unit_price: Optional[str] = None

class UpdateRecipeItemQuantityRequest(BaseModel):
    quantity: float

class UpdateRecipeRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class LoadRecipeRequest(BaseModel):
    item_ids: Optional[List[int]] = None

@router.get("/recipes")
async def get_recipes(request: Request):
    """Get all recipes for user"""
    user_id = request.state.user_id
    recipes = get_user_recipes(user_id)
    return {"recipes": recipes}

@router.post("/recipes/create")
async def create_new_recipe(recipe_req: CreateRecipeRequest, request: Request):
    """Create a new empty recipe"""
    user_id = request.state.user_id
    recipe_id = create_recipe(user_id, recipe_req.name, recipe_req.description)
    return {"success": True, "recipe_id": recipe_id}

@router.post("/recipes/save-cart")
async def save_cart_recipe(recipe_req: SaveCartAsRecipeRequest, request: Request):
    """Save current cart as a recipe"""
    user_id = request.state.user_id

    # Check cart isn't empty
    cart = get_user_cart(user_id)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    recipe_id = save_cart_as_recipe(user_id, recipe_req.name, recipe_req.description)

    return {"success": True, "recipe_id": recipe_id}

@router.post("/recipes/{recipe_id}/items")
async def add_item(recipe_id: int, item_req: AddItemToRecipeRequest, request: Request):
    """Add an item to a recipe"""
    user_id = request.state.user_id

    # Verify recipe belongs to user
    recipes = get_user_recipes(user_id)
    if not any(r['id'] == recipe_id for r in recipes):
        raise HTTPException(status_code=404, detail="Recipe not found")

    add_item_to_recipe(recipe_id, {
        'name': item_req.name,
        'price': item_req.price,
        'quantity': item_req.quantity,
        'aisle': item_req.aisle,
        'image': item_req.image,
        'search_term': item_req.search_term,
        'is_sold_by_weight': item_req.is_sold_by_weight,
        'unit_price': item_req.unit_price
    })

    return {"success": True}

@router.put("/recipes/items/{item_id}/quantity")
async def update_item_quantity(item_id: int, qty_req: UpdateRecipeItemQuantityRequest, request: Request):
    """Update item quantity in recipe"""
    update_recipe_item_quantity(item_id, qty_req.quantity)
    return {"success": True}

@router.delete("/recipes/items/{item_id}")
async def remove_item(item_id: int, request: Request):
    """Remove item from recipe"""
    remove_item_from_recipe(item_id)
    return {"success": True}

@router.put("/recipes/{recipe_id}")
async def update_recipe_metadata(recipe_id: int, update_req: UpdateRecipeRequest, request: Request):
    """Update recipe name or description"""
    user_id = request.state.user_id

    # Verify recipe belongs to user
    recipes = get_user_recipes(user_id)
    if not any(r['id'] == recipe_id for r in recipes):
        raise HTTPException(status_code=404, detail="Recipe not found")

    update_recipe(recipe_id, update_req.name, update_req.description)
    return {"success": True}

@router.delete("/recipes/{recipe_id}")
async def delete_recipe_endpoint(recipe_id: int, request: Request):
    """Delete a recipe"""
    user_id = request.state.user_id
    delete_recipe(user_id, recipe_id)
    return {"success": True}

@router.post("/recipes/{recipe_id}/add-to-cart")
async def load_recipe(recipe_id: int, load_req: LoadRecipeRequest, request: Request):
    """
    Load recipe items into cart

    If item_ids is provided, only those items are added.
    Otherwise, all items are added.
    """
    user_id = request.state.user_id

    try:
        load_recipe_to_cart(user_id, recipe_id, load_req.item_ids)
        cart = get_user_cart(user_id)
        return {"success": True, "cart": cart}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
