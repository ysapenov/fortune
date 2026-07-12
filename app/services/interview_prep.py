"""
Interview Preparation Service

Generates interview preparation materials using the LLM client.
"""

import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session
from app.models.models import InterviewPrep, JobPosting
from app.services.llm_client import llm_client

def create_interview_prep(
    db: Session,
    company_name: str,
    job_posting_id: Optional[int] = None,
    job_title: str = "",
    job_description: str = "",
) -> InterviewPrep:
    """
    Generate and persist interview preparation materials.
    """
    if job_posting_id:
        job_posting = db.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
        if job_posting:
            if not job_title:
                job_title = job_posting.title or ""
            if not job_description:
                job_description = job_posting.description or ""
            if not company_name:
                company_name = job_posting.company or ""

    if not company_name:
        raise ValueError("Company name is required")

    # Generate structured prep from LLM
    prep_data = llm_client.prep_interview(company_name, job_description)

    # Persist
    prep = InterviewPrep(
        job_posting_id=job_posting_id,
        company_name=company_name,
        research_summary=prep_data.get("summary", ""),
        interesting_facts=json.dumps(prep_data.get("facts", [])),
        questions=json.dumps(prep_data.get("questions", [])),
        created_at=datetime.now(timezone.utc),
    )

    db.add(prep)
    db.commit()
    db.refresh(prep)

    return prep

def get_interview_prep(db: Session, prep_id: int) -> Optional[InterviewPrep]:
    return db.query(InterviewPrep).filter(InterviewPrep.id == prep_id).first()

def list_interview_preps(db: Session, skip: int = 0, limit: int = 100) -> list:
    return db.query(InterviewPrep).order_by(InterviewPrep.id.desc()).offset(skip).limit(limit).all()

def delete_interview_prep(db: Session, prep_id: int) -> bool:
    prep = get_interview_prep(db, prep_id)
    if not prep:
        return False
    db.delete(prep)
    db.commit()
    return True


def generate_company_research(company_name: str) -> dict:
    """
    Generate structured company research data using the LLM.
    Returns a dict suitable for the PDF export function.
    """
    prompt = f"""
    Provide a structured research brief about {company_name} for interview preparation.

    Return ONLY a JSON object with exactly these keys:
    - "description": A 2-3 sentence overview of what the company does.
    - "products": An array of 3-5 key products or services.
    - "culture": A 1-2 sentence description of the company culture and values.
    - "leadership": An array of 2-3 key executives, each with "name" and "title" keys.
    - "recent_news": An array of 2-3 recent notable events or announcements.
    """
    try:
        return llm_client.generate_json(prompt)
    except Exception:
        # Fallback: return empty structure so PDF still generates
        return {
            "description": f"{company_name} is a technology company.",
            "products": [],
            "culture": "",
            "leadership": [],
            "recent_news": [],
        }
