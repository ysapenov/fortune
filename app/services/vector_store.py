"""Vector store service backed by ChromaDB.

Manages two persistent collections:
  - "job_postings"  : chunked embeddings of job description text
  - "resume_chunks" : chunked embeddings of parsed resume sections
  - "ats_knowledge" : ATS best-practice tips (seeded once at startup)

All collections are stored on disk under CHROMA_DB_PATH so data survives
application restarts.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings

from app.config import ATS_KNOWLEDGE_PATH, CHROMA_DB_PATH, RAG_TOP_K
from app.services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

_COLLECTION_JOBS = "job_postings"
_COLLECTION_RESUMES = "resume_chunks"
_COLLECTION_ATS = "ats_knowledge"


class VectorStore:
    """ChromaDB-backed vector store with two document collections."""

    def __init__(self) -> None:
        # Lazily initialised on first use so import order does not matter.
        self._client: Optional[chromadb.ClientAPI] = None
        self._jobs_col: Optional[chromadb.Collection] = None
        self._resumes_col: Optional[chromadb.Collection] = None
        self._ats_col: Optional[chromadb.Collection] = None
        self._initialised = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init_store(self) -> None:
        """Initialise the ChromaDB client and collections.

        Safe to call multiple times — subsequent calls are no-ops.
        """
        if self._initialised:
            return
        try:
            Path(CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=CHROMA_DB_PATH,
                settings=Settings(anonymized_telemetry=False),
            )
            self._jobs_col = self._client.get_or_create_collection(
                name=_COLLECTION_JOBS,
                metadata={"hnsw:space": "cosine"},
            )
            self._resumes_col = self._client.get_or_create_collection(
                name=_COLLECTION_RESUMES,
                metadata={"hnsw:space": "cosine"},
            )
            self._ats_col = self._client.get_or_create_collection(
                name=_COLLECTION_ATS,
                metadata={"hnsw:space": "cosine"},
            )
            self._initialised = True
            logger.info(
                "VectorStore initialised at %s  |  jobs=%d  resumes=%d  ats=%d",
                CHROMA_DB_PATH,
                self._jobs_col.count(),
                self._resumes_col.count(),
                self._ats_col.count(),
            )
            # Seed ATS knowledge base if the collection is empty.
            if self._ats_col.count() == 0:
                self._seed_ats_knowledge()
        except Exception as exc:
            logger.error("VectorStore init failed: %s", exc)

    def _seed_ats_knowledge(self) -> None:
        """Embed and insert ATS tips from the bundled knowledge base file."""
        path = Path(ATS_KNOWLEDGE_PATH)
        if not path.exists():
            logger.warning("ATS knowledge file not found at %s — skipping seed.", path)
            return
        try:
            tips: List[Dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed to load ATS knowledge base: %s", exc)
            return

        ids, embeddings, documents, metadatas = [], [], [], []
        for tip in tips:
            emb = embedding_service.embed_text(tip["tip"])
            if not emb:
                continue
            ids.append(tip["id"])
            embeddings.append(emb)
            documents.append(tip["tip"])
            metadatas.append(
                {
                    "category": tip.get("category", "general"),
                    "applies_to": ",".join(tip.get("applies_to", ["all"])),
                }
            )

        if ids:
            assert self._ats_col is not None
            self._ats_col.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
            logger.info("Seeded %d ATS tips into vector store.", len(ids))

    # ------------------------------------------------------------------
    # Job Postings
    # ------------------------------------------------------------------

    def add_job_posting(
        self,
        job_id: int,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Chunk *text*, embed each chunk, and upsert into the jobs collection.

        Returns the number of chunks indexed.
        """
        self._ensure_init()
        assert self._jobs_col is not None

        # Remove stale entries for this job before re-indexing.
        self.delete_job_posting(job_id)

        chunks_data = embedding_service.chunk_and_embed(text)
        if not chunks_data:
            return 0

        base_meta = {**(metadata or {}), "job_id": str(job_id)}
        ids, embeddings, documents, metadatas = [], [], [], []
        for idx, chunk in enumerate(chunks_data):
            if not chunk["embedding"]:
                continue
            ids.append(f"job_{job_id}_chunk_{idx}")
            embeddings.append(chunk["embedding"])
            documents.append(chunk["text"])
            metadatas.append({**base_meta, "chunk_index": idx})

        if ids:
            self._jobs_col.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        logger.debug("Indexed %d chunks for job_id=%d", len(ids), job_id)
        return len(ids)

    def delete_job_posting(self, job_id: int) -> None:
        """Remove all chunks associated with *job_id* from the jobs collection."""
        self._ensure_init()
        assert self._jobs_col is not None
        try:
            self._jobs_col.delete(where={"job_id": str(job_id)})
        except Exception as exc:
            logger.debug("delete_job_posting(%d): %s", job_id, exc)

    def search_similar_jobs(
        self,
        query_embedding: List[float],
        n: int = RAG_TOP_K,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return the top-*n* job chunks most similar to *query_embedding*.

        *filters* maps ChromaDB ``where`` clause keys to values
        (e.g. ``{"company": "Google"}``).
        """
        self._ensure_init()
        assert self._jobs_col is not None
        if not query_embedding or self._jobs_col.count() == 0:
            return []
        try:
            kwargs: Dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": min(n, self._jobs_col.count()),
                "include": ["documents", "metadatas", "distances"],
            }
            if filters:
                kwargs["where"] = filters
            result = self._jobs_col.query(**kwargs)
            return self._unpack_results(result)
        except Exception as exc:
            logger.error("search_similar_jobs failed: %s", exc)
            return []

    # ------------------------------------------------------------------
    # Resumes
    # ------------------------------------------------------------------

    def add_resume(
        self,
        resume_id: int,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Index a resume's text into the resume_chunks collection."""
        self._ensure_init()
        assert self._resumes_col is not None

        self.delete_resume(resume_id)

        chunks_data = embedding_service.chunk_and_embed(text)
        if not chunks_data:
            return 0

        base_meta = {**(metadata or {}), "resume_id": str(resume_id)}
        ids, embeddings, documents, metadatas = [], [], [], []
        for idx, chunk in enumerate(chunks_data):
            if not chunk["embedding"]:
                continue
            ids.append(f"resume_{resume_id}_chunk_{idx}")
            embeddings.append(chunk["embedding"])
            documents.append(chunk["text"])
            metadatas.append({**base_meta, "chunk_index": idx})

        if ids:
            self._resumes_col.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )
        logger.debug("Indexed %d chunks for resume_id=%d", len(ids), resume_id)
        return len(ids)

    def delete_resume(self, resume_id: int) -> None:
        """Remove all chunks for *resume_id* from the resume_chunks collection."""
        self._ensure_init()
        assert self._resumes_col is not None
        try:
            self._resumes_col.delete(where={"resume_id": str(resume_id)})
        except Exception as exc:
            logger.debug("delete_resume(%d): %s", resume_id, exc)

    def search_similar_chunks(
        self,
        query_embedding: List[float],
        collection: str = _COLLECTION_RESUMES,
        n: int = RAG_TOP_K,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Generic similarity search across any collection."""
        self._ensure_init()
        col = self._get_collection(collection)
        if col is None or not query_embedding or col.count() == 0:
            return []
        try:
            kwargs: Dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": min(n, col.count()),
                "include": ["documents", "metadatas", "distances"],
            }
            if filters:
                kwargs["where"] = filters
            result = col.query(**kwargs)
            return self._unpack_results(result)
        except Exception as exc:
            logger.error("search_similar_chunks(%s) failed: %s", collection, exc)
            return []

    # ------------------------------------------------------------------
    # ATS Knowledge Base
    # ------------------------------------------------------------------

    def search_ats_tips(
        self,
        query_embedding: List[float],
        n: int = RAG_TOP_K,
    ) -> List[Dict[str, Any]]:
        """Retrieve ATS tips semantically relevant to *query_embedding*."""
        return self.search_similar_chunks(
            query_embedding=query_embedding,
            collection=_COLLECTION_ATS,
            n=n,
        )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def get_collection_stats(self) -> Dict[str, Any]:
        """Return document counts for each collection (health check)."""
        self._ensure_init()
        return {
            "job_postings": self._jobs_col.count() if self._jobs_col else 0,
            "resume_chunks": self._resumes_col.count() if self._resumes_col else 0,
            "ats_knowledge": self._ats_col.count() if self._ats_col else 0,
            "chroma_db_path": CHROMA_DB_PATH,
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ensure_init(self) -> None:
        if not self._initialised:
            self.init_store()

    def _get_collection(self, name: str) -> Optional[chromadb.Collection]:
        mapping = {
            _COLLECTION_JOBS: self._jobs_col,
            _COLLECTION_RESUMES: self._resumes_col,
            _COLLECTION_ATS: self._ats_col,
        }
        return mapping.get(name)

    @staticmethod
    def _unpack_results(result: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert ChromaDB query result dict to a flat list of match dicts."""
        output: List[Dict[str, Any]] = []
        docs = (result.get("documents") or [[]])[0]
        metas = (result.get("metadatas") or [[]])[0]
        dists = (result.get("distances") or [[]])[0]
        for doc, meta, dist in zip(docs, metas, dists):
            # ChromaDB returns cosine *distance* (lower = more similar).
            # Convert to similarity score in [0, 1].
            similarity = max(0.0, 1.0 - dist)
            output.append(
                {
                    "text": doc,
                    "metadata": meta,
                    "similarity": round(similarity, 4),
                }
            )
        return output


# Module-level singleton
vector_store = VectorStore()
