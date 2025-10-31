from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict
from src.auth import get_current_user, AuthUser
from src.database import add_favorite, remove_favorite, get_favorites, check_if_favorited
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class AddFavoriteRequest(BaseModel):
    product_name: str
    price: str
    aisle: str
    image_url: str = ""
    is_sold_by_weight: bool = False

@router.post("/favorites/add")
async def add_favorite_item(
    request: AddFavoriteRequest,
    user: AuthUser = Depends(get_current_user)
):
    """
    Manually add item to favorites

    Sets is_manual=TRUE and purchase_count=999 to ensure it appears in frequent items
    """
    try:
        logger.info(f"Adding favorite '{request.product_name}' for user {user.id}")

        add_favorite(
            user_id=str(user.id),
            product_name=request.product_name,
            price=request.price,
            aisle=request.aisle,
            image_url=request.image_url,
            is_sold_by_weight=request.is_sold_by_weight
        )

        return {
            "success": True,
            "message": f"Added '{request.product_name}' to favorites"
        }
    except Exception as e:
        logger.error(f"Failed to add favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/favorites/{product_name}")
async def remove_favorite_item(
    product_name: str,
    user: AuthUser = Depends(get_current_user)
):
    """
    Remove item from favorites

    Sets is_manual=FALSE. If item is not auto-frequent (count < 2), deletes it entirely.
    """
    try:
        logger.info(f"Removing favorite '{product_name}' for user {user.id}")

        remove_favorite(str(user.id), product_name)

        return {
            "success": True,
            "message": f"Removed '{product_name}' from favorites"
        }
    except Exception as e:
        logger.error(f"Failed to remove favorite: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/favorites")
async def get_user_favorites(user: AuthUser = Depends(get_current_user)):
    """
    Get all manually favorited items for the current user

    Returns items where is_manual=TRUE, sorted by most recently added
    """
    try:
        favorites = get_favorites(str(user.id))
        return {"favorites": favorites}
    except Exception as e:
        logger.error(f"Failed to get favorites: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/favorites/check/{product_name}")
async def check_favorite_status(
    product_name: str,
    user: AuthUser = Depends(get_current_user)
):
    """
    Check if a specific product is favorited by the user

    Used by frontend to show correct star icon state
    """
    try:
        is_favorited = check_if_favorited(str(user.id), product_name)
        return {
            "is_favorited": is_favorited,
            "product_name": product_name
        }
    except Exception as e:
        logger.error(f"Failed to check favorite status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
