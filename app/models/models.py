"""SQLAlchemy models for the Job Hunt Helper application."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Enum,
    LargeBinary,
)
from sqlalchemy.orm import relationship

from app.database import Base


class ApplicationStatus(str, enum.Enum):
    """Status values for job applications."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    OFFER = "offer"


def _utcnow():
    return datetime.now(timezone.utc)


class JobPosting(Base):
    """A discovered job posting from a target company."""

    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, index=True)
    company = Column(String(255), nullable=False, index=True)
    title = Column(String(500), nullable=False, index=True)
    url = Column(String(2048), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    date_posted = Column(DateTime, nullable=True)
    date_discovered = Column(DateTime, default=_utcnow, nullable=False)
    keywords = Column(Text, nullable=True)  # JSON-encoded list
    is_active = Column(Boolean, default=True, nullable=False)
    source = Column(String(255), nullable=True)

    # Relationships
    applications = relationship("Application", back_populates="job_posting")
    tailored_resumes = relationship("TailoredResume", back_populates="job_posting")
    interview_preps = relationship("InterviewPrep", back_populates="job_posting")

    def __repr__(self):
        return f"<JobPosting(id={self.id}, company='{self.company}', title='{self.title}')>"


class Resume(Base):
    """An uploaded resume."""

    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_content = Column(LargeBinary, nullable=True)
    parsed_data = Column(Text, nullable=True)  # JSON text
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)

    # Relationships
    tailored_resumes = relationship("TailoredResume", back_populates="resume")

    def __repr__(self):
        return f"<Resume(id={self.id}, filename='{self.filename}')>"


class TailoredResume(Base):
    """A resume tailored for a specific job posting."""

    __tablename__ = "tailored_resumes"

    id = Column(Integer, primary_key=True, index=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=False)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    tailored_data = Column(Text, nullable=True)  # JSON
    file_path = Column(String(2048), nullable=True)
    format = Column(String(10), nullable=True)  # pdf, docx
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="tailored_resumes")
    job_posting = relationship("JobPosting", back_populates="tailored_resumes")
    application = relationship("Application", back_populates="tailored_resume", uselist=False)

    def __repr__(self):
        return f"<TailoredResume(id={self.id}, resume_id={self.resume_id}, job_id={self.job_posting_id})>"


class Application(Base):
    """A job application with tracking."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(Integer, ForeignKey("job_postings.id"), nullable=False)
    tailored_resume_id = Column(
        Integer, ForeignKey("tailored_resumes.id"), nullable=True
    )
    status = Column(
        Enum(ApplicationStatus),
        default=ApplicationStatus.DRAFT,
        nullable=False,
    )
    prefilled_data = Column(Text, nullable=True)  # JSON
    submitted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow, nullable=False)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow, nullable=False)
    status_updated_at = Column(DateTime, default=_utcnow, nullable=False)
    notes = Column(Text, nullable=True)

    # Relationships
    job_posting = relationship("JobPosting", back_populates="applications")
    tailored_resume = relationship("TailoredResume", back_populates="application")

    def __repr__(self):
        return f"<Application(id={self.id}, status='{self.status}')>"


class InterviewPrep(Base):
    """Interview preparation materials for a company/role."""

    __tablename__ = "interview_preps"

    id = Column(Integer, primary_key=True, index=True)
    job_posting_id = Column(
        Integer, ForeignKey("job_postings.id"), nullable=True
    )
    company_name = Column(String(255), nullable=False)
    research_summary = Column(Text, nullable=True)
    interesting_facts = Column(Text, nullable=True)  # JSON-encoded list
    questions = Column(Text, nullable=True)  # JSON-encoded list
    created_at = Column(DateTime, default=_utcnow, nullable=False)

    # Relationships
    job_posting = relationship("JobPosting", back_populates="interview_preps")

    def __repr__(self):
        return f"<InterviewPrep(id={self.id}, company='{self.company_name}')>"
