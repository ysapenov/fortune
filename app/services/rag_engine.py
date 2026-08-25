"""RAG Engine — orchestrates the Retrieve → Augment → Generate pipeline.

Two main capabilities:
  1. analyze_resume_for_job  — RAG-augmented resume optimization with gap
     analysis and retrieved ATS best-practice context.
  2. recommend_jobs_for_resume — cosine-similarity job ranking for a resume.
  3. find_similar_jobs       — find jobs semantically similar to a given job.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.config import RAG_TOP_K
from app.services.embedding_service import embedding_service
from app.services.vector_store import vector_store

logger = logging.getLogger(__name__)


def _flatten_resume(resume: Dict[str, Any]) -> str:
    """Flatten a parsed resume dict to a single searchable string."""
    parts: List[str] = []

    for key in ("name", "email", "phone", "location", "summary"):
        val = resume.get(key, "")
        if val:
            parts.append(str(val))

    for exp in resume.get("experience", []):
        for field in ("company", "title", "dates", "description"):
            val = exp.get(field, "")
            if val:
                parts.append(str(val))

    for edu in resume.get("education", []):
        for field in ("institution", "degree", "dates"):
            val = edu.get(field, "")
            if val:
                parts.append(str(val))

    skills = resume.get("skills", [])
    if skills:
        parts.append(", ".join(str(s) for s in skills))

    certs = resume.get("certifications", [])
    if certs:
        parts.append(", ".join(str(c) for c in certs))

    return "\n".join(parts)


class RAGEngine:
    """Orchestrates embedding retrieval and LLM augmentation for resume/job tasks."""

    # ------------------------------------------------------------------
    # Resume analysis (RAG-augmented optimization)
    # ------------------------------------------------------------------

    def analyze_resume_for_job(
        self,
        resume_data: Dict[str, Any],
        job_posting: Dict[str, Any],
        llm_client: Any,
    ) -> Dict[str, Any]:
        """Run the full RAG pipeline for resume tailoring.

        Pipeline:
        1. Flatten resume and job description to text.
        2. Embed both.
        3. Retrieve ATS tips relevant to the job description.
        4. Identify semantic gap: job requirements not covered by resume.
        5. Build an augmented prompt and call the LLM.
        6. Return optimized resume + semantic analysis metadata.

        Args:
            resume_data: Parsed resume dict (from resume_parser).
            job_posting: Dict with keys ``title``, ``description``, ``company``.
            llm_client: LLMClient instance (injected to avoid circular import).

        Returns:
            Dict with keys:
              ``optimized_resume`` — tailored resume dict
              ``semantic_analysis`` — gap analysis and retrieved context
        """
        job_description = job_posting.get("description", "")
        job_title = job_posting.get("title", "")
        company = job_posting.get("company", "")
        resume_text = _flatten_resume(resume_data)

        # --- Step 1: embed job description as query ---
        job_embedding = embedding_service.embed_query(job_description)

        # --- Step 2: retrieve ATS tips relevant to this job ---
        ats_tips: List[str] = []
        if job_embedding:
            raw_tips = vector_store.search_ats_tips(job_embedding, n=RAG_TOP_K)
            ats_tips = [r["text"] for r in raw_tips]

        # --- Step 3: semantic gap analysis ---
        gap_analysis = self._compute_gap_analysis(resume_text, job_description)

        # --- Step 4: build augmented prompt ---
        augmented_prompt = self._build_optimization_prompt(
            resume_data=resume_data,
            job_title=job_title,
            company=company,
            job_description=job_description,
            ats_tips=ats_tips,
            gap_analysis=gap_analysis,
        )

        # --- Step 5: LLM call ---
        try:
            optimized = llm_client.generate_json(augmented_prompt)
        except Exception as exc:
            logger.error("RAG LLM call failed: %s — falling back to original resume", exc)
            optimized = resume_data

        return {
            "optimized_resume": optimized,
            "semantic_analysis": {
                "ats_tips_used": ats_tips,
                "gap_analysis": gap_analysis,
            },
        }

    def _compute_gap_analysis(
        self,
        resume_text: str,
        job_description: str,
    ) -> Dict[str, Any]:
        """Identify which job requirement segments are likely not covered.

        Strategy: chunk the job description, embed each chunk, then query the
        resume_chunks collection for the nearest match. Chunks whose top
        similarity falls below a threshold are flagged as gaps.
        """
        GAP_THRESHOLD = 0.45  # cosine similarity; below this = likely gap

        jd_chunks = embedding_service.chunk_text(job_description)
        gaps: List[str] = []
        covered: List[str] = []

        for chunk in jd_chunks:
            emb = embedding_service.embed_query(chunk)
            if not emb:
                continue
            # Search only resume chunks that exist in the store; if the store
            # is empty (first run before indexing), we treat everything as a gap.
            results = vector_store.search_similar_chunks(
                query_embedding=emb,
                collection="resume_chunks",
                n=1,
            )
            top_sim = results[0]["similarity"] if results else 0.0
            if top_sim < GAP_THRESHOLD:
                gaps.append(chunk[:200])  # truncate for prompt brevity
            else:
                covered.append(chunk[:200])

        return {
            "gap_count": len(gaps),
            "covered_count": len(covered),
            "gap_snippets": gaps[:5],  # top-5 gaps for the prompt
        }

    @staticmethod
    def _build_optimization_prompt(
        resume_data: Dict[str, Any],
        job_title: str,
        company: str,
        job_description: str,
        ats_tips: List[str],
        gap_analysis: Dict[str, Any],
    ) -> str:
        """Assemble the RAG-augmented prompt for resume optimization."""
        tips_block = "\n".join(f"- {tip}" for tip in ats_tips) if ats_tips else "None retrieved."
        gap_snippets = gap_analysis.get("gap_snippets", [])
        gap_block = (
            "\n".join(f"  * {g}" for g in gap_snippets)
            if gap_snippets
            else "  No significant gaps detected."
        )

        return f"""You are an expert ATS resume optimizer. Tailor the provided resume JSON for the target role.

== ATS BEST PRACTICES (retrieved context) ==
{tips_block}

== SEMANTIC GAP ANALYSIS ==
The following job requirement snippets are likely under-represented in the current resume.
Address them without fabricating skills or experience:
{gap_block}

== TARGET ROLE ==
Company : {company}
Job Title: {job_title}

== JOB DESCRIPTION ==
{job_description[:3000]}

== ORIGINAL RESUME (JSON) ==
{json.dumps(resume_data, indent=2)[:4000]}

== STRICT INSTRUCTIONS ==
1. Return ONLY valid JSON matching the exact schema of the original resume. No extra keys.
2. Do NOT invent skills, companies, dates, or achievements that are not in the original.
3. You MAY: reorder bullet points, rephrase descriptions using job-description language,
   move skills to the top of the Skills list, and update the Summary to target the role.
4. Mirror exact keyword phrases from the job description where they truthfully apply.
5. Apply the ATS best practices above where they truthfully improve the resume.
6. Do not output any text outside the JSON object.
"""

    # ------------------------------------------------------------------
    # Job recommendation (vector similarity)
    # ------------------------------------------------------------------

    def recommend_jobs_for_resume(
        self,
        resume_id: int,
        resume_text: str,
        n: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return top-*n* jobs ranked by semantic similarity to the resume.

        Args:
            resume_id: DB id of the resume (used only for logging).
            resume_text: Flat text representation of the resume.
            n: Number of recommendations to return.
            filters: Optional ChromaDB ``where`` filters (e.g. company, location).

        Returns:
            List of dicts: ``{job_id, chunk_text, similarity, metadata}``.
        """
        query_emb = embedding_service.embed_query(resume_text)
        if not query_emb:
            logger.warning("Could not embed resume %d for recommendations.", resume_id)
            return []

        raw = vector_store.search_similar_jobs(
            query_embedding=query_emb,
            n=n * 3,  # over-fetch then deduplicate by job_id
            filters=filters,
        )

        # Deduplicate by job_id, keeping highest similarity per job.
        seen: Dict[str, Dict[str, Any]] = {}
        for hit in raw:
            jid = hit["metadata"].get("job_id", "")
            if jid not in seen or hit["similarity"] > seen[jid]["similarity"]:
                seen[jid] = {
                    "job_id": int(jid) if jid else None,
                    "similarity": hit["similarity"],
                    "snippet": hit["text"][:300],
                    "metadata": hit["metadata"],
                }

        ranked = sorted(seen.values(), key=lambda x: x["similarity"], reverse=True)
        return ranked[:n]

    # ------------------------------------------------------------------
    # Similar jobs
    # ------------------------------------------------------------------

    def find_similar_jobs(
        self,
        job_id: int,
        job_text: str,
        n: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find jobs semantically similar to the given job posting.

        Args:
            job_id: DB id of the reference job (excluded from results).
            job_text: Raw text of the reference job description.
            n: Number of similar jobs to return.
        """
        query_emb = embedding_service.embed_query(job_text)
        if not query_emb:
            return []

        raw = vector_store.search_similar_jobs(
            query_embedding=query_emb,
            n=(n + 1) * 3,  # over-fetch to handle dedup + self-exclusion
        )

        seen: Dict[str, Dict[str, Any]] = {}
        for hit in raw:
            jid = hit["metadata"].get("job_id", "")
            if jid == str(job_id):
                continue  # exclude the reference job itself
            if jid not in seen or hit["similarity"] > seen[jid]["similarity"]:
                seen[jid] = {
                    "job_id": int(jid) if jid else None,
                    "similarity": hit["similarity"],
                    "snippet": hit["text"][:300],
                    "metadata": hit["metadata"],
                }

        ranked = sorted(seen.values(), key=lambda x: x["similarity"], reverse=True)
        return ranked[:n]


# Module-level singleton
rag_engine = RAGEngine()
