"""
Application Manager Service

Handles semi-automated job application management:
- Pre-fills application forms with user profile data and tailored resume data
- Creates applications in 'draft' status
- Presents all pre-filled fields for user review
- CRITICAL: No auto-submit — user must explicitly confirm via confirm_application()
- Tracks status: draft → submitted → rejected/interview/offer
- Persists all application data to SQLite
"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.models import Application, JobPosting, TailoredResume


# Valid status values and allowed transitions
VALID_STATUSES = {"draft", "submitted", "rejected", "interview", "offer"}

# Status transitions: from_status -> set of allowed to_statuses
# NOTE: There is NO transition that bypasses the explicit confirm step.
# The only way to reach "submitted" is via confirm_application().
ALLOWED_TRANSITIONS = {
    "draft": {"submitted"},       # Only via confirm_application()
    "submitted": {"rejected", "interview", "offer"},
    "interview": {"rejected", "offer"},
    "rejected": set(),            # Terminal state
    "offer": {"rejected"},        # Can still be rejected after offer
}


def _build_prefilled_data(
    job_posting: Optional[JobPosting],
    tailored_resume: Optional[TailoredResume],
    user_profile: Optional[dict] = None,
) -> dict:
    """
    Build pre-filled application form data from available sources.

    Combines data from the job posting, tailored resume, and user profile
    into a structured dictionary suitable for form pre-filling.
    """
    prefilled = {
        "company": "",
        "job_title": "",
        "job_url": "",
        "location": "",
        "applicant_name": "",
        "applicant_email": "",
        "applicant_phone": "",
        "applicant_summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "cover_letter_draft": "",
        "additional_notes": "",
    }

    # Fill from job posting
    if job_posting:
        prefilled["company"] = job_posting.company or ""
        prefilled["job_title"] = job_posting.title or ""
        prefilled["job_url"] = job_posting.url or ""
        prefilled["location"] = job_posting.location or ""

    # Fill from tailored resume (parsed JSON content)
    if tailored_resume and tailored_resume.tailored_data:
        raw = tailored_resume.tailored_data
        content = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(content, dict):
            prefilled["skills"] = content.get("skills", [])
            prefilled["experience"] = content.get("experience", [])
            prefilled["education"] = content.get("education", [])
            prefilled["applicant_summary"] = content.get("summary", "")
            # Extract contact info from resume if present
            contact = content.get("contact", {})
            if isinstance(contact, dict):
                prefilled["applicant_name"] = contact.get("name", "")
                prefilled["applicant_email"] = contact.get("email", "")
                prefilled["applicant_phone"] = contact.get("phone", "")

    # Override with explicit user profile data if provided
    if user_profile and isinstance(user_profile, dict):
        for key in ["applicant_name", "applicant_email", "applicant_phone"]:
            if key in user_profile and user_profile[key]:
                prefilled[key] = user_profile[key]

    return prefilled


def create_application(
    db: Session,
    job_posting_id: int,
    tailored_resume_id: Optional[int] = None,
    user_profile: Optional[dict] = None,
    notes: Optional[str] = None,
) -> Application:
    """
    Create a new application in 'draft' status with pre-filled data.

    The application is NEVER auto-submitted. It starts as 'draft' and
    the user must explicitly call confirm_application() to submit.

    Args:
        db: Database session
        job_posting_id: ID of the target job posting
        tailored_resume_id: Optional ID of a tailored resume to use
        user_profile: Optional dict with user contact info
        notes: Optional notes for the application

    Returns:
        The created Application object in 'draft' status
    """
    # Fetch related objects
    job_posting = db.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
    if not job_posting:
        raise ValueError(f"Job posting with id {job_posting_id} not found")

    tailored_resume = None
    if tailored_resume_id:
        tailored_resume = (
            db.query(TailoredResume)
            .filter(TailoredResume.id == tailored_resume_id)
            .first()
        )

    # Build pre-filled data
    prefilled_data = _build_prefilled_data(job_posting, tailored_resume, user_profile)

    # Create the application — always starts as 'draft'
    application = Application(
        job_posting_id=job_posting_id,
        tailored_resume_id=tailored_resume_id,
        status="draft",  # ALWAYS draft — never auto-submitted
        prefilled_data=prefilled_data,
        notes=notes or "",
        submitted_at=None,  # Not submitted yet
    )

    db.add(application)
    db.commit()
    db.refresh(application)

    return application


def get_application(db: Session, application_id: int) -> Optional[Application]:
    """Get a single application by ID."""
    return db.query(Application).filter(Application.id == application_id).first()


def list_applications(
    db: Session,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
) -> list:
    """
    List applications, optionally filtered by status.

    Args:
        db: Database session
        status: Optional status filter (draft, submitted, rejected, interview, offer)
        skip: Number of records to skip for pagination
        limit: Maximum number of records to return

    Returns:
        List of Application objects
    """
    query = db.query(Application)
    if status:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'. Must be one of: {VALID_STATUSES}")
        query = query.filter(Application.status == status)
    return query.offset(skip).limit(limit).all()


def update_application(
    db: Session,
    application_id: int,
    updates: dict,
) -> Application:
    """
    Update application fields before submission.

    Only applications in 'draft' status can have their pre-filled data modified.
    This does NOT change the status — that requires explicit confirm or status update.

    Args:
        db: Database session
        application_id: ID of the application to update
        updates: Dictionary of fields to update in the prefilled_data

    Returns:
        The updated Application object
    """
    application = get_application(db, application_id)
    if not application:
        raise ValueError(f"Application with id {application_id} not found")

    if application.status != "draft":
        raise ValueError(
            f"Cannot modify application in '{application.status}' status. "
            "Only 'draft' applications can be edited."
        )

    # Update prefilled_data fields
    current_data = application.prefilled_data or {}
    if isinstance(current_data, dict) and isinstance(updates, dict):
        current_data.update(updates)
        application.prefilled_data = current_data

    # Update notes if provided
    if "notes" in updates:
        application.notes = updates.pop("notes", application.notes)

    db.commit()
    db.refresh(application)

    return application


def confirm_application(db: Session, application_id: int) -> Application:
    """
    Explicitly confirm and submit an application.

    This is the ONLY way to transition an application from 'draft' to 'submitted'.
    There is NO auto-submit path. The user must explicitly call this function.

    Args:
        db: Database session
        application_id: ID of the application to confirm

    Returns:
        The confirmed Application object with status='submitted'

    Raises:
        ValueError: If the application is not in 'draft' status
    """
    application = get_application(db, application_id)
    if not application:
        raise ValueError(f"Application with id {application_id} not found")

    if application.status != "draft":
        raise ValueError(
            f"Cannot confirm application in '{application.status}' status. "
            "Only 'draft' applications can be confirmed for submission."
        )

    # Transition to submitted — this is the only path to 'submitted'
    application.status = "submitted"
    application.submitted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(application)

    return application


def update_application_status(
    db: Session,
    application_id: int,
    new_status: str,
) -> Application:
    """
    Update the status of an application (for post-submission tracking).

    Valid transitions:
    - submitted → rejected, interview, offer
    - interview → rejected, offer
    - offer → rejected

    NOTE: draft → submitted is NOT allowed here.
    Use confirm_application() for that transition.

    Args:
        db: Database session
        application_id: ID of the application
        new_status: The new status to set

    Returns:
        The updated Application object
    """
    application = get_application(db, application_id)
    if not application:
        raise ValueError(f"Application with id {application_id} not found")

    if new_status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{new_status}'. Must be one of: {VALID_STATUSES}")

    current_status = application.status

    # CRITICAL: draft → submitted can ONLY happen via confirm_application()
    if current_status == "draft" and new_status == "submitted":
        raise ValueError(
            "Cannot change status from 'draft' to 'submitted' via status update. "
            "Use the confirm endpoint to explicitly submit the application."
        )

    allowed = ALLOWED_TRANSITIONS.get(current_status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Cannot transition from '{current_status}' to '{new_status}'. "
            f"Allowed transitions from '{current_status}': {allowed or 'none (terminal state)'}"
        )

    application.status = new_status
    application.status_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(application)

    return application


def delete_application(db: Session, application_id: int) -> bool:
    """
    Delete an application.

    Args:
        db: Database session
        application_id: ID of the application to delete

    Returns:
        True if deleted, False if not found
    """
    application = get_application(db, application_id)
    if not application:
        return False

    db.delete(application)
    db.commit()
    return True


def get_dashboard_summary(db: Session) -> dict:
    """
    Get a dashboard summary with counts by status, timeline, and success rates.
    """
    status_counts_raw = (
        db.query(Application.status, func.count(Application.id))
        .group_by(Application.status)
        .all()
    )
    status_counts = {status: count for status, count in status_counts_raw}
    for status in VALID_STATUSES:
        if status not in status_counts:
            status_counts[status] = 0
    total = sum(status_counts.values())

    recent = (
        db.query(Application)
        .order_by(Application.id.desc())
        .limit(10)
        .all()
    )
    
    all_apps = db.query(Application).all()
    timeline_data = {}
    company_stats = {}
    for app in all_apps:
        date_str = app.created_at.strftime("%Y-%m-%d")
        timeline_data[date_str] = timeline_data.get(date_str, 0) + 1
        
        company = (app.job_posting.company if app.job_posting else None) or "Unknown"
        if company not in company_stats:
            company_stats[company] = {"total": 0, "success": 0}
        company_stats[company]["total"] += 1
        if app.status in ("interview", "offer"):
            company_stats[company]["success"] += 1
            
    timeline = [{"date": k, "count": v} for k, v in sorted(timeline_data.items())]
    success_rates = [
        {"company": k, "rate": round((v["success"] / v["total"] * 100), 1)}
        for k, v in company_stats.items()
    ]

    return {
        "status_counts": status_counts,
        "total": total,
        "recent_applications": recent,
        "timeline": timeline,
        "success_rates": success_rates,
    }
