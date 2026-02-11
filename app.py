from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
import logging

from src.api import search, cart, lists, recipes, health, auth, images, favorites, store
from config.settings import settings
from contextlib import asynccontextmanager

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting Wegmans Shopping App")
    if settings.DATABASE_URL:
        try:
            from src.database import get_db
            with get_db() as cursor:
                cursor.execute("SELECT 1")
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            logger.warning("⚠️  App starting in degraded mode - database operations will fail")
    else:
        logger.warning("⚠️  DATABASE_URL not set - database operations will fail")

    yield

    # Shutdown (if needed)
    logger.info("👋 Shutting down Wegmans Shopping App")

# Initialize FastAPI with lifespan
app = FastAPI(
    title="Wegmans Shopping App",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None,
    lifespan=lifespan
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(cart.router, prefix="/api", tags=["cart"])
app.include_router(lists.router, prefix="/api", tags=["lists"])
app.include_router(recipes.router, prefix="/api", tags=["recipes"])
app.include_router(images.router, prefix="/api", tags=["images"])
app.include_router(favorites.router, prefix="/api", tags=["favorites"])
app.include_router(store.router, prefix="/api", tags=["store"])

# Serve static files (CSS/JS)
app.mount("/css", StaticFiles(directory="frontend/css"), name="css")
app.mount("/js", StaticFiles(directory="frontend/js"), name="js")

# Serve frontend at root
@app.get("/")
async def serve_frontend():
    return FileResponse("frontend/index.html")

# Serve password reset page
@app.get("/reset-password")
async def serve_reset_password():
    return FileResponse("frontend/reset-password.html")

# OLD session middleware removed - now using Supabase Auth with JWT tokens
# Anonymous users are created on-demand in src/auth.py::create_anonymous_user()

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
