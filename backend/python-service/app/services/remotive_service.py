"""
Remotive Job Search Service
Completely FREE - No API key required!
Focus: Remote jobs only
"""

import httpx
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

REMOTIVE_BASE_URL = "https://remotive.com/api/remote-jobs"


class RemotiveJobSearchService:
    """Search for remote jobs using Remotive API - Completely FREE"""
    
    def __init__(self):
        self.enabled = True  # No API key required!
        logger.info("Remotive API enabled (Unlimited FREE remote job searches)")
    
    async def search_jobs(
        self,
        category: str = None,  # software-dev, customer-support, design, etc.
        company: str = None,
        search: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        Search for remote jobs using Remotive API
        
        Args:
            category: Job category slug (software-dev, data, design, etc.)
            company: Company name
            search: Search query
            limit: Number of results (max 50)
        
        Returns:
            List of job dictionaries
        """
        try:
            # Build query parameters
            params = {
                "limit": min(limit, 50)
            }
            
            if category:
                params["category"] = category
            
            if company:
                params["company_name"] = company
            
            if search:
                params["search"] = search
            
            logger.info(f"Searching Remotive (Remote Jobs): '{search or category or 'all'}'")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(REMOTIVE_BASE_URL, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Remotive API error: {response.status_code}")
                    return []
                
                data = response.json()
                jobs = data.get("jobs", [])
                
                if not jobs:
                    logger.info(f"No remote jobs found on Remotive")
                    return []
                
                logger.info(f"Found {len(jobs)} remote jobs from Remotive")
                
                # Transform to our format
                transformed = [self._transform_job(job) for job in jobs]
                return transformed
        
        except Exception as e:
            logger.error(f"Remotive search failed: {e}")
            return []
    
    def _transform_job(self, job: Dict) -> Dict:
        """Transform Remotive API response to our format"""
        return {
            "job_id": str(job.get("id", "")),
            "title": job.get("title", ""),
            "company": job.get("company_name", ""),
            "location": "Remote",  # All Remotive jobs are remote
            "salary": job.get("salary", "Not specified"),
            "job_type": job.get("job_type", "Full-time"),
            "description": job.get("description", ""),
            "requirements": self._extract_tags(job.get("tags", [])),
            "external_url": job.get("url", ""),
            "source": "Remotive (Remote Jobs)",
            "posted_date": job.get("publication_date", ""),
            "company_logo": job.get("company_logo", None),
            "category": job.get("category", ""),
            "candidate_required_location": job.get("candidate_required_location", "Anywhere")
        }
    
    def _extract_tags(self, tags: List[str]) -> List[str]:
        """Convert tags to requirements"""
        return tags[:5] if tags else []  # Return first 5 tags as requirements


# Singleton instance
remotive_service = RemotiveJobSearchService()
