"""
Multi-Source Job Search Service
Combines JSearch, Adzuna, The Muse, and Remotive APIs
Smart fallback and result aggregation
"""

import asyncio
from typing import List, Dict, Optional
import logging

from app.services.job_search_service import job_search_service as jsearch_service
from app.services.adzuna_service import adzuna_service
from app.services.themuse_service import themuse_service
from app.services.remotive_service import remotive_service

logger = logging.getLogger(__name__)


class MultiSourceJobSearchService:
    """
    Unified job search across multiple APIs
    - JSearch: 100/month (primary, high quality)
    - Adzuna: 5,000/month (backup, good coverage)
    - The Muse: Unlimited (premium companies)
    - Remotive: Unlimited (remote jobs only)
    """
    
    def __init__(self):
        self.jsearch = jsearch_service
        self.adzuna = adzuna_service
        self.themuse = themuse_service
        self.remotive = remotive_service
        
        # Track API usage for smart distribution
        self.api_usage = {
            "jsearch": 0,
            "adzuna": 0,
            "themuse": 0,
            "remotive": 0
        }
        
        logger.info("[EMOJI] Multi-Source Job Search Service initialized")
        logger.info(f"   [SYMBOL] JSearch: {'Enabled' if self.jsearch.enabled else 'Disabled'}")
        logger.info(f"   [SYMBOL] Adzuna: {'Enabled' if self.adzuna.enabled else 'Disabled'}")
        logger.info(f"   [SYMBOL] The Muse: Enabled")
        logger.info(f"   [SYMBOL] Remotive: Enabled")
    
    async def search_jobs(
        self,
        query: str,
        location: str = None,
        strategy: str = "smart",  # smart, aggregate, jsearch_only, free_only
        max_results: int = 50
    ) -> Dict:
        """
        Search jobs across multiple APIs with different strategies
        
        Args:
            query: Job search query
            location: Location filter
            strategy: Search strategy:
                - "smart": Try APIs in order, stop at first success
                - "aggregate": Combine results from all APIs
                - "jsearch_only": Use only JSearch
                - "free_only": Use only unlimited free APIs (Muse + Remotive)
            max_results: Maximum number of results
        
        Returns:
            Dict with jobs and metadata
        """
        logger.info(f"[EMOJI] Multi-source search: '{query}' in '{location or 'any'}' (strategy: {strategy})")
        
        if strategy == "smart":
            return await self._smart_search(query, location, max_results)
        elif strategy == "aggregate":
            return await self._aggregate_search(query, location, max_results)
        elif strategy == "jsearch_only":
            return await self._jsearch_only_search(query, location, max_results)
        elif strategy == "free_only":
            return await self._free_only_search(query, location, max_results)
        else:
            return await self._smart_search(query, location, max_results)
    
    async def _smart_search(self, query: str, location: str, max_results: int) -> Dict:
        """
        Smart sequential fallback strategy
        Try APIs in order of quality, stop at first success
        """
        # Try JSearch first (best quality)
        if self.jsearch.enabled:
            try:
                logger.info("1️⃣ Trying JSearch (primary)...")
                jobs = await self.jsearch.search_jobs(query, location, num_pages=1)
                if jobs:
                    self.api_usage["jsearch"] += 1
                    logger.info(f"[SYMBOL] Success with JSearch: {len(jobs)} jobs")
                    return {
                        "jobs": jobs[:max_results],
                        "total": len(jobs),
                        "source": "JSearch",
                        "sources_used": ["JSearch"],
                        "strategy": "smart"
                    }
            except Exception as e:
                logger.warning(f"[SYMBOL]️ JSearch failed: {e}")
        
        # Fallback to Adzuna (5,000/month free)
        if self.adzuna.enabled:
            try:
                logger.info("2️⃣ Trying Adzuna (fallback)...")
                jobs = await self.adzuna.search_jobs(query, location)
                if jobs:
                    self.api_usage["adzuna"] += 1
                    logger.info(f"[SYMBOL] Success with Adzuna: {len(jobs)} jobs")
                    return {
                        "jobs": jobs[:max_results],
                        "total": len(jobs),
                        "source": "Adzuna",
                        "sources_used": ["Adzuna"],
                        "strategy": "smart"
                    }
            except Exception as e:
                logger.warning(f"[SYMBOL]️ Adzuna failed: {e}")
        
        # Fallback to The Muse (unlimited free)
        try:
            logger.info("3️⃣ Trying The Muse (fallback)...")
            jobs = await self.themuse.search_jobs(query, location)
            if jobs:
                self.api_usage["themuse"] += 1
                logger.info(f"[SYMBOL] Success with The Muse: {len(jobs)} jobs")
                return {
                    "jobs": jobs[:max_results],
                    "total": len(jobs),
                    "source": "The Muse",
                    "sources_used": ["The Muse"],
                    "strategy": "smart"
                }
        except Exception as e:
            logger.warning(f"[SYMBOL]️ The Muse failed: {e}")
        
        # Last resort: Remotive (remote jobs only)
        try:
            logger.info("4️⃣ Trying Remotive (last resort - remote only)...")
            category = self._map_query_to_category(query)
            jobs = await self.remotive.search_jobs(category=category, search=query)
            if jobs:
                self.api_usage["remotive"] += 1
                logger.info(f"[SYMBOL] Success with Remotive: {len(jobs)} jobs")
                return {
                    "jobs": jobs[:max_results],
                    "total": len(jobs),
                    "source": "Remotive",
                    "sources_used": ["Remotive"],
                    "strategy": "smart"
                }
        except Exception as e:
            logger.warning(f"[SYMBOL]️ Remotive failed: {e}")
        
        # All APIs failed
        logger.error("[SYMBOL] All job search APIs failed")
        return {
            "jobs": [],
            "total": 0,
            "source": "None",
            "sources_used": [],
            "strategy": "smart",
            "error": "All APIs failed"
        }
    
    async def _aggregate_search(self, query: str, location: str, max_results: int) -> Dict:
        """
        Aggregate results from all APIs in parallel
        Combine and deduplicate results
        """
        logger.info("[EMOJI] Aggregating results from all APIs...")
        
        # Search all APIs in parallel
        tasks = []
        sources_attempted = []
        
        if self.jsearch.enabled:
            tasks.append(self._safe_jsearch(query, location))
            sources_attempted.append("JSearch")
        
        if self.adzuna.enabled:
            tasks.append(self._safe_adzuna(query, location))
            sources_attempted.append("Adzuna")
        
        tasks.append(self._safe_themuse(query, location))
        sources_attempted.append("The Muse")
        
        tasks.append(self._safe_remotive(query))
        sources_attempted.append("Remotive")
        
        # Wait for all API calls
        results = await asyncio.gather(*tasks)
        
        # Combine results
        all_jobs = []
        sources_succeeded = []
        
        for i, jobs in enumerate(results):
            if jobs:
                all_jobs.extend(jobs)
                sources_succeeded.append(sources_attempted[i])
                logger.info(f"   [SYMBOL] {sources_attempted[i]}: {len(jobs)} jobs")
        
        # Deduplicate by URL and title
        unique_jobs = self._deduplicate_jobs(all_jobs)
        
        logger.info(f"[SYMBOL] Aggregated {len(unique_jobs)} unique jobs from {len(sources_succeeded)} sources")
        
        return {
            "jobs": unique_jobs[:max_results],
            "total": len(unique_jobs),
            "source": "Multiple Sources",
            "sources_used": sources_succeeded,
            "strategy": "aggregate",
            "breakdown": {source: len([j for j in unique_jobs if j.get("source") == source]) 
                         for source in sources_succeeded}
        }
    
    async def _jsearch_only_search(self, query: str, location: str, max_results: int) -> Dict:
        """Use only JSearch API"""
        if not self.jsearch.enabled:
            return {"jobs": [], "total": 0, "error": "JSearch not enabled"}
        
        jobs = await self.jsearch.search_jobs(query, location, num_pages=1)
        self.api_usage["jsearch"] += 1
        
        return {
            "jobs": jobs[:max_results],
            "total": len(jobs),
            "source": "JSearch",
            "sources_used": ["JSearch"],
            "strategy": "jsearch_only"
        }
    
    async def _free_only_search(self, query: str, location: str, max_results: int) -> Dict:
        """Use only unlimited free APIs (The Muse + Remotive)"""
        logger.info("🆓 Using only unlimited free APIs...")
        
        # Search both in parallel
        tasks = [
            self._safe_themuse(query, location),
            self._safe_remotive(query)
        ]
        
        results = await asyncio.gather(*tasks)
        
        all_jobs = []
        sources = []
        
        if results[0]:
            all_jobs.extend(results[0])
            sources.append("The Muse")
        if results[1]:
            all_jobs.extend(results[1])
            sources.append("Remotive")
        
        unique_jobs = self._deduplicate_jobs(all_jobs)
        
        return {
            "jobs": unique_jobs[:max_results],
            "total": len(unique_jobs),
            "source": "Free APIs",
            "sources_used": sources,
            "strategy": "free_only"
        }
    
    # Safe wrappers that don't throw exceptions
    async def _safe_jsearch(self, query: str, location: str) -> List[Dict]:
        try:
            return await self.jsearch.search_jobs(query, location, num_pages=1)
        except:
            return []
    
    async def _safe_adzuna(self, query: str, location: str) -> List[Dict]:
        try:
            return await self.adzuna.search_jobs(query, location)
        except:
            return []
    
    async def _safe_themuse(self, query: str, location: str) -> List[Dict]:
        try:
            return await self.themuse.search_jobs(query, location)
        except:
            return []
    
    async def _safe_remotive(self, query: str) -> List[Dict]:
        try:
            category = self._map_query_to_category(query)
            return await self.remotive.search_jobs(category=category, search=query)
        except:
            return []
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Deduplicate jobs by URL and title"""
        seen = set()
        unique = []
        
        for job in jobs:
            # Create unique identifier from URL or title+company
            identifier = job.get("external_url") or f"{job.get('title')}:{job.get('company')}"
            
            if identifier not in seen:
                seen.add(identifier)
                unique.append(job)
        
        return unique
    
    def _map_query_to_category(self, query: str) -> str:
        """Map search query to Remotive category"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["developer", "engineer", "programmer", "software", "python", "java", "javascript"]):
            return "software-dev"
        elif any(word in query_lower for word in ["data", "analyst", "scientist", "ml", "ai"]):
            return "data"
        elif any(word in query_lower for word in ["design", "designer", "ux", "ui"]):
            return "design"
        elif any(word in query_lower for word in ["marketing", "content", "seo"]):
            return "marketing"
        elif any(word in query_lower for word in ["support", "customer", "success"]):
            return "customer-support"
        elif any(word in query_lower for word in ["sales", "account"]):
            return "sales"
        else:
            return "software-dev"  # Default
    
    def get_usage_stats(self) -> Dict:
        """Get API usage statistics"""
        return {
            "usage": self.api_usage,
            "apis_enabled": {
                "jsearch": self.jsearch.enabled,
                "adzuna": self.adzuna.enabled,
                "themuse": True,
                "remotive": True
            }
        }


# Singleton instance
multi_search_service = MultiSourceJobSearchService()
