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
    max_results: int = 20  # Increased from 10 to 20
    offset: int = 0        # For pagination support
    store_number: int = 86 # Default: Raleigh, NC

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

    # Check cache first FOR THIS STORE (pagination from cache)
    cached = get_cached_search(search.search_term, search.store_number)
    if cached:
        logger.info(f"✅ Cache hit for '{search.search_term}' at store {search.store_number} (offset: {search.offset})")
        # Return paginated slice from cache
        start = search.offset
        end = start + search.max_results
        return {
            "products": cached[start:end],
            "from_cache": True,
            "total_in_cache": len(cached)
        }

    # Not in cache, query Algolia directly (NO BROWSER!)
    logger.info(f"⚡ Cache miss - Querying Algolia API for '{search.search_term}' at store {search.store_number}")

    try:
        # Always fetch more results to populate cache (100 products)
        products = scraper.search_products(
            search.search_term,
            max_results=100,  # Cache lots of results
            store_number=search.store_number
        )

        logger.info(f"✅ Search complete - Found {len(products)} products in ~1 second!")

        # Cache results in background FOR THIS STORE (all 100 products)
        background_tasks.add_task(cache_search_results, search.search_term, products, search.store_number)

        # Return requested page
        start = search.offset
        end = start + search.max_results
        return {
            "products": products[start:end],
            "from_cache": False,
            "total_found": len(products)
        }

    except Exception as e:
        logger.error(f"❌ Search failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/frequent")
async def get_frequent(user: AuthUser = Depends(get_current_user_optional)):
    """Get frequently purchased items for user's default store (user-specific)"""
    from src.database import get_frequent_items, get_user_store
    store_number = get_user_store(str(user.id))
    items = get_frequent_items(str(user.id), store_number, limit=20)
    return {"items": items}
