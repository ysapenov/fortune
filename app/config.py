"""Application configuration."""

import os
from pathlib import Path


# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Database
# Ensure data directory exists
data_dir = BASE_DIR / "data"
data_dir.mkdir(exist_ok=True)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{data_dir / 'job_hunt_helper.db'}",
)

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


# Companies CSV path
COMPANIES_CSV_PATH = os.getenv(
    "COMPANIES_CSV_PATH",
    str(BASE_DIR / "data" / "companies.csv"),
)

# Scraper settings
SCRAPE_INTERVAL_MINUTES = int(os.getenv("SCRAPE_INTERVAL_MINUTES", "60"))

# Pagination defaults
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Resume storage directory
RESUME_STORAGE_DIR = os.getenv(
    "RESUME_STORAGE_DIR",
    str(BASE_DIR / "storage" / "resumes"),
)

# Tailored resume output directory
TAILORED_RESUME_DIR = os.getenv(
    "TAILORED_RESUME_DIR",
    str(BASE_DIR / "storage" / "tailored"),
)
