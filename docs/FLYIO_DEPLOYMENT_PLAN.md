# Fly.io Deployment Plan with SQLite Database
## Production-Ready Architecture - $0/month

**Target:** 2-10 users on Fly.io free tier
**Database:** SQLite (better than JSON files!)
**Cost:** $0/month forever
**Effort:** 6-8 hours total

---

## Architecture Overview

```
┌──────────────────────────────────────────────┐
│         INTERNET (HTTPS Traffic)             │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│         FLY.IO GLOBAL PROXY                  │
│      (Automatic HTTPS, DDoS Protection)      │
└────────────────┬─────────────────────────────┘
                 │
                 ▼
┌──────────────────────────────────────────────┐
│      YOUR APP VM (256MB RAM - FREE)          │
│                                              │
│  ┌────────────────────────────────────┐     │
│  │  NGINX (Static Files)              │     │
│  │  /static/index.html, /static/css/  │     │
│  └────────────┬───────────────────────┘     │
│               │                              │
│  ┌────────────▼───────────────────────┐     │
│  │  FastAPI (Python 3.11)             │     │
│  │  - User sessions (server-side)     │     │
│  │  - API endpoints                   │     │
│  │  - Background scraper              │     │
│  └────────────┬───────────────────────┘     │
│               │                              │
│  ┌────────────▼───────────────────────┐     │
│  │  SQLite Database                   │     │
│  │  /data/wegmans.db (on volume)      │     │
│  │                                    │     │
│  │  Tables:                           │     │
│  │  - users (simple table)            │     │
│  │  - shopping_carts                  │     │
│  │  - saved_lists                     │     │
│  │  - frequent_items                  │     │
│  │  - search_cache                    │     │
│  └────────────────────────────────────┘     │
│                                              │
└──────────────────────────────────────────────┘
           ↕
   Fly Volume (1GB)
   Persistent storage
```

### Why SQLite Instead of JSON?

| Feature | JSON Files | SQLite |
|---------|-----------|---------|
| **Concurrent Access** | ❌ Race conditions | ✅ ACID transactions |
| **Data Integrity** | ❌ Can corrupt | ✅ Guaranteed consistency |
| **Queries** | ❌ Load entire file | ✅ Fast indexed queries |
| **Relationships** | ❌ Manual joins | ✅ Foreign keys |
| **Backups** | ⚠️ Copy each file | ✅ Single file backup |
| **Size** | ❌ Large JSON files | ✅ Compressed storage |
| **Cost on Fly.io** | ✅ FREE | ✅ FREE |

**Bottom line:** SQLite is a real database with zero extra cost.

---

## Database Schema

### Users Table (Simple - No Passwords Yet)
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

For now: User identified by session cookie, no login required.

### Shopping Carts Table
```sql
CREATE TABLE shopping_carts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    aisle TEXT,
    image_url TEXT,
    search_term TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Saved Lists Table
```sql
CREATE TABLE saved_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE saved_list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price REAL,
    quantity INTEGER NOT NULL,
    aisle TEXT,
    FOREIGN KEY (list_id) REFERENCES saved_lists(id) ON DELETE CASCADE
);
```

### Search Cache Table (Performance!)
```sql
CREATE TABLE search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term TEXT UNIQUE NOT NULL,
    results_json TEXT NOT NULL,  -- Store product array as JSON
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 0
);

-- Auto-expire cache after 7 days
CREATE INDEX idx_search_cache_date ON search_cache(cached_at);
```

### Frequent Items Table (Auto-populated)
```sql
CREATE TABLE frequent_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT UNIQUE NOT NULL,
    price REAL,
    aisle TEXT,
    image_url TEXT,
    purchase_count INTEGER DEFAULT 1,
    last_purchased TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## Project Structure (Fly.io Optimized)

```
wegmans-shopping/
├── app.py                      # FastAPI entry point
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Fly.io container
├── fly.toml                    # Fly.io configuration
├── .dockerignore
├── .gitignore
├── README.md
│
├── src/
│   ├── __init__.py
│   ├── config.py              # Settings (env vars)
│   ├── database.py            # SQLite connection & models
│   ├── models.py              # Pydantic models (API)
│   ├── scraper.py             # Wegmans scraper (existing)
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── search.py          # Search endpoints
│   │   ├── cart.py            # Cart endpoints
│   │   ├── lists.py           # Saved lists endpoints
│   │   └── health.py          # Health check
│   │
│   └── utils/
│       ├── __init__.py
│       ├── cache.py           # Search cache helpers
│       └── sessions.py        # Simple session management
│
├── static/
│   ├── index.html             # Your UI (shop_ui_final.html)
│   ├── css/
│   │   └── styles.css         # Extracted CSS
│   └── js/
│       └── app.js             # Extracted JS
│
├── migrations/
│   └── init.sql               # Initial database schema
│
└── tests/
    ├── test_api.py
    └── test_database.py
```

---

## Implementation Plan

### Phase 1: Database Setup (2 hours)

#### Step 1.1: Create Database Module (45 min)

**`src/database.py`:**
```python
import sqlite3
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
import json

DATABASE_PATH = Path(__file__).parent.parent / "data" / "wegmans.db"

def init_database():
    """Initialize database with schema"""
    DATABASE_PATH.parent.mkdir(exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dicts

    # Read schema
    schema_path = Path(__file__).parent.parent / "migrations" / "init.sql"
    with open(schema_path) as f:
        conn.executescript(f.read())

    conn.close()

@contextmanager
def get_db():
    """Context manager for database connections"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Cart operations
def get_user_cart(user_id: int) -> list:
    """Get all items in user's cart"""
    with get_db() as db:
        cursor = db.execute("""
            SELECT * FROM shopping_carts
            WHERE user_id = ?
            ORDER BY added_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def add_to_cart(user_id: int, product: dict, quantity: int = 1):
    """Add item to cart (or update quantity if exists)"""
    with get_db() as db:
        # Check if item already in cart
        cursor = db.execute("""
            SELECT id, quantity FROM shopping_carts
            WHERE user_id = ? AND product_name = ?
        """, (user_id, product['name']))

        existing = cursor.fetchone()
        if existing:
            # Update quantity
            new_qty = existing['quantity'] + quantity
            db.execute("""
                UPDATE shopping_carts
                SET quantity = ?
                WHERE id = ?
            """, (new_qty, existing['id']))
        else:
            # Insert new item
            db.execute("""
                INSERT INTO shopping_carts
                (user_id, product_name, price, quantity, aisle, image_url, search_term)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                product['name'],
                float(product['price'].replace('$', '')),
                quantity,
                product.get('aisle'),
                product.get('image'),
                product.get('search_term', '')
            ))

def update_cart_quantity(user_id: int, cart_item_id: int, quantity: int):
    """Update item quantity in cart"""
    with get_db() as db:
        db.execute("""
            UPDATE shopping_carts
            SET quantity = ?
            WHERE id = ? AND user_id = ?
        """, (quantity, cart_item_id, user_id))

def remove_from_cart(user_id: int, cart_item_id: int):
    """Remove item from cart"""
    with get_db() as db:
        db.execute("""
            DELETE FROM shopping_carts
            WHERE id = ? AND user_id = ?
        """, (cart_item_id, user_id))

def clear_cart(user_id: int):
    """Clear entire cart"""
    with get_db() as db:
        db.execute("DELETE FROM shopping_carts WHERE user_id = ?", (user_id,))

# Search cache operations
def get_cached_search(search_term: str) -> Optional[list]:
    """Get cached search results (if not expired)"""
    with get_db() as db:
        cursor = db.execute("""
            SELECT results_json, cached_at
            FROM search_cache
            WHERE search_term = ?
            AND datetime(cached_at, '+7 days') > datetime('now')
        """, (search_term.lower(),))

        row = cursor.fetchone()
        if row:
            # Increment hit count
            db.execute("""
                UPDATE search_cache
                SET hit_count = hit_count + 1
                WHERE search_term = ?
            """, (search_term.lower(),))

            return json.loads(row['results_json'])
        return None

def cache_search_results(search_term: str, results: list):
    """Cache search results"""
    with get_db() as db:
        db.execute("""
            INSERT OR REPLACE INTO search_cache (search_term, results_json, cached_at, hit_count)
            VALUES (?, ?, CURRENT_TIMESTAMP, COALESCE(
                (SELECT hit_count FROM search_cache WHERE search_term = ?),
                0
            ))
        """, (search_term.lower(), json.dumps(results), search_term.lower()))

# Saved lists operations
def get_user_lists(user_id: int) -> list:
    """Get all saved lists for user"""
    with get_db() as db:
        cursor = db.execute("""
            SELECT l.*, COUNT(li.id) as item_count
            FROM saved_lists l
            LEFT JOIN saved_list_items li ON l.id = li.list_id
            WHERE l.user_id = ?
            GROUP BY l.id
            ORDER BY l.created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]

def save_cart_as_list(user_id: int, list_name: str) -> int:
    """Save current cart as a list"""
    with get_db() as db:
        # Create list
        cursor = db.execute("""
            INSERT INTO saved_lists (user_id, name)
            VALUES (?, ?)
        """, (user_id, list_name))
        list_id = cursor.lastrowid

        # Copy cart items to list
        db.execute("""
            INSERT INTO saved_list_items (list_id, product_name, price, quantity, aisle)
            SELECT ?, product_name, price, quantity, aisle
            FROM shopping_carts
            WHERE user_id = ?
        """, (list_id, user_id))

        return list_id

def load_list_to_cart(user_id: int, list_id: int):
    """Load a saved list into cart"""
    with get_db() as db:
        # Verify list belongs to user
        cursor = db.execute("""
            SELECT id FROM saved_lists WHERE id = ? AND user_id = ?
        """, (list_id, user_id))
        if not cursor.fetchone():
            raise ValueError("List not found")

        # Clear current cart
        clear_cart(user_id)

        # Load list items into cart
        db.execute("""
            INSERT INTO shopping_carts
            (user_id, product_name, price, quantity, aisle, search_term)
            SELECT ?, product_name, price, quantity, aisle, ''
            FROM saved_list_items
            WHERE list_id = ?
        """, (user_id, list_id))

# Frequent items
def update_frequent_items(user_id: int):
    """Update frequent items based on completed carts"""
    # This runs when user "completes" a shopping trip
    with get_db() as db:
        db.execute("""
            INSERT INTO frequent_items (product_name, price, aisle, image_url, purchase_count, last_purchased)
            SELECT
                product_name,
                price,
                aisle,
                image_url,
                1,
                CURRENT_TIMESTAMP
            FROM shopping_carts
            WHERE user_id = ?
            ON CONFLICT(product_name) DO UPDATE SET
                purchase_count = purchase_count + 1,
                last_purchased = CURRENT_TIMESTAMP,
                price = excluded.price,
                aisle = excluded.aisle
        """, (user_id,))

def get_frequent_items(limit: int = 20) -> list:
    """Get most frequently purchased items"""
    with get_db() as db:
        cursor = db.execute("""
            SELECT * FROM frequent_items
            ORDER BY purchase_count DESC, last_purchased DESC
            LIMIT ?
        """, (limit,))
        return [dict(row) for row in cursor.fetchall()]
```

#### Step 1.2: Create Migration SQL (15 min)

**`migrations/init.sql`:**
```sql
-- Users table (simple, no passwords for now)
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shopping carts
CREATE TABLE IF NOT EXISTS shopping_carts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price REAL NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    aisle TEXT,
    image_url TEXT,
    search_term TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_cart_user ON shopping_carts(user_id);

-- Saved lists
CREATE TABLE IF NOT EXISTS saved_lists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS saved_list_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    list_id INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    price REAL,
    quantity INTEGER NOT NULL DEFAULT 1,
    aisle TEXT,
    FOREIGN KEY (list_id) REFERENCES saved_lists(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_list_items ON saved_list_items(list_id);

-- Search cache (7 day TTL)
CREATE TABLE IF NOT EXISTS search_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    search_term TEXT UNIQUE NOT NULL COLLATE NOCASE,
    results_json TEXT NOT NULL,
    cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hit_count INTEGER DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_search_term ON search_cache(search_term);
CREATE INDEX IF NOT EXISTS idx_search_cache_date ON search_cache(cached_at);

-- Frequent items (auto-populated)
CREATE TABLE IF NOT EXISTS frequent_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT UNIQUE NOT NULL COLLATE NOCASE,
    price REAL,
    aisle TEXT,
    image_url TEXT,
    purchase_count INTEGER DEFAULT 1,
    last_purchased TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_frequent_items_count ON frequent_items(purchase_count DESC);

-- Insert default user for testing
INSERT OR IGNORE INTO users (id, username) VALUES (1, 'default_user');
```

#### Step 1.3: Test Database Locally (30 min)

```python
# test_database.py
from src.database import (
    init_database,
    add_to_cart,
    get_user_cart,
    get_cached_search,
    cache_search_results
)

# Initialize
init_database()

# Test cart
product = {
    'name': 'Whole Milk',
    'price': '$3.99',
    'aisle': '12A',
    'image': 'https://example.com/milk.jpg'
}

add_to_cart(user_id=1, product=product, quantity=2)
cart = get_user_cart(user_id=1)
print(f"Cart: {cart}")

# Test cache
cache_search_results('milk', [product])
cached = get_cached_search('milk')
print(f"Cached: {cached}")

print("✅ Database working!")
```

---

### Phase 2: FastAPI Application (2-3 hours)

#### Step 2.1: Main Application (30 min)

**`app.py`:**
```python
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from src.database import init_database
from src.api import search, cart, lists, health
from src.config import settings

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="Wegmans Shopping App",
    version="1.0.0",
    docs_url="/api/docs" if settings.DEBUG else None
)

# CORS (for development)
if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Initialize database on startup
@app.on_event("startup")
async def startup():
    logger.info("🚀 Starting Wegmans Shopping App")
    init_database()
    logger.info("✅ Database initialized")

# Include API routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(cart.router, prefix="/api", tags=["cart"])
app.include_router(lists.router, prefix="/api", tags=["lists"])

# Serve static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve frontend
@app.get("/")
async def serve_frontend():
    return FileResponse("static/index.html")

# Simple session middleware (stores user_id in cookie)
@app.middleware("http")
async def session_middleware(request: Request, call_next):
    # Get or create user session
    user_id = request.cookies.get("user_id")
    if not user_id:
        user_id = "1"  # Default user for now (no auth)

    request.state.user_id = int(user_id)
    response = await call_next(request)

    # Set cookie if not present
    if not request.cookies.get("user_id"):
        response.set_cookie("user_id", user_id, max_age=31536000)  # 1 year

    return response

if __name__ == "__main__":
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info"
    )
```

#### Step 2.2: Configuration (15 min)

**`src/config.py`:**
```python
import os
from pathlib import Path

class Settings:
    # Server
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Scraper
    STORE_LOCATION = os.getenv("STORE_LOCATION", "Raleigh")
    SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"

    # Paths
    BASE_DIR = Path(__file__).parent.parent
    DATA_DIR = BASE_DIR / "data"
    STATIC_DIR = BASE_DIR / "static"

    # Cache
    SEARCH_CACHE_DAYS = int(os.getenv("SEARCH_CACHE_DAYS", "7"))

settings = Settings()
```

#### Step 2.3: API Endpoints (1.5 hours)

**`src/api/cart.py`:**
```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.database import (
    get_user_cart,
    add_to_cart,
    update_cart_quantity,
    remove_from_cart,
    clear_cart,
    update_frequent_items
)

router = APIRouter()

class AddToCartRequest(BaseModel):
    product_name: str
    price: str
    quantity: int = 1
    aisle: str | None = None
    image_url: str | None = None
    search_term: str | None = None

class UpdateQuantityRequest(BaseModel):
    cart_item_id: int
    quantity: int

@router.get("/cart")
async def get_cart(request: Request):
    """Get user's shopping cart"""
    user_id = request.state.user_id
    cart = get_user_cart(user_id)
    return {"cart": cart}

@router.post("/cart/add")
async def add_item_to_cart(item: AddToCartRequest, request: Request):
    """Add item to cart"""
    user_id = request.state.user_id

    product = {
        'name': item.product_name,
        'price': item.price,
        'aisle': item.aisle,
        'image': item.image_url,
        'search_term': item.search_term
    }

    add_to_cart(user_id, product, item.quantity)
    cart = get_user_cart(user_id)

    return {"success": True, "cart": cart}

@router.put("/cart/quantity")
async def update_quantity(update: UpdateQuantityRequest, request: Request):
    """Update item quantity in cart"""
    user_id = request.state.user_id
    update_cart_quantity(user_id, update.cart_item_id, update.quantity)
    cart = get_user_cart(user_id)

    return {"success": True, "cart": cart}

@router.delete("/cart/{cart_item_id}")
async def remove_item(cart_item_id: int, request: Request):
    """Remove item from cart"""
    user_id = request.state.user_id
    remove_from_cart(user_id, cart_item_id)
    cart = get_user_cart(user_id)

    return {"success": True, "cart": cart}

@router.delete("/cart")
async def clear_user_cart(request: Request):
    """Clear entire cart"""
    user_id = request.state.user_id
    clear_cart(user_id)

    return {"success": True, "cart": []}

@router.post("/cart/complete")
async def complete_shopping(request: Request):
    """Mark shopping as complete and update frequent items"""
    user_id = request.state.user_id
    update_frequent_items(user_id)
    clear_cart(user_id)

    return {"success": True, "message": "Shopping completed!"}
```

**`src/api/search.py`:**
```python
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
import asyncio
from src.scraper import WegmansScraper
from src.database import get_cached_search, cache_search_results
from src.config import settings

router = APIRouter()

# Keep scraper instance alive (optimization)
_scraper = None

async def get_scraper():
    global _scraper
    if _scraper is None:
        _scraper = WegmansScraper(
            headless=settings.SCRAPER_HEADLESS,
            store_location=settings.STORE_LOCATION
        )
        await _scraper.__aenter__()
    return _scraper

class SearchRequest(BaseModel):
    search_term: str
    max_results: int = 10

@router.post("/search")
async def search_products(search: SearchRequest, background_tasks: BackgroundTasks):
    """Search for products (with caching)"""

    # Check cache first
    cached = get_cached_search(search.search_term)
    if cached:
        return {
            "products": cached[:search.max_results],
            "from_cache": True
        }

    # Not in cache, scrape Wegmans
    try:
        scraper = await get_scraper()
        products = await scraper.search_products(
            search.search_term,
            max_results=search.max_results
        )

        # Cache results in background
        background_tasks.add_task(cache_search_results, search.search_term, products)

        return {
            "products": products,
            "from_cache": False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/frequent")
async def get_frequent_items():
    """Get frequently purchased items"""
    from src.database import get_frequent_items
    items = get_frequent_items(limit=20)
    return {"items": items}
```

**`src/api/lists.py`:**
```python
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from src.database import (
    get_user_lists,
    save_cart_as_list,
    load_list_to_cart
)

router = APIRouter()

class SaveListRequest(BaseModel):
    name: str

@router.get("/lists")
async def get_lists(request: Request):
    """Get all saved lists for user"""
    user_id = request.state.user_id
    lists = get_user_lists(user_id)
    return {"lists": lists}

@router.post("/lists/save")
async def save_list(save_req: SaveListRequest, request: Request):
    """Save current cart as a list"""
    user_id = request.state.user_id
    list_id = save_cart_as_list(user_id, save_req.name)

    return {"success": True, "list_id": list_id}

@router.post("/lists/{list_id}/load")
async def load_list(list_id: int, request: Request):
    """Load a saved list into cart"""
    user_id = request.state.user_id

    try:
        load_list_to_cart(user_id, list_id)
        return {"success": True}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
```

**`src/api/health.py`:**
```python
from fastapi import APIRouter
from datetime import datetime
import sqlite3
from src.database import DATABASE_PATH

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint"""

    # Check database connectivity
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("SELECT 1")
        conn.close()
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "database": db_status
    }
```

---

### Phase 3: Update Frontend (1 hour)

Update your existing `shop_ui_final.html` to use the new API endpoints:

**Changes needed:**
```javascript
// OLD: Save to localStorage/JSON files
localStorage.setItem('cart', JSON.stringify(cart))

// NEW: Save to database via API
async function saveCart() {
    await fetch('/api/cart/add', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            product_name: product.name,
            price: product.price,
            quantity: quantity,
            aisle: product.aisle,
            image_url: product.image
        })
    });
}

// Load cart from database on page load
async function loadCart() {
    const response = await fetch('/api/cart');
    const data = await response.json();
    cart = data.cart;
    renderCart();
}
```

I can help you update the frontend after we get the backend working.

---

### Phase 4: Docker & Fly.io Setup (1 hour)

#### Step 4.1: Create Dockerfile (20 min)

**`Dockerfile`:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8000

# Run app
CMD ["python", "app.py"]
```

#### Step 4.2: Update Requirements (10 min)

**`requirements.txt`:**
```txt
# Web framework
fastapi==0.104.1
uvicorn[standard]==0.24.0

# Scraping
playwright==1.40.0

# Utilities
python-dotenv==1.0.0
pydantic==2.5.0
```

#### Step 4.3: Create Fly Config (15 min)

**`fly.toml`:**
```toml
app = "wegmans-shopping"

[build]
  dockerfile = "Dockerfile"

[env]
  HOST = "0.0.0.0"
  PORT = "8000"
  STORE_LOCATION = "Raleigh"
  SCRAPER_HEADLESS = "true"

[[services]]
  internal_port = 8000
  protocol = "tcp"
  auto_stop_machines = true
  auto_start_machines = true
  min_machines_running = 0

  [[services.ports]]
    port = 80
    handlers = ["http"]
    force_https = true

  [[services.ports]]
    port = 443
    handlers = ["tls", "http"]

  [[services.http_checks]]
    interval = "30s"
    timeout = "5s"
    grace_period = "10s"
    method = "GET"
    path = "/api/health"

# Mount volume for database
[mounts]
  source = "wegmans_data"
  destination = "/app/data"
```

#### Step 4.4: Create .dockerignore (5 min)

**`.dockerignore`:**
```
__pycache__
*.pyc
.git
.gitignore
.env
venv/
*.md
data/*.json
.DS_Store
```

---

### Phase 5: Deploy to Fly.io (1 hour)

#### Step 5.1: Install Fly CLI (5 min)
```bash
# Mac
brew install flyctl

# Verify
fly version
```

#### Step 5.2: Login (2 min)
```bash
fly auth signup
# Or: fly auth login
```

#### Step 5.3: Create Fly App (5 min)
```bash
cd wegmans-shopping

fly launch --no-deploy
# Answer prompts:
# App name: wegmans-shopping-abc123 (or auto-generate)
# Region: iad (or closest to you)
# PostgreSQL? No
# Redis? No
```

#### Step 5.4: Create Volume for Database (5 min)
```bash
# Create 1GB volume (free tier = 3GB total)
fly volumes create wegmans_data --size 1 --region iad

# Verify
fly volumes list
```

#### Step 5.5: Deploy! (10 min)
```bash
# Build and deploy
fly deploy

# Takes 2-3 minutes first time
# Watch logs
fly logs
```

#### Step 5.6: Open Your App (1 min)
```bash
fly open
```

Visit: `https://wegmans-shopping-abc123.fly.dev`

#### Step 5.7: Check Health (2 min)
```bash
# API health check
curl https://wegmans-shopping-abc123.fly.dev/api/health

# SSH into VM
fly ssh console

# Check database
ls -lh /app/data/
sqlite3 /app/data/wegmans.db "SELECT COUNT(*) FROM users;"
```

---

## Testing Checklist

### Local Testing
- [ ] Database initializes correctly
- [ ] Can add items to cart
- [ ] Can search for products
- [ ] Search results are cached
- [ ] Can save/load lists
- [ ] Frontend loads correctly
- [ ] API endpoints work

### Fly.io Testing
- [ ] App deploys successfully
- [ ] HTTPS works
- [ ] Database persists across restarts
- [ ] Search returns results
- [ ] Cart updates correctly
- [ ] No memory issues (check `fly status`)

### Load Testing (Optional)
```bash
# Test with 10 concurrent users
ab -n 100 -c 10 https://your-app.fly.dev/api/health
```

---

## Maintenance

### View Logs
```bash
fly logs
fly logs --follow  # Real-time
```

### Deploy Updates
```bash
git add .
git commit -m "Update feature X"
fly deploy
```

### Backup Database
```bash
# SSH in and copy database
fly ssh sftp get /app/data/wegmans.db ./backup-$(date +%Y%m%d).db

# Or setup automated backups
fly ssh console
sqlite3 /app/data/wegmans.db ".backup '/tmp/backup.db'"
exit
fly ssh sftp get /tmp/backup.db ./backup.db
```

### Restart App
```bash
fly apps restart
```

### Scale (if needed)
```bash
# Use bigger VM (costs $1.94/month)
fly scale vm shared-cpu-512mb

# Back to free tier
fly scale vm shared-cpu-256mb
```

---

## Cost Breakdown

### Fly.io Free Tier
- **VMs:** 1 × 256MB = FREE ✅
- **Storage:** 1GB volume = FREE ✅
- **Bandwidth:** < 160GB/month = FREE ✅
- **HTTPS:** Included = FREE ✅

### Total: $0/month

### If You Exceed Free Tier
- Upgrade to 512MB RAM: $1.94/month
- Extra bandwidth (161-500GB): $2.00/month
- Still < $5/month total

---

## Timeline Summary

| Phase | Task | Time |
|-------|------|------|
| 1 | Database setup | 2 hours |
| 2 | FastAPI backend | 2-3 hours |
| 3 | Frontend updates | 1 hour |
| 4 | Docker & Fly config | 1 hour |
| 5 | Deploy & test | 1 hour |
| **Total** | | **7-8 hours** |

---

## Next Steps

**Ready to start?** I can help you with:

1. **Phase 1: Database setup** (2 hours)
   - Create the schema
   - Write database helper functions
   - Test locally

2. **Phase 2: FastAPI backend** (2-3 hours)
   - Build API endpoints
   - Integrate database
   - Test API with Postman/curl

3. **Phase 3: Deploy to Fly.io** (1 hour)
   - Create Dockerfile
   - Deploy to Fly
   - Test live

Want me to start with Phase 1 (database setup)?

---

## Phase 6: Migration from Current Code (1-2 hours)

### Migration Strategy

**Current State:**
- 4 Python entry points
- JSON file storage
- 3,000-line HTML file
- No database

**Migration Path:**

#### Option A: Clean Slate (Recommended)
1. Create new `app.py` from scratch using plan
2. Extract CSS/JS from `shop_ui_final.html`
3. Migrate frontend to use new API endpoints
4. Test locally
5. Deploy to Fly.io
6. Archive old files

**Pros:** Clean, no legacy baggage
**Cons:** More work upfront (6-8 hours)

#### Option B: Incremental Migration
1. Keep `shop_ui_final.html` as-is initially
2. Build FastAPI backend alongside old code
3. Gradually update frontend to use new endpoints
4. Run both systems in parallel temporarily
5. Switch over when ready

**Pros:** Less risky, can rollback
**Cons:** More complex, duplicate code temporarily

### Data Migration

**No data migration needed!** You're starting fresh:
- Current JSON files are essentially cache/temporary data
- No user accounts to migrate
- No historical data to preserve

**If you want to preserve search cache:**
```python
# migration_script.py
import json
from src.database import cache_search_results

# Load old search_results.json
with open('search_results.json') as f:
    old_results = json.load(f)

# Import into database
for search_term, data in old_results.items():
    cache_search_results(search_term, data['products'])
```

### Backwards Compatibility

**Not needed** - this is a new deployment, not updating existing production.

---

## Phase 7: Security Considerations

### Current Security Posture

**What we have:**
- ✅ HTTPS (Fly.io automatic)
- ✅ No sensitive data stored
- ✅ Simple session cookies
- ✅ SQLite (no SQL injection via ORM)
- ✅ No external API keys exposed

**What we don't have:**
- ❌ User authentication (everyone shares cart)
- ❌ Input validation on frontend
- ❌ Rate limiting
- ❌ CSRF protection
- ❌ XSS protection headers

### Security Improvements Needed

#### Phase 7.1: Input Validation (30 min)
Add Pydantic validation to all API endpoints:
```python
# Already in plan - Pydantic models validate inputs
class SearchRequest(BaseModel):
    search_term: str = Field(..., min_length=1, max_length=100)
    max_results: int = Field(default=10, ge=1, le=50)
```

#### Phase 7.2: Rate Limiting (1 hour)
Prevent abuse of search endpoint:
```python
# Add to requirements.txt:
slowapi==0.1.9

# Add to app.py:
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter

@app.post("/api/search")
@limiter.limit("10/minute")  # Max 10 searches per minute
async def search_products(...):
    ...
```

#### Phase 7.3: Security Headers (15 min)
Add security headers to responses:
```python
# Add middleware to app.py
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
```

#### Phase 7.4: Simple Password Protection (Optional - 1 hour)
Add HTTP Basic Auth for the entire site:
```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets

security = HTTPBasic()

def verify_password(credentials: HTTPBasicCredentials = Depends(security)):
    correct_password = os.getenv("APP_PASSWORD", "")
    if not correct_password:
        return  # No password set = open access

    is_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8")
    )
    if not is_correct:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Basic"},
        )

# Protect all routes
app = FastAPI(dependencies=[Depends(verify_password)])
```

Set in Fly.io: `fly secrets set APP_PASSWORD=your-secret-password`

### Security Checklist

**Before Going Live:**
- [ ] HTTPS enabled (automatic on Fly.io)
- [ ] Input validation on all endpoints
- [ ] Rate limiting on search endpoint
- [ ] Security headers added
- [ ] No secrets in code (use environment variables)
- [ ] Optional: Password protection enabled
- [ ] Database file permissions correct
- [ ] Logging doesn't expose sensitive data

**For 2-10 Friends:**
This level of security is **more than sufficient**.

---

## Phase 8: Monitoring & Observability (30 min)

### Built-in Health Check

Already included in plan:
```
GET /api/health

Response:
{
  "status": "ok",
  "timestamp": "2025-10-24T18:00:00",
  "database": "ok"
}
```

### Fly.io Monitoring

**Free tier includes:**
- VM metrics (CPU, RAM usage)
- HTTP request logs
- Deployment logs
- Health check monitoring

**Access:**
```bash
# View metrics
fly dashboard  # Opens web UI

# Real-time logs
fly logs --follow

# Status
fly status
```

### External Monitoring (Optional)

**UptimeRobot (Free):**
1. Sign up at uptimerobot.com
2. Add monitor: `https://your-app.fly.dev/api/health`
3. Check every 5 minutes
4. Email alert if down

**Setup time:** 5 minutes

### Logging Strategy

**What to log:**
- Search queries (for cache optimization)
- API errors (for debugging)
- Database errors
- Slow requests (> 5 seconds)

**What NOT to log:**
- User IPs (privacy)
- Full cart contents (unless debugging)
- Passwords (you don't have any)

**Log levels:**
```python
import logging

logger = logging.getLogger(__name__)

# INFO: Normal operations
logger.info(f"Search for '{search_term}' - {len(results)} results")

# WARNING: Recoverable issues
logger.warning("Search cache expired, re-scraping")

# ERROR: Failures
logger.error(f"Failed to scrape: {e}")
```

**View logs:**
```bash
fly logs | grep ERROR
```

### Performance Monitoring

**Track key metrics:**
- Search response time (should be < 5s)
- Cache hit rate (should be > 70%)
- Database query time (should be < 100ms)
- Memory usage (should stay < 200MB)

**Add to health endpoint:**
```python
@router.get("/health")
async def health_check():
    # Check database
    start = time.time()
    conn.execute("SELECT 1")
    db_time = time.time() - start

    # Check cache hit rate
    cache_stats = get_cache_stats()

    return {
        "status": "ok",
        "database_ms": round(db_time * 1000, 2),
        "cache_hit_rate": cache_stats['hit_rate'],
        "memory_mb": get_memory_usage()
    }
```

---

## Phase 9: Testing Strategy (2-3 hours)

### Unit Tests

**Test database operations:**
```bash
# Create tests/test_database.py
pytest tests/test_database.py

# Test coverage:
- Adding to cart
- Removing from cart
- Cache operations
- Frequent items tracking
```

**Test API endpoints:**
```bash
# Create tests/test_api.py
pytest tests/test_api.py

# Test coverage:
- Search endpoint
- Cart endpoints
- List endpoints
- Health check
```

### Integration Tests

**Test full workflows:**
```python
# tests/test_integration.py

async def test_shopping_flow():
    # Search for product
    response = await client.post("/api/search", json={"search_term": "milk"})
    products = response.json()["products"]

    # Add to cart
    response = await client.post("/api/cart/add", json={
        "product_name": products[0]["name"],
        "price": products[0]["price"],
        "quantity": 2
    })

    # Verify cart
    response = await client.get("/api/cart")
    assert len(response.json()["cart"]) == 1
```

### Manual Testing Checklist

**Before deployment:**
- [ ] Search returns results
- [ ] Add to cart works
- [ ] Update quantity works
- [ ] Remove from cart works
- [ ] Save list works
- [ ] Load list works
- [ ] Frequent items populate
- [ ] Cache works (search same term twice - faster)
- [ ] Health check returns 200
- [ ] Frontend loads
- [ ] Frontend can add to cart
- [ ] Frontend persists data across refresh

**After deployment to Fly.io:**
- [ ] HTTPS works
- [ ] All above tests pass
- [ ] Data persists after `fly apps restart`
- [ ] Logs show no errors
- [ ] Health check accessible

### Load Testing (Optional)

**Test with 10 concurrent users:**
```bash
# Install ApacheBench
brew install httpd  # Mac

# Test health endpoint
ab -n 100 -c 10 https://your-app.fly.dev/api/health

# Test search endpoint (more realistic)
ab -n 50 -c 5 -p search.json -T application/json \
   https://your-app.fly.dev/api/search
```

**Expected results (256MB VM):**
- Health check: < 100ms response time
- Search (cached): < 200ms
- Search (uncached): < 5s
- Concurrent users: 10+ no problem

---

## Phase 10: Performance Optimization

### Search Performance

**Current flow:**
1. User searches "milk"
2. Check cache → miss
3. Launch Playwright browser (~2s)
4. Navigate to Wegmans (~1s)
5. Intercept API (~2s)
6. Return results
7. **Total: ~5 seconds**

**Optimization strategies:**

#### 1. Persistent Browser Session (Already in plan)
Keep Playwright browser alive between searches.
- First search: 5 seconds
- Subsequent searches: 2 seconds
- **Improvement: 60% faster**

#### 2. Aggressive Caching (Already in plan)
Cache all searches for 7 days.
- Cache hit: < 200ms
- **Improvement: 96% faster**

#### 3. Background Cache Warming (Future)
Pre-populate cache with common items:
```python
COMMON_ITEMS = ["milk", "eggs", "bread", "cheese", "butter"]

@app.on_event("startup")
async def warm_cache():
    for item in COMMON_ITEMS:
        if not get_cached_search(item):
            # Search in background
            background_search(item)
```

### Database Performance

**Already optimized:**
- Indexes on foreign keys
- Indexes on search terms
- Single-file database (no network latency)

**Query optimization:**
```python
# BAD: N+1 query problem
for cart_item in cart_items:
    user = get_user(cart_item.user_id)  # Query per item

# GOOD: Join once
cart_with_users = db.execute("""
    SELECT c.*, u.username
    FROM shopping_carts c
    JOIN users u ON c.user_id = u.id
""")
```

### Frontend Performance

**Current issues:**
- 3,000-line HTML file
- Inline CSS/JS
- No minification
- No lazy loading

**Optimizations needed:**
1. Split CSS/JS into separate files
2. Minify assets (Vite does this)
3. Compress images
4. Lazy load product images
5. Cache static assets (Fly.io CDN)

**Expected improvements:**
- Page load: 2s → 500ms
- Time to interactive: 3s → 1s

---

## Phase 11: Rollback Plan

### If Deployment Fails

**Fly.io makes rollbacks easy:**
```bash
# View deployment history
fly releases

# Rollback to previous version
fly releases rollback

# Or deploy specific version
fly deploy --image registry.fly.io/wegmans-shopping:v5
```

### If Database Corrupts

**Backup strategy:**
```bash
# Daily backup (add to cron or GitHub Actions)
fly ssh sftp get /app/data/wegmans.db ./backups/wegmans-$(date +%Y%m%d).db

# Restore from backup
fly ssh sftp put ./backups/wegmans-20251024.db /app/data/wegmans.db
fly apps restart
```

### If Something Goes Wrong

**Emergency procedures:**

1. **Check logs:**
   ```bash
   fly logs | tail -100
   ```

2. **Check health:**
   ```bash
   curl https://your-app.fly.dev/api/health
   ```

3. **Restart app:**
   ```bash
   fly apps restart
   ```

4. **SSH into VM:**
   ```bash
   fly ssh console
   cd /app
   python -c "from src.database import init_database; init_database()"
   ```

5. **Nuclear option - destroy and redeploy:**
   ```bash
   fly apps destroy wegmans-shopping
   fly launch
   ```

---

## Phase 12: Future Enhancements

### Near Term (1-2 weeks)

**1. Multi-User Support (2 hours)**
- Add simple login page
- Hash passwords with bcrypt
- Store in `users` table
- Separate carts per user

**2. Email Shopping Lists (1 hour)**
- "Email me this list" button
- Use free service (SendGrid, Mailgun)
- Format as markdown table

**3. Store Selection (1 hour)**
- Let user choose store (currently hardcoded "Raleigh")
- Store in session/database
- Pass to scraper

**4. Better Frequent Items (1 hour)**
- Show in UI on homepage
- "Quick add" button
- Sort by recency + frequency

### Medium Term (1-2 months)

**5. Mobile-First UI (4 hours)**
- Responsive design improvements
- Touch-friendly buttons
- PWA support (install to home screen)

**6. Recipe Integration (4 hours)**
- Paste recipe URL
- Extract ingredients
- Add all to cart

**7. Price History (3 hours)**
- Track price changes over time
- Alert when items on sale
- Show price trends

**8. List Sharing (2 hours)**
- Generate shareable link
- Friend can view/copy list
- No account needed

### Long Term (3+ months)

**9. Native Mobile App (40+ hours)**
- React Native or Flutter
- Barcode scanning
- Push notifications

**10. Store Inventory API (if Wegmans provides)**
- Check if item in stock
- Show available stores
- Curbside pickup integration

**11. Multiple Stores Support (6 hours)**
- Support Whole Foods, Trader Joe's, etc.
- Abstract scraper interface
- Store-specific adapters

---

## Risk Assessment

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Playwright fails on Fly.io** | Medium | High | Test early, have fallback to Selenium |
| **256MB RAM insufficient** | Low | Medium | Upgrade to 512MB ($2/mo) |
| **Wegmans blocks scraping** | Low | High | Rate limit, rotate user agents |
| **Database corruption** | Very Low | High | Daily backups, SQLite is stable |
| **Free tier limits exceeded** | Very Low | Low | Monitor usage, upgrade if needed |

### Operational Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **App goes down** | Low | Medium | Health checks, auto-restart, monitoring |
| **Slow first load** | High | Low | Accept it or pay $2/mo for always-on |
| **Cache grows too large** | Low | Low | Expire old cache after 7 days |
| **Friends share URL publicly** | Medium | Medium | Add password protection |

### Legal Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| **Wegmans TOS violation** | Low | High | Check TOS, add rate limiting, contact them |
| **Copyright on images** | Low | Low | Images from Wegmans (fair use for personal) |
| **GDPR compliance** | None | None | No EU users, no personal data collected |

**Overall Risk Level:** **Low** for personal/friends use

**Red flags to watch for:**
- Wegmans blocks your IP
- Cease & desist letter
- Unexpected costs

---

## Cost Analysis (Detailed)

### Year 1 Costs

**Free Tier (Most Likely):**
```
Fly.io VM (256MB)        $0
Fly.io Storage (1GB)     $0
Fly.io Bandwidth         $0
Domain (optional)        $0 (use .fly.dev)
Monitoring (UptimeRobot) $0
───────────────────────────
TOTAL:                   $0/month
```

**If You Exceed Free Tier:**
```
Fly.io VM (512MB)        $1.94/month
Fly.io Storage (1GB)     $0.15/month
Bandwidth overage        ~$1/month
───────────────────────────
TOTAL:                   ~$3/month
```

**With Custom Domain:**
```
Base costs               $3/month
Domain (Namecheap)       $0.83/month ($10/year)
───────────────────────────
TOTAL:                   ~$4/month
```

### Break-Even Analysis

**Cost per user:**
- 2 users: $0/user/month
- 5 users: $0/user/month
- 10 users: $0.30/user/month (if upgraded)

**Compared to alternatives:**
- Railway: $5/month minimum
- DigitalOcean: $6/month + maintenance time
- Heroku: $7/month
- AWS: $10-20/month (complexity)

**Winner:** Fly.io free tier

---

## Implementation Timeline

### Realistic Schedule (Part-Time Work)

**Week 1:**
- [ ] Day 1-2: Phase 1 (Database setup) - 2 hours
- [ ] Day 3-5: Phase 2 (FastAPI backend) - 3 hours
- [ ] Day 6-7: Phase 3 (Frontend updates) - 2 hours

**Week 2:**
- [ ] Day 8: Phase 4 (Docker & Fly config) - 1 hour
- [ ] Day 9: Phase 5 (Deploy to Fly.io) - 1 hour
- [ ] Day 10: Phase 7 (Security) - 1 hour
- [ ] Day 11-12: Testing & fixes - 2 hours

**Week 3:**
- [ ] Day 13: Phase 8 (Monitoring) - 30 min
- [ ] Day 14: Share with friends, gather feedback

**Total:** ~12 hours over 2-3 weeks (working 1-2 hours per day)

### Aggressive Schedule (Full Focus)

**Weekend 1:**
- Saturday: Phases 1-2 (5 hours)
- Sunday: Phases 3-4 (3 hours)

**Weekend 2:**
- Saturday: Phase 5 + testing (2 hours)
- Sunday: Security + monitoring (2 hours)

**Total:** 12 hours over 2 weekends

---

## Success Metrics

### Launch Goals (Week 1)

- [ ] App deployed to Fly.io
- [ ] HTTPS working
- [ ] Can search for products
- [ ] Can add to cart
- [ ] Cart persists across sessions
- [ ] 2 friends successfully use it

### Month 1 Goals

- [ ] 5+ active users
- [ ] 100+ searches performed
- [ ] Cache hit rate > 70%
- [ ] No downtime incidents
- [ ] Positive feedback from users

### Month 3 Goals

- [ ] 10+ active users
- [ ] 500+ searches performed
- [ ] Added 2-3 quality-of-life features
- [ ] < 5 minutes/week maintenance
- [ ] Still $0/month cost

---

## Conclusion

This plan provides a **complete roadmap** from current prototype to production-ready Fly.io deployment with:

✅ **SQLite database** (proper data management)
✅ **FastAPI backend** (modern, fast, scalable)
✅ **Docker containerization** (portable, reproducible)
✅ **Free hosting** (Fly.io free tier)
✅ **Security hardening** (HTTPS, rate limiting, validation)
✅ **Monitoring** (health checks, logs, alerts)
✅ **Performance optimization** (caching, persistent browser)
✅ **Testing strategy** (unit, integration, manual)
✅ **Rollback plan** (backups, versioning)
✅ **Future roadmap** (enhancements, scaling)

**Estimated effort:** 12 hours total
**Monthly cost:** $0
**Target users:** 2-10 friends
**Timeline:** 2-3 weeks (part-time) or 2 weekends (focused)

**Ready to implement when you are!** 🚀

