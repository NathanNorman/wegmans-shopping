# Wegmans Shopping List Builder

Interactive web app for building Wegmans shopping lists with real-time product search, auto-save, and mobile-optimized printing. Targets Raleigh, NC store.

**Live Demo:** [wegmans-shopping.onrender.com](https://wegmans-shopping.onrender.com)

## Features

- 🔍 **Real-time product search** - Search Wegmans catalog with images, prices, and aisle locations
- 💾 **Auto-save** - Shopping lists automatically save as you shop (2-second debounce)
- 🏷️ **Custom tagging** - Tag your lists (e.g., "Thanksgiving Dinner") without creating duplicates
- 📱 **Mobile optimized** - Responsive design with touch-friendly interface
- 🖨️ **Smart printing** - One-page formatted lists organized by aisle
- ⭐ **Frequent items** - Quick-add from your purchase history
- 💰 **Tax calculation** - Estimates 4% NC sales tax

## Quick Start

### Prerequisites
```bash
# Python 3.10+
python3 --version

# Install dependencies
pip install -r requirements.txt

# Optional: Install python-dotenv if not included
pip install python-dotenv
```

### Environment Setup

Create `.env` file in project root:
```bash
# Database connection (URL-encoded password)
DATABASE_URL=postgresql://user:password@host:5432/database

# Optional settings
STORE_LOCATION=Raleigh
DEBUG=false
```

**Note:** DATABASE_URL password must be URL-encoded. Use `urllib.parse.quote_plus()` for special characters.

### Run Development Server

```bash
# Start server
python3 -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000** in your browser.

### Database Migrations

Migrations are in `migrations/` directory. Run manually:

```bash
python3 << 'EOF'
import psycopg2
from urllib.parse import quote_plus
# ... connect and execute migration SQL
EOF
```

See `migrations/` for schema setup.

## Architecture

### Stack
- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL (Supabase)
- **Frontend:** Vanilla JavaScript + CSS
- **Search:** Direct Algolia API (Application ID: QGPPR19V8V)
- **Deployment:** Render

### Key Design Decisions

**Auto-Save System** - Cart changes auto-save to date-based list after 2 seconds. Only one list per day, upserted on changes. Users can tag lists with custom names (e.g., "Thanksgiving") without creating duplicates.

**Custom List Tagging** - `saved_lists.custom_name` column stores optional tag. Display shows custom name prominently when set, date as subtitle. Filtering: Custom Lists = `WHERE custom_name IS NOT NULL`.

**Mobile Print** - Uses hidden `<div class="print-only">` with `@media print` CSS to show only formatted content. Device detection via `navigator.userAgent` (not `window.innerWidth`). Generates mobile-specific compact styles (8-9px fonts, 0.2in margins).

**Direct Algolia Search** - Bypasses browser automation by calling Algolia API directly. Cached for 7 days in PostgreSQL. ~1 second per search vs ~5-6 seconds with Playwright.

**Frequent Items** - Tracks items appearing in 2+ saved lists. Images fetched on-demand from Algolia if missing. Counts decrement when lists deleted.

### Database Schema

**Core Tables:**
- `users` - BIGINT id for UUID-based sessions
- `shopping_carts` - Current cart, supports decimal quantities for weight items
- `saved_lists` - Saved lists with `is_auto_saved`, `custom_name`, `last_updated`
- `saved_list_items` - List contents (no image_url)
- `frequent_items` - Items in 2+ lists with purchase_count
- `search_cache` - Algolia responses (7-day TTL)

**Key Pattern:** One list per day (date-based name), optionally tagged with custom_name. No duplicates.

## API Endpoints

### Cart
- `POST /api/cart/add` - Add item (decimal quantities supported)
- `GET /api/cart` - Get cart
- `PUT /api/cart/quantity` - Update quantity
- `DELETE /api/cart/{id}` - Remove item
- `DELETE /api/cart` - Clear cart

### Lists
- `POST /api/lists/auto-save` - Upsert today's list
- `POST /api/lists/tag` - Tag today's list with custom name
- `GET /api/lists/today` - Get today's list summary
- `GET /api/lists` - Get all lists
- `DELETE /api/lists/{id}` - Delete list (decrements frequent_items)

### Search
- `POST /api/search` - Search Wegmans products
- `GET /api/frequent` - Get frequently bought items

## Mobile Optimizations

- Viewport-relative cart height (70vh) shows 5-7 items
- Floating action bar at top (Print | Save | Lists | Clear)
- Ultra-compact print format (single page for 20-25 items)
- Touch-friendly button sizes (42-44px)
- User Agent detection for reliable mobile print styles

## Development Notes

### Environment Variables
- `.env` must be present (not auto-loaded by uvicorn)
- `config/settings.py` uses `python-dotenv` to load it
- DATABASE_URL requires URL-encoded password

### Print Implementation
**DO:** Use hidden div + `@media print` (current approach)
**DON'T:** Use iframe.print() (40% failure on iOS) or window.open() (leaves blank tabs)

### Mobile Detection
**For print styles:** Use `navigator.userAgent` (reliable)
**For CSS responsive:** Use `@media (max-width: 767px)` (standard)
**Never use:** `window.innerWidth` for print detection (affected by zoom/URL bars)

### User Sessions
- UUID-based IDs (12-digit from uuid.uuid4().int)
- Created ONCE on first visit (no cookie present)
- Stored in database users table (BIGINT id column)
- Cookie expires after 1 year

## Deployment (Render)

Auto-deploys from `main` branch. Requires:
- Environment variable: `DATABASE_URL` (Supabase connection string)
- Build command: `pip install -r requirements.txt`
- Start command: `python3 -m uvicorn app:app --host 0.0.0.0 --port $PORT`

## Project Structure

```
wegmans-shopping/
├── app.py                 # FastAPI app + session middleware
├── config/
│   └── settings.py        # Environment config (loads .env)
├── src/
│   ├── api/              # API routers (cart, lists, search, health)
│   ├── database.py       # Database functions (psycopg2)
│   ├── scraper/          # Algolia API client
│   └── models/           # Pydantic models
├── frontend/
│   ├── index.html        # Main UI
│   ├── js/main.js        # App logic (~1500 lines)
│   └── css/styles.css    # Responsive styles with mobile support
├── migrations/           # SQL migrations (run manually)
└── .env                  # Environment variables (not in git)
```

## Contributing

See `CLAUDE.md` for detailed architecture notes and development patterns.

## License

MIT License
