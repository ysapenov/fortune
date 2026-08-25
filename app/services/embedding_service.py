"""Embedding service wrapping Gemini text-embedding-004 via google-genai SDK.

Responsibilities:
- Generate embeddings for arbitrary text (single or batch).
- Chunk long texts (resumes, job descriptions) into semantically meaningful
  segments with configurable overlap before embedding.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

import google.genai as genai
from google.genai import types as genai_types

from app.config import (
    EMBEDDING_MODEL,
    GEMINI_API_KEY,
    RAG_CHUNK_OVERLAP,
    RAG_CHUNK_SIZE,
)

logger = logging.getLogger(__name__)

# Section header patterns used to split resumes and job descriptions into
# semantically meaningful chunks rather than arbitrary character windows.
_SECTION_HEADER_RE = re.compile(
    r"(?im)^\s*"
    r"(summary|objective|profile|experience|work history|employment|"
    r"education|skills|certifications|projects|publications|awards|"
    r"responsibilities|requirements|qualifications|about|overview)\s*[:\-]?\s*$"
)


class EmbeddingService:
    """Wrapper around Gemini text-embedding-004 with chunking utilities."""

    def __init__(self) -> None:
        if not GEMINI_API_KEY:
            logger.warning(
                "GEMINI_API_KEY is not set; EmbeddingService will be non-functional."
            )
            self._client: Optional[genai.Client] = None
        else:
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        self._model = EMBEDDING_MODEL

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def embed_text(self, text: str) -> List[float]:
        """Return a 768-dimensional embedding vector for *text*.

        Returns an empty list when the client is not configured or when the
        API call fails, so callers can degrade gracefully.
        """
        if self._client is None:
            return []
        text = text.strip()
        if not text:
            return []
        try:
            response = self._client.models.embed_content(
                model=self._model,
                contents=text,
                config=genai_types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT"
                ),
            )
            return response.embeddings[0].values  # type: ignore[index]
        except Exception as exc:  # pragma: no cover
            logger.error("embed_text failed: %s", exc)
            return []

    def embed_query(self, text: str) -> List[float]:
        """Embed a search *query* (uses RETRIEVAL_QUERY task type for better
        retrieval performance vs. RETRIEVAL_DOCUMENT used for indexed chunks).
        """
        if self._client is None:
            return []
        text = text.strip()
        if not text:
            return []
        try:
            response = self._client.models.embed_content(
                model=self._model,
                contents=text,
                config=genai_types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY"
                ),
            )
            return response.embeddings[0].values  # type: ignore[index]
        except Exception as exc:  # pragma: no cover
            logger.error("embed_query failed: %s", exc)
            return []

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of texts, returning a list of vectors in the same order."""
        if self._client is None:
            return [[] for _ in texts]
        results: List[List[float]] = []
        for text in texts:
            results.append(self.embed_text(text))
        return results

    def chunk_text(
        self,
        text: str,
        chunk_size: int = RAG_CHUNK_SIZE,
        overlap: int = RAG_CHUNK_OVERLAP,
    ) -> List[str]:
        """Split *text* into overlapping chunks suitable for embedding.

        Strategy (in priority order):
        1. Split on recognised section headers to honour document structure.
        2. If any resulting segment is still longer than *chunk_size* words,
           split it further using a sliding window with *overlap* words.
        3. Discard chunks that contain fewer than 5 words (noise).
        """
        if not text or not text.strip():
            return []

        # Step 1: split on section headers
        sections: List[str] = []
        last_end = 0
        for match in _SECTION_HEADER_RE.finditer(text):
            segment = text[last_end : match.start()].strip()
            if segment:
                sections.append(segment)
            last_end = match.start()
        tail = text[last_end:].strip()
        if tail:
            sections.append(tail)

        if not sections:
            sections = [text]

        # Step 2: sliding-window split for over-length sections
        chunks: List[str] = []
        for section in sections:
            words = section.split()
            if len(words) <= chunk_size:
                chunks.append(section)
            else:
                start = 0
                while start < len(words):
                    end = min(start + chunk_size, len(words))
                    chunks.append(" ".join(words[start:end]))
                    if end == len(words):
                        break
                    start += chunk_size - overlap

        # Step 3: discard noise chunks
        return [c for c in chunks if len(c.split()) >= 5]

    def chunk_and_embed(
        self,
        text: str,
        chunk_size: int = RAG_CHUNK_SIZE,
        overlap: int = RAG_CHUNK_OVERLAP,
    ) -> List[dict]:
        """Convenience method: chunk *text* and embed each chunk.

        Returns:
            List of dicts with keys ``text`` (str) and ``embedding`` (List[float]).
        """
        chunks = self.chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        embeddings = self.embed_batch(chunks)
        return [
            {"text": chunk, "embedding": emb}
            for chunk, emb in zip(chunks, embeddings)
        ]


# Module-level singleton
embedding_service = EmbeddingService()
