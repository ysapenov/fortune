"""
Resume Optimizer Service

Takes parsed resume data (JSON) and a job posting, generates a tailored version
that maximizes keyword matching without fabricating content using the LLM client.
"""

from typing import Dict, Any, List, Optional
from app.services.llm_client import llm_client

def optimize_resume(
    parsed_resume: Dict[str, Any],
    job_description: str,
    job_title: str = "",
    keywords: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Generate a tailored version of a resume optimized for a specific job posting.
    Delegates to the LLM Client to truthfully tailor the resume.
    """
    if not parsed_resume or not job_description:
        return parsed_resume

    try:
        optimized = llm_client.tailor_resume(parsed_resume, job_description)
        return optimized
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to optimize resume with LLM: {e}")
        # Fallback to original if LLM fails
        return parsed_resume

def calculate_keyword_overlap(
    optimized_resume: Dict[str, Any],
    keywords: List[str],
) -> Dict[str, Any]:
    """
    Calculate keyword overlap between optimized resume and job keywords.
    """
    if not keywords:
        return {"overlap_percentage": 0.0, "matched": [], "unmatched": keywords, "total": 0}

    # Flatten the entire resume into a single text
    resume_text = _flatten_resume_text(optimized_resume).lower()
    keyword_set = set(k.lower() for k in keywords)

    matched = []
    unmatched = []

    for kw in keyword_set:
        if kw in resume_text:
            matched.append(kw)
        else:
            # Check individual words of multi-word keywords
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
