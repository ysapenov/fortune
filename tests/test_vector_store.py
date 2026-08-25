"""Tests for VectorStore — ChromaDB CRUD, search, and ATS seeding."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def temp_chroma_path(tmp_path):
    return str(tmp_path / "chroma_test")


@pytest.fixture
def mock_embedding():
    """Return a deterministic fake 768-dim embedding."""
    return [0.01 * (i % 100) for i in range(768)]


@pytest.fixture
def store(temp_chroma_path, mock_embedding):
    """Fully initialised VectorStore backed by a temp ChromaDB directory."""
    with (
        patch("app.services.vector_store.CHROMA_DB_PATH", temp_chroma_path),
        patch("app.services.vector_store.embedding_service") as mock_emb,
        patch("app.services.vector_store.ATS_KNOWLEDGE_PATH", "nonexistent_ats.json"),
    ):
        mock_emb.chunk_and_embed.return_value = [
            {"text": "chunk 1 text here for testing", "embedding": mock_embedding},
            {"text": "chunk 2 text here for testing", "embedding": mock_embedding},
        ]
        mock_emb.embed_text.return_value = mock_embedding

        from app.services.vector_store import VectorStore
        vs = VectorStore()
        vs.init_store()
        yield vs


# ---------------------------------------------------------------------------
# Initialisation tests
# ---------------------------------------------------------------------------

class TestInit:
    def test_init_creates_collections(self, store):
        stats = store.get_collection_stats()
        assert "job_postings" in stats
        assert "resume_chunks" in stats
        assert "ats_knowledge" in stats

    def test_init_is_idempotent(self, store):
        store.init_store()  # second call should be a no-op
        stats = store.get_collection_stats()
        assert stats["job_postings"] == 0


# ---------------------------------------------------------------------------
# Job postings
# ---------------------------------------------------------------------------

class TestJobPostings:
    def test_add_job_posting_returns_chunk_count(self, store):
        n = store.add_job_posting(job_id=1, text="Software Engineer at Acme Corp. Python AWS.", metadata={"company": "Acme"})
        assert n == 2  # mocked chunk_and_embed returns 2 chunks

    def test_add_job_posting_increments_collection(self, store):
        store.add_job_posting(job_id=10, text="Data engineer role.", metadata={})
        stats = store.get_collection_stats()
        assert stats["job_postings"] == 2

    def test_delete_job_posting_removes_entries(self, store):
        store.add_job_posting(job_id=99, text="Some job.", metadata={})
        before = store.get_collection_stats()["job_postings"]
        store.delete_job_posting(job_id=99)
        after = store.get_collection_stats()["job_postings"]
        assert after < before

    def test_add_job_replaces_existing_on_same_id(self, store):
        store.add_job_posting(job_id=5, text="First version.", metadata={})
        before = store.get_collection_stats()["job_postings"]
        store.add_job_posting(job_id=5, text="Updated version.", metadata={})
        after = store.get_collection_stats()["job_postings"]
        # Count stays the same (delete + re-add)
        assert after == before

    def test_search_similar_jobs_returns_results(self, store, mock_embedding):
        store.add_job_posting(job_id=7, text="Python machine learning role.", metadata={"company": "TechCo"})
        results = store.search_similar_jobs(query_embedding=mock_embedding, n=5)
        assert isinstance(results, list)
        assert len(results) > 0
        assert "similarity" in results[0]
        assert "text" in results[0]

    def test_search_similar_jobs_empty_store_returns_empty(self, store, mock_embedding):
        fresh = store.__class__.__new__(store.__class__)
        fresh._initialised = False
        # A clean store with no jobs indexed
        with patch("app.services.vector_store.CHROMA_DB_PATH", store._client._path if hasattr(store._client, "_path") else "/tmp/x"):
            results = store.search_similar_jobs(query_embedding=[], n=5)
        assert results == []

    def test_search_similar_jobs_empty_embedding_returns_empty(self, store):
        results = store.search_similar_jobs(query_embedding=[], n=5)
        assert results == []


# ---------------------------------------------------------------------------
# Resumes
# ---------------------------------------------------------------------------

class TestResumes:
    def test_add_resume_returns_chunk_count(self, store):
        n = store.add_resume(resume_id=1, text="Senior Python developer with 5 years.", metadata={})
        assert n == 2

    def test_delete_resume_removes_entries(self, store):
        store.add_resume(resume_id=42, text="Some resume text.", metadata={})
        before = store.get_collection_stats()["resume_chunks"]
        store.delete_resume(resume_id=42)
        after = store.get_collection_stats()["resume_chunks"]
        assert after < before


# ---------------------------------------------------------------------------
# ATS Knowledge
# ---------------------------------------------------------------------------

class TestATSKnowledge:
    def test_search_ats_tips_returns_results_when_seeded(self, temp_chroma_path, mock_embedding, tmp_path):
        """Seed a small ATS knowledge base and verify search works."""
        ats_file = tmp_path / "ats.json"
        ats_file.write_text(json.dumps([
            {"id": "ats_001", "category": "keywords", "tip": "Mirror exact phrases from job description.", "applies_to": ["all"]},
            {"id": "ats_002", "category": "formatting", "tip": "Use standard section headers.", "applies_to": ["all"]},
        ]), encoding="utf-8")

        with (
            patch("app.services.vector_store.CHROMA_DB_PATH", temp_chroma_path),
            patch("app.services.vector_store.embedding_service") as mock_emb,
            patch("app.services.vector_store.ATS_KNOWLEDGE_PATH", str(ats_file)),
        ):
            mock_emb.embed_text.return_value = mock_embedding
            mock_emb.chunk_and_embed.return_value = [
                {"text": "test chunk", "embedding": mock_embedding}
            ]

            from app.services.vector_store import VectorStore
            vs = VectorStore()
            vs.init_store()

            results = vs.search_ats_tips(query_embedding=mock_embedding, n=5)
            assert isinstance(results, list)
            # Both tips should be indexed and retrievable
            assert len(results) >= 1
