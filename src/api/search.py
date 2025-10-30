from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends, Request
from pydantic import BaseModel
from typing import List, Dict
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.scraper.algolia_direct import AlgoliaDirectScraper
from src.database import get_cached_search, cache_search_results
from src.auth import get_current_user_optional, AuthUser
from config.settings import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# Direct Algolia scraper (no browser needed!)
scraper = AlgoliaDirectScraper()

class SearchRequest(BaseModel):
    search_term: str
    max_results: int = 10

def rate_limit_decorator():
    """Conditionally apply rate limiting based on settings"""
    if settings.ENABLE_RATE_LIMITING:
        return limiter.limit("60/minute")
    else:
        # No-op decorator for tests
        def noop_decorator(func):
            return func
        return noop_decorator

@router.post("/search")
@rate_limit_decorator()
async def search_products(request: Request, search: SearchRequest, background_tasks: BackgroundTasks):
    """
    Search for products via direct Algolia API (with caching)

    Returns products from cache if available, otherwise queries Algolia directly
    """

    # Check cache first
    cached = get_cached_search(search.search_term)
    if cached:
        logger.info(f"✅ Cache hit for '{search.search_term}'")
        return {
            "products": cached[:search.max_results],
            "from_cache": True
        }

    # Not in cache, query Algolia directly (NO BROWSER!)
    logger.info(f"⚡ Cache miss - Querying Algolia API for '{search.search_term}'")

    try:
        products = scraper.search_products(
            search.search_term,
            max_results=search.max_results
        )

        logger.info(f"✅ Search complete - Found {len(products)} products in ~1 second!")

        # Cache results in background
        background_tasks.add_task(cache_search_results, search.search_term, products)

        return {
            "products": products,
            "from_cache": False
        }

    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/frequent")
async def get_frequent(user: AuthUser = Depends(get_current_user_optional)):
    """Get frequently purchased items (user-specific)"""
    from src.database import get_frequent_items
    items = get_frequent_items(user.id, limit=20)
    return {"items": items}
