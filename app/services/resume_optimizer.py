"""
Resume Optimizer Service

Takes parsed resume data (JSON) and a job posting, generates a tailored version
that maximizes keyword matching without fabricating content using the LLM client.

Two optimization paths are available:
  - optimize_resume()          : Direct LLM call (baseline, always available).
  - optimize_resume_with_rag() : RAG-augmented call with retrieved ATS context
                                 and semantic gap analysis (preferred).
"""

import logging
from typing import Any, Dict, List, Optional

from app.services.llm_client import llm_client

logger = logging.getLogger(__name__)


def optimize_resume(
    parsed_resume: Dict[str, Any],
    job_description: str,
    job_title: str = "",
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate a tailored resume via a direct LLM call (baseline path).

    Returns the original resume unchanged on LLM failure.
    """
    if not parsed_resume or not job_description:
        return parsed_resume

    try:
        optimized = llm_client.tailor_resume(parsed_resume, job_description)
        return optimized
    except Exception as exc:
        logger.error("optimize_resume (direct LLM) failed: %s", exc)
        return parsed_resume


def optimize_resume_with_rag(
    parsed_resume: Dict[str, Any],
    job_posting: Dict[str, Any],
) -> Dict[str, Any]:
    """Generate a tailored resume using the RAG pipeline (preferred path).

    Retrieves ATS best-practice context and performs semantic gap analysis
    before invoking the LLM, producing higher-quality tailoring.

    Args:
        parsed_resume: Parsed resume dict (from resume_parser).
        job_posting: Dict with at minimum ``description``, ``title``, ``company``.

    Returns:
        Dict with keys:
          ``optimized_resume`` — tailored resume dict (same schema as input)
          ``semantic_analysis`` — dict with ``ats_tips_used`` and ``gap_analysis``
    """
    # Lazy import to avoid circular dependency at module load time.
    from app.services.rag_engine import rag_engine  # noqa: PLC0415

    if not parsed_resume or not job_posting.get("description"):
        return {"optimized_resume": parsed_resume, "semantic_analysis": {}}

    try:
        result = rag_engine.analyze_resume_for_job(
            resume_data=parsed_resume,
            job_posting=job_posting,
            llm_client=llm_client,
        )
        return result
    except Exception as exc:
        logger.error(
            "optimize_resume_with_rag failed: %s — falling back to direct LLM", exc
        )
        # Graceful fallback: run the direct LLM path instead.
        optimized = optimize_resume(
            parsed_resume=parsed_resume,
            job_description=job_posting.get("description", ""),
            job_title=job_posting.get("title", ""),
        )
        return {"optimized_resume": optimized, "semantic_analysis": {}}


def calculate_keyword_overlap(
    optimized_resume: Dict[str, Any],
    keywords: List[str],
) -> Dict[str, Any]:
    """Calculate keyword overlap between optimized resume and job keywords."""
    if not keywords:
        return {"overlap_percentage": 0.0, "matched": [], "unmatched": keywords, "total": 0}

    resume_text = _flatten_resume_text(optimized_resume).lower()
    keyword_set = set(k.lower() for k in keywords)

    matched = []
    unmatched = []

    for kw in keyword_set:
        if kw in resume_text:
            matched.append(kw)
        else:
            kw_words = kw.split()
            if len(kw_words) > 1 and all(w in resume_text for w in kw_words):
                matched.append(kw)
            else:
                unmatched.append(kw)

    total = len(keyword_set)
    overlap_pct = (len(matched) / total * 100) if total > 0 else 0.0

    return {
        "overlap_percentage": round(overlap_pct, 1),
        "matched": sorted(matched),
        "unmatched": sorted(unmatched),
        "total": total,
    }


def _flatten_resume_text(resume: Dict[str, Any]) -> str:
    """Flatten all resume fields into a single text string for keyword matching."""
    parts = []
    for field in ["name", "email", "phone", "location", "summary"]:
        val = resume.get(field, "")
        if val:
            parts.append(str(val))
    for exp in resume.get("experience", []):
        for key in ["company", "title", "dates", "description"]:
            val = exp.get(key, "")
            if val:
                parts.append(str(val))
    for edu in resume.get("education", []):
        for key in ["institution", "degree", "dates", "gpa"]:
            val = edu.get(key, "")
            if val:
                parts.append(str(val))
    for skill in resume.get("skills", []):
        parts.append(str(skill))
    for cert in resume.get("certifications", []):
        parts.append(str(cert))
    return " ".join(parts)
