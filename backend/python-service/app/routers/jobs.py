from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from pydantic import BaseModel

from app.routers.auth import get_current_user_optional
from app.models.user import User
from app.services.job_search_aggregator import JobSearchAggregator
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jobs", tags=["Jobs"])
job_search_aggregator = JobSearchAggregator()


class JobSearchRequest(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    country: Optional[str] = None
    remote_only: Optional[bool] = False
    date_posted: Optional[str] = None
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    sort_by: Optional[str] = None
    limit: Optional[int] = 20
    use_all_apis: Optional[bool] = True


@router.post("/search")
async def search_jobs(
    request: JobSearchRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """Public job search endpoint backed by the multi-API aggregator."""
    try:
        query = request.query or "Software Engineer"
        location = request.location or "Remote"

        if current_user:
            logger.info(f"Job search by user {current_user.id}: '{query}' in {location}")
        else:
            logger.info(f"Job search (anonymous): '{query}' in {location}")
        result = await job_search_aggregator.search_jobs(
            query=query,
            location=location,
            job_type=request.job_type,
            country=request.country,
            remote_only=request.remote_only,
            date_posted=request.date_posted,
            salary_min=request.salary_min,
            salary_max=request.salary_max,
            sort_by=request.sort_by,
            limit=request.limit,
            use_all_apis=request.use_all_apis
        )
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job search endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Job search failed: {str(e)}"
        )
