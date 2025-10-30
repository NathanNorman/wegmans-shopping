"""
Image fetching API - Background image loading for frequent items
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from src.auth import get_current_user_optional, AuthUser
from src.scraper.algolia_direct import AlgoliaDirectScraper
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


class ImageFetchRequest(BaseModel):
    product_names: List[str]  # List of product names to fetch images for


class ImageResult(BaseModel):
    product_name: str
    image_url: str | None
    success: bool


@router.post("/images/fetch")
async def fetch_images(
    request: ImageFetchRequest,
    user: AuthUser = Depends(get_current_user_optional)
) -> dict:
    """
    Fetch images for multiple products in parallel

    Returns:
        {
            "results": [
                {"product_name": "...", "image_url": "...", "success": true},
                ...
            ],
            "success_count": 5,
            "total_count": 8
        }
    """
    if not request.product_names:
        return {"results": [], "success_count": 0, "total_count": 0}

    if len(request.product_names) > 20:
        raise HTTPException(
            status_code=400,
            detail="Maximum 20 products per request"
        )

    scraper = AlgoliaDirectScraper()
    results = []
    success_count = 0

    for product_name in request.product_names:
        try:
            # Search for single product to get image
            products = scraper.search_products(product_name, max_results=1)

            if products and len(products) > 0:
                image_url = products[0].get('image')
                results.append({
                    "product_name": product_name,
                    "image_url": image_url,
                    "success": bool(image_url)
                })
                if image_url:
                    success_count += 1
            else:
                results.append({
                    "product_name": product_name,
                    "image_url": None,
                    "success": False
                })

        except Exception as e:
            logger.error(f"Failed to fetch image for '{product_name}': {e}")
            results.append({
                "product_name": product_name,
                "image_url": None,
                "success": False
            })

    return {
        "results": results,
        "success_count": success_count,
        "total_count": len(request.product_names)
    }
