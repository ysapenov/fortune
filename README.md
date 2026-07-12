# Job Hunt Helper

A personal Job Hunt Helper application designed to automate and streamline the job search process. Powered end-to-end by an LLM-agnostic architecture (currently utilizing Gemini), it searches for relevant job postings from target companies, truthfully tailors your resume to specific roles, pre-fills job applications for your review, and generates structured interview prep materials.

## Features

- **LLM-Powered Job Search**: Strictly searches for relevant positions exclusively from the provided target tech companies (`data/companies.csv`). **Constraint:** This scraper will ONLY extract real jobs sourced directly from live internet searches. It is explicitly forbidden from generating artificial or mock job postings. If search engines block the automated request or no real jobs are found online, the scraper will legitimately return 0 results.
- **Truthful Resume Tailoring**: Uses LLM to parse and tailor your resume to the job description by reordering skills and emphasizing relevant experience—strictly without generating false information.
- **Application Tracking & Dashboard**: Semi-automated application pre-filling requiring explicit user approval. Features a comprehensive dashboard with editable statuses and graphical charts (Timeline Bar Chart, Status Donut Chart, and Success Rate Radar Chart).
- **Structured Interview Prep**: Generates a short summary about the company and its main products, 3 interesting facts, and role-specific interview questions.

## Architecture

- **Backend**: Python FastAPI
- **Database**: SQLite (SQLAlchemy)
- **Frontend**: Vanilla CSS + HTML Templates (Jinja2)
- **Testing**: Pytest

## Setup & Running Locally

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the Application**
   ```bash
   python run.py
   ```
   The application will start at `http://127.0.0.1:8000`.

## Directory Structure
- `app/`: FastAPI application code
- `tests/`: Pytest test suite
- `data/companies.csv`: Target companies to scrape
- `documentation/`: Documentation directory including PRD.md, PROJECT.md, CONTRIBUTING.md
- `scripts/`: Standalone test scripts
- `logs/`: Log files and debug outputs

## Testing
Run the test suite with:
```bash
python -m pytest tests/ -v
```
