"""Resume upload, parsing, and optimization API endpoints."""

import json
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Resume, TailoredResume, JobPosting
from app.services.resume_parser import parse_resume
from app.services.resume_optimizer import optimize_resume, optimize_resume_with_rag
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class ResumeOut(BaseModel):
    id: int
    filename: str
    parsed_data: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class TailoredResumeOut(BaseModel):
    id: int
    resume_id: int
    job_posting_id: int
    tailored_data: Optional[str] = None
    file_path: Optional[str] = None
    semantic_analysis: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)

class OptimizeRequest(BaseModel):
    job_posting_id: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=ResumeOut)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a PDF or DOCX resume, parse it, save to DB, and index into vector store."""
    content = await file.read()

    try:
        parsed_data = parse_resume(content, file.filename)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {e}")

    resume = Resume(
        filename=file.filename,
        original_content=content,
        parsed_data=json.dumps(parsed_data)
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    # Index the new resume into the vector store for future similarity searches.
    try:
        from app.services.resume_optimizer import _flatten_resume_text  # noqa: PLC0415
        resume_text = _flatten_resume_text(parsed_data)
        if resume_text.strip():
            vector_store.add_resume(
                resume_id=resume.id,
                text=resume_text,
                metadata={"filename": file.filename or ""},
            )
    except Exception as exc:
        logger.warning("Vector store indexing failed for resume %d: %s", resume.id, exc)

    return ResumeOut.model_validate(resume)


@router.get("/", response_model=list[ResumeOut])
def list_resumes(db: Session = Depends(get_db)):
    """List all uploaded resumes."""
    resumes = db.query(Resume).order_by(Resume.created_at.desc()).all()
    return [ResumeOut.model_validate(r) for r in resumes]


@router.get("/{resume_id}", response_model=ResumeOut)
def get_resume(resume_id: int, db: Session = Depends(get_db)):
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
    return ResumeOut.model_validate(resume)


@router.post("/{resume_id}/optimize", response_model=TailoredResumeOut)
def optimize_resume_for_job(
    resume_id: int,
    body: OptimizeRequest,
    use_rag: bool = Query(True, description="Use RAG pipeline for optimization (recommended)."),
    db: Session = Depends(get_db),
):
    """Generate a tailored resume optimized for a specific job posting.

    When ``use_rag=true`` (default), the RAG pipeline retrieves ATS best-practice
    context and performs semantic gap analysis before calling the LLM. Set
    ``use_rag=false`` to use the direct LLM call (faster but less contextual).
    """
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    job = db.query(JobPosting).filter(JobPosting.id == body.job_posting_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    parsed_data = json.loads(resume.parsed_data) if resume.parsed_data else {}
    semantic_analysis: Optional[Dict[str, Any]] = None

    if use_rag:
        job_posting_dict = {
            "title": job.title or "",
            "company": job.company or "",
            "description": job.description or "",
        }
        result = optimize_resume_with_rag(
            parsed_resume=parsed_data,
            job_posting=job_posting_dict,
        )
        optimized_data = result.get("optimized_resume", parsed_data)
        semantic_analysis = result.get("semantic_analysis") or {}
    else:
        optimized_data = optimize_resume(
            parsed_resume=parsed_data,
            job_description=job.description or "",
            job_title=job.title,
        )

    tailored = TailoredResume(
        resume_id=resume.id,
        job_posting_id=job.id,
        tailored_data=json.dumps(optimized_data),
        format="pdf"
    )
    db.add(tailored)
    db.commit()
    db.refresh(tailored)

    out = TailoredResumeOut.model_validate(tailored)
    out.semantic_analysis = semantic_analysis
    return out

