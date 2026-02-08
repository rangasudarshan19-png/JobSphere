"""
Adzuna Job Search Service
Free tier: 5,000 requests/month
"""

import os
import httpx
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

# Adzuna API configuration
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "1784d309")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "b0f826f21d9cdf107de454edfd41396e")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"


class AdzunaJobSearchService:
    """Search for jobs using Adzuna API - 5,000 free searches/month"""
    
    def __init__(self):
        self.app_id = ADZUNA_APP_ID
        self.app_key = ADZUNA_APP_KEY
        self.enabled = ADZUNA_APP_ID and ADZUNA_APP_KEY
        
        if self.enabled:
            logger.info("[SYMBOL] Adzuna API enabled (5,000 free searches/month)")
            logger.info(f"   App ID: {self.app_id}")
        else:
            logger.warning("[SYMBOL]️ Adzuna API not configured")
    
    async def search_jobs(
        self,
        query: str,
        location: str = None,
        country: str = "us",  # us, uk, in, ca, au, etc.
        results_per_page: int = 20,
        page: int = 1,
        sort_by: str = "date"  # date, salary, relevance
    ) -> List[Dict]:
        """
        Search for jobs using Adzuna API
        
        Args:
            query: Job title/keywords
            location: City or region
            country: Country code (us, uk, in, ca, au, de, fr, etc.)
            results_per_page: Number of results (max 50)
            page: Page number
            sort_by: Sort order (date, salary, relevance)
        
        Returns:
            List of job dictionaries
        """
        if not self.enabled:
            logger.warning("Adzuna API not configured")
            return []
        
        try:
            # Build query parameters
            params = {
                "app_id": self.app_id,
                "app_key": self.app_key,
                "results_per_page": min(results_per_page, 50),
                "what": query,
                "sort_by": sort_by
            }
            
            if location:
                params["where"] = location
            
            # Construct URL
            url = f"{ADZUNA_BASE_URL}/{country}/search/{page}"
            
            logger.info(f"[EMOJI] Searching Adzuna: '{query}' in '{location or 'any location'}' ({country})")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"[SYMBOL] Adzuna API error: {response.status_code} - {response.text}")
                    return []
                
                data = response.json()
                jobs = data.get("results", [])
                
                if not jobs:
                    logger.info(f"[SYMBOL]️ No jobs found on Adzuna for: {query}")
                    return []
                
                logger.info(f"[SYMBOL] Found {len(jobs)} jobs from Adzuna")
                
                # Transform to our format
                transformed = [self._transform_job(job) for job in jobs]
                return transformed
        
        except Exception as e:
            logger.error(f"[SYMBOL] Adzuna search failed: {e}")
            return []
    
    def _transform_job(self, job: Dict) -> Dict:
        """Transform Adzuna API response to our format"""
        # Extract salary info
        salary = self._format_salary(job)
        
        return {
            "job_id": job.get("id", ""),
            "title": job.get("title", ""),
            "company": job.get("company", {}).get("display_name", ""),
            "location": job.get("location", {}).get("display_name", ""),
            "salary": salary,
            "job_type": self._extract_job_type(job.get("description", "")),
            "description": job.get("description", ""),
            "requirements": [],
            "external_url": job.get("redirect_url", ""),
            "source": "Adzuna",
            "posted_date": job.get("created", ""),
            "company_logo": None,
            "category": job.get("category", {}).get("label", ""),
            "contract_type": job.get("contract_type", ""),
            "contract_time": job.get("contract_time", "")
        }
    
    def _format_salary(self, job: Dict) -> str:
        """Format salary from Adzuna fields"""
        salary_min = job.get("salary_min")
        salary_max = job.get("salary_max")
        
        if salary_min and salary_max:
            return f"${salary_min:,.0f} - ${salary_max:,.0f}"
        elif salary_min:
            return f"${salary_min:,.0f}+"
        elif salary_max:
            return f"Up to ${salary_max:,.0f}"
        
        return "Not specified"
    
    def _extract_job_type(self, description: str) -> str:
        """Extract job type from description"""
        desc_lower = description.lower()
        if "full-time" in desc_lower or "full time" in desc_lower:
            return "Full-time"
        elif "part-time" in desc_lower or "part time" in desc_lower:
            return "Part-time"
        elif "contract" in desc_lower:
            return "Contract"
        elif "internship" in desc_lower or "intern" in desc_lower:
            return "Internship"
        return "Full-time"


# Singleton instance
adzuna_service = AdzunaJobSearchService()
