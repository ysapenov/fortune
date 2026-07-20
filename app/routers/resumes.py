"""Resume upload, parsing, and optimization API endpoints."""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Resume, TailoredResume, JobPosting
from app.services.resume_parser import parse_resume
from app.services.resume_optimizer import optimize_resume

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

    model_config = ConfigDict(from_attributes=True)

class OptimizeRequest(BaseModel):
    job_posting_id: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=ResumeOut)
async def upload_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Upload a PDF or DOCX resume, parse it, and save to DB."""
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
def optimize_resume_for_job(resume_id: int, body: OptimizeRequest, db: Session = Depends(get_db)):
    """Generate a tailored resume optimized for a specific job posting."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")
        
    job = db.query(JobPosting).filter(JobPosting.id == body.job_posting_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
        
    parsed_data = json.loads(resume.parsed_data) if resume.parsed_data else {}
    
    optimized_data = optimize_resume(
        parsed_resume=parsed_data,
        job_description=job.description or "",
        job_title=job.title
    )
    
    # Export to PDF (mock path for now)
    # pdf_path = export_resume(optimized_data, format="pdf") 
    
    tailored = TailoredResume(
        resume_id=resume.id,
        job_posting_id=job.id,
        tailored_data=json.dumps(optimized_data),
        format="pdf"
    )
    db.add(tailored)
    db.commit()
    db.refresh(tailored)
    
    return TailoredResumeOut.model_validate(tailored)
