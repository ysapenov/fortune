"""Frontend HTML routes."""

import json

from fastapi import APIRouter, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import JobPosting, Resume
from app.services.scraper import JobScraper

router = APIRouter(tags=["frontend"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/", response_class=HTMLResponse)
def index(request: Request, db: Session = Depends(get_db)):
    """Redirect root to jobs page."""
    result = JobScraper.filter_postings(db, page=1, page_size=50)
    return templates.TemplateResponse(
        request=request,
        name="jobs/list.html",
        context={"active_page": "jobs", "jobs": result["items"]},
    )


@router.get("/jobs", response_class=HTMLResponse)
def jobs_page(request: Request, db: Session = Depends(get_db)):
    """Render jobs list page."""
    result = JobScraper.filter_postings(db, page=1, page_size=50)
    return templates.TemplateResponse(
        request=request,
        name="jobs/list.html",
        context={"active_page": "jobs", "jobs": result["items"]},
    )


@router.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_detail_page(request: Request, job_id: int, db: Session = Depends(get_db)):
    """Render job detail page."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return templates.TemplateResponse(
        request=request,
        name="jobs/detail.html",
        context={"active_page": "jobs", "job": job},
    )


# ─── Resumes ─────────────────────────────────────────────────────────────────

@router.get("/resumes", response_class=HTMLResponse)
def resumes_page(request: Request, db: Session = Depends(get_db)):
    """Render resumes list page."""
    resumes = db.query(Resume).order_by(Resume.created_at.desc()).all()
    return templates.TemplateResponse(
        request=request,
        name="resumes/list.html",
        context={"active_page": "resumes", "resumes": resumes},
    )


@router.get("/resumes/{resume_id}", response_class=HTMLResponse)
def resume_detail_page(request: Request, resume_id: int, db: Session = Depends(get_db)):
    """Render resume detail page."""
    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    parsed = None
    if resume.parsed_data:
        parsed = (
            json.loads(resume.parsed_data)
            if isinstance(resume.parsed_data, str)
            else resume.parsed_data
        )

    jobs = (
        db.query(JobPosting)
        .filter(JobPosting.is_active == True)  # noqa: E712
        .order_by(JobPosting.date_posted.desc())
        .all()
    )

    return templates.TemplateResponse(
        request=request,
        name="resumes/detail.html",
        context={
            "active_page": "resumes",
            "resume": resume,
            "parsed": parsed,
            "jobs": jobs,
        },
    )


@router.get("/resumes/{resume_id}/optimize", response_class=HTMLResponse)
def optimize_resume_page(
    request: Request,
    resume_id: int,
    job_id: int = None,
    db: Session = Depends(get_db),
):
    """Run resume optimization and show results page."""
    import json as _json
    from app.models.models import TailoredResume
    from app.services.resume_optimizer import optimize_resume
    from app.services.resume_parser import parse_resume

    resume = db.query(Resume).filter(Resume.id == resume_id).first()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    job = None
    tailored = None

    if job_id:
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()

    if job and resume.parsed_data:
        # Check if we already have a tailored resume for this combo
        existing = (
            db.query(TailoredResume)
            .filter(
                TailoredResume.resume_id == resume_id,
                TailoredResume.job_posting_id == job_id,
            )
            .order_by(TailoredResume.id.desc())
            .first()
        )
        if existing:
            tailored = existing
        else:
            # Run optimization
            try:
                parsed = _json.loads(resume.parsed_data) if isinstance(resume.parsed_data, str) else resume.parsed_data
                optimized = optimize_resume(
                    parsed_resume=parsed,
                    job_description=job.description or "",
                    job_title=job.title,
                )
                tailored = TailoredResume(
                    resume_id=resume.id,
                    job_posting_id=job.id,
                    tailored_data=_json.dumps(optimized),
                    format="pdf",
                )
                db.add(tailored)
                db.commit()
                db.refresh(tailored)
            except Exception:
                pass  # tailored stays None; template shows fallback

    # Parse tailored_data for the template
    tailored_parsed = None
    if tailored and tailored.tailored_data:
        try:
            tailored_parsed = _json.loads(tailored.tailored_data) if isinstance(tailored.tailored_data, str) else tailored.tailored_data
        except Exception:
            tailored_parsed = None

    return templates.TemplateResponse(
        request=request,
        name="resumes/optimize.html",
        context={
            "active_page": "resumes",
            "resume": resume,
            "job": job,
            "tailored": tailored,
            "tailored_parsed": tailored_parsed,
        },
    )


# ─── Applications ─────────────────────────────────────────────────────────────

@router.get("/applications", response_class=HTMLResponse)
def applications_page(request: Request):
    """Render applications dashboard page."""
    return templates.TemplateResponse(
        request=request,
        name="applications/dashboard.html",
        context={"active_page": "applications"},
    )


@router.get("/applications/new", response_class=HTMLResponse)
def new_application_page(
    request: Request,
    job_id: int,
    db: Session = Depends(get_db),
):
    """Render the 'Apply to this Job' form page."""
    job = db.query(JobPosting).filter(JobPosting.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")

    resumes = db.query(Resume).order_by(Resume.created_at.desc()).all()

    return templates.TemplateResponse(
        request=request,
        name="applications/apply.html",
        context={"active_page": "applications", "job": job, "resumes": resumes},
    )


# ─── Interviews ───────────────────────────────────────────────────────────────

@router.get("/interviews", response_class=HTMLResponse)
def interviews_page(request: Request):
    """Render interview prep list/generate page."""
    return templates.TemplateResponse(
        request=request,
        name="interviews/list.html",
        context={"active_page": "interviews"},
    )


@router.get("/interviews/new", response_class=HTMLResponse)
def new_interview_prep_page(
    request: Request,
    job_id: int = None,
    company: str = "",
    db: Session = Depends(get_db),
):
    """
    Redirect to /interviews with the modal pre-filled via query params.
    We render the list page with pre-fill context so JS can open the modal.
    """
    job = None
    if job_id:
        job = db.query(JobPosting).filter(JobPosting.id == job_id).first()

    return templates.TemplateResponse(
        request=request,
        name="interviews/list.html",
        context={
            "active_page": "interviews",
            "prefill_company": company or (job.company if job else ""),
            "prefill_job_id": job_id or "",
            "prefill_title": job.title if job else "",
            "auto_open_modal": True,
        },
    )
