"""Tests for RAGEngine — pipeline orchestration with mocked dependencies."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.services.rag_engine import RAGEngine, _flatten_resume


# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

SAMPLE_RESUME = {
    "name": "Jane Doe",
    "email": "jane@example.com",
    "phone": "555-1234",
    "location": "San Francisco, CA",
    "summary": "Senior software engineer with 8 years of Python and AWS experience.",
    "experience": [
        {
            "company": "Acme Corp",
            "title": "Senior Engineer",
            "dates": "2019 - Present",
            "description": "Built scalable microservices with Python and Kubernetes.",
        }
    ],
    "education": [
        {"institution": "UC Berkeley", "degree": "BS Computer Science", "dates": "2012-2016", "gpa": "3.8"}
    ],
    "skills": ["Python", "AWS", "Docker", "Kubernetes", "FastAPI"],
    "certifications": ["AWS Certified Solutions Architect"],
}

SAMPLE_JOB = {
    "title": "Senior Python Engineer",
    "company": "TechCorp",
    "description": (
        "We are looking for a Senior Python Engineer with strong experience in "
        "AWS, Kubernetes, and microservices. Requirements: 5+ years Python, "
        "experience with Docker, CI/CD pipelines. Nice to have: Go, Terraform."
    ),
}


# ---------------------------------------------------------------------------
# _flatten_resume helper
# ---------------------------------------------------------------------------

class TestFlattenResume:
    def test_flattens_all_fields(self):
        text = _flatten_resume(SAMPLE_RESUME)
        assert "Jane Doe" in text
        assert "Acme Corp" in text
        assert "Python" in text
        assert "UC Berkeley" in text
        assert "AWS Certified Solutions Architect" in text

    def test_empty_resume_returns_empty_string(self):
        assert _flatten_resume({}) == ""

    def test_missing_optional_fields_handled_gracefully(self):
        minimal = {"name": "Bob", "skills": ["Go"]}
        text = _flatten_resume(minimal)
        assert "Bob" in text
        assert "Go" in text


# ---------------------------------------------------------------------------
# RAGEngine.analyze_resume_for_job
# ---------------------------------------------------------------------------

class TestAnalyzeResumeForJob:
    @pytest.fixture
    def engine(self):
        return RAGEngine()

    @pytest.fixture
    def mock_llm(self):
        llm = MagicMock()
        llm.generate_json.return_value = SAMPLE_RESUME  # LLM returns "optimized" resume
        return llm

    def test_returns_optimized_resume_and_semantic_analysis(self, engine, mock_llm):
        with (
            patch("app.services.rag_engine.embedding_service") as mock_emb,
            patch("app.services.rag_engine.vector_store") as mock_vs,
        ):
            mock_emb.embed_query.return_value = [0.1] * 768
            mock_emb.chunk_text.return_value = ["requirement chunk one two three four five"]
            mock_vs.search_ats_tips.return_value = [
                {"text": "Mirror exact phrases from the job description.", "similarity": 0.9}
            ]
            mock_vs.search_similar_chunks.return_value = [
                {"text": "Python microservices chunk", "similarity": 0.7}
            ]

            result = engine.analyze_resume_for_job(
                resume_data=SAMPLE_RESUME,
                job_posting=SAMPLE_JOB,
                llm_client=mock_llm,
            )

        assert "optimized_resume" in result
        assert "semantic_analysis" in result
        assert "ats_tips_used" in result["semantic_analysis"]
        assert "gap_analysis" in result["semantic_analysis"]

    def test_falls_back_to_original_on_llm_failure(self, engine):
        failing_llm = MagicMock()
        failing_llm.generate_json.side_effect = RuntimeError("LLM down")

        with (
            patch("app.services.rag_engine.embedding_service") as mock_emb,
            patch("app.services.rag_engine.vector_store") as mock_vs,
        ):
            mock_emb.embed_query.return_value = [0.1] * 768
            mock_emb.chunk_text.return_value = []
            mock_vs.search_ats_tips.return_value = []
            mock_vs.search_similar_chunks.return_value = []

            result = engine.analyze_resume_for_job(
                resume_data=SAMPLE_RESUME,
                job_posting=SAMPLE_JOB,
                llm_client=failing_llm,
            )

        # Falls back to original resume on LLM failure
        assert result["optimized_resume"] == SAMPLE_RESUME

    def test_empty_job_description_returns_original(self, engine, mock_llm):
        """If embedding fails (returns []), should still return a valid result."""
        with (
            patch("app.services.rag_engine.embedding_service") as mock_emb,
            patch("app.services.rag_engine.vector_store") as mock_vs,
        ):
            mock_emb.embed_query.return_value = []  # no embedding
            mock_emb.chunk_text.return_value = []
            mock_vs.search_ats_tips.return_value = []
            mock_vs.search_similar_chunks.return_value = []

            result = engine.analyze_resume_for_job(
                resume_data=SAMPLE_RESUME,
                job_posting=SAMPLE_JOB,
                llm_client=mock_llm,
            )

        assert "optimized_resume" in result


# ---------------------------------------------------------------------------
# RAGEngine.recommend_jobs_for_resume
# ---------------------------------------------------------------------------

class TestRecommendJobsForResume:
    @pytest.fixture
    def engine(self):
        return RAGEngine()

    def test_returns_ranked_list_of_jobs(self, engine):
        with patch("app.services.rag_engine.embedding_service") as mock_emb, \
             patch("app.services.rag_engine.vector_store") as mock_vs:
            mock_emb.embed_query.return_value = [0.1] * 768
            mock_vs.search_similar_jobs.return_value = [
                {"text": "Python job at TechCo", "metadata": {"job_id": "1", "company": "TechCo"}, "similarity": 0.92},
                {"text": "Go engineer at StartupX", "metadata": {"job_id": "2", "company": "StartupX"}, "similarity": 0.75},
                {"text": "Another Python job", "metadata": {"job_id": "1", "company": "TechCo"}, "similarity": 0.88},
            ]

            results = engine.recommend_jobs_for_resume(
                resume_id=1,
                resume_text="Python AWS Kubernetes engineer",
                n=5,
            )

        # Deduplication: job_id=1 appears twice; only highest-sim kept
        job_ids = [r["job_id"] for r in results]
        assert job_ids.count(1) == 1
        # Results sorted by similarity descending
        sims = [r["similarity"] for r in results]
        assert sims == sorted(sims, reverse=True)

    def test_empty_embedding_returns_empty(self, engine):
        with patch("app.services.rag_engine.embedding_service") as mock_emb:
            mock_emb.embed_query.return_value = []
            results = engine.recommend_jobs_for_resume(
                resume_id=1, resume_text="some resume text"
            )
        assert results == []


# ---------------------------------------------------------------------------
# RAGEngine.find_similar_jobs
# ---------------------------------------------------------------------------

class TestFindSimilarJobs:
    @pytest.fixture
    def engine(self):
        return RAGEngine()

    def test_excludes_reference_job_from_results(self, engine):
        with patch("app.services.rag_engine.embedding_service") as mock_emb, \
             patch("app.services.rag_engine.vector_store") as mock_vs:
            mock_emb.embed_query.return_value = [0.1] * 768
            mock_vs.search_similar_jobs.return_value = [
                {"text": "Job 10 itself", "metadata": {"job_id": "10"}, "similarity": 0.99},
                {"text": "Related job 11", "metadata": {"job_id": "11"}, "similarity": 0.80},
            ]

            results = engine.find_similar_jobs(job_id=10, job_text="ML engineer role", n=3)

        job_ids = [r["job_id"] for r in results]
        assert 10 not in job_ids
        assert 11 in job_ids

    def test_empty_embedding_returns_empty(self, engine):
        with patch("app.services.rag_engine.embedding_service") as mock_emb:
            mock_emb.embed_query.return_value = []
            results = engine.find_similar_jobs(job_id=1, job_text="some job")
        assert results == []
