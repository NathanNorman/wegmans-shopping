from fastapi import APIRouter, HTTPException, Depends
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
    get_user_cart,
    get_user_store
)
from src.auth import get_current_user_optional, AuthUser
from src.parsers.recipe_parser import parse_recipe_text
from src.scraper.algolia_direct import AlgoliaDirectScraper
import logging

logger = logging.getLogger(__name__)

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
    sell_by_unit: str = "Each"  # Unit name for display (lb, oz, pkg, Each, etc.)

class UpdateRecipeItemQuantityRequest(BaseModel):
    quantity: float

class UpdateRecipeRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class LoadRecipeRequest(BaseModel):
    item_ids: Optional[List[int]] = None

class ParseRecipeRequest(BaseModel):
    text: str

class ImportSearchRequest(BaseModel):
    ingredients: List[str]  # List of ingredient names
    max_results_per_item: int = 3
    store_number: int = 86  # Store number from UI (default: Raleigh)

@router.get("/recipes")
async def get_recipes(user: AuthUser = Depends(get_current_user_optional)):
    """Get all recipes for user at their default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)
    recipes = get_user_recipes(user_id, store_number)
    return {"recipes": recipes}

@router.get("/recipes/{recipe_id}/items")
async def get_recipe_items(recipe_id: int, user: AuthUser = Depends(get_current_user_optional)):
    """Get items for a specific recipe"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)

    # Get recipe and verify ownership
    recipes = get_user_recipes(user_id, store_number)
    recipe = next((r for r in recipes if r['id'] == recipe_id), None)

    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")

    return {"success": True, "items": recipe['items'], "recipe": {"id": recipe['id'], "name": recipe['name']}}

@router.post("/recipes/create")
async def create_new_recipe(recipe_req: CreateRecipeRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Create a new empty recipe for user's default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)
    recipe_id = create_recipe(user_id, recipe_req.name, store_number, recipe_req.description)
    return {"success": True, "recipe_id": recipe_id}

@router.post("/recipes/save-cart")
async def save_cart_recipe(recipe_req: SaveCartAsRecipeRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Save current cart as a recipe for user's default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)

    # Check cart isn't empty
    cart = get_user_cart(user_id, store_number)
    if not cart:
        raise HTTPException(status_code=400, detail="Cart is empty")

    recipe_id = save_cart_as_recipe(user_id, recipe_req.name, store_number, recipe_req.description)

    return {"success": True, "recipe_id": recipe_id}

@router.post("/recipes/{recipe_id}/items")
async def add_item(recipe_id: int, item_req: AddItemToRecipeRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Add an item to a recipe for user's default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)

    # Verify recipe belongs to user at this store
    recipes = get_user_recipes(user_id, store_number)
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
        'unit_price': item_req.unit_price,
        'sell_by_unit': item_req.sell_by_unit
    })

    return {"success": True}

@router.put("/recipes/items/{item_id}/quantity")
async def update_item_quantity(item_id: int, qty_req: UpdateRecipeItemQuantityRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Update item quantity in recipe"""
    update_recipe_item_quantity(item_id, qty_req.quantity)
    return {"success": True}

@router.delete("/recipes/items/{item_id}")
async def remove_item(item_id: int, user: AuthUser = Depends(get_current_user_optional)):
    """Remove item from recipe"""
    remove_item_from_recipe(item_id)
    return {"success": True}

@router.put("/recipes/{recipe_id}")
async def update_recipe_metadata(recipe_id: int, update_req: UpdateRecipeRequest, user: AuthUser = Depends(get_current_user_optional)):
    """Update recipe name or description for user's default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)

    # Verify recipe belongs to user at this store
    recipes = get_user_recipes(user_id, store_number)
    if not any(r['id'] == recipe_id for r in recipes):
        raise HTTPException(status_code=404, detail="Recipe not found")

    update_recipe(recipe_id, update_req.name, update_req.description)
    return {"success": True}

@router.delete("/recipes/{recipe_id}")
async def delete_recipe_endpoint(recipe_id: int, user: AuthUser = Depends(get_current_user_optional)):
    """Delete a recipe from user's default store"""
    user_id = str(user.id)
    store_number = get_user_store(user_id)
    delete_recipe(user_id, recipe_id, store_number)
    return {"success": True}

@router.post("/recipes/parse")
async def parse_recipe(
    request: ParseRecipeRequest,
    user: AuthUser = Depends(get_current_user_optional)
):
    """
    Parse recipe text into structured ingredient list

    Request: { "text": "raw recipe text..." }
    Response: {
        "success": True,
        "ingredients": [
            {
                "original": "2 tablespoons olive oil",
                "name": "olive oil",
                "optional": false,
                "confidence": "high"
            },
            ...
        ],
        "count": 15
    }
    """
    try:
        ingredients = parse_recipe_text(request.text)

        logger.info(f"Parsed {len(ingredients)} ingredients from recipe text")

        return {
            "success": True,
            "ingredients": ingredients,
            "count": len(ingredients)
        }
    except Exception as e:
        logger.error(f"Recipe parse error: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to parse recipe: {str(e)}")


@router.post("/recipes/import-search")
async def import_search(
    request: ImportSearchRequest,
    user: AuthUser = Depends(get_current_user_optional)
):
    """
    Search Wegmans for multiple ingredients (batch search for import)

    Request: {
        "ingredients": ["olive oil", "chicken breasts", "onion"],
        "max_results_per_item": 3,
        "store_number": 86
    }

    Response: {
        "success": True,
        "results": [
            {
                "ingredient": "olive oil",
                "matches": [
                    {"name": "Italian Olive Oil", "price": "$8.99", ...},
                    {"name": "Spanish Olive Oil", "price": "$6.99", ...},
                    {"name": "Organic Olive Oil", "price": "$12.99", ...}
                ],
                "match_count": 3
            },
            ...
        ],
        "total_ingredients": 3
    }
    """
    # Use store_number from request (respects UI selection)
    store_number = request.store_number
    scraper = AlgoliaDirectScraper()
    results = []

    for ingredient_name in request.ingredients:
        try:
            # Use Algolia scraper directly
            logger.info(f"Searching for ingredient: {ingredient_name} at store {store_number}")
            products = scraper.search_products(
                query=ingredient_name,
                max_results=request.max_results_per_item,
                store_number=store_number
            )

            results.append({
                "ingredient": ingredient_name,
                "matches": products[:request.max_results_per_item],
                "match_count": len(products)
            })

            logger.info(f"Found {len(products)} matches for '{ingredient_name}'")

        except Exception as e:
            logger.warning(f"Search failed for '{ingredient_name}': {e}")
            results.append({
                "ingredient": ingredient_name,
                "matches": [],
                "match_count": 0,
                "error": str(e)
            })

    return {
        "success": True,
        "results": results,
        "total_ingredients": len(request.ingredients)
    }


@router.post("/recipes/{recipe_id}/add-to-cart")
async def load_recipe(recipe_id: int, load_req: LoadRecipeRequest, user: AuthUser = Depends(get_current_user_optional)):
    """
    Load recipe items into cart for user's default store

    If item_ids is provided, only those items are added.
    Otherwise, all items are added.
    """
    user_id = str(user.id)
    store_number = get_user_store(user_id)

    try:
        load_recipe_to_cart(user_id, recipe_id, store_number, load_req.item_ids)
        cart = get_user_cart(user_id, store_number)
        return {"success": True, "cart": cart}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
