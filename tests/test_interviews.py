"""Tests for interview prep service, PDF export, and API router."""

import json
from unittest.mock import patch, MagicMock
import pytest

from app.models.models import JobPosting, InterviewPrep
from app.services.pdf_export import export_interview_prep_pdf


def test_pdf_export_service():
    prep_data = {
        "company_name": "Nvidia",
        "job_title": "Senior GPU Architect",
        "research_summary": "Nvidia is the leader in accelerated computing and AI hardware.",
        "questions": [
            {"question": "Explain GPU memory hierarchy.", "category": "Technical", "framework": "STAR", "number": 1},
            {"question": "How do CUDA cores differ from Tensor cores?", "category": "Technical", "framework": "STAR", "number": 2},
        ],
    }

    pdf_bytes = export_interview_prep_pdf(
        company_name=prep_data["company_name"],
        job_title=prep_data["job_title"],
        research_summary=prep_data["research_summary"],
        questions=prep_data["questions"],
    )
    assert pdf_bytes is not None
    assert len(pdf_bytes) > 100
    assert pdf_bytes.startswith(b"%PDF")



@patch("app.services.interview_prep.llm_client.prep_interview")
def test_interview_prep_api(mock_prep, client, db_session):
    mock_prep.return_value = {
        "summary": "CrowdStrike is a cloud-native cybersecurity platform.",
        "facts": ["Founded by George Kurtz", "Falcon platform", "Security Cloud"],
        "questions": ["How do you detect endpoint intrusions?", "Describe an incident response workflow."],
    }

    job = JobPosting(
        company="CrowdStrike",
        title="Security Engineer",
        url="https://crowdstrike.com/jobs/1",
        description="Cybersecurity engineering position",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # 1. Generate interview prep
    gen_res = client.post(
        "/api/interviews/generate",
        json={
            "company_name": "CrowdStrike",
            "job_posting_id": job.id,
            "job_title": "Security Engineer",
            "job_description": "Cybersecurity engineering position",
        },
    )
    assert gen_res.status_code == 201
    prep_data = gen_res.json()
    prep_id = prep_data["id"]
    assert prep_data["company_name"] == "CrowdStrike"
    assert len(prep_data["questions"]) == 2

    # 2. List interview preps
    list_res = client.get("/api/interviews/")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Export PDF
    pdf_res = client.get(f"/api/interviews/{prep_id}/export")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert len(pdf_res.content) > 100
