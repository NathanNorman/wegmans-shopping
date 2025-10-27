from fastapi import APIRouter
from datetime import datetime
from src.database import get_db

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    
    # Check database connectivity
    try:
        with get_db() as cursor:
            cursor.execute("SELECT 1")
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status,
        "service": "wegmans-shopping"
    }
