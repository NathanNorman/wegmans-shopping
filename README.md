# Wegmans Shopping List Builder

Interactive web-based shopping list builder for Wegmans stores. Search products, get prices and aisle locations, and generate organized shopping lists.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Create shopping list from file
python3 shop.py shopping_list.txt

# Or start from scratch interactively
python3 shop.py

# Or paste from clipboard
pbpaste | python3 shop.py --stdin
```

Opens interactive web UI at **http://localhost:8080**

## Three Ways to Create Lists

### 1. From File (Recommended)

Create `my_list.txt`:
```
Milk
Eggs
Bread
2,Butter
```

Run: `python3 shop.py my_list.txt`

### 2. Interactive Entry

Run: `python3 shop.py`

Then type items:
```
1. Milk
2. 2,Eggs
3. Bread
```

### 3. From Clipboard/Pipe

```bash
pbpaste | python3 shop.py --stdin
echo -e "Milk\nEggs\nBread" | python3 shop.py --stdin
```

## How It Works

1. **Searches Wegmans** - Finds 10 product options per item (~5 seconds each)
2. **Interactive Selection** - Web UI shows product photos, prices, aisles
3. **Pick Products** - Click the correct product for each item
4. **Final List** - Single table organized by aisle with totals
5. **Edit & Export** - Change quantities, delete items, add more, copy markdown

## Features

- ✅ Product images and prices
- ✅ Physical aisle locations (Raleigh, NC store)
- ✅ Interactive re-search if wrong results
- ✅ Editable quantities in final list
- ✅ Add/remove items after completion
- ✅ Tax calculation (~4% average for NC)
- ✅ Export to markdown

## Architecture

**Scraping Method:** Playwright intercepts Algolia API responses (Wegmans' search backend). Products are loaded via JavaScript, not in initial HTML.

**Optimization:** Reuses single browser session and sets store location once per session (~30% faster).

## Current Status

### ✅ Completed
- Browser automation setup with Playwright
- Anti-bot detection bypass
- Rate limiting
- Screenshot and HTML debugging
- Flexible selector strategies

### ⚠️ In Progress
- Product data extraction - Products are rendered client-side and require:
  - Either: Longer wait times for JavaScript execution
  - Or: Direct API interception to capture Algolia requests

### 📋 Next Steps

1. **Option A: Intercept Network Requests**
   - Use Playwright's `page.route()` to capture Algolia API calls
   - Extract product data directly from API responses
   - This is the fastest and most reliable approach

2. **Option B: Wait for Full Render**
   - Increase wait time after page load
   - Use more specific selectors once products render
   - Parse rendered HTML for product data

3. **Option C: Direct Algolia API**
   - Reverse engineer Algolia API calls
   - Query Algolia directly (requires API keys from browser)
   - Bypass browser entirely for better performance

## API Findings

### Algolia Integration
```
Application ID: QGPPR19V8V
Domains:
  - QGPPR19V8V-dsn.algolia.net
  - insights.algolia.io
```

### Wegmans Endpoints
```
Search: https://www.wegmans.com/shop/search?query={query}
Categories: https://www.wegmans.com/shop/categories/{id}
```

## Data Model

Products should include:
```python
{
    'name': str,        # Product name
    'price': str,       # Price (e.g., "$4.99")
    'sku': str,         # Product SKU/ID
    'url': str,         # Product page URL
    'image_url': str,   # Product image
    'category': str,    # Product category/aisle
    'availability': str # In stock status
}
```

## Rate Limiting

Default: 2 seconds between requests
Configurable via `rate_limit` parameter

## Legal & Ethics

- Respect robots.txt
- Implement rate limiting
- Use for personal/research purposes only
- Check Wegmans Terms of Service before commercial use

## Troubleshooting

### Products not loading
- Increase wait time in `search_products()`
- Check debug_screenshot.png and debug_page.html
- Products may require longer JavaScript execution time

### Timeout errors
- Increase timeout parameter
- Check network connection
- Verify Wegmans site is accessible

## Contributing

To improve product extraction:
1. Run with `headless=False` to observe page behavior
2. Check browser console for errors
3. Inspect network tab for API calls
4. Update selectors in `_extract_product_data()`

## License

MIT License - See LICENSE file for details
