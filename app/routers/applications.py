"""
Application Management API Router

Endpoints for managing job applications:
- List, create, update, delete applications
- Explicit confirmation before submission (no auto-submit)
- Status tracking and dashboard summary
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from app.database import get_db
from app.services import application_manager

router = APIRouter(prefix="/api/applications", tags=["applications"])


# ─── Request/Response Models ──────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    """Request body for creating a new application."""
    job_posting_id: int
    tailored_resume_id: Optional[int] = None
    user_profile: Optional[dict] = None
    notes: Optional[str] = ""


class ApplicationUpdate(BaseModel):
    """Request body for updating application pre-filled fields."""
    updates: dict = Field(
        ...,
        description="Dictionary of fields to update in the pre-filled data"
    )


class StatusUpdate(BaseModel):
    """Request body for updating application status."""
    status: str = Field(
        ...,
        description="New status: rejected, interview, or offer"
    )


class ApplicationResponse(BaseModel):
    """Response model for a single application."""
    id: int
    job_posting_id: int
    tailored_resume_id: Optional[int] = None
    status: str
    prefilled_data: Optional[dict] = None
    submitted_at: Optional[str] = None
    notes: Optional[str] = ""

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    """Response model for the dashboard summary."""
    status_counts: dict
    total: int
    recent_applications: list
    timeline: list
    success_rates: list


# ─── Helper Functions ─────────────────────────────────────────────────────────

def _application_to_dict(app) -> dict:
    """Convert an Application model to a response dictionary."""
    return {
        "id": app.id,
        "job_posting_id": app.job_posting_id,
        "tailored_resume_id": app.tailored_resume_id,
        "status": app.status,
        "prefilled_data": app.prefilled_data,
        "submitted_at": str(app.submitted_at) if app.submitted_at else None,
        "notes": app.notes,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """
    Get the application dashboard summary.

    Returns status counts and recent activity.
    Must be defined before /{id} to avoid path conflicts.
    """
    summary = application_manager.get_dashboard_summary(db)
    return {
        "status_counts": summary["status_counts"],
        "total": summary["total"],
        "recent_applications": [
            _application_to_dict(app) for app in summary["recent_applications"]
        ],
        "timeline": summary.get("timeline", []),
        "success_rates": summary.get("success_rates", []),
    }


@router.get("/")
def list_applications(
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """
    List all applications with optional filtering by status.

    Query parameters:
    - status: Filter by draft, submitted, rejected, interview, or offer
    - skip: Number of records to skip (pagination)
    - limit: Maximum records to return
    """
    try:
        applications = application_manager.list_applications(
            db, status=status, skip=skip, limit=limit
        )
        return [_application_to_dict(app) for app in applications]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/", status_code=201)
def create_application(
    body: ApplicationCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new application in 'draft' status.

    The application is pre-filled with data from the job posting and
    optional tailored resume. It is NOT auto-submitted — the user
    must explicitly confirm via PUT /{id}/confirm.
    """
    try:
        app = application_manager.create_application(
            db,
            job_posting_id=body.job_posting_id,
            tailored_resume_id=body.tailored_resume_id,
            user_profile=body.user_profile,
            notes=body.notes,
        )
        return _application_to_dict(app)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{application_id}")
def get_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    """
    Get application detail with all pre-filled fields.

    Returns the full application including all pre-filled data
    for user review before confirmation.
    """
    app = application_manager.get_application(db, application_id)
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return _application_to_dict(app)


@router.put("/{application_id}")
def update_application(
    application_id: int,
    body: ApplicationUpdate,
    db: Session = Depends(get_db),
):
    """
    Update application fields before submission.

    Only applications in 'draft' status can be edited.
    Use this to modify pre-filled data before confirming.
    """
    try:
        app = application_manager.update_application(
            db, application_id, body.updates
        )
        return _application_to_dict(app)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{application_id}/confirm")
def confirm_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    """
    Explicitly confirm and submit an application.

    This is the ONLY way to submit an application. The application
    must be in 'draft' status. After confirmation, the status
    changes to 'submitted' and submitted_at is recorded.

    NO application is ever auto-submitted.
    """
    try:
        app = application_manager.confirm_application(db, application_id)
        return _application_to_dict(app)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{application_id}/status")
def update_status(
    application_id: int,
    body: StatusUpdate,
    db: Session = Depends(get_db),
):
    """
    Update application status for tracking.

    Valid transitions:
    - submitted → rejected, interview, offer
    - interview → rejected, offer
    - offer → rejected

    NOTE: draft → submitted is NOT allowed here.
    Use PUT /{id}/confirm instead.
    """
    try:
        app = application_manager.update_application_status(
            db, application_id, body.status
        )
        return _application_to_dict(app)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{application_id}")
def delete_application(
    application_id: int,
    db: Session = Depends(get_db),
):
    """Delete an application."""
    deleted = application_manager.delete_application(db, application_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Application not found")
    return {"detail": "Application deleted successfully"}
