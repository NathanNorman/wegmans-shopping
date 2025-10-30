# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Interactive Wegmans shopping list builder with real-time product search, auto-save, and mobile-optimized printing. Uses PostgreSQL (Supabase), FastAPI backend, and vanilla JavaScript frontend. Scrapes Wegmans.com via direct Algolia API calls (no browser automation needed for production).

## Key Architecture

### Modern Stack (Post-Redesign)
- **Backend:** FastAPI (Python 3.10+) with separate API routers
- **Database:** PostgreSQL via Supabase (connection string in .env, URL-encoded)
- **Frontend:** Vanilla JS + CSS (no framework), mobile-first responsive design
- **Search:** Direct Algolia API calls (src/scraper/algolia_direct.py) - ~1 second per search
- **Deployment:** Render (auto-deploys from main branch)

### Data Flow
1. User searches → `/api/search` → Algolia API (with 7-day cache)
2. Add to cart → `/api/cart/add` → PostgreSQL `shopping_carts` table
3. Auto-save (2sec debounce) → `/api/lists/auto-save` → Updates today's list
4. Print → Hidden div with `@media print` CSS → `window.print()`

### Critical Implementation Details

**Auto-Save System** - Cart changes trigger 2-second debounced auto-save to date-based list (e.g., "Wednesday, October 29, 2025"). Only ONE list per day, upserted on each change. Users can optionally tag with custom name (e.g., "Thanksgiving") via `custom_name` column.

**Custom List Tagging** - "Save Custom List" doesn't create duplicate - it adds `custom_name` tag to today's auto-saved list. Display shows custom name prominently with date as subtitle. Filter by `WHERE custom_name IS NOT NULL` for "Custom Lists" section.

**Mobile Print** - Uses hidden div (`.print-only`) + `@media print` to show only formatted content. Detects mobile via `navigator.userAgent` (not `window.innerWidth`), generates ultra-compact styles (8-9px fonts, 0.2in margins). Avoids iframe/window.open for reliability.

**User Sessions** - UUID-based user IDs (12-digit from uuid.uuid4().int). BIGINT columns for user_id to support large IDs. User created ONCE on first visit (no cookie), stored in cookie for 1 year.

**Frequent Items** - Rebuilt from `saved_list_items` when lists are saved/printed. Shows items appearing in 2+ lists. Images fetched on-demand if missing. Count decrements when lists deleted.

## Common Commands

### Development Server
```bash
# Load .env and start server
python3 -m uvicorn app:app --reload --host 127.0.0.1 --port 8000

# Or for deployment (Render uses this)
python3 -m uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Database Migrations
```bash
# Run migration manually
python3 << 'EOF'
import subprocess, psycopg2
from urllib.parse import quote_plus

whoami = subprocess.run(['whoami'], capture_output=True, text=True).stdout.strip()
password = subprocess.run(['security', 'find-generic-password', '-a', whoami, '-s', 'supabase-wegmans-password', '-w'], capture_output=True, text=True).stdout.strip()
conn_str = f"postgresql://postgres.pisakkjmyeobvcgxbmhk:{quote_plus(password)}@aws-1-us-east-2.pooler.supabase.com:5432/postgres"

with open('migrations/004_custom_list_tags.sql', 'r') as f:
    conn = psycopg2.connect(conn_str)
    cursor = conn.cursor()
    cursor.execute(f.read())
    conn.commit()
EOF
```

### Clear User Data
```bash
# Reset database to fresh state (useful for testing)
# See src/database.py for helper functions
```

## Database Schema

### Key Tables
- **users** - id (BIGINT), username
- **shopping_carts** - Current cart items per user, supports decimal quantities for weight-based items
- **saved_lists** - Saved shopping lists with columns:
  - `is_auto_saved` (BOOLEAN) - TRUE for date-based auto-saves, FALSE for legacy
  - `custom_name` (TEXT) - Optional tag for custom naming (e.g., "Thanksgiving")
  - `last_updated` (TIMESTAMP) - Track when list was modified
- **saved_list_items** - Items in saved lists (no image_url column)
- **frequent_items** - Items appearing in 2+ lists, purchase_count tracks list occurrences
- **search_cache** - Algolia responses cached for 7 days

### Custom List Tagging Model
**One list per day, optionally tagged:**
- Auto-save creates: `name="Wednesday, October 29, 2025"`, `is_auto_saved=TRUE`, `custom_name=NULL`
- User tags it: `custom_name="Thanksgiving"` (same list, just tagged)
- Display logic: Show `custom_name` if set, else show `name`
- NO duplicate lists for same day - tagging is additive

## API Endpoints

### Cart Operations
- `GET /api/cart` - Get user's cart
- `POST /api/cart/add` - Add item (supports decimal qty for weight items)
- `PUT /api/cart/quantity` - Update item quantity
- `DELETE /api/cart/{id}` - Remove item
- `DELETE /api/cart` - Clear entire cart
- `POST /api/cart/update-frequent` - Update frequent items without clearing

### List Operations
- `GET /api/lists` - Get all lists (includes custom_name, is_auto_saved)
- `POST /api/lists/auto-save` - Upsert today's date-based list
- `POST /api/lists/tag` - Tag today's list with custom_name
- `GET /api/lists/today` - Get today's list summary
- `POST /api/lists/{id}/load` - Load list to cart
- `DELETE /api/lists/{id}` - Delete list (decrements frequent_items counts)

### Search
- `POST /api/search` - Search Wegmans (body: `{search_term: str, max_results: int}`)
- `GET /api/frequent` - Get frequently bought items

## Important Patterns

### Environment Setup
- `.env` file MUST have URL-encoded DATABASE_URL (use `urllib.parse.quote_plus()` for password)
- `python-dotenv` loaded in `config/settings.py` (not uvicorn automatic)
- Supabase password stored in macOS Keychain: `security find-generic-password -a $(whoami) -s 'supabase-wegmans-password' -w`

### Mobile vs Desktop Detection
- **For print styles:** Use `navigator.userAgent` detection (reliable), NOT `window.innerWidth` (affected by zoom/bars)
- **For CSS:** Use `@media (max-width: 767px)` as usual
- Mobile print requires `@media print` with device-specific styles injected dynamically

### Print Implementation (Hidden Div Approach)
```javascript
// Industry standard - no iframes, no new windows
1. Generate { html, styles } = generatePrintableList()
2. Create hidden div with class="print-only"
3. Inject styles into <head> with @media print rules
4. Call window.print() on main page
5. CSS hides everything except .print-only during print
```

### Debugging Print Issues
- Never use `@media print and (max-width: 767px)` - mobile browsers ignore nested queries
- Use JavaScript device detection, generate inline styles
- Hidden div + @media print is most reliable cross-browser approach
- Test with actual Print Preview on mobile device, not desktop DevTools

## Testing

**Test Suite:** 193 tests with 94% code coverage

**Run tests:**
```bash
pytest --cov=src --cov-report=html
```

**Test files:**
- `tests/test_api.py` - API endpoints (lists, recipes, cart, search, images)
- `tests/test_database.py` - Database operations
- `tests/test_auth.py` - Auth integration tests
- `tests/test_auth_module.py` - Auth module unit tests
- `tests/test_api_auth.py` - Auth API endpoints

**Important:** Tests run with `ENABLE_RATE_LIMITING=false` to avoid test interference.

## Database Rebuild Warning

**CRITICAL:** When rebuilding the database (DROP TABLE users CASCADE), remember:

- `public.users` (our app) gets dropped ✅
- `auth.users` (Supabase Auth) is NOT affected ❌
- Users can still authenticate (JWT from auth.users)
- But operations fail (foreign keys to missing public.users records)

**Fix after rebuild:**
```python
# Re-insert authenticated users into public.users
INSERT INTO users (id, email, is_anonymous, created_at)
SELECT id, email, FALSE, created_at
FROM auth.users
WHERE email IS NOT NULL
ON CONFLICT (id) DO NOTHING;
```

Or manually insert specific users as needed.

## Render CLI Usage

**Service ID**: `srv-d3vt00h5pdvs7390bh10`
**Service Name**: `wegmans-shopping`
**URL**: https://wegmans-shopping.onrender.com

### Common Commands

**IMPORTANT**: Render CLI requires `-o` flag for non-interactive mode in Claude Code.

**List services:**
```bash
render services list -o json
```

**Get service logs (last 100 lines):**
```bash
render logs -o text --resources srv-d3vt00h5pdvs7390bh10 --limit 100
```

**Get recent logs (tail):**
```bash
render logs -o text --resources srv-d3vt00h5pdvs7390bh10 --limit 50 | tail -30
```

**Filter logs by text:**
```bash
render logs -o text --resources srv-d3vt00h5pdvs7390bh10 --text "ERROR" --limit 100
```

**Check deployment status:**
```bash
render services list -o json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data:
    if item['service']['name'] == 'wegmans-shopping':
        print(f\"Updated: {item['service']['updatedAt']}\")
        print(f\"Status: {item['service']['suspended']}\")
"
```

### Troubleshooting

**If logs command fails with TTY error:**
- Always use `-o text` or `-o json` flag
- Always use `--resources` flag with service ID

**If build fails:**
```bash
# Get build logs
render logs -o text --resources srv-d3vt00h5pdvs7390bh10 --limit 200 | grep -A 10 "ERROR"
```

**Common build issues:**
- Dockerfile referencing removed dependencies (e.g., Playwright)
- Missing dependencies in requirements.txt
- Environment variables not set in Render dashboard

### Deployment Process

1. **Push to GitHub**: `git push origin main`
2. **Render auto-detects** push and starts build
3. **Build takes** ~2-3 minutes (faster without Playwright)
4. **Check logs**: `render logs -o text --resources srv-d3vt00h5pdvs7390bh10 --limit 50`
5. **Verify**: `curl https://wegmans-shopping.onrender.com/api/health`

### Quick Health Check

```bash
# Check if production is responding
curl -s https://wegmans-shopping.onrender.com/api/health | python3 -m json.tool
```
