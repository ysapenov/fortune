# Product Requirements Document (PRD)

**Product Name:** Job Hunt Helper
**Author:** Yera
**Date:** 2026-07-11
**Updated:** 2026-08-25
**Status:** Approved / Development

---

## 1. Product Vision & Goals

**Problem Statement:** 
The job search process is tedious, involving repetitive tasks like finding relevant postings across multiple company career pages, manually tailoring resumes for each position to pass ATS systems, filling out application forms, and preparing company-specific interview materials.

**Product Vision:** 
Build a production-grade, LLM-powered Job Hunt Helper application for personal use to automate and streamline the job search process. The app will act as an end-to-end assistant that finds relevant positions, truthfully tailors resumes via a RAG pipeline, surfaces semantically matched job recommendations, pre-fills applications, and generates structured interview prep materials.

**Key Architecture:** 
LLM-agnostic architecture (initially using Gemini API) with a Python FastAPI backend, SQLite database, ChromaDB vector store, and a vanilla HTML/CSS/JS frontend.

---

## 2. Target Audience
* **Primary User:** Job seeker (personal use).
* **Target Companies:** A configured list of tech companies (provided in `data/companies.csv`), including Nvidia, Salesforce, Adobe, Databricks, CrowdStrike, etc.

---

## 3. Functional Requirements

### 3.1 Job Posting Search & Aggregation
* **Target Scope:** Strictly search and aggregate job postings from the career pages of the companies listed in `data/companies.csv`. Public job board APIs can act as fallbacks.
* **LLM Filtering:** Filter jobs using LLMs to return only relevant positions.
* **Capabilities:** Filter results by role type, location, keywords, and date posted.
* **Deduplication:** Detect and merge duplicate postings from the same company.
* **Refresh:** Provide a scheduled or on-demand refresh mechanism.
* **Auto-Indexing:** Newly scraped job postings are automatically embedded and indexed into the vector store for semantic search.

### 3.2 Resume Optimization & ATS Tailoring
* **Import:** Upload original resume in PDF or DOCX format.
* **Parsing:** Parse resume into a structured internal representation (JSON/YAML) without data loss on key fields.
* **RAG-Augmented Tailoring (default):** Before invoking the LLM, the RAG engine:
  1. Embeds the job description and retrieves the most relevant ATS best-practice tips from the knowledge base.
  2. Performs a semantic gap analysis — identifying job requirement segments not semantically covered by the resume.
  3. Injects the retrieved context and gap analysis into the LLM prompt.
  * **Crucial:** The original resume content must never be fabricated (no hallucinations); no false information should be generated.
* **Direct LLM Tailoring (fallback):** Available via `?use_rag=false`; delegates directly to the LLM without retrieval augmentation.
* **Combined ATS Score:** Reports keyword match percentage, semantic cosine similarity, and a combined weighted score.
* **Export:** Download the tailored resume as a PDF or DOCX.
* **Auto-Indexing:** Uploaded resumes are automatically embedded and indexed into the vector store.

### 3.3 Application Management
* **Semi-Automated Pre-fill:** Pre-fill job application forms with user profile data and the tailored resume.
* **Explicit Approval:** Present a review screen showing all pre-filled fields. Explicit user confirmation is strictly required before submission (no auto-submit paths).
* **Dashboard:** A UI dashboard to track application processes.
  * Must display status tracking (draft, submitted, rejected, interview, offer).
  * Status and date of status changes must be editable by the user.
* **Analytics/Charts UI:** The top of the dashboard page must contain an overview of total counts, segmentation by status, and graphical charts, specifically:
  * Timeline Bar Chart
  * Status Donut Chart
  * Success Rate Radar Chart (e.g., Success Rate by Company)

### 3.4 Interview Preparation Materials
* **Structured Generation:** For any target job posting or company, generate:
  * A short summary about the company and its main products.
  * 3 interesting facts about the company.
  * Role-specific interview questions (at least 10) based on the job description.
* **Viewing & Exporting:** Viewable in the web UI and exportable as a PDF document.

### 3.5 RAG-Based Recommendations & Vector Search
* **Personalized Job Recommendations:** Given a resume, perform cosine similarity search across all indexed job postings to return top-N semantically matched roles, even when exact keywords differ.
* **Similar Job Discovery:** For any job posting, surface semantically similar positions from the indexed collection.
* **ATS Knowledge Base:** A curated, bundled knowledge base of ATS best-practice tips (`data/ats_knowledge.json`) is embedded at startup and retrieved contextually during resume optimization.
* **Vector Store Health:** An API endpoint reports collection document counts and storage path for operational monitoring.
* **Manual Re-indexing:** Endpoints available to trigger full re-indexing of all existing jobs or resumes (e.g., after migrating from a previous version).

---

## 4. Non-Functional Requirements & Tech Stack

* **Backend:** Python FastAPI.
* **Frontend:** Web UI (HTML/CSS/JS with Jinja2 templates) incorporating chart libraries (e.g., Chart.js), adhering to Material Design 3 (M3) adaptive and accessible principles under the "Fortune" design system.
* **Storage:** SQLite via SQLAlchemy (`database.py` and `models/`).
* **Vector Store:** ChromaDB (local, persistent, disk-backed). Stored at `data/chroma_db/` (git-ignored). No external server required.
* **Embeddings:** Gemini `text-embedding-004` via the existing `google-genai` SDK. Produces 768-dimensional vectors. Reuses `GEMINI_API_KEY` — no additional credentials needed.
* **Deployment & Setup:** The application must run locally with a single setup command (`python run.py` or `pip install -r requirements.txt && python run.py`), after configuring the `.env` file for API keys.
* **Testing:** Pytest framework. Code must achieve at least 70% test coverage on core modules (resume parser, job scraper, keyword matcher, embedding service, RAG engine, vector store). Both Unit and Integration tests are required.

---

## 5. Milestones & Timeline

| Phase | Description |
|---|---|
| **M1** | **Backend Core + Job Scraping:** FastAPI app setup, DB models, job scraping service, job search limited to `data/companies.csv` with LLM filtering. |
| **M2** | **Resume Optimization:** PDF/DOCX parsing, truthful LLM-powered tailoring (no hallucinations), and export to PDF/DOCX. |
| **M3** | **Application Management:** Pre-fill forms, review screen, explicit submission confirmation, status tracking dashboard, and graphical charts. |
| **M4** | **Interview Preparation:** LLM-generated structured prep (company summary, 3 facts, questions), Web UI, and PDF export. |
| **M5** | **Frontend + Integration + Docs + Tests:** Web UI templates with charts, complete integration, README, API Docs, CONTRIBUTING.md, and comprehensive Pytest suite. |
| **M6** | **RAG Pipeline + Vector Search:** Embedding service, ChromaDB vector store, RAG-augmented resume optimization, semantic job recommendations, ATS knowledge base, combined match scoring, and 45-test RAG suite. |

---

## 6. Acceptance Criteria

* **Job Search:** Successfully discovers job postings from at least 10 companies without crashing.
* **Resume Optimization:** Keyword overlap >= 60% compared to job posting. No fabricated data. RAG path returns `semantic_analysis` with retrieved ATS tips and gap analysis.
* **Application Management:** Code review verifies no auto-submit paths exist.
* **Interview Prep:** Generates company summary, 3 interesting facts, and at least 10 questions.
* **Recommendations:** `GET /api/recommendations/jobs/{resume_id}` returns a ranked list with similarity scores. `GET /api/recommendations/status` confirms all three collections are initialised.
* **Quality:** `python -m pytest tests/ -v` executes the full suite without import errors and all tests pass.

