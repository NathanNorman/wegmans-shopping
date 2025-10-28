from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict
from src.scraper.wegmans_scraper import WegmansScraper
from src.database import get_cached_search, cache_search_results
from config.settings import settings
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# NO persistent scraper - create on-demand and close after use
# This saves ~200-300MB RAM when idle (perfect for free tier!)

class SearchRequest(BaseModel):
    search_term: str
    max_results: int = 10

@router.post("/search")
async def search_products(search: SearchRequest, background_tasks: BackgroundTasks):
    """
    Search for products (with caching)

    Returns products from cache if available, otherwise scrapes Wegmans
    """

    # Check cache first
    cached = get_cached_search(search.search_term)
    if cached:
        logger.info(f"✅ Cache hit for '{search.search_term}'")
        return {
            "products": cached[:search.max_results],
            "from_cache": True
        }

    # Not in cache, scrape Wegmans
    logger.info(f"⚡ Cache miss - Starting scraper for '{search.search_term}'")

    # Create scraper on-demand (saves memory when idle)
    async with WegmansScraper(
        headless=settings.SCRAPER_HEADLESS,
        store_location=settings.STORE_LOCATION
    ) as scraper:
        try:
            products = await scraper.search_products(
                search.search_term,
                max_results=search.max_results
            )

            logger.info(f"✅ Scraping complete - Found {len(products)} products")

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
async def get_frequent():
    """Get frequently purchased items"""
    from src.database import get_frequent_items
    items = get_frequent_items(limit=20)
    return {"items": items}
