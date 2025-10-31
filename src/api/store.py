from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from src.auth import get_current_user, AuthUser
from src.database import get_user_store, update_user_store, clear_all_user_data
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class UpdateStoreRequest(BaseModel):
    store_number: int

@router.get("/store")
async def get_current_store(user: AuthUser = Depends(get_current_user)):
    """Get user's current default store"""
    try:
        store_number = get_user_store(str(user.id))
        logger.info(f"User {user.id} current store: {store_number}")
        return {"store_number": store_number}
    except Exception as e:
        logger.error(f"Failed to get user store: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/store")
async def update_store(
    request: UpdateStoreRequest,
    user: AuthUser = Depends(get_current_user)
):
    """
    Update user's default store

    NOTE: Existing data remains at previous store.
    Switching stores will show that store's data.
    """
    try:
        old_store = get_user_store(str(user.id))
        update_user_store(str(user.id), request.store_number)

        logger.info(f"User {user.id} switched store: {old_store} → {request.store_number}")

        return {
            "success": True,
            "old_store": old_store,
            "new_store": request.store_number,
            "message": f"Switched to store {request.store_number}"
        }
    except Exception as e:
        logger.error(f"Failed to update user store: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store/switch-clear")
async def switch_store_clear_data(
    request: UpdateStoreRequest,
    user: AuthUser = Depends(get_current_user)
):
    """
    Switch store and clear all data for the NEW store (fresh start)

    WARNING: This deletes all cart/lists/favorites/recipes at the new store.
    Use the regular PUT /store if you want to preserve data.
    """
    try:
        old_store = get_user_store(str(user.id))

        # Clear data for NEW store (fresh start)
        clear_all_user_data(str(user.id), request.store_number)

        # Update user's default store
        update_user_store(str(user.id), request.store_number)

        logger.info(f"User {user.id} switched & cleared: {old_store} → {request.store_number}")

        return {
            "success": True,
            "old_store": old_store,
            "new_store": request.store_number,
            "data_cleared": True,
            "message": f"Switched to store {request.store_number} (fresh start)"
        }
    except Exception as e:
        logger.error(f"Failed to switch store and clear data: {e}")
        raise HTTPException(status_code=500, detail=str(e))
