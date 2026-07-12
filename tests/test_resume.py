from app.services.resume_optimizer import optimize_resume, calculate_keyword_overlap
from app.services.keyword_matcher import extract_keywords

def test_extract_keywords():
    desc = "Looking for a Software Engineer with Python, FastAPI, and Docker experience. Must know Agile."
    keywords = extract_keywords(desc)
    assert "python" in keywords
    assert "fastapi" in keywords
    assert "docker" in keywords
    assert "agile" in keywords

from unittest.mock import patch

@patch("app.services.resume_optimizer.llm_client.tailor_resume")
def test_optimize_resume(mock_tailor):
    parsed_resume = {
        "summary": "Experienced developer building backend systems.",
        "skills": ["java", "c++", "python", "aws"],
        "experience": [
            {
                "company": "Tech Corp",
                "title": "Software Engineer",
                "description": "Created web services and managed databases."
            }
        ]
    }

    job_desc = "We need a Python developer who has built web applications and worked with AWS and Docker."

    mock_tailor.return_value = {
        "summary": "Experienced Python developer building backend systems on AWS.",
        "skills": ["python", "aws", "java", "c++"],
        "experience": parsed_resume["experience"]
    }

    optimized = optimize_resume(parsed_resume, job_desc, "Python Developer")

    # Python and AWS should be prioritized in skills
    assert optimized["skills"][0].lower() in ["python", "aws"]
    assert optimized["skills"][1].lower() in ["python", "aws"]

def test_keyword_overlap():
    optimized_resume = {
        "skills": ["python", "aws", "docker"],
        "summary": "I am a python developer."
    }
    keywords = ["python", "aws", "kubernetes"]
    
    result = calculate_keyword_overlap(optimized_resume, keywords)
    assert result["overlap_percentage"] > 60.0
    assert "python" in result["matched"]
    assert "aws" in result["matched"]
    assert "kubernetes" in result["unmatched"]
