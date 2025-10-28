"""
Direct Algolia API scraper - NO BROWSER NEEDED!
Queries Wegmans' Algolia search index directly via HTTP.
"""
import requests
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class AlgoliaDirectScraper:
    """Direct Algolia API scraper (no Playwright, instant results!)"""
    
    ALGOLIA_APP_ID = "QGPPR19V8V"
    ALGOLIA_API_KEY = "9a10b1401634e9a6e55161c3a60c200d"  # Public search-only key
    ALGOLIA_URL = "https://qgppr19v8v-dsn.algolia.net/1/indexes/*/queries"
    
    # Raleigh, NC store
    STORE_NUMBER = 86
    
    def search_products(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search Wegmans products via direct Algolia API call
        
        Args:
            query: Search term
            max_results: Maximum products to return
            
        Returns:
            List of product dictionaries with name, price, aisle, image
        """
        logger.info(f"🚀 Direct Algolia search for '{query}' at store {self.STORE_NUMBER}")
        
        # Build request payload
        payload = {
            "requests": [{
                "indexName": "products",
                "query": query,
                "hitsPerPage": max_results,
                "filters": f"storeNumber:{self.STORE_NUMBER} AND fulfilmentType:instore"
            }]
        }
        
        headers = {
            "x-algolia-api-key": self.ALGOLIA_API_KEY,
            "x-algolia-application-id": self.ALGOLIA_APP_ID,
            "Content-Type": "application/json"
        }
        
        try:
            response = requests.post(
                self.ALGOLIA_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            results = data.get('results', [])
            
            if not results:
                logger.warning("No results from Algolia")
                return []
            
            hits = results[0].get('hits', [])
            logger.info(f"✅ Got {len(hits)} hits from Algolia")
            
            # Extract product data
            products = []
            for hit in hits:
                try:
                    product = {
                        'name': hit.get('productName', ''),
                        'price': self._extract_price(hit),
                        'aisle': self._extract_aisle(hit),
                        'image': self._extract_image(hit),
                        'is_sold_by_weight': hit.get('isSoldByWeight', False),
                        'unit_price': hit.get('price_inStore', {}).get('unitPrice') if isinstance(hit.get('price_inStore'), dict) else None,
                        'sell_by_unit': hit.get('onlineSellByUnit', 'Each'),
                        'approx_weight': hit.get('onlineApproxUnitWeight', 1.0)
                    }
                    
                    if product['name']:
                        products.append(product)
                        
                except Exception as e:
                    logger.error(f"Error parsing product: {e}")
                    continue
            
            logger.info(f"🎯 Returning {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"❌ Algolia API call failed: {e}")
            raise
    
    def _extract_price(self, hit: Dict) -> str:
        """Extract price from hit"""
        if 'price_inStore' in hit and isinstance(hit['price_inStore'], dict):
            amount = hit['price_inStore'].get('amount')
            if amount:
                return f"${amount:.2f}"
        return "$0.00"
    
    def _extract_aisle(self, hit: Dict) -> str:
        """Extract aisle from hit"""
        if 'planogram' in hit and isinstance(hit['planogram'], dict):
            aisle = hit['planogram'].get('aisle')
            if aisle:
                return str(aisle)
        
        # Fallback to categories
        categories = hit.get('categories', [])
        if categories:
            return categories[0] if isinstance(categories[0], str) else "Unknown"
        
        return "Unknown"
    
    def _extract_image(self, hit: Dict) -> str:
        """Extract image URL from hit"""
        images = hit.get('images', [])
        if images and len(images) > 0:
            return images[0]
        return ""
