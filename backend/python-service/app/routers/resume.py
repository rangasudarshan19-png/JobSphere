from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, List
from app.utils.database import get_db
from app.routers.auth import get_current_user, get_current_user_optional
from app.models.user import User
from app.services.resume_generator import resume_generator
from app.services.job_search_aggregator import JobSearchAggregator
import json

router = APIRouter(prefix="/api/resume", tags=["resume"])

# Initialize job search aggregator
job_search_aggregator = JobSearchAggregator()

# ============ HELPER FUNCTIONS ============
def _normalize_resume_data(resume_data: Dict) -> Dict:
    """
    Transform resume_data from frontend format to exporter format
    Ensures all required fields for PDF/DOCX export are present
    """
    if not resume_data:
        return {}
    
    normalized = {}
    
    # Ensure contact object exists
    if 'contact' in resume_data:
        normalized['contact'] = resume_data['contact']
    else:
        # Build contact from flat fields
        normalized['contact'] = {
            'full_name': resume_data.get('full_name', 'John Doe'),
            'email': resume_data.get('email', ''),
            'phone': resume_data.get('phone', ''),
            'location': resume_data.get('location', ''),
            'linkedin': resume_data.get('linkedin', ''),
            'profile_picture': None  # Don't include in exports for ATS compliance
        }
    
    # Map professional_summary to summary
    if 'professional_summary' in resume_data:
        normalized['summary'] = resume_data['professional_summary']
    elif 'summary' in resume_data:
        normalized['summary'] = resume_data['summary']
    else:
        normalized['summary'] = ''
    
    # Copy experience, education, skills, projects, certifications
    # Handle both list and JSON string formats
    for field in ['experience', 'education', 'skills', 'projects', 'certifications']:
        if field in resume_data:
            value = resume_data[field]
            if isinstance(value, str):
                try:
                    normalized[field] = json.loads(value)
                except:
                    normalized[field] = value
            else:
                normalized[field] = value
        else:
            normalized[field] = []
    
    # Copy other fields
    for key in resume_data:
        if key not in ['full_name', 'email', 'phone', 'location', 'linkedin', 'profile_picture', 
                       'professional_summary', 'experience', 'education', 'skills', 'projects', 'certifications', 'contact', 'summary']:
            normalized[key] = resume_data[key]
    
    return normalized

# Pydantic models
class ResumeData(BaseModel):
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    profile_picture: Optional[str] = None  # Base64 encoded image or URL
    summary: str
    experience: str
    education: str
    skills: str
    projects: Optional[str] = None
    certifications: Optional[str] = None
    additional_info: Optional[str] = None  # Extra context for better AI generation
    template_style: Optional[str] = "Professional"  # Modern, Professional, Creative, ATS-Optimized, Executive

class ResumeAnalysisRequest(BaseModel):
    resume_content: str

class JobSearchRequest(BaseModel):
    query: Optional[str] = None  # Job title/keywords (auto-detect from resume if None)
    location: Optional[str] = None  # e.g., "Remote", "USA", "Bangalore"
    skills: Optional[List[str]] = None  # User's skills for matching
    experience: Optional[str] = None  # Experience description
    job_type: Optional[str] = None  # full-time, part-time, contract, remote
    country: Optional[str] = None  # e.g., 'us', 'in'
    remote_only: Optional[bool] = False
    date_posted: Optional[str] = None  # day|week|month
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    sort_by: Optional[str] = None  # relevance|date
    use_resume: Optional[bool] = False  # auto-fill query/location from saved resume
    ai_best_match: Optional[bool] = False  # return AI-style best match suggestions
    limit: Optional[int] = 20  # Max jobs to return
    use_all_apis: Optional[bool] = True  # Combine results from all free APIs

@router.post("/save")
def save_resume(
    resume: ResumeData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Save or update user's resume with email verification warning"""
    try:
        # Check if resume email matches verified account email
        email_mismatch_warning = None
        if resume.email.lower() != current_user.email.lower():
            email_mismatch_warning = {
                "type": "email_mismatch",
                "message": f"[SYMBOL]️ Resume email ({resume.email}) differs from your verified account email ({current_user.email})",
                "suggestion": "Companies will contact you at the resume email. Make sure it's correct!",
                "verified_email": current_user.email,
                "resume_email": resume.email
            }
        
        # Store resume data in user's profile
        resume_json = json.dumps(resume.dict())
        
        # Update user record with resume data
        current_user.resume_data = resume_json
        db.commit()
        
        response = {
            "message": "Resume saved successfully",
            "resume_id": current_user.id,
            "verified_account_email": current_user.email
        }
        
        # Include warning if emails don't match
        if email_mismatch_warning:
            response["warning"] = email_mismatch_warning
            
        return response
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save resume: {str(e)}"
        )

@router.post("/validate-contact")
def validate_contact_info(
    resume: ResumeData,
    current_user: User = Depends(get_current_user)
):
    """
    Validate resume contact information before saving
    Returns warnings if contact info differs from verified account
    """
    warnings = []
    
    # Check email mismatch
    if resume.email.lower() != current_user.email.lower():
        warnings.append({
            "field": "email",
            "type": "mismatch",
            "severity": "warning",
            "message": f"Resume email differs from verified account email",
            "details": {
                "verified_email": current_user.email,
                "resume_email": resume.email,
                "recommendation": "Companies will contact you at the resume email. Double-check it's correct!"
            }
        })
    
    # Check for missing critical info
    if not resume.phone:
        warnings.append({
            "field": "phone",
            "type": "missing",
            "severity": "info",
            "message": "Phone number not provided",
            "details": {
                "recommendation": "Adding a phone number increases your chances of getting contacted"
            }
        })
    
    if not resume.location:
        warnings.append({
            "field": "location",
            "type": "missing",
            "severity": "info",
            "message": "Location not provided",
            "details": {
                "recommendation": "Location helps employers find local candidates"
            }
        })
    
    return {
        "valid": True,
        "warnings": warnings,
        "verified_account_email": current_user.email,
        "has_critical_warnings": any(w["severity"] == "warning" for w in warnings)
    }

@router.get("/get")
def get_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get user's saved resume with verified email info"""
    try:
        if not hasattr(current_user, 'resume_data') or not current_user.resume_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No resume found"
            )
        
        resume_dict = json.loads(current_user.resume_data)
        
        # Add verified email info for frontend reference
        return {
            **resume_dict,
            "verified_account_email": current_user.email,
            "email_matches_account": resume_dict.get("email", "").lower() == current_user.email.lower()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve resume: {str(e)}"
        )

@router.delete("/delete")
def delete_resume(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete user's resume"""
    try:
        current_user.resume_data = None
        db.commit()
        
        return {"message": "Resume deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete resume: {str(e)}"
        )


# === AI-POWERED RESUME GENERATION ===

class CompanyResearchRequest(BaseModel):
    company_name: str

class GenerateResumeRequest(BaseModel):
    company_name: str
    job_title: Optional[str] = None
    full_name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    profile_picture: Optional[str] = None  # Base64 encoded image
    
    # Work Experience (list of dicts or JSON string)
    experience: List[Dict] | str
    
    # Education
    education: List[Dict] | str
    
    # Skills
    skills: List[str] | str
    
    # Optional fields
    projects: Optional[List[Dict] | str] = None
    certifications: Optional[List[str] | str] = None
    summary: Optional[str] = None
    
    # New fields for better AI generation
    additional_info: Optional[str] = None  # Extra information for context
    ai_suggestions: Optional[str] = None  # Specific instructions for AI (e.g., "emphasize leadership")
    template_preference: Optional[str] = "Professional"  # Preferred resume template


@router.post("/research-company")
async def research_company(
    request: CompanyResearchRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Research company and get resume optimization recommendations
    
    Returns company type, culture keywords, template style, and tips
    """
    try:
        print(f"\n{'='*60}")
        print(f"[EMOJI] Company Research Request from: {current_user.email if current_user else 'Anonymous'}")
        print(f"   Company: {request.company_name}")
        print(f"{'='*60}\n")
        
        research = await resume_generator.research_company(request.company_name)
        
        return {
            "company_name": request.company_name,
            **research
        }
        
    except Exception as e:
        print(f"[SYMBOL] Company research error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to research company: {str(e)}"
        )


@router.post("/generate-ai-resume")
async def generate_ai_resume(
    request: GenerateResumeRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate complete AI-optimized resume tailored to specific company
    Includes email verification warning if contact email differs from verified account
    
    Flow:
    1. Research company culture and preferences
    2. Generate resume content optimized for that company
    3. Return formatted resume with ATS optimization
    4. Warn if contact email differs from verified account email
    """
    try:
        print(f"\n{'='*60}")
        print(f"[EMOJI] AI Resume Generation Request")
        print(f"   User: {current_user.email if current_user else 'Anonymous'}")
        print(f"   Company: {request.company_name}")
        print(f"   Target Role: {request.job_title or 'Not specified'}")
        print(f"{'='*60}\n")
        
        # Check email mismatch if user is authenticated
        email_warning = None
        if current_user and request.email.lower() != current_user.email.lower():
            email_warning = {
                "type": "email_mismatch",
                "severity": "warning",
                "message": f"[SYMBOL]️ Resume email ({request.email}) differs from your verified account email ({current_user.email})",
                "suggestion": "Make sure this is the correct email where you want to receive job offers!",
                "verified_email": current_user.email,
                "resume_email": request.email
            }
            print(f"[SYMBOL]️  Email mismatch detected: {request.email} vs {current_user.email}")
        
        # Step 1: Research company
        print("Step 1: Researching company...")
        company_research = await resume_generator.research_company(request.company_name)
        
        # Step 2: Prepare user info
        print("Step 2: Processing user information...")
        user_info = {
            "full_name": request.full_name,
            "email": request.email,
            "phone": request.phone,
            "location": request.location,
            "linkedin": request.linkedin,
            "profile_picture": request.profile_picture,
            "experience": request.experience if isinstance(request.experience, list) else json.loads(request.experience),
            "education": request.education if isinstance(request.education, list) else json.loads(request.education),
            "skills": request.skills if isinstance(request.skills, list) else json.loads(request.skills),
            "projects": request.projects if not request.projects or isinstance(request.projects, list) else json.loads(request.projects),
            "certifications": request.certifications if not request.certifications or isinstance(request.certifications, list) else json.loads(request.certifications),
            "summary": request.summary,
            "additional_info": request.additional_info,
            "ai_suggestions": request.ai_suggestions,
            "template_preference": request.template_preference
        }
        
        # Step 3: Generate AI resume content
        print("Step 3: Generating AI-optimized resume content...")
        resume_content = await resume_generator.generate_resume_content(
            user_info=user_info,
            company_research=company_research,
            job_title=request.job_title,
            ai_suggestions=request.ai_suggestions
        )
        
        print(f"\n[SYMBOL] Resume generated successfully!")
        print(f"   Template: {company_research.get('recommended_template')}")
        print(f"   Tone: {company_research.get('tone')}")
        print(f"   Keywords: {len(resume_content.get('keywords_optimized', []))} optimized\n")
        
        response = {
            "success": True,
            "company_research": company_research,
            "resume": {
                "contact": {
                    "full_name": request.full_name,
                    "email": request.email,
                    "phone": request.phone,
                    "location": request.location,
                    "linkedin": request.linkedin,
                    "profile_picture": request.profile_picture
                },
                **resume_content
            },
            "metadata": {
                "generated_for_company": request.company_name,
                "target_job_title": request.job_title,
                "template_style": request.template_preference or company_research.get('recommended_template'),
                "tone": company_research.get('tone'),
                "ats_optimized": True
            }
        }
        
        # Add email warning if present
        if email_warning:
            response["warning"] = email_warning
            
        if current_user:
            response["verified_account_email"] = current_user.email
            
        return response
        
    except Exception as e:
        print(f"[SYMBOL] Resume generation error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate resume: {str(e)}"
        )


# === RESUME DOWNLOAD ENDPOINTS ===

class ResumeDownloadRequest(BaseModel):
    resume_data: Dict
    format: str = "pdf"  # "pdf" or "docx"
    template_style: Optional[str] = "Professional"


@router.post("/download")
async def download_resume(
    request: ResumeDownloadRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Download resume in PDF or DOCX format
    """
    try:
        from app.services.resume_export import resume_exporter
        
        if not request.resume_data:
            raise ValueError("Resume data is empty")
        
        format_lower = request.format.lower() if request.format else "pdf"
        template = request.template_style or "Professional"
        
        print(f"[EMOJI] Download: {format_lower.upper()} format, template={template}")
        
        # Transform resume_data into the structure expected by exporter
        # Frontend sends proper structure, just ensure all fields are present
        resume_data_normalized = _normalize_resume_data(request.resume_data)
        
        # Ensure we have valid file content
        if format_lower == "pdf":
            try:
                file_content = await resume_exporter.generate_pdf(
                    resume_data_normalized,
                    template
                )
            except Exception as pdf_error:
                print(f"[SYMBOL]️  PDF failed: {str(pdf_error)[:100]} - using DOCX instead")
                file_content = await resume_exporter.generate_docx(
                    resume_data_normalized,
                    template
                )
                format_lower = "docx"  # Change extension
            
            media_type = "application/pdf" if format_lower == "pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            
        elif format_lower == "docx":
            file_content = await resume_exporter.generate_docx(
                resume_data_normalized,
                template
            )
            media_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            raise ValueError(f"Invalid format: {request.format}")
        
        # Generate filename
        full_name = "resume"
        if isinstance(resume_data_normalized, dict):
            contact = resume_data_normalized.get('contact', {})
            if isinstance(contact, dict) and contact.get('full_name'):
                full_name = str(contact['full_name']).replace(' ', '_')
        
        filename = f"resume_{full_name}.{format_lower}"
        
        print(f"[SYMBOL] Generated: {filename} ({len(file_content)} bytes)")
        
        from fastapi.responses import Response
        return Response(
            content=file_content,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(file_content)),
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        import traceback
        print(f"[SYMBOL] Download error: {str(e)[:200]}")
        print(traceback.format_exc()[:200])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Download failed: {str(e)[:100]}"
        )


@router.get("/list")
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get all saved resumes for the current user"""
    try:
        # For now, we store one resume per user
        # In future, you can create a separate Resume table for multiple resumes
        if hasattr(current_user, 'resume_data') and current_user.resume_data:
            resume_dict = json.loads(current_user.resume_data)
            return {
                "resumes": [{
                    "id": current_user.id,
                    "full_name": resume_dict.get("full_name"),
                    "email": resume_dict.get("email"),
                    "created_at": current_user.created_at.isoformat() if hasattr(current_user, 'created_at') else None,
                    "updated_at": current_user.updated_at.isoformat() if hasattr(current_user, 'updated_at') else None,
                    "template_style": resume_dict.get("template_style", "Professional")
                }],
                "count": 1
            }
        else:
            return {
                "resumes": [],
                "count": 0
            }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list resumes: {str(e)}"
        )


# === POST-RESUME ACTION ENDPOINTS ===

class PostResumeActionsRequest(BaseModel):
    resume_id: str
    action: str  # "cover_letter", "interview_prep", "job_search"


@router.post("/actions")
async def get_post_resume_actions(
    request: PostResumeActionsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get available actions after resume generation/save
    
    Returns appropriate data/redirects for:
    - Cover Letter Generation (with resume context)
    - Interview Prep (questions based on resume)
    - Job Search (jobs matching resume)
    """
    try:
        # Get saved resume
        if not hasattr(current_user, 'resume_data') or not current_user.resume_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No resume found. Please save a resume first."
            )
        
        resume_data = json.loads(current_user.resume_data)
        
        if request.action == "cover_letter":
            return {
                "action": "cover_letter",
                "redirect_url": "/cover-letter.html",
                "context": {
                    "full_name": resume_data.get("full_name"),
                    "email": resume_data.get("email"),
                    "phone": resume_data.get("phone"),
                    "skills": resume_data.get("skills"),
                    "experience": resume_data.get("experience"),
                    "resume_summary": resume_data.get("summary")
                }
            }
        
        elif request.action == "interview_prep":
            return {
                "action": "interview_prep",
                "redirect_url": "/interview-prep.html",
                "context": {
                    "skills": resume_data.get("skills"),
                    "experience": resume_data.get("experience"),
                    "education": resume_data.get("education"),
                    "projects": resume_data.get("projects")
                }
            }
        
        elif request.action == "job_search":
            return {
                "action": "job_search",
                "redirect_url": "/job-matching.html",
                "context": {
                    "skills": resume_data.get("skills"),
                    "location": resume_data.get("location"),
                    "experience_level": "mid",  # Can be extracted from experience
                    "job_preferences": resume_data.get("skills")
                }
            }
        
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Use: cover_letter, interview_prep, or job_search"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process action: {str(e)}"
        )


@router.post("/job-search")
async def search_jobs(
    request: JobSearchRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Search for jobs using multiple free APIs (The Muse, Remotive, JSearch, Adzuna)
    
    Automatically detects job title and location from resume context if not provided.
    Combines results from all available free APIs for comprehensive job listings.
    
    Args:
        query: Job title/keywords (e.g., "Python Developer", "UX Designer")
        location: Job location (e.g., "Remote", "USA", "New York", "Bangalore")
        skills: User's skills (for UI display/matching)
        experience: Experience description (for context)
        job_type: Filter by type (full-time, part-time, contract, remote)
        limit: Max jobs to return (default 20)
        use_all_apis: Combine results from all free APIs (default true)
    
    Returns:
        Dict with jobs from multiple sources, total count, and API sources used
    
    Free APIs used:
    - The Muse (Unlimited)
    - Remotive (Unlimited remote jobs)
    - JSearch (100/month free tier)
    - Adzuna (Free tier)
    """
    try:
        def _parse_json_or_fallback(value, fallback):
            if value is None:
                return fallback
            if isinstance(value, (list, dict)):
                return value
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return fallback
            return fallback

        def _flatten_skills(skills_value) -> List[str]:
            if isinstance(skills_value, list):
                return [s.strip() for s in skills_value if str(s).strip()]
            if isinstance(skills_value, dict):
                merged = []
                for v in skills_value.values():
                    if isinstance(v, list):
                        merged.extend(v)
                return [s.strip() for s in merged if str(s).strip()]
            if isinstance(skills_value, str):
                # fallback to comma split
                return [s.strip() for s in skills_value.split(',') if s.strip()]
            return []

        # Start with request values
        search_query = request.query
        search_location = request.location
        resume_skills = request.skills or []

        # If user wants to auto-use their saved resume
        if request.use_resume and current_user and getattr(current_user, "resume_data", None):
            try:
                resume_data = json.loads(current_user.resume_data)
                # Derive query from skills, experience, or summary
                if not search_query:
                    skills_field = resume_data.get("skills") or []
                    parsed_skills = _parse_json_or_fallback(skills_field, [])
                    derived_skills = _flatten_skills(parsed_skills)

                    # Try to infer from experience titles
                    exp_field = resume_data.get("experience") or []
                    parsed_exp = _parse_json_or_fallback(exp_field, [])
                    exp_title = ""
                    if isinstance(parsed_exp, list) and parsed_exp:
                        exp_title = (parsed_exp[0].get("title") or parsed_exp[0].get("position") or "") if isinstance(parsed_exp[0], dict) else ""

                    # Try to infer from summary keywords
                    summary_text = (resume_data.get("summary") or "").lower()
                    inferred_role = ""
                    if "tester" in summary_text or "testing" in summary_text or "qa" in summary_text:
                        inferred_role = "Software Tester"

                    resume_skills = derived_skills or resume_skills
                    search_query = exp_title or inferred_role or (derived_skills[0] if derived_skills else "Software Tester")
                # Derive location
                if not search_location:
                    search_location = resume_data.get("location") or "Remote"
                # Merge skills
                if not resume_skills and resume_data.get("skills"):
                    resume_skills = derived_skills
            except Exception as e:
                print(f"Resume parsing failed, falling back: {e}")

        search_query = search_query or "Software Tester"
        search_location = search_location or "Remote"

        if current_user:
            print(f"[EMOJI] Job search by user {current_user.id}: '{search_query}' in {search_location}")
        else:
            print(f"[EMOJI] Job search (anonymous): '{search_query}' in {search_location}")

        result = await job_search_aggregator.search_jobs(
            query=search_query,
            location=search_location,
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

        # Add user context if provided
        if resume_skills:
            result["user_skills"] = resume_skills

        # Optional: AI-style best match (simple skill overlap ranking)
        if request.ai_best_match and result.get("jobs"):
            skills_lower = [s.lower() for s in resume_skills]
            def score(job):
                text = ((job.get("title") or "") + " " + (job.get("description") or "")).lower()
                return sum(1 for s in skills_lower if s and s in text)
            ranked = sorted(result["jobs"], key=score, reverse=True)
            result["ai_best_matches"] = ranked[:5]
        
        return result
        
    except Exception as e:
        print(f"[SYMBOL] Job search endpoint error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Job search failed: {str(e)}"
        )
