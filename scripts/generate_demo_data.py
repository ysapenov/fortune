import sys
import os
from datetime import datetime, timedelta, timezone

# Add the project root to sys.path so we can import 'app'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, init_db
from app.models.models import JobPosting, Application, ApplicationStatus
import json
import random

# Ensure database tables exist
init_db()

db = SessionLocal()

# Dummy data components
companies = [
    "Google", "Amazon", "Microsoft", "Meta", "Apple", "Netflix", 
    "OpenAI", "Anthropic", "Palantir", "Databricks", "Snowflake", "Stripe"
]
job_titles = [
    "Software Engineer", "Senior Frontend Developer", "Backend Engineer",
    "Full Stack Developer", "Machine Learning Engineer", "Data Scientist",
    "DevOps Engineer", "Site Reliability Engineer", "Product Manager",
    "Staff Software Engineer", "Security Engineer", "Engineering Manager"
]
locations = ["San Francisco, CA", "New York, NY", "Seattle, WA", "Remote", "Austin, TX", "London, UK"]
statuses = list(ApplicationStatus)

def _random_date(days_back=30):
    return datetime.now(timezone.utc) - timedelta(days=random.randint(0, days_back), hours=random.randint(0, 23))

try:
    print("Generating demo data...")
    for i in range(12):
        company = random.choice(companies)
        title = random.choice(job_titles)
        location = random.choice(locations)
        
        # 1. Create a JobPosting
        job = JobPosting(
            company=company,
            title=title,
            url=f"https://{company.lower().replace(' ', '')}.com/careers/job-{random.randint(1000, 9999)}",
            location=location,
            description=f"This is a dummy job description for {title} at {company}.",
            date_posted=_random_date(60),
            date_discovered=_random_date(30),
            keywords=json.dumps(["Python", "FastAPI", "React", "Docker", "AWS"]),
            is_active=True,
            source="LinkedIn"
        )
        db.add(job)
        db.flush() # flush to get job.id

        # 2. Create an Application for it
        status = random.choice(statuses)
        submitted_date = None
        if status != ApplicationStatus.DRAFT:
            submitted_date = _random_date(20)
            
        app = Application(
            job_posting_id=job.id,
            status=status,
            submitted_at=submitted_date,
            created_at=_random_date(25),
            status_updated_at=_random_date(5),
            notes=f"Demo application for {company}."
        )
        db.add(app)
        
    db.commit()
    print("Successfully generated 12 dummy job postings and applications!")
except Exception as e:
    db.rollback()
    print(f"Error generating data: {e}")
finally:
    db.close()
