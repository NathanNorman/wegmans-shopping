# Wegmans Scraper - Quick Start Guide

## ✅ Working Features

Your Wegmans scraper is fully functional and extracts:
- **Product Name** - e.g., "Coca-Cola Cola"
- **Aisle Location** - e.g., "10B" (physical store aisle)
- **Price** - e.g., "$8.99" (in-store price at Raleigh, NC)

## Usage

### Simple Search

```python
import asyncio
from wegmans_scraper import WegmansScraper

async def search_wegmans():
    async with WegmansScraper(headless=False, store_location="Raleigh") as scraper:
        # Search for any product
        products = await scraper.search_products("coke", max_results=20)

        # Display results
        for product in products:
            print(f"{product['name']} - {product['aisle']} - {product['price']}")

asyncio.run(search_wegmans())
```

### Run the Example

```bash
python3 wegmans_scraper.py
```

Example output:
```
Wegmans Raleigh, NC - Product Search Results
============================================================

Found 20 products for 'coke':

1. Coca-Cola Cola
   Aisle: 10B
   Price: $8.99

2. Diet Coke Diet Cola
   Aisle: 10B
   Price: $8.99
...
```

## Data Output

Products are saved to `raleigh_products.json`:

```json
[
  {
    "name": "Coca-Cola Cola",
    "aisle": "10B",
    "price": "$8.99"
  },
  {
    "name": "Diet Coke Cola",
    "aisle": "10B",
    "price": "$8.99"
  }
]
```

## How It Works

1. **Opens Browser** - Uses Playwright to automate Chrome
2. **Sets Store Location** - Targets Raleigh, NC Wegmans
3. **Intercepts API** - Captures Algolia search responses (their product database)
4. **Extracts Data** - Parses JSON to get name, aisle, price
5. **Saves Results** - Outputs to JSON file

## Customization

### Change Store Location

```python
# Try different Wegmans locations
scraper = WegmansScraper(store_location="Raleigh")
scraper = WegmansScraper(store_location="Rochester")
```

### Different Search Terms

```python
products = await scraper.search_products("milk", max_results=50)
products = await scraper.search_products("eggs", max_results=10)
products = await scraper.search_products("bread")  # No limit
```

### Headless Mode (Faster)

```python
# Run without visible browser (faster for automation)
async with WegmansScraper(headless=True) as scraper:
    products = await scraper.search_products("chicken")
```

### Rate Limiting

```python
# Slower rate limiting (more polite)
async with WegmansScraper(rate_limit=5.0) as scraper:
    products = await scraper.search_products("pizza")
```

## Debug Files

When running, the scraper creates:
- `raleigh_products.json` - Final product list
- `algolia_responses.json` - Raw API data (for debugging)
- `debug_screenshot.png` - Page screenshot (if issues occur)

## Tips

- First run may be slower due to browser startup
- Prices shown are **in-store** prices, not delivery prices
- Aisle locations are specific to the Raleigh store
- Some items show "See Store Associate" or "Front End Register Area" instead of aisle numbers

## Example Searches

```python
# Build a shopping list
searches = ["milk", "eggs", "bread", "chicken", "apples"]

for item in searches:
    products = await scraper.search_products(item, max_results=5)
    print(f"\n{item.upper()}:")
    for p in products:
        print(f"  {p['name']} - {p['aisle']} - {p['price']}")
```

## Notes

- This scraper is for **personal use only**
- Respects rate limiting (default 2 seconds between requests)
- Targets Raleigh, NC Wegmans by default
- Extracts in-store prices (not delivery prices)
- Uses Algolia API interception (faster than HTML parsing)

Enjoy your automated Wegmans price checking! 🛒
