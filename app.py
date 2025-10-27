from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from src.api import search, cart, lists, health
from config.settings import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Wegmans Shopping App",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None
)

# CORS (for development)
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(cart.router, prefix="/api", tags=["cart"])
app.include_router(lists.router, prefix="/api", tags=["lists"])

# Serve static files (CSS/JS)
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

# Serve frontend at root
@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

# Simple session middleware
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    # Get or create user session
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = "1"  # Default user (no auth for now)

    request.state.user_id = int(user_id)
    response = await call_next(request)

    # Set cookie if not present
    if not request.cookies.get("user_id"):
        response.set_cookie("user_id", user_id, max_age=31536000)  # 1 year

    return response

@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting Wegmans Shopping App")
    # Test database connection (only if DATABASE_URL is set)
    if settings.DATABASE_URL:
        try:
            from src.database import get_db
            with get_db() as cursor:
                cursor.execute("SELECT 1")
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            raise
    else:
        logger.warning("⚠️  DATABASE_URL not set - database operations will fail")

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
