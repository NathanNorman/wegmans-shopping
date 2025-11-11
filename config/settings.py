"""
Configuration settings for Wegmans Shopping App

Supports environment variables for deployment flexibility.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Base directory (project root)
BASE_DIR = Path(__file__).parent.parent

# Load .env file from project root
load_dotenv(BASE_DIR / ".env")

class Settings:
    """Application settings"""

    # Server configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    # Database - Supabase PostgreSQL
    DATABASE_URL = os.getenv("DATABASE_URL", "")

    # Supabase Auth
    SUPABASE_URL = os.getenv("SUPABASE_URL", "https://pisakkjmyeobvcgxbmhk.supabase.co")
    SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "")  # Public key (safe for frontend)
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")  # SECRET (backend only!)

    # Scraper configuration
    STORE_LOCATION = os.getenv("STORE_LOCATION", "Raleigh")
    SCRAPER_HEADLESS = os.getenv("SCRAPER_HEADLESS", "true").lower() == "true"
    SEARCH_MAX_RESULTS = int(os.getenv("SEARCH_MAX_RESULTS", "10"))

    # Algolia configuration (Wegmans product search)
    ALGOLIA_APP_ID = os.getenv("ALGOLIA_APP_ID", "QGPPR19V8V")
    ALGOLIA_API_KEY = os.getenv("ALGOLIA_API_KEY", "9a10b1401634e9a6e55161c3a60c200d")
    ALGOLIA_STORE_NUMBER = int(os.getenv("ALGOLIA_STORE_NUMBER", "108"))  # Default: Raleigh, NC (1200 Wake Towne Dr)

    # Data paths
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = DATA_DIR / "cache"
    USER_DATA_DIR = DATA_DIR / "user"
    REFERENCE_DIR = DATA_DIR / "reference"

    # Static files (frontend directory)
    STATIC_DIR = BASE_DIR / "frontend"

    # Cache settings
    SEARCH_CACHE_DAYS = int(os.getenv("SEARCH_CACHE_DAYS", "7"))

    # Debug settings (production should always be False)
    ENABLE_DEBUG_FILES = os.getenv("ENABLE_DEBUG_FILES", "false").lower() == "true"
    DEBUG_DIR = BASE_DIR / "debug_output"

    # Rate limiting (disable in tests to avoid interference)
    ENABLE_RATE_LIMITING = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"

    def __init__(self):
        """Ensure data directories exist"""
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.USER_DATA_DIR.mkdir(exist_ok=True)
        self.REFERENCE_DIR.mkdir(exist_ok=True)

# Global settings instance
settings = Settings()
