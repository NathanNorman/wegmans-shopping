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

    # Data paths
    DATA_DIR = BASE_DIR / "data"
    CACHE_DIR = DATA_DIR / "cache"
    USER_DATA_DIR = DATA_DIR / "user"
    REFERENCE_DIR = DATA_DIR / "reference"

    # Static files (frontend directory)
    STATIC_DIR = BASE_DIR / "frontend"

    # Cache settings
    SEARCH_CACHE_DAYS = int(os.getenv("SEARCH_CACHE_DAYS", "7"))

    def __init__(self):
        """Ensure data directories exist"""
        self.DATA_DIR.mkdir(exist_ok=True)
        self.CACHE_DIR.mkdir(exist_ok=True)
        self.USER_DATA_DIR.mkdir(exist_ok=True)
        self.REFERENCE_DIR.mkdir(exist_ok=True)

# Global settings instance
settings = Settings()
