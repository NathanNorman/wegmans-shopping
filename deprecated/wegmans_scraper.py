#!/usr/bin/env python3
"""
Wegmans Product Scraper

This scraper extracts product information from wegmans.com including:
- Product names
- Prices
- SKUs
- Categories/Aisles
- Availability
- Images
"""

import asyncio
import json
import time
from typing import List, Dict, Optional
from pathlib import Path
from playwright.async_api import async_playwright, Page, Browser
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WegmansScraper:
    """Scraper for wegmans.com product data"""

    BASE_URL = "https://www.wegmans.com"
    SEARCH_URL = f"{BASE_URL}/shop/search"

    def __init__(self, headless: bool = True, rate_limit: float = 2.0, store_location: str = "Raleigh"):
        """
        Initialize the scraper

        Args:
            headless: Run browser in headless mode
            rate_limit: Minimum seconds between requests
            store_location: Store location (default: "Raleigh" for Raleigh, NC)
        """
        self.headless = headless
        self.rate_limit = rate_limit
        self.store_location = store_location
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.last_request_time = 0
        self.store_location_set = False  # Track if we've set the store
        self.current_api_responses = []  # Store API responses for current search

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self):
        """Start the browser"""
        logger.info("Starting browser...")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',  # Required for Docker/containers
                '--disable-dev-shm-usage',  # Reduces memory usage
                '--disable-gpu'  # Not needed in headless mode
            ]
        )

        # Create a single page with realistic headers
        self.page = await self.browser.new_page()
        await self.page.set_extra_http_headers({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br'
        })

        logger.info("Browser started")

    async def close(self):
        """Close the browser"""
        if self.page:
            await self.page.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info("Browser closed")

    async def _rate_limit(self):
        """Enforce rate limiting"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit:
            await asyncio.sleep(self.rate_limit - elapsed)
        self.last_request_time = time.time()

    async def _set_store_location(self):
        """
        Set the store location by navigating to homepage and selecting store
        """
        try:
            logger.info(f"Setting store location to: {self.store_location}")

            # Navigate to homepage first
            await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)

            # Try to click store selector button
            try:
                # Look for store location button/selector
                store_button = await self.page.query_selector('button:has-text("Raleigh"), button:has-text("Store"), [class*="store"], [class*="location"]')
                if store_button:
                    await store_button.click()
                    await asyncio.sleep(1)

                    # Type Raleigh in search if there's an input
                    store_input = await self.page.query_selector('input[type="text"], input[placeholder*="store"], input[placeholder*="location"]')
                    if store_input:
                        await store_input.fill(self.store_location)
                        await asyncio.sleep(1)

                        # Try to click Raleigh option
                        raleigh_option = await self.page.query_selector('text=/Raleigh/')
                        if raleigh_option:
                            await raleigh_option.click()
                            await asyncio.sleep(1)
                            logger.info("Successfully set store to Raleigh")
                        else:
                            logger.warning("Could not find Raleigh option")
            except Exception as e:
                logger.warning(f"Could not set store location via UI: {e}")

        except Exception as e:
            logger.warning(f"Error setting store location: {e}")

    async def _set_store_location_fast(self):
        """
        Set store location via localStorage (instant, no UI interaction)
        Raleigh, NC store
        """
        try:
            logger.info(f"⚡ Setting store to Raleigh via localStorage (fast method)")

            # Navigate to homepage first to set domain context
            await self.page.goto(self.BASE_URL, wait_until="domcontentloaded", timeout=10000)

            # Set Raleigh store in localStorage
            # Store ID for Raleigh, NC: 86 (common ID across Wegmans)
            await self.page.evaluate("""
                () => {
                    localStorage.setItem('selectedStore', JSON.stringify({
                        id: '86',
                        name: 'Raleigh, NC',
                        address: '7900 Skyland Ridge Pkwy, Raleigh, NC 27617'
                    }));
                    localStorage.setItem('storeId', '86');
                    localStorage.setItem('storeName', 'Raleigh');
                }
            """)

            logger.info("✅ Store location set to Raleigh (store ID: 86)")

        except Exception as e:
            logger.warning(f"⚠️  Could not set store via localStorage: {e}")
            logger.info("Continuing anyway - Wegmans may still show regional products")

    async def search_products(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """
        Search for products by intercepting Algolia API responses

        Args:
            query: Search term
            max_results: Maximum number of results to return

        Returns:
            List of product dictionaries
        """
        logger.info(f"Searching for: {query}")
        await self._rate_limit()

        # Clear previous responses
        self.current_api_responses = []
        products = []

        # Intercept Algolia API requests (define once, reuse instance variable)
        async def handle_route(route, request):
            """Intercept, MODIFY, and capture API responses"""
            logger.debug(f"🌐 Intercepted request: {request.url[:100]}...")

            # Check if this is an Algolia search API call
            if 'algolia' in request.url.lower() and 'queries' in request.url.lower():
                logger.info(f"🎯 ALGOLIA API CALL INTERCEPTED: {request.url[:150]}")

                # MODIFY the request to inject Raleigh store (86)
                try:
                    request_body = request.post_data
                    if request_body:
                        request_data = json.loads(request_body)

                        # Inject store 86 into filters for each query
                        for req in request_data.get('requests', []):
                            old_filter = req.get('filters', '')

                            # Replace storeNumber:0 or storeNumber:X with storeNumber:86
                            if 'storeNumber:' in old_filter:
                                import re
                                new_filter = re.sub(r'storeNumber:\d+', 'storeNumber:86', old_filter)
                                req['filters'] = new_filter
                                logger.info(f"🔧 MODIFIED filter: {old_filter[:100]} → {new_filter[:100]}")
                            elif old_filter:
                                # Add store if not present
                                req['filters'] = f"storeNumber:86 AND {old_filter}"
                                logger.info(f"🔧 ADDED storeNumber:86 to filters")

                        # Send MODIFIED request
                        response = await route.fetch(
                            method=request.method,
                            headers=request.headers,
                            post_data=json.dumps(request_data)
                        )
                    else:
                        response = await route.fetch()
                except Exception as e:
                    logger.warning(f"⚠️  Could not modify request: {e}")
                    response = await route.fetch()

                # Log RESPONSE body (what Algolia sends back)
                try:
                    body = await response.body()
                    data = json.loads(body)
                    self.current_api_responses.append(data)

                    # Log summary of response
                    total_hits = sum(len(r.get('hits', [])) for r in data.get('results', []))
                    logger.info(f"📦 Captured Algolia RESPONSE with {len(data.get('results', []))} result sets, {total_hits} total hits")

                    # Log first result details if empty
                    if total_hits == 0 and data.get('results'):
                        first_result = data['results'][0] if data['results'] else {}
                        logger.warning(f"⚠️  EMPTY RESPONSE! First result keys: {list(first_result.keys())[:10]}")
                        if 'params' in first_result:
                            logger.info(f"   Query params were: {first_result.get('params', '')[:200]}")

                except Exception as e:
                    logger.warning(f"❌ Error parsing API response: {e}")
            else:
                logger.debug(f"  Skipping non-Algolia request")
                response = await route.fetch()

            await route.fulfill(response=response)

        # Enable request interception for Algolia (only if not already enabled)
        if not hasattr(self, '_route_enabled'):
            logger.info("🔌 Setting up Algolia API route interception: **/*algolia*/**")
            await self.page.route("**/*algolia*/**", handle_route)
            self._route_enabled = True
            logger.info("✅ Route interception enabled")
        else:
            logger.info("ℹ️  Route interception already enabled (reusing session)")

        # Set store location only once per session
        if not self.store_location_set:
            await self._set_store_location_fast()
            self.store_location_set = True

        # Navigate to search page
        search_url = f"{self.SEARCH_URL}?query={query}"
        logger.info(f"Navigating to: {search_url}")

        # Use domcontentloaded instead of networkidle (much faster)
        await self.page.goto(search_url, wait_until="domcontentloaded", timeout=30000)

        # Wait for Algolia API calls to complete (poll instead of fixed wait)
        # NOTE: In production (Render), Algolia calls take 30-70 seconds to arrive!
        # The calls with actual products (storeNumber:69) come last
        logger.info("⏳ Waiting for Algolia API responses (max 75 seconds)...")
        max_wait = 75  # Maximum 75 seconds (Render is VERY slow)
        check_interval = 0.5  # Check every 500ms
        elapsed = 0

        # Track when we get responses with actual product hits
        first_hit_response_time = None
        last_response_time = elapsed

        while elapsed < max_wait:
            # Check if we got responses with actual products
            has_products = False
            if len(self.current_api_responses) > 0:
                last_response_time = elapsed
                for resp in self.current_api_responses:
                    for result in resp.get('results', []):
                        if len(result.get('hits', [])) > 0:
                            has_products = True
                            if first_hit_response_time is None:
                                first_hit_response_time = elapsed
                                logger.info(f"⚡ Got first response WITH PRODUCTS after {elapsed:.1f}s! Will wait 5 more seconds...")
                            break

            # If we have products and it's been 5 seconds since first hit, stop
            if has_products and first_hit_response_time and elapsed >= (first_hit_response_time + 5.0):
                logger.info(f"✅ Captured {len(self.current_api_responses)} response(s) - stopping wait")
                break

            await asyncio.sleep(check_interval)
            elapsed += check_interval

        logger.info(f"⏱️  Wait complete. Captured {len(self.current_api_responses)} API response(s) in {elapsed:.1f}s")

        # Process captured API responses
        if self.current_api_responses:
            logger.info(f"✅ SUCCESS: Captured {len(self.current_api_responses)} Algolia API responses")

            # Save raw API responses for debugging
            with open("algolia_responses.json", "w") as f:
                json.dump(self.current_api_responses, f, indent=2)
            logger.info("Saved raw Algolia responses to algolia_responses.json")

            products = self._parse_algolia_responses(self.current_api_responses, max_results)
            logger.info(f"✅ Algolia parsing returned {len(products)} products")
        else:
            logger.warning("⚠️  NO ALGOLIA API RESPONSES CAPTURED - Falling back to HTML parsing")
            logger.info("This means Algolia API interception did not work")
            # Fallback to HTML parsing
            # await self.page.screenshot(path="debug_screenshot.png", full_page=True)  # Disabled for production
            # logger.info("Saved debug screenshot")
            products = await self._extract_products_from_page(self.page, max_results)
            logger.info(f"📄 HTML parsing returned {len(products)} products")

        logger.info(f"🎯 FINAL RESULT: Returning {len(products)} products to API")
        return products

    def _parse_algolia_responses(self, responses: List[Dict], max_results: Optional[int] = None) -> List[Dict]:
        """
        Parse Algolia API responses to extract product data

        Args:
            responses: List of Algolia API response dictionaries
            max_results: Maximum number of products to return

        Returns:
            List of product dictionaries
        """
        products = []
        logger.info(f"🔍 Parsing {len(responses)} Algolia response(s)")

        for idx, response in enumerate(responses):
            results = response.get('results', [])
            logger.info(f"  Response {idx+1}: Found {len(results)} result(s)")

            for result_idx, result in enumerate(results):
                hits = result.get('hits', [])
                logger.info(f"    Result {result_idx+1}: Found {len(hits)} hit(s) (products)")

                for hit_idx, hit in enumerate(hits):
                    try:
                        # Check if sold by weight
                        is_weight = hit.get('isSoldByWeight', False)

                        # Extract unit price if available
                        unit_price = None
                        if 'price_inStore' in hit and isinstance(hit['price_inStore'], dict):
                            unit_price = hit['price_inStore'].get('unitPrice')  # e.g., "$9.99/lb."

                        # Extract essential fields: name, aisle, price, image
                        product_name = hit.get('productName') or hit.get('name') or hit.get('title')
                        product_aisle = self._extract_aisle(hit)
                        product_price = self._extract_price(hit)
                        product_image = self._extract_image(hit)

                        # DEBUG: Log first hit details if name is missing
                        if hit_idx == 0 and not product_name:
                            logger.warning(f"⚠️  First hit has no name! Available keys: {list(hit.keys())[:20]}")
                            logger.warning(f"   productName={hit.get('productName')}, name={hit.get('name')}, title={hit.get('title')}")

                        product = {
                            'name': product_name,
                            'aisle': product_aisle,
                            'price': product_price,
                            'image': product_image,
                            # NEW: Weight-based fields
                            'is_sold_by_weight': is_weight,
                            'unit_price': unit_price,
                            'sell_by_unit': hit.get('onlineSellByUnit', 'Each'),
                            'approx_weight': hit.get('onlineApproxUnitWeight', 1.0)
                        }

                        # Only add if we got at least a name
                        if product['name']:
                            products.append(product)

                            # Check max results
                            if max_results and len(products) >= max_results:
                                logger.info(f"✅ Reached max_results ({max_results}), stopping parse")
                                return products
                        else:
                            if hit_idx < 3:  # Log first 3 failures only
                                logger.warning(f"⚠️  Skipping hit #{hit_idx+1} - no name found (name={product_name}, price={product_price}, aisle={product_aisle})")

                    except Exception as e:
                        logger.error(f"❌ Error parsing product hit #{hit_idx+1}: {e}")
                        logger.debug(f"Hit data: {hit}")

        return products

    def _extract_aisle(self, hit: Dict) -> Optional[str]:
        """Extract aisle/location from Algolia hit"""
        # Check planogram first (most specific)
        if 'planogram' in hit and isinstance(hit['planogram'], dict):
            aisle = hit['planogram'].get('aisle')
            if aisle:
                return str(aisle)

        # Fallback to category-based aisle fields
        aisle_fields = ['aisle', 'aisle_location', 'location']
        for field in aisle_fields:
            if field in hit and hit[field]:
                return str(hit[field])

        # Last resort: use main category
        if 'categories' in hit and isinstance(hit['categories'], dict):
            # Get the most specific category level
            for level in ['lvl2', 'lvl1', 'lvl0']:
                if level in hit['categories']:
                    cat = hit['categories'][level]
                    # Extract just the last part after '>'
                    if ' > ' in cat:
                        return cat.split(' > ')[-1]
                    return cat

        return "Unknown"

    def _extract_price(self, hit: Dict) -> Optional[str]:
        """Extract price from Algolia hit"""
        # Check for in-store price first (most relevant for Raleigh store)
        if 'price_inStore' in hit and isinstance(hit['price_inStore'], dict):
            amount = hit['price_inStore'].get('amount')
            if amount:
                return f"${amount:.2f}"

        # Check for delivery price as fallback
        if 'price_delivery' in hit and isinstance(hit['price_delivery'], dict):
            amount = hit['price_delivery'].get('amount')
            if amount:
                return f"${amount:.2f}"

        # Try other price fields
        price_fields = ['price', 'regular_price', 'list_price', 'regularPrice', 'salePrice']
        for field in price_fields:
            if field in hit and hit[field]:
                price = hit[field]
                # Format as currency if it's a number
                if isinstance(price, (int, float)):
                    return f"${price:.2f}"
                # Handle string prices
                price_str = str(price)
                if not price_str.startswith('$'):
                    return f"${price_str}"
                return price_str
        return "N/A"

    def _extract_image(self, hit: Dict) -> Optional[str]:
        """Extract product image URL from Algolia hit"""
        if 'images' in hit and isinstance(hit['images'], list) and len(hit['images']) > 0:
            return hit['images'][0]
        elif 'image' in hit:
            return hit['image']
        return None

    async def _extract_products_from_page(self, page: Page, max_results: Optional[int] = None) -> List[Dict]:
        """
        Extract product data from the current page

        Args:
            page: Playwright page object
            max_results: Maximum number of products to extract

        Returns:
            List of product dictionaries
        """
        products = []

        # Save debug info
        content = await page.content()
        with open("debug_page.html", "w") as f:
            f.write(content)
        logger.info("Saved page HTML to debug_page.html")
        # await page.screenshot(path="debug_screenshot.png", full_page=True)  # Disabled for production
        # logger.info("Saved debug screenshot to debug_screenshot.png")

        # Try multiple selector strategies
        selectors = [
            'li',  # Try all list items first
            '[data-testid="product-tile"]',
            '.product-tile',
            '[class*="ProductTile"]',
            '[class*="product"]',
            'article',
            'div[class*="item"]'
        ]

        product_elements = None
        used_selector = None
        for selector in selectors:
            product_elements = await page.query_selector_all(selector)
            if product_elements and len(product_elements) > 5:  # Need reasonable number
                used_selector = selector
                logger.info(f"Found {len(product_elements)} elements using selector: {selector}")
                break

        if not product_elements or len(product_elements) < 5:
            logger.warning(f"Could not find enough product elements (found {len(product_elements) if product_elements else 0})")
            logger.debug(f"Page content preview: {content[:1000]}")
            return []

        for i, element in enumerate(product_elements):
            if max_results and i >= max_results:
                break

            try:
                product = await self._extract_product_data(element)
                if product:
                    products.append(product)
            except Exception as e:
                logger.error(f"Error extracting product {i}: {e}")

        return products

    async def _extract_product_data(self, element) -> Optional[Dict]:
        """
        Extract data from a single product element

        Args:
            element: Playwright element handle

        Returns:
            Product dictionary or None
        """
        try:
            product = {}

            # Extract product name
            name_selectors = [
                '[data-testid="product-title"]',
                'h2',
                'h3',
                '[class*="title"]',
                '[class*="name"]'
            ]
            for selector in name_selectors:
                name_el = await element.query_selector(selector)
                if name_el:
                    product['name'] = (await name_el.text_content()).strip()
                    break

            # Extract price
            price_selectors = [
                '[data-testid="product-price"]',
                '[class*="price"]',
                '[class*="Price"]',
                'span[class*="dollar"]'
            ]
            for selector in price_selectors:
                price_el = await element.query_selector(selector)
                if price_el:
                    price_text = (await price_el.text_content()).strip()
                    product['price'] = price_text
                    break

            # Extract SKU/ID
            sku_selectors = [
                '[data-testid="product-sku"]',
                '[data-product-id]',
                '[data-sku]',
                '[data-id]'
            ]
            for selector in sku_selectors:
                if await element.get_attribute('data-product-id'):
                    product['sku'] = await element.get_attribute('data-product-id')
                    break
                elif await element.get_attribute('data-sku'):
                    product['sku'] = await element.get_attribute('data-sku')
                    break
                elif await element.get_attribute('data-id'):
                    product['sku'] = await element.get_attribute('data-id')
                    break

            # Extract image
            img_el = await element.query_selector('img')
            if img_el:
                product['image_url'] = await img_el.get_attribute('src')
                product['image_alt'] = await img_el.get_attribute('alt')

            # Extract link
            link_el = await element.query_selector('a')
            if link_el:
                href = await link_el.get_attribute('href')
                if href:
                    product['url'] = href if href.startswith('http') else f"{self.BASE_URL}{href}"

            # Only return if we got at least a name
            if product.get('name'):
                return product

        except Exception as e:
            logger.error(f"Error extracting product data: {e}")

        return None


def save_products(products: List[Dict], filename: str = "products.json"):
    """
    Save products to a JSON file

    Args:
        products: List of product dictionaries
        filename: Output filename
    """
    output_path = Path(filename)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(products, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(products)} products to {output_path}")


async def main():
    """Main function"""
    # Example usage - Search for Coke at Raleigh, NC Wegmans
    async with WegmansScraper(headless=False, store_location="Raleigh") as scraper:
        # Search for products
        products = await scraper.search_products("coke", max_results=20)

        # Print results
        print(f"\n{'='*60}")
        print(f"Wegmans Raleigh, NC - Product Search Results")
        print(f"{'='*60}")
        print(f"\nFound {len(products)} products for 'coke':\n")

        for i, product in enumerate(products, 1):
            print(f"{i}. {product.get('name', 'Unknown')}")
            print(f"   Aisle: {product.get('aisle', 'Unknown')}")
            print(f"   Price: {product.get('price', 'N/A')}")
            print()

        # Save to file
        if products:
            save_products(products, "raleigh_products.json")
            print(f"✓ Saved {len(products)} products to raleigh_products.json")


if __name__ == "__main__":
    asyncio.run(main())
