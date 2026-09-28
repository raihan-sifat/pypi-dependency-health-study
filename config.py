"""
Shared configuration, constants, and helper utilities for the study.
"""

import os
import time
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

import requests
from dotenv import load_dotenv

# ── Load environment variables ──────────────────────────────────────────────
load_dotenv()

# ── Paths ───────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"
FIGURES_DIR = PROJECT_ROOT / "figures"
PAPER_DIR = PROJECT_ROOT / "paper"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
FIGURES_DIR.mkdir(exist_ok=True)
PAPER_DIR.mkdir(exist_ok=True)

# ── Study parameters ───────────────────────────────────────────────────────
TOP_N_PACKAGES = 1000  # Number of top packages to analyse
ABANDONMENT_MONTHS = 18  # Months of inactivity → "silently abandoned"
AT_RISK_MONTHS = 12  # Months of inactivity → "at-risk"
SINGLE_MAINTAINER_COMMIT_THRESHOLD = 10  # Min commits in 24 months to count
LOOKBACK_MONTHS = 24  # Window for contributor activity analysis

# ── Derived dates ──────────────────────────────────────────────────────────
DATA_COLLECTION_DATE = datetime.now(timezone.utc)
ABANDONMENT_CUTOFF = DATA_COLLECTION_DATE - timedelta(days=ABANDONMENT_MONTHS * 30)
AT_RISK_CUTOFF = DATA_COLLECTION_DATE - timedelta(days=AT_RISK_MONTHS * 30)
CONTRIBUTOR_WINDOW_START = DATA_COLLECTION_DATE - timedelta(days=LOOKBACK_MONTHS * 30)

# ── API configuration ──────────────────────────────────────────────────────
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
PYPI_BASE_URL = "https://pypi.org/pypi"
GITHUB_API_URL = "https://api.github.com"
OSV_API_URL = "https://api.osv.dev/v1/query"
TOP_PACKAGES_URL = (
    "https://hugovk.github.io/top-pypi-packages/"
    "top-pypi-packages-30-days.min.json"
)

# ── HTTP session with default headers ──────────────────────────────────────
def get_github_session() -> requests.Session:
    """Return a requests session pre-configured for the GitHub API."""
    session = requests.Session()
    session.headers.update({
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    if GITHUB_TOKEN:
        session.headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return session


def get_default_session() -> requests.Session:
    """Return a plain requests session with a polite User-Agent."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": "pypi-dependency-health-study/1.0 "
                      "(research; github.com/raihan-sifat)"
    })
    return session


# ── Rate-limit-aware request helper ────────────────────────────────────────
def rate_limited_get(
    session: requests.Session,
    url: str,
    params: dict | None = None,
    max_retries: int = 3,
    backoff_base: float = 2.0,
) -> requests.Response | None:
    """
    GET *url* with automatic retry on 429 / 403 rate-limit responses.
    Returns None if all retries are exhausted.
    """
    for attempt in range(max_retries):
        try:
            resp = session.get(url, params=params, timeout=30)

            if resp.status_code == 200:
                return resp

            if resp.status_code in (429, 403):
                # GitHub sends rate-limit reset as a Unix timestamp
                reset = resp.headers.get("X-RateLimit-Reset")
                if reset:
                    wait = max(int(reset) - int(time.time()), 1) + 1
                else:
                    wait = backoff_base ** (attempt + 1)
                logging.warning(
                    "Rate-limited (%s) on %s — waiting %ds (attempt %d/%d)",
                    resp.status_code, url, wait, attempt + 1, max_retries,
                )
                time.sleep(wait)
                continue

            if resp.status_code == 404:
                return None  # Resource simply doesn't exist

            logging.warning(
                "Unexpected status %s for %s", resp.status_code, url
            )
            return None

        except requests.RequestException as exc:
            logging.warning("Request error for %s: %s", url, exc)
            time.sleep(backoff_base ** (attempt + 1))

    logging.error("All retries exhausted for %s", url)
    return None


# ── Logging ────────────────────────────────────────────────────────────────
def setup_logging(name: str = "study") -> logging.Logger:
    """Configure and return a logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s  %(levelname)-8s  %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

