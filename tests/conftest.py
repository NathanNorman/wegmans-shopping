"""
Pytest configuration and fixtures

Provides shared fixtures for database, test client, and user management.
"""
import pytest
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from app import app
from src.database import get_connection_pool
import psycopg2
from psycopg2.extras import RealDictCursor


@pytest.fixture(scope="session")
def test_database_url():
    """Get test database URL from environment"""
    db_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not db_url:
        pytest.skip("No TEST_DATABASE_URL or DATABASE_URL set")
    return db_url


@pytest.fixture(scope="function")
def db_connection(test_database_url):
    """
    Provide a database connection with transaction rollback

    Each test gets a fresh connection and all changes are rolled back
    """
    conn = psycopg2.connect(test_database_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    yield cursor

    # Rollback all changes after test
    conn.rollback()
    cursor.close()
    conn.close()


@pytest.fixture(scope="function", autouse=True)
def reset_rate_limiter():
    """Auto-reset rate limiter before and after each test"""
    from app import limiter
    try:
        limiter.reset()
    except:
        pass

    yield  # Run test

    # Reset after test too
    try:
        limiter.reset()
    except:
        pass


@pytest.fixture(scope="function")
def client():
    """
    FastAPI test client with anonymous user ID

    Provides a requests-like interface for testing API endpoints.
    Includes X-Anonymous-User-ID header for consistent user identity across requests.
    """
    import uuid
    anonymous_id = str(uuid.uuid4())

    with TestClient(app) as test_client:
        # Set default headers for all requests
        test_client.headers = {"X-Anonymous-User-ID": anonymous_id}
        yield test_client


@pytest.fixture
def test_user_id():
    """Generate a test user UUID"""
    import uuid
    return str(uuid.uuid4())


@pytest.fixture
def test_anonymous_user(test_user_id):
    """
    Create a test anonymous user

    NOTE: Uses src.database functions instead of direct SQL
    to work with current schema (handles duplicate columns)
    """
    from src.database import get_db

    # Create user using database connection pool
    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO users (id, email, is_anonymous, created_at)
            VALUES (%s, NULL, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING
        """, (test_user_id,))

    return test_user_id


@pytest.fixture
def test_authenticated_user():
    """
    Create a test authenticated user

    NOTE: Uses src.database functions to work with current schema
    """
    import uuid
    from src.database import get_db

    user_id = str(uuid.uuid4())
    email = f"test-{user_id[:8]}@example.com"

    with get_db() as cursor:
        cursor.execute("""
            INSERT INTO users (id, email, is_anonymous, created_at)
            VALUES (%s, %s, FALSE, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO NOTHING
        """, (user_id, email))

    return {"id": user_id, "email": email}


@pytest.fixture
def test_cart_item():
    """Sample cart item for testing"""
    return {
        "name": "Test Product",
        "price": "$9.99",
        "quantity": 2,
        "aisle": "Produce",
        "image": "https://example.com/image.jpg",
        "search_term": "test",
        "is_sold_by_weight": False,
        "unit_price": None
    }


@pytest.fixture
def test_products():
    """Sample products for testing"""
    return [
        {"name": "Bananas", "price": "$0.59", "aisle": "Produce", "image": "https://example.com/bananas.jpg"},
        {"name": "Milk", "price": "$3.99", "aisle": "Dairy", "image": "https://example.com/milk.jpg"},
        {"name": "Bread", "price": "$2.49", "aisle": "Bakery", "image": "https://example.com/bread.jpg"}
    ]
