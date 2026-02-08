"""
Job Scraper Router
API endpoints for importing and parsing job postings
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.models.user import User
from app.utils.database import get_db
from app.routers.auth import get_current_user
from app.services.job_scraper import JobScraper

router = APIRouter(prefix="/api/scraper", tags=["Job Scraper"])

# Initialize scraper service
scraper = JobScraper()


class JobUrlRequest(BaseModel):
    url: str
    notes: Optional[str] = ""


class JobParseRequest(BaseModel):
    job_title: str
    company_name: str
    location: Optional[str] = ""
    job_description: Optional[str] = ""
    salary: Optional[str] = ""
    job_type: Optional[str] = ""
    url: Optional[str] = ""
    notes: Optional[str] = ""


@router.post("/parse-url")
def parse_job_url(
    request: JobUrlRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Parse a job posting URL and extract information
    
    Supports:
    - LinkedIn job postings
    - Indeed job postings
    - Generic job posting URLs
    
    Returns extracted job details ready for application creation
    """
    
    # Validate URL format
    if not scraper.validate_url(request.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format. Please provide a valid job posting URL."
        )
    
    try:
        # Extract job information
        job_info = scraper.extract_job_info(request.url)
        
        # Add user notes if provided
        if request.notes:
            existing_notes = job_info.get('notes', '')
            job_info['notes'] = f"{existing_notes}\n{request.notes}".strip()
        
        # Generate application notes
        auto_notes = scraper.generate_application_notes(job_info)
        if auto_notes:
            job_info['notes'] = f"{auto_notes}\n{job_info.get('notes', '')}".strip()
        
        # Suggest initial status
        job_info['suggested_status'] = scraper.suggest_status(job_info)
        
        return {
            "success": True,
            "platform": job_info.get('platform', 'Unknown'),
            "data": job_info,
            "message": f"Successfully parsed job posting from {job_info.get('platform', 'URL')}"
        }
    
    except Exception as e:
        # Even if parsing fails, return basic info
        return {
            "success": True,
            "platform": "Unknown",
            "data": {
                "url": request.url,
                "platform": "Other",
                "job_title": "",
                "company_name": "",
                "location": "",
                "job_description": "",
                "notes": request.notes,
                "suggested_status": "saved"
            },
            "message": "URL saved. Please fill in job details manually.",
            "parse_error": str(e)
        }


@router.post("/extract-keywords")
def extract_keywords_from_description(
    job_description: str,
    current_user: User = Depends(get_current_user)
):
    """
    Extract technical keywords and skills from job description
    
    Useful for:
    - Resume optimization
    - Interview preparation
    - Skills gap analysis
    """
    
    if not job_description or len(job_description.strip()) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job description is too short"
        )
    
    keywords = scraper.extract_keywords(job_description)
    
    return {
        "keywords": keywords,
        "count": len(keywords),
        "description_length": len(job_description)
    }


@router.post("/validate-data")
def validate_job_data(
    request: JobParseRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Validate and clean manually entered job data
    
    Returns cleaned data ready for application creation
    """
    
    # Convert Pydantic model to dict
    job_data = request.model_dump()
    
    # Parse and clean the data
    cleaned_data = scraper.parse_manual_entry(job_data)
    
    # Validate required fields
    if not cleaned_data.get('job_title'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Job title is required"
        )
    
    if not cleaned_data.get('company_name'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Company name is required"
        )
    
    # Suggest status
    cleaned_data['suggested_status'] = scraper.suggest_status(cleaned_data)
    
    return {
        "success": True,
        "data": cleaned_data,
        "message": "Job data validated successfully"
    }


@router.get("/platforms")
def get_supported_platforms(current_user: User = Depends(get_current_user)):
    """
    Get list of supported job platforms
    
    Returns platform names and example URLs
    """
    
    platforms = [
        {
            "name": "LinkedIn",
            "identifier": "linkedin.com",
            "example": "https://www.linkedin.com/jobs/view/123456789",
            "description": "LinkedIn job postings",
            "supported": True
        },
        {
            "name": "Indeed",
            "identifier": "indeed.com",
            "example": "https://www.indeed.com/viewjob?jk=abc123",
            "description": "Indeed job listings",
            "supported": True
        },
        {
            "name": "Generic",
            "identifier": "any",
            "example": "https://company.com/careers/job/123",
            "description": "Any job posting URL",
            "supported": True
        }
    ]
    
    return {
        "platforms": platforms,
        "total": len(platforms)
    }


@router.post("/quick-add")
def quick_add_from_url(
    request: JobUrlRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Quick parse and prepare job data in one step
    
    Combines URL parsing, keyword extraction, and data validation
    Perfect for "Add from URL" button functionality
    """
    
    # Validate URL
    if not scraper.validate_url(request.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL format"
        )
    
    try:
        # Parse URL
        job_info = scraper.extract_job_info(request.url)
        
        # Extract keywords if description available
        if job_info.get('job_description'):
            job_info['keywords'] = scraper.extract_keywords(job_info['job_description'])
        
        # Generate notes
        auto_notes = scraper.generate_application_notes(job_info)
        user_notes = request.notes or ""
        job_info['notes'] = f"{auto_notes}\n{user_notes}".strip()
        
        # Suggest status
        job_info['suggested_status'] = scraper.suggest_status(job_info)
        
        # Ready-to-use application data
        application_data = {
            "job_title": job_info.get('job_title', ''),
            "company_name": job_info.get('company_name', ''),
            "location": job_info.get('location', ''),
            "job_description": job_info.get('job_description', ''),
            "salary": job_info.get('salary', ''),
            "job_type": job_info.get('job_type', ''),
            "job_url": job_info.get('url', ''),
            "notes": job_info.get('notes', ''),
            "status": job_info.get('suggested_status', 'saved')
        }
        
        return {
            "success": True,
            "platform": job_info.get('platform', 'Unknown'),
            "application_data": application_data,
            "keywords": job_info.get('keywords', []),
            "message": f"Job parsed from {job_info.get('platform', 'URL')}. Review and save.",
            "needs_review": not bool(job_info.get('job_title'))  # Flag if title is missing
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to parse job URL: {str(e)}"
        )
