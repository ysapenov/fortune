"""Tests for EmbeddingService — chunking logic and embedding call mocking."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.services.embedding_service import EmbeddingService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def service_no_key(monkeypatch):
    """EmbeddingService with no API key — non-functional but safe."""
    monkeypatch.setattr("app.services.embedding_service.GEMINI_API_KEY", "")
    return EmbeddingService()


@pytest.fixture
def service_with_mock():
    """EmbeddingService with a mocked genai.Client."""
    with patch("app.services.embedding_service.genai.Client") as MockClient:
        fake_embedding = MagicMock()
        fake_embedding.values = [0.1, 0.2, 0.3] * 256  # 768 dims
        fake_response = MagicMock()
        fake_response.embeddings = [fake_embedding]
        MockClient.return_value.models.embed_content.return_value = fake_response

        import app.services.embedding_service as mod
        orig_key = mod.GEMINI_API_KEY
        mod.GEMINI_API_KEY = "fake-key"
        svc = EmbeddingService()
        yield svc
        mod.GEMINI_API_KEY = orig_key


# ---------------------------------------------------------------------------
# chunk_text tests
# ---------------------------------------------------------------------------

class TestChunkText:
    def test_empty_string_returns_empty(self, service_no_key):
        assert service_no_key.chunk_text("") == []

    def test_whitespace_only_returns_empty(self, service_no_key):
        assert service_no_key.chunk_text("   \n  ") == []

    def test_short_text_is_single_chunk(self, service_no_key):
        text = "Python developer with AWS and Docker experience."
        chunks = service_no_key.chunk_text(text, chunk_size=500)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_is_split_into_multiple_chunks(self, service_no_key):
        # 600-word text should split into 2 chunks with chunk_size=500, overlap=50
        word = "experience "
        text = word * 600
        chunks = service_no_key.chunk_text(text, chunk_size=500, overlap=50)
        assert len(chunks) >= 2

    def test_overlap_causes_shared_words(self, service_no_key):
        words = [f"word{i}" for i in range(100)]
        text = " ".join(words)
        chunks = service_no_key.chunk_text(text, chunk_size=60, overlap=10)
        assert len(chunks) >= 2
        # Last 10 words of chunk 0 should appear at start of chunk 1
        c0_tail = chunks[0].split()[-10:]
        c1_head = chunks[1].split()[:10]
        assert c0_tail == c1_head

    def test_section_headers_split_document(self, service_no_key):
        text = (
            "John Doe Software Engineer\n"
            "Experience\n"
            "Led backend team at Acme Corp 2020-2023\n"
            "Skills\n"
            "Python Go Kubernetes Docker\n"
        )
        chunks = service_no_key.chunk_text(text)
        # At least 2 chunks due to section header split
        assert len(chunks) >= 2

    def test_noise_chunks_discarded(self, service_no_key):
        # A 3-word chunk should be discarded (< 5 words threshold)
        short = "Hi there."
        long_section = "Skills\n" + " ".join([f"skill{i}" for i in range(20)])
        chunks = service_no_key.chunk_text(short + "\n" + long_section, chunk_size=500)
        for chunk in chunks:
            assert len(chunk.split()) >= 5

    def test_chunk_and_embed_no_key_returns_empty_embeddings(self, service_no_key):
        result = service_no_key.chunk_and_embed("Python developer with 5 years experience.")
        assert isinstance(result, list)
        for item in result:
            assert "text" in item
            assert "embedding" in item
            assert item["embedding"] == []


# ---------------------------------------------------------------------------
# embed_text / embed_query tests
# ---------------------------------------------------------------------------

class TestEmbedding:
    def test_embed_text_no_key_returns_empty(self, service_no_key):
        result = service_no_key.embed_text("hello world")
        assert result == []

    def test_embed_query_no_key_returns_empty(self, service_no_key):
        result = service_no_key.embed_query("senior python engineer")
        assert result == []

    def test_embed_text_empty_string_returns_empty(self, service_no_key):
        assert service_no_key.embed_text("") == []
        assert service_no_key.embed_text("   ") == []

    def test_embed_batch_no_key_returns_list_of_empty(self, service_no_key):
        result = service_no_key.embed_batch(["text1", "text2"])
        assert result == [[], []]

    def test_embed_text_with_mock_returns_vector(self, service_with_mock):
        result = service_with_mock.embed_text("Python engineer at AWS")
        assert len(result) == 768

    def test_embed_query_with_mock_returns_vector(self, service_with_mock):
        result = service_with_mock.embed_query("machine learning engineer")
        assert len(result) == 768

    def test_embed_batch_with_mock_returns_vectors(self, service_with_mock):
        results = service_with_mock.embed_batch(["text1", "text2"])
        assert len(results) == 2
        for r in results:
            assert len(r) == 768
