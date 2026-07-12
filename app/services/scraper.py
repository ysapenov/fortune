"""Job scraping service.

Since the application runs in CODE_ONLY mode (no external network access),
this module provides a realistic *simulation* of career-page scraping.
It reads the target companies from ``companies.csv``, constructs plausible
job postings with realistic titles, descriptions, and URLs, and stores them
in the database with full deduplication and filtering support.

When network access becomes available the ``_fetch_careers_page`` method
can be swapped to perform real HTTP requests.
"""

import csv
import hashlib
import json
import logging
import random
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy.orm import Session

from app.config import COMPANIES_CSV_PATH
from app.services.keyword_matcher import extract_keywords
from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Realistic data used to construct simulated postings
# ---------------------------------------------------------------------------

_ROLE_TEMPLATES: List[Dict[str, Any]] = [
    {
        "title": "Senior Software Engineer",
        "keywords": ["python", "java", "microservices", "aws", "docker", "kubernetes", "ci/cd", "rest", "sql"],
        "description_template": (
            "We are looking for a Senior Software Engineer to join our {team} team at {company}. "
            "You will design and build scalable {domain} services, collaborate with cross-functional "
            "teams, and mentor junior engineers.\n\n"
            "Requirements:\n"
            "- 5+ years of experience in software development\n"
            "- Proficiency in Python, Java, or Go\n"
            "- Experience with microservices architecture and RESTful APIs\n"
            "- Familiarity with AWS/GCP/Azure cloud platforms\n"
            "- Strong understanding of Docker and Kubernetes\n"
            "- Experience with CI/CD pipelines (Jenkins, GitHub Actions)\n"
            "- Solid knowledge of SQL and NoSQL databases\n"
            "- Excellent problem-solving and communication skills"
        ),
    },
    {
        "title": "Machine Learning Engineer",
        "keywords": ["python", "machine learning", "deep learning", "tensorflow", "pytorch", "sql", "aws", "docker"],
        "description_template": (
            "{company} is hiring a Machine Learning Engineer for our {team} team. "
            "You will develop and deploy ML models that power {domain} features used by "
            "millions of users.\n\n"
            "Requirements:\n"
            "- MS or PhD in Computer Science, Statistics, or related field\n"
            "- 3+ years building production ML systems\n"
            "- Expert-level Python and SQL skills\n"
            "- Experience with TensorFlow, PyTorch, or scikit-learn\n"
            "- Knowledge of deep learning, NLP, or computer vision\n"
            "- Familiarity with cloud-based ML pipelines (AWS SageMaker, GCP Vertex AI)\n"
            "- Docker and Kubernetes experience is a plus"
        ),
    },
    {
        "title": "Frontend Developer",
        "keywords": ["javascript", "typescript", "react", "html", "css", "redux", "git", "agile", "rest"],
        "description_template": (
            "Join {company}'s {team} team as a Frontend Developer. Build beautiful, "
            "performant user interfaces for our {domain} platform.\n\n"
            "Requirements:\n"
            "- 3+ years of frontend development experience\n"
            "- Strong JavaScript and TypeScript skills\n"
            "- Experience with React (or Angular/Vue)\n"
            "- Proficiency in HTML5 and CSS3\n"
            "- Knowledge of state management (Redux, MobX)\n"
            "- Familiarity with RESTful APIs and GraphQL\n"
            "- Experience with Git and Agile methodologies\n"
            "- Eye for design and attention to detail"
        ),
    },
    {
        "title": "DevOps Engineer",
        "keywords": ["linux", "docker", "kubernetes", "terraform", "aws", "ci/cd", "python", "bash", "monitoring"],
        "description_template": (
            "{company}'s {team} team is seeking a DevOps Engineer to build and maintain "
            "our {domain} infrastructure.\n\n"
            "Requirements:\n"
            "- 4+ years of DevOps/SRE experience\n"
            "- Deep Linux systems administration knowledge\n"
            "- Expert with Docker and Kubernetes orchestration\n"
            "- Infrastructure-as-Code experience (Terraform, CloudFormation)\n"
            "- AWS or GCP cloud platform expertise\n"
            "- CI/CD pipeline design (Jenkins, GitLab CI, GitHub Actions)\n"
            "- Scripting with Python and Bash\n"
            "- Monitoring tools: Prometheus, Grafana, Datadog"
        ),
    },
    {
        "title": "Data Engineer",
        "keywords": ["python", "sql", "spark", "airflow", "aws", "etl", "data pipeline", "postgresql", "docker"],
        "description_template": (
            "{company} is looking for a Data Engineer to join our {team} team. "
            "Design and operate data pipelines powering {domain} analytics.\n\n"
            "Requirements:\n"
            "- 3+ years of data engineering experience\n"
            "- Strong Python and SQL skills\n"
            "- Experience with Apache Spark, Airflow, or similar\n"
            "- Knowledge of ETL/ELT design patterns\n"
            "- Familiarity with cloud data warehouses (Snowflake, BigQuery, Redshift)\n"
            "- PostgreSQL or MySQL administration\n"
            "- Docker and container orchestration\n"
            "- Experience with data quality and governance frameworks"
        ),
    },
    {
        "title": "Backend Engineer",
        "keywords": ["python", "go", "rest", "postgresql", "redis", "docker", "kubernetes", "git", "microservices"],
        "description_template": (
            "Join {company} as a Backend Engineer on the {team} team. "
            "Architect and implement high-throughput {domain} services.\n\n"
            "Requirements:\n"
            "- 3+ years backend development experience\n"
            "- Proficiency in Python, Go, or Java\n"
            "- RESTful API design and implementation\n"
            "- PostgreSQL or similar relational databases\n"
            "- Redis caching layer experience\n"
            "- Docker and Kubernetes\n"
            "- Microservices architecture and event-driven design\n"
            "- Git-based version control workflows"
        ),
    },
    {
        "title": "Security Engineer",
        "keywords": ["security", "cybersecurity", "python", "linux", "aws", "iam", "encryption", "devsecops"],
        "description_template": (
            "{company}'s {team} team is hiring a Security Engineer to protect "
            "our {domain} infrastructure and customer data.\n\n"
            "Requirements:\n"
            "- 4+ years of cybersecurity experience\n"
            "- Expertise in cloud security (AWS, GCP, Azure)\n"
            "- IAM policies and zero-trust architecture\n"
            "- Vulnerability assessment and penetration testing\n"
            "- DevSecOps practices and tooling\n"
            "- Python scripting for security automation\n"
            "- Linux administration and hardening\n"
            "- Encryption and key management"
        ),
    },
    {
        "title": "Full Stack Engineer",
        "keywords": ["javascript", "typescript", "react", "node.js", "python", "postgresql", "docker", "git", "aws"],
        "description_template": (
            "{company} is hiring a Full Stack Engineer for the {team} team to build "
            "end-to-end {domain} features.\n\n"
            "Requirements:\n"
            "- 4+ years full-stack development experience\n"
            "- Frontend: JavaScript/TypeScript, React\n"
            "- Backend: Node.js or Python\n"
            "- Database: PostgreSQL, MongoDB, or similar\n"
            "- Cloud deployment (AWS/GCP)\n"
            "- Docker and CI/CD\n"
            "- Git and Agile practices\n"
            "- Strong communication and collaboration skills"
        ),
    },
    {
        "title": "Product Manager - Technical",
        "keywords": ["agile", "scrum", "jira", "sql", "api", "confluence", "git"],
        "description_template": (
            "{company} is seeking a Technical Product Manager to drive the {domain} "
            "product roadmap on the {team} team.\n\n"
            "Requirements:\n"
            "- 5+ years of product management in tech\n"
            "- Strong technical background (CS degree or equivalent)\n"
            "- Agile/Scrum methodology expertise\n"
            "- Data-driven decision making with SQL skills\n"
            "- Experience with API-first product development\n"
            "- Proficiency with Jira, Confluence\n"
            "- Excellent stakeholder communication skills\n"
            "- Understanding of Git workflows and CI/CD"
        ),
    },
    {
        "title": "Site Reliability Engineer",
        "keywords": ["linux", "kubernetes", "docker", "terraform", "python", "monitoring", "prometheus", "grafana", "aws"],
        "description_template": (
            "Join {company}'s SRE team to ensure the reliability of our {domain} "
            "platform. You will work closely with {team} engineers to build resilient "
            "systems.\n\n"
            "Requirements:\n"
            "- 4+ years SRE or DevOps experience\n"
            "- Expert Linux administration\n"
            "- Kubernetes cluster management\n"
            "- Terraform infrastructure-as-code\n"
            "- Python automation scripting\n"
            "- Monitoring: Prometheus, Grafana, PagerDuty\n"
            "- AWS or GCP cloud expertise\n"
            "- Incident response and postmortem culture"
        ),
    },
    {
        "title": "Cloud Solutions Architect",
        "keywords": ["aws", "azure", "gcp", "terraform", "kubernetes", "docker", "networking", "security", "python"],
        "description_template": (
            "{company} is looking for a Cloud Solutions Architect to design and implement "
            "cloud-native architectures for {domain} on the {team} team.\n\n"
            "Requirements:\n"
            "- 6+ years of cloud architecture experience\n"
            "- Multi-cloud expertise (AWS, Azure, GCP)\n"
            "- Terraform and infrastructure-as-code\n"
            "- Kubernetes and container orchestration\n"
            "- Networking: VPC, DNS, load balancing, CDN\n"
            "- Security best practices and compliance\n"
            "- Python or Go scripting\n"
            "- AWS Solutions Architect Professional or equivalent certification"
        ),
    },
    {
        "title": "QA Automation Engineer",
        "keywords": ["python", "javascript", "git", "ci/cd", "selenium", "rest", "agile", "sql", "docker"],
        "description_template": (
            "{company}'s {team} team needs a QA Automation Engineer to build and "
            "maintain testing frameworks for {domain} products.\n\n"
            "Requirements:\n"
            "- 3+ years of QA automation experience\n"
            "- Python or JavaScript test frameworks\n"
            "- Selenium, Playwright, or Cypress\n"
            "- REST API testing\n"
            "- CI/CD integration for test suites\n"
            "- SQL for data validation\n"
            "- Git version control\n"
            "- Agile/Scrum team experience"
        ),
    },
]

_TEAMS = [
    "Platform", "Infrastructure", "Core", "Growth", "Enterprise",
    "Data", "AI/ML", "Security", "Product", "Cloud", "Mobile",
    "Developer Experience", "Reliability", "Analytics",
]

_DOMAINS = [
    "cloud computing", "data analytics", "cybersecurity", "enterprise SaaS",
    "AI/ML", "developer tools", "networking", "e-commerce", "fintech",
    "healthcare tech", "identity management", "observability",
]

_LOCATIONS = [
    "San Francisco, CA", "New York, NY", "Seattle, WA", "Austin, TX",
    "Denver, CO", "Remote", "Boston, MA", "Chicago, IL",
    "San Jose, CA", "Raleigh, NC", "Portland, OR", "Remote - US",
    "Bangalore, India", "London, UK", "Toronto, Canada",
]

_SENIORITY_PREFIXES = ["", "Senior ", "Staff ", "Principal ", "Lead ", "Junior "]


def _company_slug(name: str) -> str:
    """Convert company name to a URL-friendly slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def _build_career_url(company_name: str, job_title: str, job_id: int) -> str:
    """Construct a realistic career-page URL for a company."""
    slug = _company_slug(company_name)
    title_slug = _company_slug(job_title)
    return f"https://{slug}.com/careers/{title_slug}-{job_id}"


def _dedup_key(company: str, title: str, url: str) -> str:
    """Create a deduplication hash from company + title + url."""
    raw = f"{company.lower().strip()}|{title.lower().strip()}|{url.lower().strip()}"
    return hashlib.sha256(raw.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Main scraper class
# ---------------------------------------------------------------------------

class JobScraper:
    """Scrapes (or simulates scraping) career pages for target companies.

    Parameters
    ----------
    companies_csv_path:
        Path to ``companies.csv``.  Defaults to the project-level file.
    """

    def __init__(self, companies_csv_path: Optional[str] = None):
        self.companies_csv_path = companies_csv_path or COMPANIES_CSV_PATH
        self._companies: Optional[List[str]] = None
        self._seen_hashes: set[str] = set()
        self._last_scraped: dict[str, datetime] = {}

    # -- company loading -----------------------------------------------------

    def load_companies(self) -> List[str]:
        """Read company names from the CSV file."""
        if self._companies is not None:
            return self._companies

        path = Path(self.companies_csv_path)
        if not path.exists():
            logger.warning("Companies CSV not found at %s", path)
            self._companies = []
            return self._companies

        companies: List[str] = []
        with open(path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                name = row.get("Name", "").strip()
                if name:
                    companies.append(name)
        self._companies = companies
        logger.info("Loaded %d companies from %s", len(companies), path)
        return self._companies

    # -- posting generation --------------------------------------------------

    def _search_jobs_for_company(
        self,
        company: str,
        job_type: str,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """Perform a real web search for jobs and parse with LLM."""
        import time
        import urllib.parse
        from playwright.sync_api import sync_playwright

        query_type = "internship" if job_type.lower() == "internship" else "software engineer"
        query = f'"{company}" {query_type} careers'
        
        logger.info(f"Searching Yahoo with Playwright for: {query}")
        
        raw_results = []
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-dev-shm-usage'])
                page = browser.new_page(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
                
                safe_query = urllib.parse.quote(query)
                page.goto(f"https://search.yahoo.com/search?p={safe_query}")
                
                # Accept cookies if Yahoo asks
                try:
                    if page.locator("button.agree, button[name='agree']").count() > 0:
                        page.locator("button.agree, button[name='agree']").first.click()
                except:
                    pass
                
                page.wait_for_timeout(2000) # Let the DOM settle
                
                # Extract results
                results = page.locator("div.algo").all()
                for r in results[:15]:
                    a_loc = r.locator("a").first
                    title = ""
                    href = ""
                    
                    if a_loc.count() > 0:
                        href = a_loc.get_attribute("href")
                        h3 = r.locator("h3").first
                        title = h3.text_content() if h3.count() > 0 else a_loc.text_content()
                        
                    body = r.text_content()
                    
                    if title or href:
                        raw_results.append({
                            "title": title,
                            "href": href,
                            "body": body
                        })
                browser.close()
                print(f"RAW YAHOO RESULTS: {raw_results}")
        except Exception as e:
            logger.error(f"Playwright search failed for {company}: {e}")
            return []

        if not raw_results:
            return []

        # Pass raw results to LLM to extract structured postings
        extracted_jobs = llm_client.extract_jobs_from_search(company, raw_results, job_type)
        
        postings = []
        for job in extracted_jobs[:max_results]:
            postings.append({
                "company": company,
                "title": job.get("title", "Unknown Title"),
                "url": job.get("url", ""),
                "location": job.get("location", "Unknown"),
                "description": job.get("description", ""),
                "date_posted": datetime.now(timezone.utc),
                "keywords": json.dumps(job.get("keywords", [])),
                "source": "playwright_search",
            })
            
        time.sleep(1)  # Be polite — avoid hammering Yahoo Search
        return postings

    # -- deduplication -------------------------------------------------------

    def is_duplicate(self, posting: Dict[str, Any]) -> bool:
        """Return True if this posting was already seen."""
        key = _dedup_key(
            posting["company"], posting["title"], posting["url"]
        )
        if key in self._seen_hashes:
            return True
        self._seen_hashes.add(key)
        return False

    def is_duplicate_in_db(self, posting: Dict[str, Any], db: Session) -> bool:
        """Check the database for an existing identical posting."""
        from app.models.models import JobPosting

        existing = (
            db.query(JobPosting)
            .filter(
                JobPosting.company == posting["company"],
                JobPosting.title == posting["title"],
                JobPosting.url == posting["url"],
            )
            .first()
        )
        return existing is not None

    # -- scrape orchestration ------------------------------------------------

    def scrape(
        self,
        db: Session,
        *,
        companies: Optional[List[str]] = None,
        job_type: str = "permanent",
        max_per_company: int = 3,
    ) -> List[Dict[str, Any]]:
        """Scrape postings and persist new ones to the database.

        Parameters
        ----------
        db:
            SQLAlchemy session.
        companies:
            Optional subset of companies to scrape.  Defaults to all.
        job_type:
            Type of job ('permanent' or 'internship').
        max_per_company:
            Max results to request per company.

        Returns
        -------
        list of dicts representing newly inserted postings.
        """
        from app.models.models import JobPosting

        target_companies = companies or self.load_companies()
        new_postings: List[Dict[str, Any]] = []

        for company in target_companies:
            # Skip if we successfully scraped this company in the last 1 hour
            last_time = self._last_scraped.get(company)
            if last_time and (datetime.now() - last_time) < timedelta(hours=1):
                logger.info("Skipping %s (already scraped within last hour)", company)
                continue

            try:
                raw = self._search_jobs_for_company(
                    company, job_type=job_type, max_results=max_per_company
                )
                for posting_data in raw:
                    if self.is_duplicate(posting_data):
                        logger.debug("Skipping duplicate: %s @ %s", posting_data["title"], company)
                        continue
                    if self.is_duplicate_in_db(posting_data, db):
                        logger.debug("Already in DB: %s @ %s", posting_data["title"], company)
                        continue

                    posting = JobPosting(
                        company=posting_data["company"],
                        title=posting_data["title"],
                        url=posting_data["url"],
                        location=posting_data["location"],
                        description=posting_data["description"],
                        date_posted=posting_data["date_posted"],
                        keywords=posting_data["keywords"],
                        is_active=True,
                        source=posting_data["source"],
                    )
                    db.add(posting)
                    new_postings.append(posting_data)
                
                # Commit progress per company so we don't lose data on exceptions
                db.commit()
                self._last_scraped[company] = datetime.now()
            except Exception as e:
                error_msg = str(e).lower()
                logger.error(f"Error scraping {company}: {e}")
                if "quota" in error_msg or "429" in error_msg or "rate limit" in error_msg:
                    logger.warning("Rate limit reached. Stopping scrape loop and returning partial results.")
                    break
                # For other errors, skip this company and continue
                db.rollback()
                continue

        logger.info("Scraped %d new postings from %d companies", len(new_postings), len(target_companies))
        return new_postings

    # -- refresh (re-scrape) -------------------------------------------------

    def refresh(self, db: Session, *, companies: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Re-scrape postings.  Identical to ``scrape`` but resets seen hashes."""
        self._seen_hashes.clear()
        return self.scrape(db, companies=companies)

    # -- filtering -----------------------------------------------------------

    @staticmethod
    def filter_postings(
        db: Session,
        *,
        keyword: Optional[str] = None,
        location: Optional[str] = None,
        company: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        is_active: Optional[bool] = True,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        """Query persisted postings with filtering and pagination.

        Returns a dict with ``items``, ``total``, ``page``, ``page_size``.
        """
        from app.models.models import JobPosting

        query = db.query(JobPosting)

        if is_active is not None:
            query = query.filter(JobPosting.is_active == is_active)
        if keyword:
            kw_pattern = f"%{keyword}%"
            query = query.filter(
                (JobPosting.title.ilike(kw_pattern))
                | (JobPosting.description.ilike(kw_pattern))
                | (JobPosting.keywords.ilike(kw_pattern))
            )
        if location:
            query = query.filter(JobPosting.location.ilike(f"%{location}%"))
        if company:
            query = query.filter(JobPosting.company.ilike(f"%{company}%"))
        if date_from:
            query = query.filter(JobPosting.date_posted >= date_from)
        if date_to:
            query = query.filter(JobPosting.date_posted <= date_to)

        total = query.count()
        items = (
            query.order_by(JobPosting.date_posted.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
