import json
import logging

import google.genai as genai

from app.config import GEMINI_API_KEY

logger = logging.getLogger(__name__)


class LLMClient:
    """An LLM-agnostic client interface, currently using Google Gemini (google-genai SDK)."""

    def __init__(self):
        if GEMINI_API_KEY:
            self.client = genai.Client(api_key=GEMINI_API_KEY)
            self.model_name = "gemini-2.5-flash"
        else:
            logger.warning("GEMINI_API_KEY is not set. LLM features will fail.")
            self.client = None
            self.model_name = None

    def _generate_content(self, prompt: str) -> str:
        if not self.client:
            raise ValueError("LLM is not configured properly. Missing API key.")
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
            )
            return response.text
        except Exception as e:
            logger.error(f"Error generating content from LLM: {e}")
            raise

    def generate_json(self, prompt: str) -> dict:
        """Helper to ensure the LLM returns JSON and parse it."""
        full_prompt = (
            prompt
            + "\n\nIMPORTANT: Return ONLY valid JSON. Do not include markdown formatting "
            "like ```json...```, just the raw JSON object or array."
        )
        text = self._generate_content(full_prompt)
        text = text.strip()

        # Clean up markdown if the LLM still returns it
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from LLM: {text}")
            raise ValueError("LLM did not return valid JSON") from e

    def is_job_relevant(self, job_title: str, job_description: str) -> bool:
        """Determine if a job is relevant for a software engineering / tech role."""
        prompt = f"""
        Analyze the following job posting and determine if it is relevant to a software engineering, data, or product role.
        Return ONLY a JSON object with a single boolean key "relevant".
        
        Job Title: {job_title}
        Job Description Preview: {job_description[:1000]}
        """
        try:
            result = self.generate_json(prompt)
            return result.get("relevant", False)
        except Exception:
            return False

    def extract_jobs_from_search(self, company: str, search_results: list, job_type: str) -> list:
        """Parse raw search results and extract valid job postings."""
        prompt = f"""
        I searched the web for {job_type} jobs at {company}.
        Here are the raw search snippets:
        {json.dumps(search_results, indent=2)}

        Extract a list of distinct, valid job postings for {company} from these snippets.
        Ignore anything that is not a job posting.
        Ensure they match the job type: '{job_type}'. For example, if job_type is 'internship', only extract internships.

        Return ONLY a JSON array of objects, where each object has:
        - "title": Job title
        - "url": URL of the job posting
        - "description": A short description based on the snippet
        - "location": Location if mentioned, else "Unknown"
        - "keywords": A list of up to 5 relevant technical keywords found in the title/snippet (e.g. ["Python", "Data"])

        If no valid jobs are found, return an empty array [].
        """
        try:
            results = self.generate_json(prompt)
            print("LLM RAW OUTPUT:", results)
            if isinstance(results, list):
                return results
            if isinstance(results, dict) and "jobs" in results:
                return results["jobs"]
            return []
        except Exception as e:
            logger.error(f"Failed to extract jobs via LLM: {e}")
            raise RuntimeError(f"LLM parsing failed: {e}")

    def tailor_resume(self, original_resume_data: dict, job_description: str) -> dict:
        """Truthfully tailor resume without hallucination."""
        prompt = f"""
        You are an expert ATS resume optimizer. Your task is to tailor the provided resume data to match the job description.
        
        CRITICAL RULES:
        1. NO HALLUCINATIONS: Do not invent any new experience, skills, metrics, or education.
        2. TRUTHFULNESS: You may only reorder skills, rephrase bullet points to emphasize relevant experience, and select the most relevant points.
        3. FORMAT: Output the exact same JSON structure as the original_resume_data, just with optimized content.
        
        Job Description:
        {job_description}
        
        Original Resume Data (JSON):
        {json.dumps(original_resume_data, indent=2)}
        """
        return self.generate_json(prompt)

    def prep_interview(self, company_name: str, job_description: str) -> dict:
        """Generate structured interview prep."""
        prompt = f"""
        Generate an interview preparation guide for {company_name} based on the following job description.
        
        CRITICAL STRUCTURE REQUIRED:
        Return a JSON object with EXACTLY these three keys:
        1. "summary": A short summary (1-2 paragraphs) about the company and its main products.
        2. "facts": An array of exactly 3 interesting facts about the company.
        3. "questions": An array of 5 to 10 possible interview questions tailored to the job description.
        
        Job Description:
        {job_description}
        """
        return self.generate_json(prompt)


# Global singleton instance
llm_client = LLMClient()
