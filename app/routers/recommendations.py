"""Recommendations API endpoints — vector similarity and indexing.

Prefix: /api/recommendations
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import JobPosting, Resume
from app.services.embedding_service import embedding_service
from app.services.rag_engine import rag_engine
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------


class JobRecommendation(BaseModel):
    job_id: Optional[int] = None
    similarity: float
    snippet: str
    company: Optional[str] = None
    title: Optional[str] = None
    location: Optional[str] = None
    url: Optional[str] = None


class IndexResult(BaseModel):
    indexed: int
    message: str


class StoreStatus(BaseModel):
    job_postings: int
    resume_chunks: int
    ats_knowledge: int
    chroma_db_path: str


# ---------------------------------------------------------------------------
# Helper to enrich recommendations with DB metadata
# ---------------------------------------------------------------------------


def _enrich_recommendations(
    raw: List[Dict[str, Any]], db: Session
) -> List[JobRecommendation]:
    """Attach DB-sourced job metadata to each similarity result."""
    enriched: List[JobRecommendation] = []
    for hit in raw:
        job_id = hit.get("job_id")
        job = None
        if job_id:
            job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
        enriched.append(
            JobRecommendation(
                job_id=job_id,
                similarity=hit.get("similarity", 0.0),
                snippet=hit.get("snippet", ""),
                company=job.company if job else None,
                title=job.title if job else None,
                location=job.location if job else None,
                url=job.url if job else None,
            )
        )
    return enriched


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/jobs/{resume_id}", response_model=List[JobRecommendation])
def recommend_jobs(
    resume_id: int,
    n: int = Query(10, ge=1, le=50, description="Number of recommendations."),
    company: Optional[str] = Query(None, description="Filter by company name."),
    db: Session = Depends(get_db),
) -> List[JobRecommendation]:
    """Return top-N job postings semantically matched to a resume.

    The resume must exist in the DB. Jobs are ranked by cosine similarity
    between their description embeddings and the resume embedding.
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    parsed = json.loads(resume.parsed_data) if resume.parsed_data else {}
    if not parsed:
        raise HTTPException(
            status_code=422,
            detail="Resume has no parsed data. Re-upload the resume.",
        )

    # Flatten resume to text for embedding
    from app.services.resume_optimizer import _flatten_resume_text  # noqa: PLC0415

    resume_text = _flatten_resume_text(parsed)
    if not resume_text.strip():
        raise HTTPException(status_code=422, detail="Resume text is empty.")

    filters: Optional[Dict[str, Any]] = {"company": company} if company else None

    raw = rag_engine.recommend_jobs_for_resume(
        resume_id=resume_id,
        resume_text=resume_text,
        n=n,
        filters=filters,
    )

    if not raw:
        return []

    return _enrich_recommendations(raw, db)


@router.get("/similar/{job_id}", response_model=List[JobRecommendation])
def find_similar_jobs(
    job_id: int,
    n: int = Query(5, ge=1, le=20, description="Number of similar jobs."),
    db: Session = Depends(get_db),
) -> List[JobRecommendation]:
    """Find job postings semantically similar to the given job.

    Useful for exploring related roles when browsing a job listing.
    """
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found.")

    job_text = f"{job.title}\n{job.company}\n{job.description or ''}"
    raw = rag_engine.find_similar_jobs(job_id=job_id, job_text=job_text, n=n)

    if not raw:
        return []

    return _enrich_recommendations(raw, db)


@router.post("/index/jobs", response_model=IndexResult)
def index_jobs(db: Session = Depends(get_db)) -> IndexResult:
    """(Re-)index all active job postings into the vector store.

    Idempotent — existing entries are replaced before re-indexing.
    """
    jobs = db.query(JobPosting).filter(JobPosting.is_active == True).all()  # noqa: E712
    total = 0
    for job in jobs:
        text = f"{job.title}\n{job.company}\n{job.description or ''}"
        meta = {
            "company": job.company or "",
            "title": job.title or "",
            "location": job.location or "",
        }
        chunks = vector_store.add_job_posting(job_id=job.id, text=text, metadata=meta)
        total += chunks

    return IndexResult(
        indexed=len(jobs),
        message=f"Indexed {len(jobs)} job postings ({total} total chunks) into the vector store.",
    )


@router.post("/index/resumes", response_model=IndexResult)
def index_resumes(db: Session = Depends(get_db)) -> IndexResult:
    """(Re-)index all resumes into the vector store."""
    from app.services.resume_optimizer import _flatten_resume_text  # noqa: PLC0415

    resumes = db.query(Resume).all()
    total = 0
    for resume in resumes:
        parsed = json.loads(resume.parsed_data) if resume.parsed_data else {}
        if not parsed:
            continue
        text = _flatten_resume_text(parsed)
        if not text.strip():
            continue
        meta = {"filename": resume.filename or ""}
        chunks = vector_store.add_resume(resume_id=resume.id, text=text, metadata=meta)
        total += chunks

    return IndexResult(
        indexed=len(resumes),
        message=f"Indexed {len(resumes)} resumes ({total} total chunks) into the vector store.",
    )


@router.get("/status", response_model=StoreStatus)
def vector_store_status() -> StoreStatus:
    """Return the current health and document counts of the vector store."""
    stats = vector_store.get_collection_stats()
    return StoreStatus(**stats)
