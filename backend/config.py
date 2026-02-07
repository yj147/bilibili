"""
Bili-Sentinel Backend Configuration
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = DATA_DIR / "exports"

# Ensure directories exist
DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# Database
DATABASE_PATH = DATA_DIR / "sentinel.db"

# Server config
HOST = os.getenv("SENTINEL_HOST", "0.0.0.0")
PORT = int(os.getenv("SENTINEL_PORT", "8000"))
DEBUG = os.getenv("SENTINEL_DEBUG", "true").lower() == "true"

# HTTP client settings
HTTP_TIMEOUT = float(os.getenv("SENTINEL_HTTP_TIMEOUT", "10.0"))
MAX_RETRIES = int(os.getenv("SENTINEL_MAX_RETRIES", "3"))

# Worker settings
WORKERS = int(os.getenv("SENTINEL_WORKERS", "1"))

# Anti-detection settings
MIN_DELAY = 2.0  # seconds
MAX_DELAY = 10.0  # seconds
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]
