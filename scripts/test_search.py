import sys
import json
import logging
from app.services.scraper import JobScraper
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO)

db = SessionLocal()
scraper = JobScraper()
companies = scraper.load_companies()
if not companies:
    print("No companies loaded.")
    sys.exit(1)

company = companies[0]
print(f"Testing search for {company}...")
results = scraper._search_jobs_for_company(company, job_type="permanent", max_results=3)

print("Results:")
print(json.dumps(results, indent=2, default=str))
