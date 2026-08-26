"""Job search and scraping API endpoints."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import JobPosting
from app.services.scraper import JobScraper

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Shared scraper instance
_scraper = JobScraper()


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class JobPostingOut(BaseModel):
    """Schema for serialising a JobPosting to JSON."""

    id: int
    company: str
    title: str
    url: str
    location: Optional[str] = None
    description: Optional[str] = None
    date_posted: Optional[datetime] = None
    date_discovered: Optional[datetime] = None
    keywords: Optional[str] = None
    is_active: bool = True
    source: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedJobs(BaseModel):
    items: list[JobPostingOut]
    total: int
    page: int
    page_size: int


class ScrapeRequest(BaseModel):
    companies: Optional[list[str]] = Field(
        None, description="Specific companies to scrape.  None = all."
    )
    job_type: str = Field(
        "permanent", description="Type of job (permanent or internship)."
    )
    max_per_company: int = Field(3, ge=1, le=20)


class ScrapeResult(BaseModel):
    new_postings: int
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=PaginatedJobs)
def list_jobs(
    keyword: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    company: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all job postings with optional filtering and pagination."""
    result = JobScraper.filter_postings(
        db,
        keyword=keyword,
        location=location,
        company=company,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return PaginatedJobs(
        items=[JobPostingOut.model_validate(j) for j in result["items"]],
        total=result["total"],
        page=result["page"],
        page_size=result["page_size"],
    )


@router.post("/scrape", response_model=ScrapeResult)
def scrape_jobs(body: ScrapeRequest, db: Session = Depends(get_db)):
    """Trigger scraping for all or specific companies."""
    from app.services.vector_store import vector_store  # noqa: PLC0415

    try:
        new = _scraper.scrape(
            db,
            companies=body.companies,
            job_type=body.job_type,
            max_per_company=body.max_per_company,
        )
        # Auto-index new postings into the vector store.
        for posting in new:
            job_id = posting.get("id")
            if not job_id:
                continue
            text = f"{posting.get('title', '')}\n{posting.get('company', '')}\n{posting.get('description', '')}"
            meta = {
                "company": posting.get("company", "") or "",
                "title": posting.get("title", "") or "",
                "location": posting.get("location", "") or "",
            }
            try:
                vector_store.add_job_posting(job_id=job_id, text=text, metadata=meta)
            except Exception as ve:
                import logging  # noqa: PLC0415
                logging.getLogger(__name__).warning("VS index failed for job %s: %s", job_id, ve)

        return ScrapeResult(
            new_postings=len(new),
            message=f"Scraped {len(new)} new job postings.",
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "429" in error_msg or "rate limit" in error_msg:
            raise HTTPException(status_code=429, detail="LLM API Quota Exceeded. Please try again in 1 minute.")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}", response_model=JobPostingOut)
def get_job(job_id: int, db: Session = Depends(get_db)):
    """Retrieve a single job posting by ID."""
    posting = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not posting:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return JobPostingOut.model_validate(posting)


@router.post("/refresh", response_model=ScrapeResult)
def refresh_jobs(
    body: Optional[ScrapeRequest] = None,
    db: Session = Depends(get_db),
):
    """Refresh / re-scrape postings (resets dedup cache)."""
    companies = body.companies if body else None
    try:
        new = _scraper.refresh(db, companies=companies)
        return ScrapeResult(
            new_postings=len(new),
            message=f"Refreshed — {len(new)} new postings added.",
        )
    except Exception as e:
        error_msg = str(e).lower()
        if "quota" in error_msg or "429" in error_msg or "rate limit" in error_msg:
            raise HTTPException(status_code=429, detail="LLM API Quota Exceeded. Please try again in 1 minute.")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    """Delete a job posting."""
    posting = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not posting:
        raise HTTPException(status_code=404, detail="Job posting not found")
    
    # Remove vectors from ChromaDB if present
    try:
        from app.services.vector_store import vector_store
        vector_store.delete_job_posting(job_id)
    except Exception:
        pass

    db.delete(posting)
    db.commit()
    return {"message": "Job deleted successfully"}
