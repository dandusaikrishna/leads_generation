import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (one level up in config_files folder)
env_path = Path(__file__).parent.parent / "config_files" / ".env"
if env_path.exists():
    load_dotenv(env_path)

# ─────────────────────────────────────────────────────────────────────────────
# API KEYS - Loaded from environment variables
# ─────────────────────────────────────────────────────────────────────────────
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# ─────────────────────────────────────────────────────────────────────────────
# REQUEST CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT = 30  # seconds
RETRY_ATTEMPTS = 3
RETRY_DELAY = 2  # seconds

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
LOG_FORMAT = "[%(asctime)s] %(levelname)s - %(name)s: %(message)s"

# ─────────────────────────────────────────────────────────────────────────────
# DIRECTORY CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # Go up to project root
OUTPUT_DIR = BASE_DIR / "output"
CACHE_DIR = BASE_DIR / ".cache"
LOG_DIR = BASE_DIR / "logs"

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
# EMAIL SCORING CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────
ROLE_SCORES = {
    "hr": {
        "base": 50,
        "found_bonus": 30,
        "keyword_bonus": 15,
    },
    "founder": {
        "base": 50,
        "found_bonus": 30,
        "keyword_bonus": 15,
    },
}
