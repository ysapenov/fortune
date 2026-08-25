"""Integration tests for /api/recommendations endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models.models import JobPosting, Resume


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def db_engine():
    # StaticPool ensures all connections share the same in-memory database so
    # tables created by create_all() are visible inside TestClient requests.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)



@pytest.fixture
def db_session(db_engine):
    SessionLocal = sessionmaker(bind=db_engine)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sample_resume(db_session):
    resume = Resume(
        filename="test_resume.pdf",
        original_content=b"fake",
        parsed_data=json.dumps({
            "name": "Jane Doe",
            "summary": "Senior Python AWS engineer with Kubernetes experience.",
            "skills": ["Python", "AWS", "Docker"],
            "experience": [{"company": "Acme", "title": "SWE", "dates": "2020-2023", "description": "Built APIs."}],
            "education": [],
            "certifications": [],
        }),
    )
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)
    return resume


@pytest.fixture
def sample_job(db_session):
    job = JobPosting(
        company="TechCo",
        title="Senior Python Engineer",
        url="https://techco.com/job/1",
        description="Python AWS Kubernetes microservices role.",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)
    return job


# ---------------------------------------------------------------------------
# GET /api/recommendations/status
# ---------------------------------------------------------------------------

class TestStatus:
    def test_status_returns_collection_counts(self, client):
        with patch("app.routers.recommendations.vector_store") as mock_vs:
            mock_vs.get_collection_stats.return_value = {
                "job_postings": 5,
                "resume_chunks": 3,
                "ats_knowledge": 45,
                "chroma_db_path": "/data/chroma",
            }
            resp = client.get("/api/recommendations/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_postings"] == 5
        assert data["ats_knowledge"] == 45


# ---------------------------------------------------------------------------
# GET /api/recommendations/jobs/{resume_id}
# ---------------------------------------------------------------------------

class TestRecommendJobs:
    def test_404_for_missing_resume(self, client):
        resp = client.get("/api/recommendations/jobs/99999")
        assert resp.status_code == 404

    def test_returns_recommendations_for_valid_resume(self, client, sample_resume, sample_job):
        with (
            patch("app.routers.recommendations.rag_engine") as mock_rag,
            patch("app.routers.recommendations.vector_store"),
        ):
            mock_rag.recommend_jobs_for_resume.return_value = [
                {
                    "job_id": sample_job.id,
                    "similarity": 0.88,
                    "snippet": "Python AWS Kubernetes role.",
                    "metadata": {},
                }
            ]
            resp = client.get(f"/api/recommendations/jobs/{sample_resume.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["job_id"] == sample_job.id
        assert data[0]["similarity"] == 0.88
        assert data[0]["company"] == "TechCo"

    def test_empty_list_when_no_vector_matches(self, client, sample_resume):
        with patch("app.routers.recommendations.rag_engine") as mock_rag:
            mock_rag.recommend_jobs_for_resume.return_value = []
            resp = client.get(f"/api/recommendations/jobs/{sample_resume.id}")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /api/recommendations/similar/{job_id}
# ---------------------------------------------------------------------------

class TestSimilarJobs:
    def test_404_for_missing_job(self, client):
        resp = client.get("/api/recommendations/similar/99999")
        assert resp.status_code == 404

    def test_returns_similar_jobs(self, client, sample_job, db_session):
        similar_job = JobPosting(
            company="OtherCo", title="Python Developer",
            url="https://other.co/job/2",
            description="Python microservices role.", is_active=True,
        )
        db_session.add(similar_job)
        db_session.commit()
        db_session.refresh(similar_job)

        with patch("app.routers.recommendations.rag_engine") as mock_rag:
            mock_rag.find_similar_jobs.return_value = [
                {
                    "job_id": similar_job.id,
                    "similarity": 0.82,
                    "snippet": "Python microservices role.",
                    "metadata": {},
                }
            ]
            resp = client.get(f"/api/recommendations/similar/{sample_job.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["job_id"] == similar_job.id


# ---------------------------------------------------------------------------
# POST /api/recommendations/index/jobs
# ---------------------------------------------------------------------------

class TestIndexJobs:
    def test_index_jobs_returns_count(self, client, sample_job):
        with patch("app.routers.recommendations.vector_store") as mock_vs:
            mock_vs.add_job_posting.return_value = 3
            resp = client.post("/api/recommendations/index/jobs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["indexed"] >= 1
        assert "chunks" in data["message"] or "job" in data["message"]


# ---------------------------------------------------------------------------
# POST /api/recommendations/index/resumes
# ---------------------------------------------------------------------------

class TestIndexResumes:
    def test_index_resumes_returns_count(self, client, sample_resume):
        with patch("app.routers.recommendations.vector_store") as mock_vs:
            mock_vs.add_resume.return_value = 2
            resp = client.post("/api/recommendations/index/resumes")
        assert resp.status_code == 200
        data = resp.json()
        assert data["indexed"] >= 1
