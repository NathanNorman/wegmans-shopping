# Wegmans Shopping List Builder

Interactive web app for building Wegmans shopping lists with real-time product search, auto-save, and mobile-optimized printing. Targets Raleigh, NC store.

**Live Demo:** [wegmans-shopping.onrender.com](https://wegmans-shopping.onrender.com)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Tests](https://img.shields.io/badge/tests-30%2B%20passing-brightgreen.svg)](tests/)

---

## Features

### Core Functionality
- 🔍 **Real-time product search** - Search 50,000+ Wegmans products with images, prices, and aisle locations
- 💾 **Auto-save** - Shopping lists automatically save as you shop (2-second debounce)
- 📱 **Mobile optimized** - Responsive design with touch-friendly interface
- 🖨️ **Smart printing** - One-page formatted lists organized by aisle
- ⭐ **Frequent items** - Quick-add from your purchase history (70-80% faster loading)
- 🔐 **User authentication** - Sign up/login with Supabase Auth
- 🍳 **Recipe support** - Save recipes and add ingredients to cart

### Technical Features
- ⚡ **High performance** - Connection pooling, batch APIs, search caching
- 🧪 **Tested** - 30+ automated tests with pytest
- 🔒 **Secure** - SQL injection protection audited, JWT authentication
- 📊 **Maintainable** - Clean architecture, comprehensive documentation
- 🚀 **Production-ready** - Migration tracking, error handling, monitoring

---

## Quick Start

### Prerequisites
```bash
# Python 3.10+
python3 --version

# Install dependencies
pip install -r requirements.txt
```

### Environment Setup

Create `.env` file in project root:
```bash
# Database (Required)
DATABASE_URL=postgresql://user:password@host:5432/database

# Supabase Auth (Required for authentication)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-key

# Algolia Search (Optional - defaults provided)
ALGOLIA_APP_ID=QGPPR19V8V
ALGOLIA_API_KEY=9a10b1401634e9a6e55161c3a60c200d
ALGOLIA_STORE_NUMBER=86

# Server Settings (Optional)
DEBUG=false
PORT=8000
HOST=0.0.0.0
```

**Note:** PASSWORD in DATABASE_URL must be URL-encoded. Use `urllib.parse.quote_plus()` for special characters.

### Database Setup

```bash
# Check migration status
python migrations/migrate.py status

# Apply all pending migrations
python migrations/migrate.py up

# List all migrations
python migrations/migrate.py list
```

See `migrations/README.md` for detailed documentation.

### Run Development Server

```bash
# Start server
python3 -m uvicorn app:app --reload --host 127.0.0.1 --port 8000
```

Open **http://localhost:8000** in your browser.

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test category
pytest -m unit  # Fast unit tests only
pytest -m api   # API endpoint tests only

# Skip slow tests
pytest -m "not slow"
```

See `tests/README.md` for complete testing guide.

---

## Architecture

### Tech Stack
- **Backend:** FastAPI (Python 3.10+) with connection pooling
- **Database:** PostgreSQL (Supabase) with migration tracking
- **Frontend:** Vanilla JavaScript + CSS (no framework)
- **Search:** Direct Algolia API (~1 second per search)
- **Auth:** Supabase Auth with JWT token caching
- **Deployment:** Render (auto-deploy from main branch)
- **Testing:** pytest with 30+ tests

### Performance Optimizations

- ⚡ **Connection pooling** - ThreadedConnectionPool (2-10 connections)
- 🎯 **Batch image API** - 70-80% faster frequent items loading
- 💾 **Search caching** - 7-day cache with graceful degradation
- 🧹 **Automatic cleanup** - Token cache cleanup, anonymous user cleanup
- 📦 **Lightweight** - 60% smaller deployments (no Playwright/browser)

### Key Design Decisions

**Auto-Save System** - Cart changes auto-save to date-based list after 2 seconds. Only one list per day, upserted on changes.

**Batch Image Loading** - Parallel image fetching via `/api/images/fetch` endpoint instead of sequential requests.

**Direct Algolia Search** - Bypasses browser automation by calling Algolia API directly. Cached for 7 days in PostgreSQL.

**Mobile Print** - Uses hidden `<div class="print-only">` with `@media print` CSS. Device detection via `navigator.userAgent` for reliable mobile styles.

**Connection Pooling** - psycopg2 ThreadedConnectionPool (2-10 connections) prevents connection exhaustion under load.

**Token Caching** - JWT tokens cached with automatic cleanup every 5 minutes to prevent memory leaks.

### Database Schema

**Core Tables:**
- `users` - UUID-based user accounts (6 clean columns)
- `shopping_carts` - Current cart items with decimal quantity support
- `saved_lists` - Saved shopping lists with auto-save flag
- `saved_list_items` - Items in saved lists
- `recipes` - User-created recipes
- `recipe_items` - Recipe ingredients
- `frequent_items` - User-specific items purchased 2+ times
- `search_cache` - Algolia responses (7-day TTL)
- `schema_migrations` - Migration tracking

**Key Pattern:** One auto-saved list per day (date-based name). Clean schema with transaction safety.

---

## API Endpoints

### Health
- `GET /api/health` - Health check

### Authentication
- `GET /api/config` - Get Supabase configuration
- `GET /api/user` - Get current user

### Cart
- `POST /api/cart/add` - Add item (decimal quantities supported)
- `GET /api/cart` - Get cart items
- `PUT /api/cart/quantity` - Update item quantity
- `DELETE /api/cart/{id}` - Remove item
- `DELETE /api/cart` - Clear entire cart
- `POST /api/cart/update-frequent` - Update frequent items

### Lists
- `POST /api/lists/auto-save` - Upsert today's list
- `GET /api/lists/today` - Get today's list summary
- `GET /api/lists` - Get all lists
- `POST /api/lists/{id}/load` - Load list to cart
- `DELETE /api/lists/{id}` - Delete list

### Recipes
- `GET /api/recipes` - Get all recipes
- `POST /api/recipes` - Create recipe
- `POST /api/recipes/from-cart` - Save cart as recipe
- `POST /api/recipes/{id}/load` - Load recipe to cart
- `DELETE /api/recipes/{id}` - Delete recipe

### Search
- `POST /api/search` - Search Wegmans products
- `GET /api/frequent` - Get frequently bought items
- `POST /api/images/fetch` - Batch image fetching (max 20 items)

---

## Development

### Project Structure

```
wegmans-shopping/
├── app.py                     # FastAPI app with lifespan management
├── config/
│   └── settings.py            # Environment configuration
├── src/
│   ├── api/                   # API routers
│   │   ├── auth.py           # Authentication endpoints
│   │   ├── cart.py           # Cart operations
│   │   ├── lists.py          # List management
│   │   ├── recipes.py        # Recipe management
│   │   ├── search.py         # Product search
│   │   ├── images.py         # Batch image fetching
│   │   └── health.py         # Health check
│   ├── auth.py               # Supabase Auth integration
│   ├── database.py           # Database operations with pooling
│   └── scraper/
│       └── algolia_direct.py # Direct Algolia API client
├── frontend/
│   ├── index.html            # Main UI
│   ├── js/
│   │   ├── main.js          # App logic
│   │   ├── auth.js          # Authentication
│   │   └── modals.js        # Modal dialogs
│   └── css/
│       ├── styles.css       # Main styles
│       └── auth.css         # Auth modal styles
├── migrations/                # SQL migrations
│   ├── migrate.py            # Migration CLI tool
│   ├── 000_migration_tracking.sql
│   ├── 001_init.sql
│   └── ...
├── scripts/                   # Maintenance scripts
│   └── cleanup_anonymous_users.py
├── tests/                     # Automated tests
│   ├── conftest.py           # Test fixtures
│   ├── test_database.py     # Database tests
│   └── test_api.py          # API tests
├── docs/                      # Documentation
│   ├── SQL_INJECTION_AUDIT.md
│   └── ...
├── deprecated/                # Old code (preserved for reference)
├── .env                       # Environment variables (not in git)
├── requirements.txt           # Python dependencies
├── pytest.ini                # Test configuration
└── README.md                 # This file
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | PostgreSQL connection string |
| `SUPABASE_URL` | Yes | - | Supabase project URL |
| `SUPABASE_ANON_KEY` | Yes | - | Supabase anonymous key |
| `SUPABASE_SERVICE_KEY` | Yes | - | Supabase service key |
| `ALGOLIA_APP_ID` | No | QGPPR19V8V | Algolia application ID |
| `ALGOLIA_API_KEY` | No | (public key) | Algolia search API key |
| `ALGOLIA_STORE_NUMBER` | No | 86 | Wegmans store number |
| `DEBUG` | No | false | Enable debug mode |
| `PORT` | No | 8000 | Server port |
| `HOST` | No | 0.0.0.0 | Server host |

### Common Tasks

**Run migrations:**
```bash
python migrations/migrate.py up
```

**Run tests:**
```bash
pytest --cov=src
```

**Clean up anonymous users:**
```bash
python scripts/cleanup_anonymous_users.py --stats
python scripts/cleanup_anonymous_users.py --dry-run
python scripts/cleanup_anonymous_users.py  # Actually cleanup
```

**Check database schema:**
```bash
psql $DATABASE_URL -c "\d users"
```

---

## Testing

### Test Suite

- **30+ automated tests** covering database operations and API endpoints
- **Test fixtures** for database, users, and test data
- **Transaction rollback** per test (isolated, no pollution)
- **Coverage reporting** with pytest-cov

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_database.py

# Specific test class
pytest tests/test_api.py::TestCartEndpoints

# Specific test
pytest tests/test_database.py::TestCartOperations::test_add_to_cart

# With coverage
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

See `tests/README.md` for complete guide.

---

## Deployment

### Render (Production)

Auto-deploys from `main` branch.

**Required Environment Variables:**
- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`
- `DEBUG=false`

**Build Command:**
```bash
pip install -r requirements.txt
```

**Start Command:**
```bash
python3 -m uvicorn app:app --host 0.0.0.0 --port $PORT
```

### Manual Deployment

```bash
# 1. Pull latest code
git pull origin main

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run migrations
python migrations/migrate.py up

# 4. Run tests
pytest

# 5. Start server
python3 -m uvicorn app:app --host 0.0.0.0 --port 8000
```

---

## Maintenance

### Automated Cleanup

**Anonymous Users** - Run daily via cron:
```bash
# Add to crontab
0 2 * * * cd /path/to/wegmans-shopping && python3 scripts/cleanup_anonymous_users.py >> logs/cleanup.log 2>&1
```

See `scripts/README.md` for setup guide.

### Monitoring

**Check cache hit rate:**
```sql
SELECT search_term, hit_count, cached_at
FROM search_cache
ORDER BY hit_count DESC
LIMIT 10;
```

**Check anonymous users:**
```bash
python scripts/cleanup_anonymous_users.py --stats
```

**Check migrations:**
```bash
python migrations/migrate.py status
```

---

## Security

- ✅ **SQL injection protected** - 100% parameterized queries (audited)
- ✅ **JWT authentication** - Supabase Auth with token caching
- ✅ **Input validation** - FastAPI/Pydantic automatic validation
- ✅ **HTTPS only** - Enforced in production
- ✅ **Environment secrets** - Sensitive data in .env (not committed)
- ✅ **Error handling** - Graceful degradation, no data leaks

See `docs/SQL_INJECTION_AUDIT.md` for complete security audit.

---

## Performance

### Benchmarks

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Concurrent requests | ~2s | ~0.6s | **70% faster** |
| Frequent items loading | ~10s | ~2-3s | **80% faster** |
| Deployment size | ~500MB | ~200MB | **60% smaller** |
| Memory usage | Growing | Stable | **Leak fixed** |

### Optimizations Applied

1. **Connection pooling** (Issue #2) - ThreadedConnectionPool
2. **Batch image API** (Issue #7) - Parallel fetching
3. **Token cache cleanup** (Issue #3) - Every 5 minutes
4. **Removed Playwright** (Issue #8) - Direct Algolia API
5. **Search caching** - 7-day PostgreSQL cache

---

## Documentation

- **README.md** - This file (project overview)
- **CLAUDE.md** - AI assistant context and patterns
- **CHANGELOG.md** - Complete change history
- **migrations/README.md** - Migration system guide
- **tests/README.md** - Testing guide
- **scripts/README.md** - Maintenance scripts
- **docs/SQL_INJECTION_AUDIT.md** - Security audit
- **TECH_DEBT_FIX_SUMMARY*.md** - Tech debt resolution (4 documents)

---

## Contributing

### Development Workflow

1. Create feature branch from `main`
2. Make changes and add tests
3. Run tests: `pytest --cov=src`
4. Update documentation if needed
5. Create pull request
6. Ensure CI passes (tests, linting)

### Code Style

- **Python**: PEP 8, type hints preferred
- **JavaScript**: ESLint (if configured)
- **SQL**: Parameterized queries only
- **Tests**: Arrange-Act-Assert pattern

### Before Committing

```bash
# Run tests
pytest

# Check migrations
python migrations/migrate.py status

# Format code (if black installed)
black src/ tests/

# Run linter (if flake8 installed)
flake8 src/ tests/
```

---

## Troubleshooting

### Database Connection Errors

**Issue**: `psycopg2.OperationalError: could not connect`

**Solution**:
1. Check `DATABASE_URL` is set correctly
2. Verify database is running
3. Check network/firewall rules
4. Verify credentials are URL-encoded

### Migration Errors

**Issue**: `Migration XXX failed`

**Solution**:
1. Check migration status: `python migrations/migrate.py status`
2. Review error message
3. Fix migration SQL
4. Retry: `python migrations/migrate.py up XXX`

### Tests Failing

**Issue**: Tests fail with database errors

**Solution**:
1. Verify `DATABASE_URL` or `TEST_DATABASE_URL` is set
2. Run migrations: `python migrations/migrate.py up`
3. Check database is accessible
4. Review test output for specific errors

### Search Not Working

**Issue**: Search returns no results

**Solution**:
1. Check Algolia credentials in `.env`
2. Verify store number is correct (86 for Raleigh)
3. Check search cache: May need to clear stale cache
4. Review logs for API errors

---

## License

MIT License - See LICENSE file for details

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for complete version history.

**Latest Changes:**
- ✅ All 14 tech debt issues resolved
- ✅ 30+ automated tests added
- ✅ Performance improved 50-80%
- ✅ Deployment size reduced 60%
- ✅ Security audited and documented
- ✅ Migration tracking system
- ✅ Anonymous user cleanup
- ✅ Connection pooling
- ✅ Batch image API

---

## Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Docs**: See `docs/` directory
- **Tests**: Run `pytest --help`
- **Migrations**: Run `python migrations/migrate.py --help`

---

**Built with ❤️ for Wegmans shoppers in Raleigh, NC**
