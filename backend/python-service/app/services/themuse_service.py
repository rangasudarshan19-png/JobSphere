"""
The Muse Job Search Service
Completely FREE - No API key required!
"""

import httpx
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

THEMUSE_BASE_URL = "https://www.themuse.com/api/public"


class TheMuseJobSearchService:
    """Search for jobs using The Muse API - Premium companies, Completely FREE"""
    
    def __init__(self):
        self.enabled = True  # No API key required!
        logger.info("The Muse API enabled (Unlimited FREE searches)")
    
    async def search_jobs(
        self,
        query: str = None,
        location: str = None,
        category: str = None,  # e.g., "Software Engineering", "Data Science"
        level: str = None,  # Entry Level, Mid Level, Senior Level
        company: str = None,
        page: int = 0,
        descending: bool = True
    ) -> List[Dict]:
        """
        Search for jobs using The Muse API
        
        Args:
            query: Search keywords
            location: City/State/Country or "Remote", "Flexible / Remote"
            category: Job category
            level: Experience level
            company: Company name
            page: Page number (0-indexed)
            descending: Sort by newest first
        
        Returns:
            List of job dictionaries
        """
        try:
            # Build query parameters
            params = {
                "page": page,
                "descending": str(descending).lower()
            }
            
            if query:
                # The Muse doesn't have a general query param, use category or company
                params["category"] = query
            
            if location:
                params["location"] = location
            
            if category:
                params["category"] = category
            
            if level:
                params["level"] = level
            
            if company:
                params["company"] = company
            
            url = f"{THEMUSE_BASE_URL}/jobs"
            
            logger.info(f"Searching The Muse: '{query or 'all'}' in '{location or 'any location'}'")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"The Muse API error: {response.status_code}")
                    return []
                
                data = response.json()
                jobs = data.get("results", [])
                
                if not jobs:
                    logger.info(f"No jobs found on The Muse")
                    return []
                
                logger.info(f"Found {len(jobs)} jobs from The Muse")
                
                # Transform to our format
                transformed = [self._transform_job(job) for job in jobs]
                return transformed
        
        except Exception as e:
            logger.error(f"The Muse search failed: {e}")
            return []
    
    def _transform_job(self, job: Dict) -> Dict:
        """Transform The Muse API response to our format"""
        # Extract company info
        company_info = job.get("company", {})
        
        # Extract locations
        locations = job.get("locations", [])
        location_str = ", ".join([loc.get("name", "") for loc in locations]) if locations else "Not specified"
        
        # Extract job type
        job_type = self._extract_job_type(job.get("name", ""))
        
        return {
            "job_id": str(job.get("id", "")),
            "title": job.get("name", ""),
            "company": company_info.get("name", ""),
            "location": location_str,
            "salary": "Not specified",  # The Muse doesn't provide salary
            "job_type": job_type,
            "description": job.get("contents", ""),
            "requirements": self._extract_requirements(job.get("contents", "")),
            "external_url": job.get("refs", {}).get("landing_page", ""),
            "source": "The Muse",
            "posted_date": job.get("publication_date", ""),
            "company_logo": company_info.get("refs", {}).get("logo", None),
            "categories": [cat.get("name", "") for cat in job.get("categories", [])],
            "levels": [lvl.get("name", "") for lvl in job.get("levels", [])]
        }
    
    def _extract_job_type(self, title: str) -> str:
        """Extract job type from title"""
        title_lower = title.lower()
        if "intern" in title_lower:
            return "Internship"
        elif "contract" in title_lower:
            return "Contract"
        elif "part-time" in title_lower or "part time" in title_lower:
            return "Part-time"
        return "Full-time"
    
    def _extract_requirements(self, content: str) -> List[str]:
        """Extract requirements from job description"""
        # Simple extraction - can be improved with NLP
        requirements = []
        if "bachelor" in content.lower() or "degree" in content.lower():
            requirements.append("Bachelor's degree preferred")
        if "python" in content.lower():
            requirements.append("Python experience")
        if "javascript" in content.lower():
            requirements.append("JavaScript experience")
        return requirements


# Singleton instance
themuse_service = TheMuseJobSearchService()
