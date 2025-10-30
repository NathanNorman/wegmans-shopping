# Deprecated Code

This directory contains code that has been deprecated but preserved for reference.

## Files

### `wegmans_scraper.py`
**Deprecated**: January 30, 2025
**Replaced by**: `src/scraper/algolia_direct.py`

Old browser-based scraper using Playwright. Required launching a headless browser to intercept Algolia API calls from Wegmans.com. This was slow (~5-6 seconds per search) and resource-intensive.

**Why deprecated**:
- Slow performance (browser overhead)
- Heavy dependencies (Playwright, browser binaries)
- Maintenance burden (fragile DOM scraping)
- Unnecessary - direct Algolia API calls work fine

**New approach**: Direct HTTP calls to Algolia API (~1 second per search, no browser needed).

### `server.py`
**Deprecated**: January 30, 2025
**Replaced by**: `app.py` (FastAPI)

Old simple HTTP server for development. Used Python's built-in SimpleHTTPRequestHandler.

**Why deprecated**:
- Limited functionality (no proper routing)
- No middleware support
- No async support
- Manual JSON parsing
- Still imported old `wegmans_scraper.py`

**New approach**: FastAPI with proper routing, async support, automatic JSON parsing, and middleware.

---

## Should I delete these files?

**Not yet** - Keep for reference during transition period (1-2 months).

**Delete if**:
- No issues reported with new scraper after 2 months
- No need to reference old implementation
- Confident direct Algolia approach is stable

**Keep if**:
- Need to reference old scraping logic
- Algolia API changes require fallback
- Historical context needed for debugging

---

## How to restore (if needed)

```bash
# Move back to original location
mv deprecated/wegmans_scraper.py src/scraper/
mv deprecated/server.py .

# Reinstall dependencies
pip install playwright beautifulsoup4 lxml nest-asyncio

# Install Playwright browsers
playwright install chromium
```

Then update code to import old scraper instead of `algolia_direct.py`.
