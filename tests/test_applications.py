"""Unit and integration tests for application management service and endpoints."""

import json
import pytest
from app.models.models import JobPosting, TailoredResume, Application, ApplicationStatus
from app.services import application_manager


def test_application_lifecycle(client, db_session):
    # 1. Create a job posting
    job = JobPosting(
        company="Databricks",
        title="Software Engineer",
        url="https://databricks.com/jobs/1",
        description="Python & Spark",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # 2. Create application (Draft status)
    create_res = client.post(
        "/api/applications/",
        json={
            "job_posting_id": job.id,
            "user_profile": {
                "applicant_name": "Test User",
                "applicant_email": "test@example.com",
            },
            "notes": "Interested in ML platform",
        },
    )
    assert create_res.status_code == 201
    app_data = create_res.json()
    assert app_data["status"] == "draft"
    app_id = app_data["id"]

    # 3. Update application fields while in draft
    update_res = client.put(
        f"/api/applications/{app_id}",
        json={"updates": {"additional_notes": "Updated note"}},
    )
    assert update_res.status_code == 200

    # 4. Attempt status change directly to 'submitted' via update_status endpoint (forbidden)
    forbidden_res = client.put(
        f"/api/applications/{app_id}/status",
        json={"status": "submitted"},
    )
    assert forbidden_res.status_code == 400

    # 5. Explicitly confirm application (only valid transition from draft to submitted)
    confirm_res = client.put(f"/api/applications/{app_id}/confirm")
    assert confirm_res.status_code == 200
    assert confirm_res.json()["status"] == "submitted"
    assert confirm_res.json()["submitted_at"] is not None

    # 6. Cannot edit after confirmation
    edit_post_confirm = client.put(
        f"/api/applications/{app_id}",
        json={"updates": {"additional_notes": "Should fail"}},
    )
    assert edit_post_confirm.status_code == 400

    # 7. Progress status: submitted -> interview -> offer
    interview_res = client.put(
        f"/api/applications/{app_id}/status",
        json={"status": "interview"},
    )
    assert interview_res.status_code == 200
    assert interview_res.json()["status"] == "interview"

    offer_res = client.put(
        f"/api/applications/{app_id}/status",
        json={"status": "offer"},
    )
    assert offer_res.status_code == 200
    assert offer_res.json()["status"] == "offer"

    # 8. Dashboard metrics
    dash_res = client.get("/api/applications/dashboard")
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["total"] >= 1
    assert "offer" in dash["status_counts"]


def test_delete_application(client, db_session):
    job = JobPosting(
        company="Salesforce",
        title="Backend Engineer",
        url="https://salesforce.com/jobs/2",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    app = Application(
        job_posting_id=job.id,
        status=ApplicationStatus.DRAFT,
    )
    db_session.add(app)
    db_session.commit()
    db_session.refresh(app)

    del_res = client.delete(f"/api/applications/{app.id}")
    assert del_res.status_code == 200

    get_res = client.get(f"/api/applications/{app.id}")
    assert get_res.status_code == 404
