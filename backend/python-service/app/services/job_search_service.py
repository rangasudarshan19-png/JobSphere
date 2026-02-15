"""
Job Search Service - Search for jobs using JSearch API (RapidAPI)
Free tier: 100 requests/month
"""

import os
import httpx
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# JSearch API configuration (RapidAPI)
JSEARCH_API_KEY = os.getenv("JSEARCH_API_KEY")  # RapidAPI key
JSEARCH_API_HOST = "jsearch.p.rapidapi.com"
JSEARCH_BASE_URL = "https://jsearch.p.rapidapi.com"


class JobSearchService:
    """Search for jobs across multiple platforms (Indeed, LinkedIn, Glassdoor, etc.)"""
    
    def __init__(self):
        self.api_key = JSEARCH_API_KEY
        self.enabled = JSEARCH_API_KEY is not None
        
        if self.enabled:
            logger.info("JSearch API enabled for job searching (100 free searches/month)")
            logger.info(f"   API Key loaded: {self.api_key[:20]}...")
        else:
            logger.info("JSEARCH_API_KEY not found in environment variables!")
            logger.info("   Add JSEARCH_API_KEY to your .env file and restart the server")
    async def search_jobs(
        self,
        query: str,
        location: str = None,
        num_pages: int = 1,
        date_posted: str = "all"  # all, today, 3days, week, month
    ) -> List[Dict]:
        """
        Search for jobs using JSearch API
        
        Args:
            query: Job title/keywords (e.g., "QA Engineer", "Python Developer")
            location: Location (e.g., "Bangalore", "Remote", "USA")
            num_pages: Number of pages to fetch (each page ~10 jobs)
            date_posted: Filter by posting date
        
        Returns:
            List of job dictionaries
        """
        if not self.enabled:
            raise ValueError(
                "JSearch API key not configured. "
                "Please add JSEARCH_API_KEY to your .env file and restart the server. "
                "Get your free API key at: https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch"
            )
        
        try:
            headers = {
                "X-RapidAPI-Key": self.api_key,
                "X-RapidAPI-Host": JSEARCH_API_HOST
            }
            
            params = {
                "query": f"{query} {location}" if location else query,
                "page": "1",
                "num_pages": str(num_pages),
                "date_posted": date_posted
            }
            
            logger.info(f"Searching REAL jobs via JSearch API: '{query}' in '{location or 'any location'}'")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{JSEARCH_BASE_URL}/search",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    error_msg = f"JSearch API error: {response.status_code} - {response.text}"
                    logger.error(f"{error_msg}")
                    raise Exception(error_msg)
                
                data = response.json()
                jobs = data.get("data", [])
                
                if not jobs:
                    logger.info(f"No jobs found for query: {query} in {location}")
                    return []
                
                logger.info(f"Found {len(jobs)} REAL jobs from Indeed, LinkedIn, Glassdoor")
                # Transform to our format
                transformed = [self._transform_job(job) for job in jobs]
                logger.info(f"   Transformed {len(transformed)} jobs successfully")
                return transformed
        
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            raise
    
    def _transform_job(self, job: Dict) -> Dict:
        """Transform JSearch API response to our format"""
        return {
            "job_id": job.get("job_id"),
            "title": job.get("job_title", ""),
            "company": job.get("employer_name", ""),
            "location": job.get("job_city", "") or job.get("job_country", ""),
            "salary": self._format_salary(job),
            "job_type": job.get("job_employment_type", "Full-time"),
            "description": job.get("job_description", ""),
            "requirements": job.get("job_highlights", {}).get("Qualifications", []),
            "external_url": job.get("job_apply_link", ""),
            "source": "JSearch (Real Jobs)",
            "posted_date": job.get("job_posted_at_datetime_utc", ""),
            "company_logo": job.get("employer_logo", "")
        }
    
    def _format_salary(self, job: Dict) -> str:
        """Format salary from various fields"""
        if job.get("job_salary_currency"):
            min_sal = job.get("job_min_salary")
            max_sal = job.get("job_max_salary")
            currency = job.get("job_salary_currency", "USD")
            
            if min_sal and max_sal:
                return f"{currency} {min_sal:,} - {max_sal:,}"
            elif min_sal:
                return f"{currency} {min_sal:,}+"
        
        return "Not specified"


# Singleton instance
job_search_service = JobSearchService()

