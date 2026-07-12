"""
Interview Preparation API Router

Endpoints for generating and managing interview preparation materials:
- Generate company research and role-specific questions
- View and list interview prep materials
- Export as PDF download
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import interview_prep
from app.services.pdf_export import export_interview_prep_pdf

router = APIRouter(prefix="/api/interviews", tags=["interviews"])


# ─── Request/Response Models ──────────────────────────────────────────────────

class InterviewPrepCreate(BaseModel):
    """Request body for generating interview prep materials."""
    company_name: str = Field(..., description="Name of the company")
    job_posting_id: Optional[int] = Field(
        None, description="Optional ID of a job posting for context"
    )
    job_title: Optional[str] = Field(
        "", description="Job title (used if no job_posting_id)"
    )
    job_description: Optional[str] = Field(
        "", description="Job description text (used if no job_posting_id)"
    )


class InterviewPrepResponse(BaseModel):
    """Response model for interview prep materials."""
    id: int
    job_posting_id: Optional[int] = None
    company_name: str
    research_summary: str
    questions: list
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _prep_to_dict(prep) -> dict:
    """Convert an InterviewPrep model to a response dictionary."""
    # questions and interesting_facts are stored as JSON strings in the DB
    try:
        questions = json.loads(prep.questions) if isinstance(prep.questions, str) else (prep.questions or [])
    except (json.JSONDecodeError, TypeError):
        questions = []
    return {
        "id": prep.id,
        "job_posting_id": prep.job_posting_id,
        "company_name": prep.company_name,
        "research_summary": prep.research_summary or "",
        "questions": questions,
        "created_at": str(prep.created_at) if prep.created_at else None,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/")
def list_interview_preps(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """List all interview preparation materials."""
    preps = interview_prep.list_interview_preps(db, skip=skip, limit=limit)
    return [_prep_to_dict(p) for p in preps]


@router.post("/generate", status_code=201)
def generate_interview_prep(
    body: InterviewPrepCreate,
    db: Session = Depends(get_db),
):
    """
    Generate interview preparation materials for a company/job posting.

    Generates:
    - Company research summary (description, products, news, culture, leadership)
    - Role-specific interview questions (technical, behavioral, company-specific)
    - Suggested answer frameworks for each question
    """
    try:
        prep = interview_prep.create_interview_prep(
            db,
            company_name=body.company_name,
            job_posting_id=body.job_posting_id,
            job_title=body.job_title or "",
            job_description=body.job_description or "",
        )
        return _prep_to_dict(prep)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{prep_id}")
def get_interview_prep(
    prep_id: int,
    db: Session = Depends(get_db),
):
    """Get interview prep detail."""
    prep = interview_prep.get_interview_prep(db, prep_id)
    if not prep:
        raise HTTPException(status_code=404, detail="Interview prep not found")
    return _prep_to_dict(prep)


@router.get("/{prep_id}/export")
def export_interview_prep(
    prep_id: int,
    db: Session = Depends(get_db),
):
    """
    Export interview prep materials as a PDF download.

    Returns a PDF file with professional formatting including:
    - Company name and role header
    - Research summary sections
    - Numbered questions with answer frameworks
    """
    prep = interview_prep.get_interview_prep(db, prep_id)
    if not prep:
        raise HTTPException(status_code=404, detail="Interview prep not found")

    # Generate company research data for richer PDF formatting
    research_data = interview_prep.generate_company_research(prep.company_name)

    # Determine job title from questions or use generic
    job_title = ""
    if prep.job_posting_id:
        from app.models.models import JobPosting
        job_posting = db.query(JobPosting).filter(
            JobPosting.id == prep.job_posting_id
        ).first()
        if job_posting:
            job_title = job_posting.title or ""

    if not job_title:
        job_title = "General Interview"

    # Parse questions from JSON string (stored as JSON in DB)
    try:
        questions = json.loads(prep.questions) if isinstance(prep.questions, str) else (prep.questions or [])
    except (json.JSONDecodeError, TypeError):
        questions = []

    pdf_bytes = export_interview_prep_pdf(
        company_name=prep.company_name,
        job_title=job_title,
        research_summary=prep.research_summary or "",
        questions=questions,
        research_data=research_data,
    )

    filename = f"interview_prep_{prep.company_name.lower().replace(' ', '_')}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.delete("/{prep_id}")
def delete_interview_prep(
    prep_id: int,
    db: Session = Depends(get_db),
):
    """Delete interview prep materials."""
    deleted = interview_prep.delete_interview_prep(db, prep_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Interview prep not found")
    return {"detail": "Interview prep deleted successfully"}
