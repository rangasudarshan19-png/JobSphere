"""
Job Matching API Endpoints
- Save enhanced resumes
- Search and match jobs
- Track matched jobs
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import json
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

from app.utils.database import get_db
from app.routers.auth import get_current_user
from app.models.user import User
from app.models.enhanced_resume import EnhancedResume, MatchedJob, UserJobPreferences
from app.services.resume_analyzer import resume_analyzer
from app.services.job_search_service import job_search_service
from app.services.job_matcher import job_matcher
from app.services.multi_search_service import multi_search_service

router = APIRouter(prefix="/api/job-matching", tags=["Job Matching"])


# ==================== Request/Response Models ====================

class SaveResumeRequest(BaseModel):
    resume_text: str
    original_text: Optional[str] = None

class JobSearchRequest(BaseModel):
    query: Optional[str] = None  # Auto-detect from resume if not provided
    location: Optional[str] = None
    min_match_score: Optional[int] = 80
    num_pages: Optional[int] = 1

class JobPreferencesRequest(BaseModel):
    preferred_job_titles: Optional[List[str]] = None
    preferred_locations: Optional[List[str]] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    job_types: Optional[List[str]] = None
    remote_preference: Optional[str] = "no_preference"
    min_match_score: Optional[int] = 80
    email_alerts_enabled: Optional[bool] = True
    alert_frequency: Optional[str] = "daily"


class UpdateJobStatusRequest(BaseModel):
    job_id: int
    is_saved: Optional[bool] = None
    is_applied: Optional[bool] = None
    notes: Optional[str] = None


# ==================== Endpoints ====================

@router.post("/save-enhanced-resume")
async def save_enhanced_resume(
    request: SaveResumeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Save AI-enhanced resume and extract profile for job matching
    """
    try:
        # Extract profile from resume
        logger.info(f"Extracting profile from resume for user {current_user.id}...")
        profile = await resume_analyzer.extract_profile(request.resume_text)
        
        # Create enhanced resume record
        enhanced_resume = EnhancedResume(
            user_id=current_user.id,
            original_resume_text=request.original_text or request.resume_text,
            enhanced_resume_text=request.resume_text,
            skills=json.dumps(profile.get('skills', [])),
            experience_years=profile.get('experience_years'),
            job_titles=json.dumps(profile.get('job_titles', [])),
            location_preference=profile.get('location_preference'),
            education=json.dumps(profile.get('education', [])),
            certifications=json.dumps(profile.get('certifications', [])),
            is_active=1
        )
        
        # Deactivate previous resumes
        db.query(EnhancedResume).filter(
            EnhancedResume.user_id == current_user.id,
            EnhancedResume.is_active == 1
        ).update({"is_active": 0})
        
        db.add(enhanced_resume)
        db.commit()
        db.refresh(enhanced_resume)
        
        logger.info(f"Resume saved with {len(profile.get('skills', []))} skills extracted")
        return {
            "success": True,
            "resume_id": enhanced_resume.id,
            "profile": profile,
            "message": "Resume saved and profile extracted successfully"
        }
        
    except Exception as e:
        logger.error(f"Failed to save resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save resume: {str(e)}"
        )


@router.post("/update-job-status")
async def update_job_status(
    request: UpdateJobStatusRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update a job's tracking status (saved/applied) and optional notes.
    Uses existing matched_jobs records so the board reflects saved and applied states.
    """
    try:
        job = db.query(MatchedJob).filter(
            MatchedJob.id == request.job_id,
            MatchedJob.user_id == current_user.id
        ).first()

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        if request.is_saved is not None:
            job.is_saved = 1 if request.is_saved else 0

        if request.is_applied is not None:
            job.is_applied = 1 if request.is_applied else 0
            job.applied_date = datetime.utcnow() if request.is_applied else None

        if request.notes is not None:
            # Store notes in match_reason to avoid schema changes
            job.match_reason = request.notes[:255]

        db.commit()
        db.refresh(job)

        return {
            "success": True,
            "job": {
                "id": job.id,
                "title": job.job_title,
                "company": job.company,
                "is_saved": job.is_saved,
                "is_applied": job.is_applied,
                "applied_date": job.applied_date.isoformat() if job.applied_date else None,
                "notes": job.match_reason
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update job status: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job status: {str(e)}"
        )


@router.get("/tracking-board")
async def get_tracking_board(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Return all matched jobs for the user with tracking fields for the board UI.
    """
    try:
        jobs = db.query(MatchedJob).filter(
            MatchedJob.user_id == current_user.id
        ).order_by(MatchedJob.created_at.desc()).all()

        return {
            "success": True,
            "jobs": [
                {
                    "id": job.id,
                    "title": job.job_title,
                    "company": job.company,
                    "location": job.location,
                    "salary": job.salary_range,
                    "job_type": job.job_type,
                    "source": job.source,
                    "external_url": job.external_url,
                    "is_saved": job.is_saved,
                    "is_applied": job.is_applied,
                    "applied_date": job.applied_date.isoformat() if job.applied_date else None,
                    "notes": job.match_reason,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "match_score": job.match_score,
                    "matching_skills": json.loads(job.matching_skills) if job.matching_skills else [],
                    "missing_skills": json.loads(job.missing_skills) if job.missing_skills else []
                }
                for job in jobs
            ]
        }
    except Exception as e:
        logger.error(f"Failed to load tracking board: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load tracking board: {str(e)}"
        )

@router.post("/search-jobs")
async def search_matching_jobs(
    request: JobSearchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Search for jobs and match with user's resume
    Returns jobs with 80%+ match score
    """
    try:
        # Get user's active resume
        resume = db.query(EnhancedResume).filter(
            EnhancedResume.user_id == current_user.id,
            EnhancedResume.is_active == 1
        ).first()
        
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No enhanced resume found. Please save your resume first."
            )
        
        # Extract profile
        profile = {
            "skills": json.loads(resume.skills) if resume.skills else [],
            "experience_years": resume.experience_years,
            "job_titles": json.loads(resume.job_titles) if resume.job_titles else [],
            "location_preference": resume.location_preference,
            "education": json.loads(resume.education) if resume.education else [],
            "certifications": json.loads(resume.certifications) if resume.certifications else []
        }
        
        # Determine search query (now optional - will use profile or generic fallback)
        search_query = request.query
        if not search_query:
            if profile['job_titles'] and len(profile['job_titles']) > 0:
                search_query = profile['job_titles'][0]  # Use first job title
                logger.info(f"   Using job title from profile: {search_query}")
            else:
                search_query = "Software Engineer"  # Generic fallback
                logger.info(f"   No query provided, using generic: {search_query}")
        # Determine location (empty = any location, will search broader)
        location = request.location if request.location else (profile.get('location_preference') or "")
        
        logger.info(f"Searching jobs: {search_query} in {location}")
        logger.info(f"   Min match score: {request.min_match_score or 80}%")
        logger.info(f"   Using Multi-Source Search (JSearch + Adzuna + The Muse + Remotive)...")
        # Search jobs using multi-source service with smart fallback
        try:
            search_result = await multi_search_service.search_jobs(
                query=search_query,
                location=location,
                strategy="smart",  # Try JSearch first, fallback to others
                max_results=50
            )
            jobs = search_result.get("jobs", [])
            sources_used = search_result.get("sources_used", [])
            logger.info(f"   Multi-source search returned {len(jobs)} jobs from: {', '.join(sources_used)}")
        except ValueError as e:
            # API key not configured
            logger.error(f"   API key error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(e)
            )
        except Exception as e:
            logger.error(f"   JSearch API error: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Job search API error: {str(e)}"
            )
        
        if not jobs:
            logger.info(f"   No jobs returned from API")
            return {
                "success": True,
                "matched_jobs": [],
                "message": "No jobs found for your search. The job board may be temporarily unavailable."
            }
        
        logger.info(f"Matching {len(jobs)} jobs with profile...")
        logger.info(f"   Profile has {len(profile.get('skills', []))} skills")
        # Match jobs (with batching for rate limit protection)
        min_score = request.min_match_score or 80
        matched_jobs = await job_matcher.batch_match(profile, jobs, min_score)
        logger.info(f"   {len(matched_jobs)} jobs matched with {min_score}%+ score")
        # Save matched jobs to database
        saved_count = 0
        for job in matched_jobs[:20]:  # Save top 20 matches
            try:
                matched_job = MatchedJob(
                    resume_id=resume.id,
                    user_id=current_user.id,
                    job_id=job.get('job_id'),
                    job_title=job.get('title', '')[:500],
                    company=job.get('company', '')[:255],
                    location=job.get('location', '')[:255],
                    salary_range=job.get('salary', '')[:100],
                    job_type=job.get('job_type', '')[:50],
                    description=(job.get('description', '') or '')[:255],
                    requirements=json.dumps(job.get('requirements', [])),
                    external_url=job.get('external_url', '')[:255],
                    source=job.get('source', '')[:100],
                    match_score=job.get('match_score', 0),
                    matching_skills=json.dumps(job.get('matching_skills', [])),
                    missing_skills=json.dumps(job.get('missing_skills', [])),
                    match_reason=(job.get('match_reason', '') or '')[:500],
                    expires_at=datetime.utcnow() + timedelta(days=30)
                )
                db.add(matched_job)
                saved_count += 1
            except Exception as e:
                logger.error(f"Failed to save job {job.get('title')}: {e}")
                continue
        
        db.commit()
        
        logger.info(f"Found {len(matched_jobs)} matching jobs (saved {saved_count} to database)")
        return {
            "success": True,
            "matched_jobs": matched_jobs,
            "total_found": len(jobs),
            "total_matched": len(matched_jobs),
            "min_score": min_score,
            "message": f"Found {len(matched_jobs)} jobs matching your profile"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Job search failed: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job search failed: {str(e)}"
        )


@router.get("/matched-jobs")
async def get_matched_jobs(
    min_score: Optional[int] = 80,
    limit: Optional[int] = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get cached matched jobs for user
    """
    try:
        jobs = db.query(MatchedJob).filter(
            MatchedJob.user_id == current_user.id,
            MatchedJob.match_score >= min_score,
            MatchedJob.expires_at > datetime.utcnow()
        ).order_by(MatchedJob.match_score.desc()).limit(limit).all()
        
        return {
            "success": True,
            "jobs": [
                {
                    "id": job.id,
                    "title": job.job_title,
                    "company": job.company,
                    "location": job.location,
                    "salary": job.salary_range,
                    "job_type": job.job_type,
                    "description": job.description,
                    "requirements": json.loads(job.requirements) if job.requirements else [],
                    "external_url": job.external_url,
                    "source": job.source,
                    "match_score": job.match_score,
                    "matching_skills": json.loads(job.matching_skills) if job.matching_skills else [],
                    "missing_skills": json.loads(job.missing_skills) if job.missing_skills else [],
                    "match_reason": job.match_reason,
                    "is_saved": job.is_saved,
                    "is_applied": job.is_applied,
                    "created_at": job.created_at.isoformat() if job.created_at else None
                }
                for job in jobs
            ],
            "total": len(jobs)
        }
    except Exception as e:
        logger.error(f"Failed to get matched jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get matched jobs: {str(e)}"
        )


@router.get("/my-resume")
async def get_my_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get user's active enhanced resume and profile
    """
    try:
        resume = db.query(EnhancedResume).filter(
            EnhancedResume.user_id == current_user.id,
            EnhancedResume.is_active == 1
        ).first()
        
        if not resume:
            return {
                "success": True,
                "has_resume": False,
                "message": "No resume found"
            }
        
        profile = {
            "skills": json.loads(resume.skills) if resume.skills else [],
            "experience_years": resume.experience_years,
            "job_titles": json.loads(resume.job_titles) if resume.job_titles else [],
            "location_preference": resume.location_preference,
            "education": json.loads(resume.education) if resume.education else [],
            "certifications": json.loads(resume.certifications) if resume.certifications else []
        }
        
        return {
            "success": True,
            "has_resume": True,
            "resume_id": resume.id,
            "resume_text": resume.enhanced_resume_text,
            "profile": profile,
            "created_at": resume.created_at.isoformat() if resume.created_at else None
        }
    except Exception as e:
        logger.error(f"Failed to get resume: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get resume: {str(e)}"
        )


@router.post("/save-job/{job_id}")
async def save_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a matched job as saved/favorited"""
    try:
        job = db.query(MatchedJob).filter(
            MatchedJob.id == job_id,
            MatchedJob.user_id == current_user.id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.is_saved = 1
        db.commit()
        
        return {"success": True, "message": "Job saved successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-applied/{job_id}")
async def mark_job_applied(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark a matched job as applied"""
    try:
        job = db.query(MatchedJob).filter(
            MatchedJob.id == job_id,
            MatchedJob.user_id == current_user.id
        ).first()
        
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        
        job.is_applied = 1
        job.applied_date = datetime.utcnow()
        db.commit()
        
        return {"success": True, "message": "Job marked as applied"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api-stats")
async def get_api_stats(current_user: User = Depends(get_current_user)):
    """
    Get API usage statistics and status
    """
    try:
        stats = multi_search_service.get_usage_stats()
        return {
            "success": True,
            "stats": stats,
            "apis": {
                "jsearch": {
                    "name": "JSearch (RapidAPI)",
                    "status": "enabled" if stats["apis_enabled"]["jsearch"] else "disabled",
                    "limit": "100/month",
                    "sources": ["Indeed", "LinkedIn", "Glassdoor", "ZipRecruiter"],
                    "usage": stats["usage"]["jsearch"]
                },
                "adzuna": {
                    "name": "Adzuna",
                    "status": "enabled" if stats["apis_enabled"]["adzuna"] else "disabled",
                    "limit": "5,000/month FREE",
                    "sources": ["Adzuna aggregated sources"],
                    "usage": stats["usage"]["adzuna"]
                },
                "themuse": {
                    "name": "The Muse",
                    "status": "enabled",
                    "limit": "Unlimited FREE",
                    "sources": ["The Muse premium companies"],
                    "usage": stats["usage"]["themuse"]
                },
                "remotive": {
                    "name": "Remotive",
                    "status": "enabled",
                    "limit": "Unlimited FREE",
                    "sources": ["Remotive remote jobs"],
                    "usage": stats["usage"]["remotive"]
                }
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

