# Project: Job Hunt Helper

## Architecture
- **Backend**: Python FastAPI application
- **Frontend**: Web UI (HTML/CSS/JS with Jinja2 templates or simple SPA)
- **Storage**: SQLite via SQLAlchemy
- **Vector Store**: ChromaDB (local, persistent) at `data/chroma_db/`
- **Embeddings**: Gemini `text-embedding-004` via `google-genai` SDK
- **Package**: Single setup command (`python run.py` or `pip install -r requirements.txt && python run.py`)

### Module Boundaries
- `app/` — Main application package
  - `main.py` — FastAPI app entry point + lifespan (DB init + vector store init/ATS seeding)
  - `config.py` — Configuration management (DB, API keys, RAG settings)
  - `database.py` — SQLite/SQLAlchemy setup
  - `models/` — SQLAlchemy models
  - `routers/` — API route handlers
    - `applications.py` — Application management endpoints
    - `frontend.py` — Web UI route handlers
    - `interviews.py` — Interview prep endpoints
    - `jobs.py` — Job scraping/search endpoints (auto-indexes to vector store on scrape)
    - `recommendations.py` — Vector similarity search and indexing endpoints
    - `resumes.py` — Resume upload/optimization endpoints (auto-indexes on upload, RAG path)
  - `services/` — Business logic
    - `application_manager.py` — Application pre-fill and tracking
    - `embedding_service.py` — Gemini `text-embedding-004` wrapper with semantic chunking
    - `interview_prep.py` — Interview material generation
    - `keyword_matcher.py` — Keyword extraction, regex matching, and semantic cosine scoring
    - `llm_client.py` — LLM-agnostic client (supporting Gemini initially, extensible to others)
    - `pdf_export.py` — PDF generation for export
    - `rag_engine.py` — RAG pipeline: gap analysis → ATS tip retrieval → augmented prompt
    - `resume_generator.py` — Resume generation logic
    - `resume_optimizer.py` — RAG-augmented and direct LLM resume tailoring
    - `resume_parser.py` — PDF/DOCX resume parsing
    - `scraper.py` — Job scraping service
    - `vector_store.py` — ChromaDB wrapper (job_postings, resume_chunks, ats_knowledge collections)
  - `templates/` — Jinja2 HTML templates
  - `static/` — CSS/JS assets
- `tests/` — pytest test suite
  - `conftest.py`
  - `test_embedding_service.py`
  - `test_integration.py`
  - `test_rag_engine.py`
  - `test_recommendations.py`
  - `test_resume.py`
  - `test_scraper.py`
  - `test_vector_store.py`
- `run.py` — Entry point script
- `requirements.txt` — Dependencies (includes `chromadb`)
- `README.md` — Project documentation
- `.env` — Environment variables (API keys, etc.)
- `documentation/` — Documentation directory including PRD.md, PROJECT.md, CONTRIBUTING.md
- `data/companies.csv` — Pre-existing target company list
- `data/ats_knowledge.json` — 45 curated ATS best-practice tips (RAG knowledge base, bundled)
- `data/chroma_db/` — ChromaDB persistent vector store (git-ignored, created at runtime)
- `scripts/` — Standalone test scripts
- `logs/` — Log files and debug outputs

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| 1 | Backend Core + Job Scraping | FastAPI app setup, database models, job scraping service, job search limited strictly to provided list of companies (`data/companies.csv`) with relevant positions filtered by LLM | none | DONE |
| 2 | Resume Optimization | PDF/DOCX parsing, structured representation, truthful LLM-powered tailoring (no hallucinations) adjusted to job posting, download as PDF/DOCX | M1 (database) | DONE |
| 3 | Application Management | Pre-fill forms, review screen, explicit confirmation for submission, status tracking dashboard with editable status/date and graphical charts (Timeline Bar Chart, Status Donut Chart, Success Rate by Company Radar Chart) | M1 (database), M2 (resume data) | DONE |
| 4 | Interview Preparation | LLM-generated structured prep: short company summary, 3 interesting facts, role-specific questions, web UI display, PDF export | M1 (database) | IN PROGRESS |
| 5 | Frontend + Integration + Docs + Tests | Web UI templates with chart libraries (e.g., Chart.js), full integration, README.md, API docs, CONTRIBUTING.md, pytest suite | M1-M4 | IN PROGRESS |
| 6 | RAG Pipeline + Vector Search | EmbeddingService (text-embedding-004), VectorStore (ChromaDB, 3 collections), RAGEngine (gap analysis + ATS retrieval + augmented LLM prompt), semantic job recommendations, combined ATS match score, auto-indexing on scrape/upload, 45-tip ATS knowledge base, 45 RAG tests | M1-M2 | DONE |

## Interface Contracts

### Database Models (shared across modules)
- `JobPosting`: id, company, title, url, location, description, date_posted, date_discovered, keywords, is_active
- `Resume`: id, filename, original_path, parsed_data (JSON), created_at
- `TailoredResume`: id, resume_id (FK), job_posting_id (FK), content (JSON), output_path, created_at
- `Application`: id, job_posting_id (FK), tailored_resume_id (FK), status (enum: draft/submitted/rejected/interview/offer), prefilled_data (JSON), submitted_at, notes, status_updated_at
- `InterviewPrep`: id, job_posting_id (FK), company_name, research_summary, interesting_facts (JSON), questions (JSON), created_at

### Vector Store Collections (ChromaDB)
- `job_postings` — chunked embeddings of job description text; metadata: `job_id`, `company`, `title`, `location`
- `resume_chunks` — chunked embeddings of parsed resume sections; metadata: `resume_id`, `filename`
- `ats_knowledge` — embedded ATS best-practice tips seeded from `data/ats_knowledge.json`; metadata: `category`, `applies_to`

### API Endpoints
- `GET/POST /api/jobs/` — List/search/scrape jobs (scrape auto-indexes to vector store)
- `POST /api/jobs/refresh` — Re-scrape and re-index all jobs
- `GET/POST /api/resumes/` — Upload/list resumes (upload auto-indexes to vector store)
- `POST /api/resumes/{id}/optimize?use_rag=true` — RAG-augmented tailored resume; response includes `semantic_analysis`
- `GET/POST /api/applications/` — Manage applications
- `PUT /api/applications/{id}/confirm` — Confirm/submit application
- `GET/POST /api/interviews/` — Generate/view interview prep
- `GET /api/interviews/{id}/export` — Export as PDF
- `GET /api/recommendations/jobs/{resume_id}` — Semantically ranked job recommendations for a resume
- `GET /api/recommendations/similar/{job_id}` — Jobs semantically similar to a given posting
- `POST /api/recommendations/index/jobs` — (Re-)index all active job postings into vector store
- `POST /api/recommendations/index/resumes` — (Re-)index all resumes into vector store
- `GET /api/recommendations/status` — Vector store collection counts and storage path

## Code Layout
All source code lives under `c:\Users\Yera\Antigravity\fortune\`.
See Module Boundaries above for directory structure.

