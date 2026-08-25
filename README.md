# Job Hunt Helper

A personal Job Hunt Helper application designed to automate and streamline the job search process. Powered end-to-end by an LLM-agnostic architecture (currently utilizing Gemini), it searches for relevant job postings from target companies, truthfully tailors your resume to specific roles via a **RAG pipeline**, recommends the best-matching jobs semantically, pre-fills job applications for your review, and generates structured interview prep materials.

## Features

- **LLM-Powered Job Search**: Strictly searches for relevant positions exclusively from the provided target tech companies (`data/companies.csv`). **Constraint:** This scraper will ONLY extract real jobs sourced directly from live internet searches. It is explicitly forbidden from generating artificial or mock job postings. If search engines block the automated request or no real jobs are found online, the scraper will legitimately return 0 results.
- **RAG-Based Resume Optimization**: Uses a Retrieval-Augmented Generation pipeline to tailor your resume for a specific job. Before calling the LLM, the engine retrieves the most relevant ATS best-practice tips and performs a semantic gap analysis — identifying job requirements not yet represented in the resume — then injects this context into the prompt. Strictly no hallucinations: only reordering and rephrasing of existing content.
- **Semantic Job Recommendations**: Embeds your resume and all indexed job descriptions using `text-embedding-004` and performs cosine similarity search via ChromaDB to surface the most relevant positions even when exact keywords don't match.
- **Combined ATS Match Score**: Resume-to-job matching now reports three scores: keyword overlap (regex-based), semantic similarity (embedding cosine), and a combined weighted score.
- **Application Tracking & Dashboard**: Semi-automated application pre-filling requiring explicit user approval. Features a comprehensive dashboard with editable statuses and graphical charts (Timeline Bar Chart, Status Donut Chart, and Success Rate Radar Chart).
- **Structured Interview Prep**: Generates a short summary about the company and its main products, 3 interesting facts, and role-specific interview questions.

## Architecture

- **Backend**: Python FastAPI
- **Database**: SQLite (SQLAlchemy)
- **Vector Store**: ChromaDB (local, persistent) — `data/chroma_db/`
- **Embeddings**: Gemini `text-embedding-004` via `google-genai` SDK
- **Frontend**: Vanilla CSS + HTML Templates (Jinja2) following Material Design 3 (M3)
- **Testing**: Pytest

## Setup & Running Locally

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   GEMINI_API_KEY=your_api_key_here

   # Optional — override defaults
   # CHROMA_DB_PATH=data/chroma_db
   # EMBEDDING_MODEL=text-embedding-004
   # RAG_CHUNK_SIZE=500
   # RAG_CHUNK_OVERLAP=50
   # RAG_TOP_K=5
   # ATS_KNOWLEDGE_PATH=data/ats_knowledge.json
   ```

3. **Run the Application**
   ```bash
   python run.py
   ```
   The application will start at `http://127.0.0.1:8000`.
   On first startup, ChromaDB is initialised and the 45 bundled ATS tips are automatically embedded and seeded into the vector store.

4. **Index Existing Data** *(first run only)*
   If you already have jobs or resumes in the database from a previous version, trigger a one-time re-index:
   ```bash
   curl -X POST http://127.0.0.1:8000/api/recommendations/index/jobs
   curl -X POST http://127.0.0.1:8000/api/recommendations/index/resumes
   ```
   New jobs scraped and new resumes uploaded after startup are indexed automatically.

## API Reference

### Jobs
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/jobs/` | List/filter job postings |
| `POST` | `/api/jobs/scrape` | Scrape and index new job postings |
| `POST` | `/api/jobs/refresh` | Re-scrape and re-index all jobs |
| `GET` | `/api/jobs/{id}` | Get a single job posting |
| `DELETE` | `/api/jobs/{id}` | Delete a job posting |

### Resumes
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/resumes/` | Upload PDF/DOCX resume (auto-indexed) |
| `GET` | `/api/resumes/` | List all resumes |
| `GET` | `/api/resumes/{id}` | Get a single resume |
| `POST` | `/api/resumes/{id}/optimize?use_rag=true` | Generate tailored resume via RAG pipeline. Response includes `semantic_analysis` with ATS tips used and gap analysis. Set `use_rag=false` for direct LLM call. |

### Recommendations (Vector Search)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/recommendations/jobs/{resume_id}` | Top-N job postings ranked by semantic similarity to the resume |
| `GET` | `/api/recommendations/similar/{job_id}` | Jobs semantically similar to a given posting |
| `POST` | `/api/recommendations/index/jobs` | (Re-)index all active job postings into the vector store |
| `POST` | `/api/recommendations/index/resumes` | (Re-)index all resumes into the vector store |
| `GET` | `/api/recommendations/status` | Vector store health: collection document counts |

### Applications
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/applications/` | Manage applications |
| `PUT` | `/api/applications/{id}/confirm` | Confirm/submit application |

### Interviews
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET/POST` | `/api/interviews/` | Generate/view interview prep |
| `GET` | `/api/interviews/{id}/export` | Export as PDF |

Interactive API docs available at `http://127.0.0.1:8000/docs`.

## Directory Structure

```
fortune/
├── app/
│   ├── main.py                  # FastAPI entry point + lifespan (DB + vector store init)
│   ├── config.py                # Configuration (DB, API keys, RAG settings)
│   ├── database.py              # SQLAlchemy engine + session
│   ├── models/                  # SQLAlchemy ORM models
│   ├── routers/
│   │   ├── jobs.py              # Job search & scraping endpoints
│   │   ├── resumes.py           # Resume upload & RAG optimization endpoints
│   │   ├── recommendations.py   # Vector similarity & indexing endpoints
│   │   ├── applications.py      # Application management endpoints
│   │   ├── interviews.py        # Interview prep endpoints
│   │   └── frontend.py          # Web UI route handlers
│   ├── services/
│   │   ├── embedding_service.py # Gemini text-embedding-004 wrapper + chunking
│   │   ├── vector_store.py      # ChromaDB collections (jobs, resumes, ATS tips)
│   │   ├── rag_engine.py        # RAG pipeline: retrieve → augment → generate
│   │   ├── keyword_matcher.py   # Regex keyword matching + semantic match scoring
│   │   ├── resume_optimizer.py  # RAG-augmented and direct LLM resume tailoring
│   │   ├── resume_parser.py     # PDF/DOCX parsing to structured JSON
│   │   ├── llm_client.py        # Gemini API client
│   │   ├── scraper.py           # Playwright-based job scraping
│   │   ├── interview_prep.py    # Interview material generation
│   │   ├── application_manager.py # Application pre-fill & tracking
│   │   └── pdf_export.py        # PDF export
│   ├── templates/               # Jinja2 HTML templates
│   └── static/                  # CSS/JS assets
├── data/
│   ├── companies.csv            # Target companies list
│   ├── ats_knowledge.json       # 45 curated ATS best-practice tips (RAG knowledge base)
│   └── chroma_db/               # ChromaDB persistent storage (git-ignored)
├── tests/
│   ├── test_embedding_service.py
│   ├── test_vector_store.py
│   ├── test_rag_engine.py
│   ├── test_recommendations.py
│   ├── test_resume.py
│   ├── test_scraper.py
│   └── test_integration.py
├── documentation/               # PRD, PROJECT, CONTRIBUTING
├── run.py                       # Entry point script
└── requirements.txt
```

## Testing

```bash
python -m pytest tests/ -v
```
