"""Keyword extraction and matching service.

Extracts technical keywords from job descriptions and resumes,
computes overlap/match scores, and identifies missing keywords.
"""

import re
from collections import Counter
from typing import Dict, List, Optional, Set, Tuple


# Curated set of technical skills, tools, and languages commonly found
# in tech job postings.  Organised in lowercase for case-insensitive matching.
TECH_KEYWORDS: Set[str] = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    "perl", "haskell", "lua", "dart", "elixir", "clojure", "groovy",
    "objective-c", "shell", "bash", "powershell", "sql", "nosql", "graphql",
    # Web / frontend
    "html", "css", "react", "reactjs", "react.js", "angular", "angularjs",
    "vue", "vuejs", "vue.js", "svelte", "next.js", "nextjs", "nuxt",
    "webpack", "vite", "tailwind", "bootstrap", "sass", "less",
    "jquery", "redux", "mobx", "gatsby",
    # Backend / frameworks
    "django", "flask", "fastapi", "spring", "spring boot", "express",
    "node.js", "nodejs", "rails", "ruby on rails", "asp.net", ".net",
    "laravel", "gin", "fiber", "actix", "rocket",
    # Cloud / infrastructure
    "aws", "azure", "gcp", "google cloud", "cloud", "heroku",
    "digitalocean", "oracle cloud", "ibm cloud",
    "ec2", "s3", "lambda", "ecs", "eks", "fargate",
    "cloudformation", "terraform", "pulumi", "ansible", "chef", "puppet",
    "docker", "kubernetes", "k8s", "openshift", "helm",
    "ci/cd", "cicd", "jenkins", "github actions", "gitlab ci",
    "circleci", "travis ci", "argo", "argocd",
    # Databases
    "postgresql", "postgres", "mysql", "mariadb", "sqlite",
    "mongodb", "dynamodb", "cassandra", "redis", "memcached",
    "elasticsearch", "opensearch", "neo4j", "couchdb", "cockroachdb",
    "snowflake", "bigquery", "redshift", "databricks",
    # Data / ML / AI
    "machine learning", "deep learning", "ai", "artificial intelligence",
    "nlp", "natural language processing", "computer vision",
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn",
    "pandas", "numpy", "scipy", "matplotlib", "seaborn",
    "spark", "pyspark", "hadoop", "hive", "airflow", "dagster",
    "dbt", "etl", "data pipeline", "data engineering",
    "llm", "large language model", "generative ai", "transformers",
    "hugging face", "langchain", "openai", "gpt",
    # DevOps / SRE
    "devops", "sre", "site reliability", "monitoring",
    "prometheus", "grafana", "datadog", "splunk", "new relic",
    "elk", "logstash", "kibana", "nagios", "pagerduty",
    "linux", "unix", "windows server",
    # Security
    "cybersecurity", "security", "infosec", "soc", "siem",
    "penetration testing", "vulnerability", "encryption",
    "oauth", "jwt", "saml", "zero trust", "iam",
    "firewall", "ids", "ips", "waf", "devsecops",
    # Networking
    "networking", "tcp/ip", "dns", "http", "https", "rest", "restful",
    "grpc", "websocket", "mqtt", "api", "microservices",
    "load balancer", "cdn", "vpn", "ssl", "tls",
    # Methodologies / practices
    "agile", "scrum", "kanban", "jira", "confluence",
    "tdd", "bdd", "unit testing", "integration testing",
    "code review", "pair programming", "mob programming",
    "design patterns", "solid", "dry", "oop", "functional programming",
    # Tools / misc
    "git", "github", "gitlab", "bitbucket", "svn",
    "vs code", "intellij", "vim", "emacs",
    "figma", "sketch", "adobe xd",
    "postman", "swagger", "openapi",
    "jira", "trello", "asana", "slack", "teams",
    "tableau", "power bi", "looker",
    "salesforce", "sap", "servicenow",
}

# Multi-word keywords sorted by length (longest first) so that
# "machine learning" is matched before "machine" and "learning" individually.
_MULTI_WORD_KEYWORDS = sorted(
    [kw for kw in TECH_KEYWORDS if " " in kw or "/" in kw or "." in kw],
    key=len,
    reverse=True,
)

# Single-word keywords
_SINGLE_WORD_KEYWORDS = {kw for kw in TECH_KEYWORDS if " " not in kw and "/" not in kw and "." not in kw}


def _normalise_text(text: str) -> str:
    """Lowercase and collapse whitespace, preserving useful punctuation."""
    text = text.lower()
    # Normalise various dash types to standard hyphen
    text = re.sub(r"[\u2013\u2014\u2015]", "-", text)
    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_keywords(text: str, extra_keywords: Optional[Set[str]] = None) -> List[str]:
    """Extract recognised technical keywords from *text*.

    Returns a **deduplicated** list of keywords found, ordered by first
    occurrence position in the text.

    Parameters
    ----------
    text:
        Free-form text (job description, resume content, etc.).
    extra_keywords:
        Optional additional keywords to look for beyond the built-in set.
    """
    if not text:
        return []

    normalised = _normalise_text(text)
    found: dict[str, int] = {}  # keyword -> first-occurrence position

    # 1. Multi-word / special-character keywords first
    all_multi = list(_MULTI_WORD_KEYWORDS)
    if extra_keywords:
        all_multi.extend(
            sorted(
                [kw.lower() for kw in extra_keywords if " " in kw or "/" in kw or "." in kw],
                key=len,
                reverse=True,
            )
        )

    for kw in all_multi:
        pattern = re.escape(kw)
        match = re.search(pattern, normalised)
        if match and kw not in found:
            found[kw] = match.start()

    # 2. Single-word keywords — boundary-aware
    single = _SINGLE_WORD_KEYWORDS.copy()
    if extra_keywords:
        single |= {kw.lower() for kw in extra_keywords if " " not in kw and "/" not in kw and "." not in kw}

    for kw in single:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(kw) + r"(?![a-zA-Z0-9])"
        match = re.search(pattern, normalised)
        if match and kw not in found:
            found[kw] = match.start()

    # Sort by first occurrence
    return [kw for kw, _ in sorted(found.items(), key=lambda item: item[1])]


def compute_match(
    resume_text: str,
    job_description: str,
    extra_keywords: Optional[Set[str]] = None,
) -> Dict:
    """Compare keyword overlap between *resume_text* and *job_description*.

    Returns a dict with:
      - ``match_percentage``: float 0-100
      - ``matched_keywords``: list of keywords present in both
      - ``missing_keywords``: list of job keywords absent from resume
      - ``resume_keywords``: all keywords found in resume
      - ``job_keywords``: all keywords found in job description
    """
    resume_kws = set(extract_keywords(resume_text, extra_keywords))
    job_kws = set(extract_keywords(job_description, extra_keywords))

    if not job_kws:
        return {
            "match_percentage": 100.0 if not job_kws else 0.0,
            "matched_keywords": [],
            "missing_keywords": [],
            "resume_keywords": sorted(resume_kws),
            "job_keywords": [],
        }

    matched = resume_kws & job_kws
    missing = job_kws - resume_kws
    pct = (len(matched) / len(job_kws)) * 100.0

    return {
        "match_percentage": round(pct, 2),
        "matched_keywords": sorted(matched),
        "missing_keywords": sorted(missing),
        "resume_keywords": sorted(resume_kws),
        "job_keywords": sorted(job_kws),
    }


def rank_keywords(text: str) -> List[Tuple[str, int]]:
    """Return keywords from *text* ranked by frequency.

    Each entry is ``(keyword, count)`` sorted descending by count.
    """
    if not text:
        return []

    normalised = _normalise_text(text)
    counts: Counter = Counter()

    # Count multi-word keywords
    for kw in _MULTI_WORD_KEYWORDS:
        c = len(re.findall(re.escape(kw), normalised))
        if c:
            counts[kw] += c

    # Count single-word keywords
    for kw in _SINGLE_WORD_KEYWORDS:
        pattern = r"(?<![a-zA-Z0-9])" + re.escape(kw) + r"(?![a-zA-Z0-9])"
        c = len(re.findall(pattern, normalised))
        if c:
            counts[kw] += c

    return counts.most_common()


def compute_semantic_match(
    resume_text: str,
    job_description: str,
    keyword_weight: float = 0.5,
) -> Dict:
    """Compute a combined keyword + semantic similarity score.

    Uses the embedding service to produce a cosine similarity between the
    full resume text and job description, then blends it with the keyword
    match percentage into a single ``combined_score``.

    Args:
        resume_text: Flat text of the resume.
        job_description: Full job description text.
        keyword_weight: Weight assigned to the keyword score (0–1).
            The semantic score receives ``1 - keyword_weight``.

    Returns:
        Dict with:
          ``keyword_match``   — percentage from compute_match()
          ``semantic_match``  — cosine similarity 0–100 (or None on failure)
          ``combined_score``  — weighted average of the two
          ``keyword_detail``  — full output of compute_match()
    """
    # Lazy import to avoid circular dependency and keep startup fast.
    from app.services.embedding_service import embedding_service  # noqa: PLC0415

    keyword_detail = compute_match(resume_text, job_description)
    kw_score = keyword_detail.get("match_percentage", 0.0)

    # Compute semantic similarity via embeddings.
    semantic_score: Optional[float] = None
    try:
        resume_emb = embedding_service.embed_query(resume_text)
        job_emb = embedding_service.embed_query(job_description)
        if resume_emb and job_emb:
            # Cosine similarity: dot product of two unit vectors.
            import math  # noqa: PLC0415

            dot = sum(a * b for a, b in zip(resume_emb, job_emb))
            norm_r = math.sqrt(sum(x * x for x in resume_emb))
            norm_j = math.sqrt(sum(x * x for x in job_emb))
            if norm_r > 0 and norm_j > 0:
                cosine = dot / (norm_r * norm_j)
                # Clamp to [0, 1] and scale to percentage
                semantic_score = round(max(0.0, min(1.0, cosine)) * 100.0, 2)
    except Exception as exc:  # pragma: no cover
        import logging  # noqa: PLC0415

        logging.getLogger(__name__).warning("Semantic embedding failed: %s", exc)

    # Combined score — falls back to keyword-only if semantic unavailable.
    if semantic_score is not None:
        combined = round(
            kw_score * keyword_weight + semantic_score * (1 - keyword_weight), 2
        )
    else:
        combined = round(kw_score, 2)

    return {
        "keyword_match": round(kw_score, 2),
        "semantic_match": semantic_score,
        "combined_score": combined,
        "keyword_detail": keyword_detail,
    }

