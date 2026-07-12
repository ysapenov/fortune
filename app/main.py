"""FastAPI application with CORS, lifespan, and router includes."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.routers import applications, frontend, interviews, jobs, resumes


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Application lifespan: initialise DB on startup."""
    init_db()
    yield


app = FastAPI(
    title="Job Hunt Helper",
    description="Scrape job postings, optimise resumes, manage applications, and prepare for interviews.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# API Routers (order matters — more specific paths first)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(applications.router)
app.include_router(interviews.router)

# Frontend / HTML Routers (must come last to avoid shadowing API routes)
app.include_router(frontend.router)
