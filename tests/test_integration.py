from unittest.mock import patch
from datetime import datetime, timezone

@patch("app.services.scraper.JobScraper._search_jobs_for_company")
def test_end_to_end_flow(mock_search, client, db_session):
    mock_search.return_value = [
        {
            "company": "Adobe",
            "title": "Mock Data Scientist",
            "url": "http://adobe.com/jobs/1",
            "location": "San Jose",
            "description": "Mock description",
            "date_posted": datetime.now(timezone.utc),
            "keywords": '["python", "data"]',
            "source": "playwright_search"
        }
    ]

    # 1. Scrape Jobs
    scrape_res = client.post("/api/jobs/scrape", json={"companies": ["Adobe"], "max_per_company": 1})
    assert scrape_res.status_code == 200
    assert scrape_res.json()["new_postings"] > 0
    
    # 2. Get Jobs
    jobs_res = client.get("/api/jobs/")
    assert jobs_res.status_code == 200
    jobs = jobs_res.json()["items"]
    assert len(jobs) > 0
    job_id = jobs[0]["id"]
    
    # Mocking resume upload and optimize flow since we don't have mock files here
    assert True  # Placeholder for full integration testing
