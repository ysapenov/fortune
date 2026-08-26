from unittest.mock import patch, mock_open
from datetime import datetime, timezone

from app.services.scraper import JobScraper
from app.models.models import JobPosting

@patch("os.path.exists")
@patch("builtins.open", new_callable=mock_open, read_data="Name,Industry\nNvidia,Tech\nAdobe,Tech\n")
def test_job_scraper_loads_companies(mock_file, mock_exists):
    mock_exists.return_value = True
    scraper = JobScraper()
    companies = scraper.load_companies()
    assert isinstance(companies, list)
    assert len(companies) == 2
    assert "Nvidia" in companies

@patch("app.services.scraper.JobScraper._search_jobs_for_company")
def test_scraper_generates_postings(mock_search, db_session):
    mock_search.return_value = [
        {
            "company": "Nvidia",
            "title": "Mock Software Engineer",
            "url": "http://nvidia.com/jobs/1",
            "location": "Remote",
            "description": "Mock description",
            "date_posted": datetime.now(timezone.utc),
            "keywords": '["python"]',
            "source": "playwright_search"
        },
        {
            "company": "Adobe",
            "title": "Mock Data Scientist",
            "url": "http://adobe.com/jobs/2",
            "location": "San Jose",
            "description": "Mock description",
            "date_posted": datetime.now(timezone.utc),
            "keywords": '["python", "data"]',
            "source": "playwright_search"
        }
    ]
    
    scraper = JobScraper()
    # Test scraping specific companies
    new_postings = scraper.scrape(db_session, companies=["Nvidia", "Adobe"], max_per_company=2)
    
    assert len(new_postings) > 0
    assert new_postings[0]["company"] in ["Nvidia", "Adobe"]
    
    # Verify they were saved to DB
    saved = db_session.query(JobPosting).all()
    assert len(saved) == len(new_postings)

@patch("app.services.scraper.JobScraper._search_jobs_for_company")
def test_scraper_deduplication(mock_search, db_session):
    mock_search.return_value = [
        {
            "company": "TestCompany",
            "title": "Mock Software Engineer",
            "url": "http://testcompany.com/jobs/1",
            "location": "Remote",
            "description": "Mock description",
            "date_posted": datetime.now(timezone.utc),
            "keywords": '["python"]',
            "source": "playwright_search"
        }
    ]

    scraper = JobScraper()
    # Scrape twice with same companies
    first_batch = scraper.scrape(db_session, companies=["TestCompany"], max_per_company=3)
    second_batch = scraper.scrape(db_session, companies=["TestCompany"], max_per_company=3)
    
    # Second batch should yield 0 new postings due to deduplication
    assert len(second_batch) == 0


def test_delete_job_posting_cascade(client, db_session):
    """Test deleting a job posting with linked application, tailored resume, and interview prep."""
    from app.models.models import Application, ApplicationStatus, InterviewPrep, Resume, TailoredResume

    # 1. Create a job
    job = JobPosting(
        company="Microsoft",
        title="Software Engineer",
        url="https://microsoft.com/jobs/101",
        location="Redmond, WA",
        description="Build Azure services.",
        is_active=True,
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(job)

    # 2. Create resume, tailored resume, application, and interview prep
    resume = Resume(filename="test.pdf", original_content=b"test")
    db_session.add(resume)
    db_session.commit()
    db_session.refresh(resume)

    tailored = TailoredResume(resume_id=resume.id, job_posting_id=job.id, tailored_data="{}")
    db_session.add(tailored)
    db_session.commit()
    db_session.refresh(tailored)

    app = Application(
        job_posting_id=job.id,
        tailored_resume_id=tailored.id,
        status=ApplicationStatus.DRAFT,
    )
    db_session.add(app)

    prep = InterviewPrep(job_posting_id=job.id, company_name="Microsoft")
    db_session.add(prep)
    db_session.commit()

    # 3. Call DELETE /api/jobs/{job.id}
    res = client.delete(f"/api/jobs/{job.id}")
    assert res.status_code == 200
    assert res.json()["message"] == "Job deleted successfully"

    # 4. Verify job and related records are gone
    assert db_session.query(JobPosting).filter(JobPosting.id == job.id).first() is None
    assert db_session.query(Application).filter(Application.job_posting_id == job.id).first() is None
    assert db_session.query(TailoredResume).filter(TailoredResume.job_posting_id == job.id).first() is None
    assert db_session.query(InterviewPrep).filter(InterviewPrep.job_posting_id == job.id).first() is None

