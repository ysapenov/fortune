# Project: Job Hunt Helper

## Architecture
- **Backend**: Python FastAPI application
- **Frontend**: Web UI (HTML/CSS/JS with Jinja2 templates or simple SPA)
- **Storage**: SQLite via SQLAlchemy
- **Package**: Single setup command (`python run.py` or `pip install -r requirements.txt && python run.py`)

### Module Boundaries
- `app/` — Main application package
  - `main.py` — FastAPI app entry point
  - `config.py` — Configuration management
  - `database.py` — SQLite/SQLAlchemy setup
  - `models/` — SQLAlchemy models
  - `routers/` — API route handlers
    - `applications.py` — Application management endpoints
    - `frontend.py` — Web UI route handlers
    - `interviews.py` — Interview prep endpoints
    - `jobs.py` — Job scraping/search endpoints
    - `resumes.py` — Resume upload/optimization endpoints
  - `services/` — Business logic
    - `application_manager.py` — Application pre-fill and tracking
    - `interview_prep.py` — Interview material generation
    - `keyword_matcher.py` — Keyword extraction and matching
    - `llm_client.py` — LLM-agnostic client (supporting Gemini initially, extensible to others)
    - `pdf_export.py` — PDF generation for export
    - `resume_generator.py` — Resume generation logic
    - `resume_optimizer.py` — ATS keyword optimization
    - `resume_parser.py` — PDF/DOCX resume parsing
    - `scraper.py` — Job scraping service
  - `templates/` — Jinja2 HTML templates
  - `static/` — CSS/JS assets
- `tests/` — pytest test suite
  - `conftest.py`
  - `test_integration.py`
  - `test_resume.py`
  - `test_scraper.py`
- `run.py` — Entry point script
- `requirements.txt` — Dependencies
- `README.md` — Project documentation
- `.env` — Environment variables (API keys, etc.)
- `documentation/` — Documentation directory including PRD.md, PROJECT.md, CONTRIBUTING.md
- `data/companies.csv` — Pre-existing target company list
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

## Interface Contracts

### Database Models (shared across modules)
- `JobPosting`: id, company, title, url, location, description, date_posted, date_discovered, keywords, is_active
- `Resume`: id, filename, original_path, parsed_data (JSON), created_at
- `TailoredResume`: id, resume_id (FK), job_posting_id (FK), content (JSON), output_path, created_at
- `Application`: id, job_posting_id (FK), tailored_resume_id (FK), status (enum: draft/submitted/rejected/interview/offer), prefilled_data (JSON), submitted_at, notes, status_updated_at
- `InterviewPrep`: id, job_posting_id (FK), company_name, research_summary, interesting_facts (JSON), questions (JSON), created_at

### API Endpoints
- `GET/POST /api/jobs/` — List/search/scrape jobs
- `GET/POST /api/resumes/` — Upload/list resumes
- `POST /api/resumes/{id}/optimize` — Generate tailored resume for a job
- `GET/POST /api/applications/` — Manage applications
- `PUT /api/applications/{id}/confirm` — Confirm/submit application
- `GET/POST /api/interviews/` — Generate/view interview prep
- `GET /api/interviews/{id}/export` — Export as PDF

## Code Layout
All source code lives under `c:\Users\Yera\Antigravity\fortune\`.
See Module Boundaries above for directory structure.
