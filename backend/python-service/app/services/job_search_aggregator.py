"""
Job Search Aggregator Service
Combines multiple free job APIs with intelligent fallback:
- JSearch (RapidAPI) - 100 requests/month free
- The Muse - Unlimited free
- Remotive - Unlimited free remote jobs
- Adzuna - Free tier available
- Arbeitnow - Global jobs, Unlimited free
"""

import httpx
import logging
import os
import json
from typing import List, Dict, Optional
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class JobSearchAggregator:
    """Aggregate jobs from multiple free APIs with smart fallback"""
    
    def __init__(self):
        self.jsearch_key = os.getenv("JSEARCH_API_KEY")
        self.adzuna_app_id = os.getenv("ADZUNA_APP_ID")
        self.adzuna_api_key = os.getenv("ADZUNA_API_KEY")
        
        logger.info("Job Search Aggregator initialized")
        logger.info("  The Muse: READY (Unlimited FREE)")
        logger.info("  Remotive: READY (Unlimited FREE remote)")
        logger.info("  Arbeitnow: READY (Global including India)")
        if self.jsearch_key:
            logger.info("  JSearch: READY (100/month)")
        if self.adzuna_app_id and self.adzuna_api_key:
            logger.info("  Adzuna: READY (5000/month)")
    
    async def search_jobs(
        self,
        query: str,
        location: str = None,
        job_type: str = None,
        country: str = None,
        remote_only: bool = False,
        date_posted: str = None,
        salary_min: int = None,
        salary_max: int = None,
        sort_by: str = None,
        limit: int = 20,
        use_all_apis: bool = True
    ) -> Dict:
        """Search for jobs from multiple free APIs"""
        all_jobs = []
        api_results = {}
        
        try:
            # Fast path: when use_all_apis is False, try quick/free sources and return early
            if not use_all_apis:
                # Prefer Remotive (fast + remote) then The Muse, then Arbeitnow
                try:
                    remotive_jobs = await self._search_remotive(query, location, limit, remote_only=remote_only)
                    if remotive_jobs:
                        all_jobs.extend(remotive_jobs[:limit])
                        api_results["remotive"] = len(remotive_jobs)
                        logger.info(f"Remotive (fast): Found {len(remotive_jobs)} jobs")
                        return {
                            "success": True,
                            "query": query,
                            "location": location,
                            "job_type_filter": job_type,
                            "total_jobs": min(len(remotive_jobs), limit),
                            "api_sources": api_results,
                            "jobs": remotive_jobs[:limit],
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.warning(f"Remotive (fast) failed: {e}")

                try:
                    muse_jobs = await self._search_themuse(query, location, limit, date_posted=date_posted)
                    if muse_jobs:
                        api_results["the_muse"] = len(muse_jobs)
                        logger.info(f"The Muse (fast): Found {len(muse_jobs)} jobs")
                        return {
                            "success": True,
                            "query": query,
                            "location": location,
                            "job_type_filter": job_type,
                            "total_jobs": min(len(muse_jobs), limit),
                            "api_sources": api_results,
                            "jobs": muse_jobs[:limit],
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.warning(f"The Muse (fast) failed: {e}")

                try:
                    arbeitnow_jobs = await self._search_arbeitnow(query, location, limit, remote_only=remote_only)
                    if arbeitnow_jobs:
                        api_results["arbeitnow"] = len(arbeitnow_jobs)
                        logger.info(f"Arbeitnow (fast): Found {len(arbeitnow_jobs)} jobs")
                        return {
                            "success": True,
                            "query": query,
                            "location": location,
                            "job_type_filter": job_type,
                            "total_jobs": min(len(arbeitnow_jobs), limit),
                            "api_sources": api_results,
                            "jobs": arbeitnow_jobs[:limit],
                            "timestamp": datetime.now().isoformat()
                        }
                except Exception as e:
                    logger.warning(f"Arbeitnow (fast) failed: {e}")

                # If all fast providers fail, fall through to full search below as last resort

            # 1. Search The Muse
            try:
                muse_jobs = await self._search_themuse(query, location, limit, date_posted=date_posted)
                if muse_jobs:
                    all_jobs.extend(muse_jobs)
                    api_results["the_muse"] = len(muse_jobs)
                    logger.info(f"The Muse: Found {len(muse_jobs)} jobs")
            except Exception as e:
                logger.warning(f"The Muse failed: {e}")
            
            # 2. Search Remotive
            try:
                remotive_jobs = await self._search_remotive(query, location, limit, remote_only=remote_only)
                if remotive_jobs:
                    all_jobs.extend(remotive_jobs)
                    api_results["remotive"] = len(remotive_jobs)
                    logger.info(f"Remotive: Found {len(remotive_jobs)} jobs")
            except Exception as e:
                logger.warning(f"Remotive failed: {e}")
            
            # 3. Search Arbeitnow (good for India)
            try:
                arbeitnow_jobs = await self._search_arbeitnow(query, location, limit, remote_only=remote_only)
                if arbeitnow_jobs:
                    all_jobs.extend(arbeitnow_jobs)
                    api_results["arbeitnow"] = len(arbeitnow_jobs)
                    logger.info(f"Arbeitnow: Found {len(arbeitnow_jobs)} jobs")
            except Exception as e:
                logger.warning(f"Arbeitnow failed: {e}")
            
            # 4. Search JSearch
            try:
                if self.jsearch_key:
                    jsearch_jobs = await self._search_jsearch(
                        query,
                        location,
                        limit,
                        job_type=job_type,
                        remote_only=remote_only,
                        date_posted=date_posted,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        sort_by=sort_by
                    )
                    if jsearch_jobs:
                        all_jobs.extend(jsearch_jobs)
                        api_results["jsearch"] = len(jsearch_jobs)
                        logger.info(f"JSearch: Found {len(jsearch_jobs)} jobs")
            except Exception as e:
                logger.warning(f"JSearch failed: {e}")
            
            # 5. Search Adzuna
            try:
                if self.adzuna_app_id and self.adzuna_api_key:
                    adzuna_jobs = await self._search_adzuna(
                        query,
                        location,
                        limit,
                        country=country,
                        remote_only=remote_only,
                        date_posted=date_posted,
                        salary_min=salary_min,
                        salary_max=salary_max,
                        sort_by=sort_by
                    )
                    if adzuna_jobs:
                        all_jobs.extend(adzuna_jobs)
                        api_results["adzuna"] = len(adzuna_jobs)
                        logger.info(f"Adzuna: Found {len(adzuna_jobs)} jobs")
            except Exception as e:
                logger.warning(f"Adzuna failed: {e}")
            
            # Remove duplicates
            all_jobs = self._deduplicate_jobs(all_jobs)
            all_jobs = all_jobs[:limit]
            
            if not all_jobs:
                logger.warning(f"No jobs found for '{query}' in {location}")
            
            return {
                "success": True,
                "query": query,
                "location": location,
                "job_type_filter": job_type,
                "total_jobs": len(all_jobs),
                "api_sources": api_results,
                "jobs": all_jobs,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Job search failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "jobs": []
            }
    
    async def _search_themuse(self, query: str, location: str = None, limit: int = 20, date_posted: str = None) -> List[Dict]:
        """Search The Muse API (Unlimited FREE)"""
        params = {
            "page": 0,
            "descending": "true"
        }
        
        if query:
            params["category"] = query
        
        if location and location.lower() != "remote":
            params["location"] = location
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://www.themuse.com/api/public/jobs",
                params=params
            )
            
            if response.status_code != 200:
                logger.warning(f"The Muse API error: {response.status_code}")
                return []
            
            data = response.json()
            jobs = data.get("results", [])
            
            transformed = []
            for job in jobs[:limit]:
                transformed.append({
                    "id": f"muse_{job.get('id')}",
                    "title": job.get("name"),
                    "company": job.get("company", {}).get("name", "Unknown"),
                    "location": job.get("locations", [{}])[0].get("name", "Remote"),
                    "salary": None,
                    "description": job.get("short_name", ""),
                    "url": job.get("refs", {}).get("landing_page", ""),
                    "source": "The Muse",
                    "job_type": "Full-time",
                    "posted_date": job.get("publication_date", ""),
                    "company_logo": job.get("company", {}).get("logo_url", ""),
                    "skills": []
                })
            
            return transformed
    
    async def _search_remotive(self, query: str, location: str = None, limit: int = 20, remote_only: bool = False) -> List[Dict]:
        """Search Remotive API for remote jobs (Unlimited FREE)"""
        params = {}
        
        if query:
            params["search"] = query
        
        params["limit"] = limit
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://remotive.com/api/remote-jobs",
                params=params
            )
            
            if response.status_code != 200:
                logger.warning(f"Remotive API error: {response.status_code}")
                return []
            
            data = response.json()
            jobs = data.get("jobs", [])
            
            transformed = []
            for job in jobs[:limit]:
                loc = job.get("candidate_required_location", "Remote") or "Remote"
                if remote_only and "remote" not in str(loc).lower():
                    continue
                transformed.append({
                    "id": f"remotive_{job.get('id')}",
                    "title": job.get("title"),
                    "company": job.get("company_name", "Unknown"),
                    "location": loc,
                    "salary": job.get("salary", ""),
                    "description": job.get("description", "")[:200],
                    "url": job.get("url", ""),
                    "source": "Remotive",
                    "job_type": "Full-time / Contract",
                    "posted_date": job.get("publication_date", ""),
                    "company_logo": "",
                    "skills": job.get("tags", []) if isinstance(job.get("tags"), list) else []
                })
            
            return transformed
    
    async def _search_arbeitnow(self, query: str, location: str = None, limit: int = 20, remote_only: bool = False) -> List[Dict]:
        """Search Arbeitnow API for global jobs (Unlimited FREE)"""
        params = {}
        if query:
            params["search"] = query
        params["page"] = 1
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://www.arbeitnow.com/api/v2/jobs",
                params=params
            )
            
            if response.status_code != 200:
                logger.warning(f"Arbeitnow API error: {response.status_code}")
                return []
            
            data = response.json()
            jobs = data.get("data", [])
            
            if location and location.lower() != "remote":
                jobs = [j for j in jobs if location.lower() in str(j.get("location", "")).lower()]
            
            transformed = []
            for job in jobs[:limit]:
                job_location = job.get("location", "")
                
                if remote_only:
                    if "remote" not in str(job_location).lower() and not job.get("remote", False):
                        continue
                
                if location and location.lower() == "india":
                    if "india" not in str(job_location).lower():
                        continue
                
                company_name = job.get("company", "Unknown")
                if isinstance(job.get("company"), dict):
                    company_name = job.get("company", {}).get("name", "Unknown")
                
                transformed.append({
                    "id": f"arbeitnow_{job.get('id')}",
                    "title": job.get("title"),
                    "company": company_name,
                    "location": job_location,
                    "salary": job.get("salary", ""),
                    "description": job.get("description", "")[:200] if job.get("description") else "",
                    "url": job.get("url", ""),
                    "source": "Arbeitnow",
                    "job_type": "Full-time",
                    "posted_date": job.get("created_at", ""),
                    "company_logo": "",
                    "skills": []
                })
            
            return transformed
    
    async def _search_jsearch(self, query: str, location: str = None, limit: int = 20, job_type: str = None, remote_only: bool = False, date_posted: str = None, salary_min: int = None, salary_max: int = None, sort_by: str = None) -> List[Dict]:
        """Search JSearch API (100 requests/month FREE)"""
        if not self.jsearch_key:
            return []
        
        headers = {
            "X-RapidAPI-Key": self.jsearch_key,
            "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
        }
        
        search_query = query
        if location:
            search_query = f"{query} {location}"
        
        date_map = {
            "today": "today",
            "3days": "3days",
            "week": "week",
            "month": "month"
        }
        date_param = date_map.get(date_posted, "month")
        
        params = {
            "query": search_query,
            "page": "1",
            "num_pages": "1",
            "date_posted": date_param
        }
        
        if job_type:
            params["employment_types"] = job_type
        if remote_only:
            params["remote_jobs_only"] = "true"
        if salary_min:
            params["salary_min"] = salary_min
        if salary_max:
            params["salary_max"] = salary_max
        if sort_by in {"date", "relevance"}:
            params["sort_by"] = sort_by
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                "https://jsearch.p.rapidapi.com/search",
                headers=headers,
                params=params
            )
            
            if response.status_code != 200:
                logger.warning(f"JSearch API error: {response.status_code}")
                return []
            
            data = response.json()
            jobs = data.get("data", [])
            
            transformed = []
            for job in jobs[:limit]:
                salary_text = ""
                if job.get("job_salary_currency_code"):
                    min_sal = job.get("job_salary_min", "")
                    max_sal = job.get("job_salary_max", "")
                    currency = job.get("job_salary_currency_code", "USD")
                    if min_sal or max_sal:
                        salary_text = f"{min_sal}-{max_sal} {currency}"
                
                transformed.append({
                    "id": f"jsearch_{job.get('job_id')}",
                    "title": job.get("job_title"),
                    "company": job.get("employer_name", "Unknown"),
                    "location": job.get("job_city", "Remote"),
                    "salary": salary_text,
                    "description": job.get("job_description", "")[:200],
                    "url": job.get("job_apply_link", ""),
                    "source": "JSearch",
                    "job_type": job.get("job_employment_type", "Full-time"),
                    "posted_date": job.get("job_posted_at_datetime_utc", ""),
                    "company_logo": job.get("employer_logo", ""),
                    "skills": job.get("job_required_skills", []) or []
                })
            
            if remote_only:
                transformed = [j for j in transformed if "remote" in str(j.get("location", "")).lower()]
            
            if salary_min or salary_max:
                filtered = []
                for job in transformed:
                    salary_field = job.get("salary")
                    if not salary_field:
                        continue
                    try:
                        parts = str(salary_field).split("-")
                        min_val = float(parts[0]) if parts and parts[0] else None
                        max_val = float(parts[1].split()[0]) if len(parts) > 1 else min_val
                    except Exception:
                        filtered.append(job)
                        continue
                    if salary_min and min_val and min_val < salary_min:
                        continue
                    if salary_max and max_val and max_val > salary_max:
                        continue
                    filtered.append(job)
                transformed = filtered
            
            if date_posted:
                filtered = []
                now = datetime.utcnow()
                for job in transformed:
                    posted = job.get("posted_date")
                    if not posted:
                        continue
                    try:
                        posted_dt = datetime.fromisoformat(posted.replace("Z", "+00:00")).replace(tzinfo=None)
                        age_days = (now - posted_dt).days
                        if date_posted == "today" and age_days <= 1:
                            filtered.append(job)
                        elif date_posted == "3days" and age_days <= 3:
                            filtered.append(job)
                        elif date_posted == "week" and age_days <= 7:
                            filtered.append(job)
                        elif date_posted == "month" and age_days <= 31:
                            filtered.append(job)
                    except Exception:
                        filtered.append(job)
                transformed = filtered
            
            return transformed
    
    async def _search_adzuna(self, query: str, location: str = None, limit: int = 20, country: Optional[str] = None, remote_only: bool = False, date_posted: str = None, salary_min: int = None, salary_max: int = None, sort_by: str = None) -> List[Dict]:
        """Search Adzuna API (5000 searches/month free)"""
        if not self.adzuna_app_id or not self.adzuna_api_key:
            return []
        
        country_code = (country or "us").lower()
        
        params = {
            "app_id": self.adzuna_app_id,
            "app_key": self.adzuna_api_key,
            "results_per_page": limit,
            "what": query,
            "sort_by": sort_by if sort_by in {"date", "relevance", "salary"} else "date"
        }
        
        if location and location.lower() != "remote":
            params["where"] = location
        if salary_min:
            params["salary_min"] = salary_min
        if salary_max:
            params["salary_max"] = salary_max
        if date_posted in {"today", "3days", "week", "month"}:
            window_map = {
                "today": 1,
                "3days": 3,
                "week": 7,
                "month": 31
            }
            params["max_days_old"] = window_map[date_posted]
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"https://api.adzuna.com/v1/api/jobs/{country_code}/search/1",
                params=params
            )
            
            if response.status_code != 200:
                logger.warning(f"Adzuna API error: {response.status_code}")
                return []
            
            data = response.json()
            jobs = data.get("results", [])
            
            transformed = []
            for job in jobs[:limit]:
                if remote_only:
                    loc_text = job.get("location", {}).get("display_name", "")
                    if "remote" not in str(loc_text).lower():
                        continue
                transformed.append({
                    "id": f"adzuna_{job.get('id')}",
                    "title": job.get("title"),
                    "company": job.get("company", {}).get("display_name", "Unknown"),
                    "location": job.get("location", {}).get("display_name", "Unknown"),
                    "salary": job.get("salary_max", ""),
                    "description": job.get("description", "")[:200],
                    "url": job.get("redirect_url", ""),
                    "source": "Adzuna",
                    "job_type": "Full-time",
                    "posted_date": job.get("created", ""),
                    "company_logo": "",
                    "skills": []
                })
            
            return transformed
    
    def _deduplicate_jobs(self, jobs: List[Dict]) -> List[Dict]:
        """Remove duplicate job listings"""
        seen = set()
        unique_jobs = []
        
        for job in jobs:
            # Create a unique identifier
            job_id = f"{job.get('title', '')}_{job.get('company', '')}_{job.get('location', '')}"
            
            if job_id not in seen:
                seen.add(job_id)
                unique_jobs.append(job)
        
        return unique_jobs
