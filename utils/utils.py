"""
Utility functions for HTTP requests, logging, caching, and data processing.
"""

import os
import sys
import json
import logging
import time
import re
from typing import Dict, List, Any, Optional
from functools import wraps
from urllib.parse import urlparse
import requests

# Import config from modules folder (parent directory)
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.config import (
    SERPER_API_KEY, OPENROUTER_API_KEY, REQUEST_TIMEOUT,
    RETRY_ATTEMPTS, RETRY_DELAY, LOG_FORMAT, LOG_LEVEL,
    CACHE_DIR, OUTPUT_DIR, LOG_DIR
)

# ─────────────────────────────────────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────────────────────────────────────
def setup_logger(name: str) -> logging.Logger:
    """Setup logger with consistent formatting"""
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    
    # Stream handler
    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(LOG_LEVEL)
    stream_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(stream_handler)
    
    # File handler
    file_handler = logging.FileHandler(os.path.join(LOG_DIR, f"{name}.log"))
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(file_handler)
    
    return logger


logger = setup_logger("leads_pipeline")

# ─────────────────────────────────────────────────────────────────────────────
# Retry Decorator
# ─────────────────────────────────────────────────────────────────────────────
def retry_on_failure(max_attempts: int = RETRY_ATTEMPTS, delay: float = RETRY_DELAY):
    """Decorator to retry a function on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_attempts:
                        logger.error(f"Function {func.__name__} failed after {max_attempts} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. Retrying in {delay}s...")
                    time.sleep(delay)
        return wrapper
    return decorator


# ─────────────────────────────────────────────────────────────────────────────
# HTTP Session & Helpers
# ─────────────────────────────────────────────────────────────────────────────
SESSION = requests.Session()
SESSION.headers.update({
    "Connection": "close",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})


@retry_on_failure(max_attempts=3, delay=1)
def serper_search(query: str, num: int = 12) -> List[Dict]:
    """Search using Serper API"""
    if not SERPER_API_KEY:
        logger.error("SERPER_API_KEY not configured")
        return []
    
    try:
        response = SESSION.post(
            "https://google.serper.dev/search",
            headers={
                "X-API-KEY": SERPER_API_KEY,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": num},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json().get("organic", [])
    except Exception as e:
        logger.error(f"Serper search error for query '{query}': {e}")
        return []


@retry_on_failure(max_attempts=2, delay=1)
def llm_query(prompt: str, max_tokens: int = 1000, model: str = "meta-llama/llama-3.3-70b-instruct") -> str:
    """Query LLM via OpenRouter"""
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not configured")
        return ""
    
    try:
        response = SESSION.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.1,
            },
            timeout=REQUEST_TIMEOUT * 2,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.error(f"LLM query error: {e}")
        return ""


# ─────────────────────────────────────────────────────────────────────────────
# JSON Cleaning & Parsing
# ─────────────────────────────────────────────────────────────────────────────
def clean_json_text(text: str) -> str:
    """Remove markdown code blocks and extra whitespace from JSON"""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


def safe_json_loads(text: str, default: Any = None) -> Any:
    """Safely parse JSON with default fallback"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, ValueError) as e:
        logger.debug(f"JSON parse error: {e}")
        return default


# ─────────────────────────────────────────────────────────────────────────────
# Caching
# ─────────────────────────────────────────────────────────────────────────────
class Cache:
    """Simple file-based JSON cache"""
    
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._data = {}
        self.load()
    
    def load(self):
        """Load cache from file"""
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    self._data = json.load(f)
                logger.debug(f"Loaded cache: {self.filepath} ({len(self._data)} items)")
            except Exception as e:
                logger.warning(f"Failed to load cache {self.filepath}: {e}")
                self._data = {}
    
    def save(self):
        """Save cache to file"""
        os.makedirs(os.path.dirname(self.filepath) or ".", exist_ok=True)
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved cache: {self.filepath}")
        except Exception as e:
            logger.error(f"Failed to save cache {self.filepath}: {e}")
    
    def get(self, key: str, default=None):
        """Get item from cache"""
        return self._data.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set item in cache"""
        self._data[key] = value
    
    def has(self, key: str) -> bool:
        """Check if key exists"""
        return key in self._data
    
    def __len__(self):
        return len(self._data)


# ─────────────────────────────────────────────────────────────────────────────
# URL & Domain Processing
# ─────────────────────────────────────────────────────────────────────────────
def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    try:
        parsed = urlparse(url) if url.startswith("http") else urlparse(f"https://{url}")
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def normalize_domain(domain: str) -> str:
    """Normalize domain to lowercase"""
    domain = domain.lower().strip()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def make_url(domain: str, path: str = "/") -> str:
    """Create full URL from domain"""
    domain = domain.lower().strip()
    if not domain.startswith("http"):
        domain = f"https://{domain}"
    return domain.rstrip("/") + path.lstrip("/") if path != "/" else domain


# ─────────────────────────────────────────────────────────────────────────────
# Email Processing
# ─────────────────────────────────────────────────────────────────────────────
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def normalize_email(email: str) -> str:
    """Normalize email to lowercase"""
    return email.lower().strip()


def split_name(fullname: str) -> tuple:
    """Split name into first and last name"""
    # Remove titles and parenthetical content
    name = re.sub(r"\([^)]*\)", "", fullname)
    name = re.sub(r"[^\w\s-']", "", name)
    parts = [p.strip().lower() for p in name.split() if p.strip()]
    
    titles = {"mr", "ms", "mrs", "dr", "prof", "eng", "mba", "phd"}
    parts = [p for p in parts if p not in titles]
    
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[-1]


# ─────────────────────────────────────────────────────────────────────────────
# Text Processing
# ─────────────────────────────────────────────────────────────────────────────
def extract_emails_from_text(text: str) -> List[str]:
    """Extract email addresses from text"""
    pattern = r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"
    return list(set(re.findall(pattern, text)))


def extract_urls_from_text(text: str) -> List[str]:
    """Extract URLs from text"""
    pattern = r"https?://[^\s]+"
    urls = re.findall(pattern, text)
    return list(set(urls))


# ─────────────────────────────────────────────────────────────────────────────
# Deduplication
# ─────────────────────────────────────────────────────────────────────────────
def deduplicate_companies(companies: List) -> List:
    """Remove duplicate companies by name"""
    seen = set()
    unique = []
    for company in companies:
        name_key = company.company_name.lower().strip() if hasattr(company, 'company_name') else company.get('company_name', '').lower().strip()
        if name_key not in seen:
            seen.add(name_key)
            unique.append(company)
    return unique


def deduplicate_emails(emails: List[str]) -> List[str]:
    """Remove duplicate emails"""
    return list(set(normalize_email(e) for e in emails if validate_email(e)))
