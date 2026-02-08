"""
AI Features Router
Endpoints for AI-powered interview question generation
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
import json

from app.models.user import User
from app.models.application import Application
from app.models.enhanced_resume import EnhancedResume
from app.utils.database import get_db
from app.routers.auth import get_current_user, get_current_user_optional
from app.services.interview_generator import InterviewQuestionGenerator
from app.services.skills_gap_analyzer import skills_gap_analyzer

router = APIRouter(prefix="/api/ai", tags=["AI Features"])

# Initialize services
question_generator = InterviewQuestionGenerator()


# Helper function for CTC estimation based on skills
async def _estimate_ctc_from_skills(skills: List[str], resume_text: str = "") -> Dict[str, any]:
    """
    Use AI to estimate salary/CTC range based on extracted skills
    Analyzes skill combination, experience level, and provides market insights
    """
    try:
        import google.generativeai as genai
        import os
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return _fallback_ctc_estimate(skills)
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Extract experience from resume with improved detection
        experience_info = "mid-level"  # Default
        if resume_text:
            resume_lower = resume_text.lower()
            
            # First, check for explicit year mentions to avoid false positives
            has_explicit_experience = False
            
            # Check for entry-level indicators (0-2 years) - MOST SPECIFIC FIRST
            if any(word in resume_lower for word in ["0-1 year", "1-2 years", "0 year", "1 year", "2 years experience", "fresher", "graduate 2023", "graduate 2024"]):
                experience_info = "entry-level"
                has_explicit_experience = True
            # Check for mid-level indicators (2-4 years)
            elif any(word in resume_lower for word in ["2-3 years", "3-4 years", "2 years experience", "3 years experience", "4 years experience"]):
                experience_info = "mid-level"
                has_explicit_experience = True
            # Check for senior-level years explicitly (5+ years)
            elif any(word in resume_lower for word in ["5+ years", "6+ years", "7+ years", "8+ years", "9+ years", "10+ years", "5 years experience", "6 years experience", "7 years experience"]):
                experience_info = "senior-level"
                has_explicit_experience = True
            
            # Only check for job titles if no explicit years found
            # This prevents false positives from job titles like "Senior" in "Senior Secondary"
            if not has_explicit_experience:
                # Check for senior job titles (but be careful - "Senior Secondary" is education, not job title)
                if any(word in resume_lower for word in ["senior engineer", "senior developer", "senior analyst", "lead engineer", "lead developer", "tech lead", "architect", "principal engineer"]):
                    # Extra check: make sure it's NOT "Senior Secondary" (education)
                    if "senior secondary" not in resume_lower or "senior engineer" in resume_lower or "senior developer" in resume_lower:
                        experience_info = "senior-level"
                # Check for entry-level job titles
                elif any(word in resume_lower for word in ["junior engineer", "junior developer", "associate engineer", "trainee", "intern"]):
                    experience_info = "entry-level"
                # Default remains mid-level
        
        skills_text = ", ".join(skills[:20])  # Use top 20 skills
        
        prompt = f"""
You are an expert salary analyst for the tech industry. Analyze the following skills and provide a realistic CTC/salary estimation.

Skills: {skills_text}
Experience Level: {experience_info}

Provide a JSON response with this EXACT structure:
{{
    "min_ctc_inr": <number>,
    "max_ctc_inr": <number>,
    "min_ctc_usd": <number>,
    "max_ctc_usd": <number>,
    "experience_level": "<entry/mid/senior>",
    "market_position": "<below_avg/average/above_avg/competitive>",
    "key_strengths": ["skill1", "skill2", "skill3"],
    "high_value_skills": ["skill1", "skill2"],
    "salary_boosters": ["what can increase salary"],
    "summary": "One sentence summary of earning potential"
}}

Consider:
1. Current 2025 market rates in India and USA
2. Skill demand and rarity
3. Experience level indicators
4. Skill combinations that add value
5. Industry standards for testing/development roles

Be realistic and data-driven. Base on actual market data.
"""
        
        print(f"[EMOJI] Estimating CTC for {len(skills)} skills ({experience_info})...")
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.3,
                "max_output_tokens": 1000
            }
        )
        
        result_text = response.text.strip()
        print(f"[EMOJI] AI CTC Response (first 200 chars): {result_text[:200]}")
        
        # Parse JSON response
        import re
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            ctc_data = json.loads(json_match.group())
            print(f"[SYMBOL] CTC Estimated: ₹{ctc_data.get('min_ctc_inr')}-{ctc_data.get('max_ctc_inr')} LPA")
            return ctc_data
        else:
            print("[SYMBOL]️ Could not parse AI CTC response")
            return _fallback_ctc_estimate(skills)
    
    except Exception as e:
        print(f"[SYMBOL]️ CTC estimation failed: {e}")
        return _fallback_ctc_estimate(skills)


async def _analyze_skills_for_target_ctc(current_skills: List[str], target_ctc: str, resume_text: str = "") -> Dict[str, any]:
    """
    Analyze what skills are needed to reach a target CTC
    Compares current earning potential with target and suggests skill gaps
    """
    try:
        import google.generativeai as genai
        import os
        import re
        
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"success": False, "message": "AI unavailable"}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Parse target CTC
        target_numeric = None
        target_lower = target_ctc.lower()
        numbers = re.findall(r'\d+\.?\d*', target_lower)
        if numbers:
            target_numeric = float(numbers[0])
            if 'k' in target_lower and target_numeric < 1000:
                target_numeric = target_numeric * 100000  # Convert K to actual
            elif 'lpa' in target_lower or 'lac' in target_lower:
                target_numeric = target_numeric  # Already in LPA
        
        skills_text = ", ".join(current_skills[:25])
        
        prompt = f"""
You are a career advisor analyzing skill gaps to reach a target salary.

CURRENT SITUATION:
- Current Skills: {skills_text}
- Target CTC: {target_ctc}

TASK: Analyze what additional skills are needed to reach the target CTC.

Provide a JSON response with this EXACT structure:
{{
    "can_reach_target": <true/false>,
    "current_estimated_ctc": "<estimated range based on current skills>",
    "gap_percentage": <number 0-100>,
    "skills_needed": [
        {{"skill": "skill name", "priority": "high/medium", "impact": "description", "why": "reason"}},
        ...
    ],
    "certifications_recommended": ["cert1", "cert2"],
    "timeline_months": <estimated months to acquire skills>,
    "strategy": "Overall strategy to reach target CTC",
    "realistic_assessment": "Honest assessment of feasibility"
}}

Consider:
1. Current 2025 market demand for skills
2. Realistic salary impact of each skill
3. Time required to learn skills
4. Market standards for the target CTC level
5. Skill combinations that maximize salary

Provide SPECIFIC, ACTIONABLE skills (not generic advice).
For target {target_ctc}, suggest skills that actually command that salary.
"""
        
        print(f"[EMOJI] Analyzing skills gap to reach {target_ctc}...")
        
        response = await model.generate_content_async(
            prompt,
            generation_config={
                "temperature": 0.4,
                "max_output_tokens": 1500
            }
        )
        
        result_text = response.text.strip()
        
        # Parse JSON
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            gap_analysis = json.loads(json_match.group())
            print(f"[SYMBOL] Gap analysis complete: {len(gap_analysis.get('skills_needed', []))} skills needed")
            return gap_analysis
        else:
            return {"success": False, "message": "Could not parse response"}
    
    except Exception as e:
        print(f"[SYMBOL]️ Target CTC analysis failed: {e}")
        return {"success": False, "message": str(e)}


def _fallback_ctc_estimate(skills: List[str]) -> Dict[str, any]:
    """Fallback CTC estimation when AI is unavailable"""
    skill_count = len(skills)
    
    # Basic estimation based on skill count
    if skill_count >= 20:
        return {
            "min_ctc_inr": 8.0,
            "max_ctc_inr": 15.0,
            "min_ctc_usd": 60000,
            "max_ctc_usd": 100000,
            "experience_level": "mid-senior",
            "market_position": "competitive",
            "key_strengths": skills[:3],
            "high_value_skills": skills[:2],
            "salary_boosters": ["Gain more specialized skills", "Add certifications"],
            "summary": f"With {skill_count} skills, you're positioned for mid to senior level roles"
        }
    elif skill_count >= 10:
        return {
            "min_ctc_inr": 4.0,
            "max_ctc_inr": 10.0,
            "min_ctc_usd": 40000,
            "max_ctc_usd": 70000,
            "experience_level": "mid-level",
            "market_position": "average",
            "key_strengths": skills[:3],
            "high_value_skills": skills[:2],
            "salary_boosters": ["Learn in-demand tools", "Build portfolio projects"],
            "summary": f"With {skill_count} skills, you're suitable for mid-level positions"
        }
    else:
        return {
            "min_ctc_inr": 2.5,
            "max_ctc_inr": 6.0,
            "min_ctc_usd": 30000,
            "max_ctc_usd": 50000,
            "experience_level": "entry-level",
            "market_position": "below_avg",
            "key_strengths": skills[:3],
            "high_value_skills": skills[:1],
            "salary_boosters": ["Expand skill set", "Gain hands-on experience"],
            "summary": f"With {skill_count} skills, you're best suited for entry-level roles"
        }


# Helper function for AI skill extraction
async def _extract_skills_with_ai(resume_text: str) -> List[str]:
    """
    Use AI to intelligently extract skills from resume text
    Returns a clean, categorized list of technical skills
    """
    try:
        import google.generativeai as genai
        import os
        
        # Initialize Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("[SYMBOL]️ No Gemini API key, falling back to manual extraction")
            return []
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Print full resume to debug
        print(f"[EMOJI] FULL RESUME TEXT ({len(resume_text)} chars):")
        print("=" * 80)
        print(resume_text)
        print("=" * 80)
        
        prompt = f"""
You are an expert technical recruiter analyzing a resume. Read the ENTIRE resume carefully and extract ALL technical and professional skills.

CRITICAL - READ EVERYTHING:
You MUST read and extract skills from EVERY line of the resume below. Do not skip any section.

EXTRACTION RULES:
1. Extract EVERY skill, tool, technology, methodology mentioned
2. Look in ALL sections: Summary, Experience, Skills, Education, Projects, Certifications
3. Testing skills: UAT, API Testing, Manual Testing, Automation, Regression, Integration, etc.
4. Tools: JIRA, Postman, ALM, Jenkins, Git, Control-M, SSMS, SQL Squirrel, etc.
5. Databases: SQL, MySQL, Oracle, MongoDB, SQL Server, etc.
6. Programming: Python, Java, JavaScript, C++, etc.
7. Methodologies: Agile, Scrum, Waterfall, DevOps, CI/CD, etc.
8. Cloud: AWS, Azure, GCP, etc.
9. Break down compound phrases:
   - "API Testing using Postman" → ["API Testing", "Postman"]
   - "Defect Management in JIRA" → ["Defect Management", "JIRA"]
   - "SQL queries in SQL Server" → ["SQL", "SQL Server"]
10. Normalize names: "aws"→"AWS", "sql server"→"SQL Server", "nodejs"→"Node.js"

IMPORTANT: Return 25-40 skills. Be EXTREMELY thorough. Extract everything technical.

===== COMPLETE RESUME =====
{resume_text}
===== END OF RESUME =====

Now extract ALL skills found above. Return ONLY a JSON array of strings.
Example: ["Python", "Java", "SQL", "SQL Server", "SSMS", "API Testing", "Postman", "UAT Testing", "Test Case Design", "Test Execution", "Defect Management", "JIRA", "ALM", "Control-M", "Job Monitoring", "Data Validation", "Agile", "Scrum"]
"""
        
        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,  # Very low for maximum consistency
                max_output_tokens=1500  # Much larger for comprehensive extraction
            )
        )
        
        text = response.text.strip()
        print(f"[EMOJI] AI Response (first 200 chars): {text[:200]}")
        
        # Extract JSON from response
        if '```json' in text:
            text = text.split('```json')[1].split('```')[0].strip()
        elif '```' in text:
            text = text.split('```')[1].split('```')[0].strip()
        
        print(f"[EMOJI] Parsed text: {text[:200]}")
        skills = json.loads(text)
        
        if isinstance(skills, list):
            # Clean and filter skills
            cleaned_skills = []
            seen = set()
            
            for skill in skills:
                if skill and isinstance(skill, str):
                    skill = skill.strip()
                    skill_lower = skill.lower()
                    
                    # Skip common words
                    if skill_lower in ['the', 'and', 'or', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'with']:
                        continue
                    
                    # Must be at least 2 characters
                    if len(skill) < 2:
                        continue
                    
                    # Avoid duplicates (case-insensitive)
                    if skill_lower not in seen:
                        seen.add(skill_lower)
                        cleaned_skills.append(skill)
            
            print(f"[EMOJI] Cleaned {len(skills)} → {len(cleaned_skills)} unique skills")
            return cleaned_skills[:40]  # Return up to 40 skills
        
        return []
        
    except Exception as e:
        print(f"[SYMBOL]️ AI skill extraction failed: {e}")
        return []


class InterviewQuestionsRequest(BaseModel):
    job_title: str
    job_description: Optional[str] = ""
    company_name: Optional[str] = ""


class InterviewQuestionsResponse(BaseModel):
    job_title: str
    company_name: str
    questions: Dict[str, List[str]]
    preparation_tips: List[str]
    total_questions: int


@router.post("/interview-questions", response_model=InterviewQuestionsResponse)
def generate_interview_questions(
    request: InterviewQuestionsRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate AI-powered interview questions based on job details
    
    This endpoint analyzes the job title and description to generate:
    - Technical questions based on required skills
    - Behavioral questions based on seniority level
    - General interview questions
    - Company-specific questions
    """
    try:
        # Generate questions
        questions = question_generator.generate_questions(
            job_title=request.job_title,
            job_description=request.job_description,
            company_name=request.company_name
        )
        
        # Generate preparation tips
        tips = question_generator.generate_tips(request.job_title)
        
        # Count total questions
        total = sum(len(q_list) for q_list in questions.values())
        
        return InterviewQuestionsResponse(
            job_title=request.job_title,
            company_name=request.company_name or "the company",
            questions=questions,
            preparation_tips=tips,
            total_questions=total
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {str(e)}"
        )


@router.get("/interview-questions/{application_id}", response_model=InterviewQuestionsResponse)
def generate_questions_for_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Generate interview questions for a specific application
    
    Automatically uses the job details from the application
    """
    # Get the application
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Get company name
    company_name = application.company.name if application.company else ""
    
    try:
        # Generate questions
        questions = question_generator.generate_questions(
            job_title=application.job_title or "",
            job_description=application.job_description or "",
            company_name=company_name
        )
        
        # Generate preparation tips
        tips = question_generator.generate_tips(application.job_title or "")
        
        # Count total questions
        total = sum(len(q_list) for q_list in questions.values())
        
        return InterviewQuestionsResponse(
            job_title=application.job_title or "Position",
            company_name=company_name or "the company",
            questions=questions,
            preparation_tips=tips,
            total_questions=total
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate questions: {str(e)}"
        )


@router.get("/keywords/{application_id}")
def extract_keywords_from_application(
    application_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Extract technical keywords from an application's job description
    
    Useful for identifying required skills and technologies
    """
    # Get the application
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    # Extract keywords
    text = f"{application.job_title or ''} {application.job_description or ''}"
    keywords = question_generator.extract_keywords(text)
    
    return {
        "application_id": application_id,
        "job_title": application.job_title,
        "keywords": keywords,
        "keyword_count": len(keywords)
    }


class ResumeAnalysisRequest(BaseModel):
    resume_content: str


class AnswerQuestionRequest(BaseModel):
    question: str


class CoverLetterRequest(BaseModel):
    company_name: str
    job_title: str
    job_description: Optional[str] = ""
    user_experience: Optional[str] = ""
    tone: Optional[str] = "professional"


@router.post("/generate-cover-letter")
def generate_cover_letter(
    request: CoverLetterRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate AI-powered personalized cover letter
    
    Creates a professional cover letter tailored to:
    - Specific company and position
    - Job requirements from description
    - User's skills and experience
    - Selected tone (professional, enthusiastic, confident)
    """
    print(f"\n{'='*60}")
    print(f"[EMOJI] COVER LETTER GENERATION REQUEST")
    print(f"{'='*60}")
    print(f"User: {current_user.email}")
    print(f"Company: {request.company_name}")
    print(f"Position: {request.job_title}")
    print(f"Tone: {request.tone}")
    print(f"{'='*60}\n")
    
    try:
        # Generate cover letter using Gemini AI
        cover_letter = question_generator.generate_cover_letter(
            company_name=request.company_name,
            job_title=request.job_title,
            job_description=request.job_description,
            user_experience=request.user_experience,
            tone=request.tone
        )
        
        print(f"\n[SYMBOL] Cover letter generated successfully!")
        print(f"Length: {len(cover_letter)} characters")
        print(f"Preview: {cover_letter[:150]}...")
        print(f"{'='*60}\n")
        
        return {
            "company_name": request.company_name,
            "job_title": request.job_title,
            "cover_letter": cover_letter,
            "status": "success"
        }
    
    except Exception as e:
        print(f"\n[SYMBOL] ERROR generating cover letter: {str(e)}")
        print(f"{'='*60}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cover letter: {str(e)}"
        )


@router.post("/answer-question")
def answer_interview_question(
    request: AnswerQuestionRequest,
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Generate AI-powered answer to an interview question
    
    Provides comprehensive answers including:
    - Detailed explanation
    - Key points to mention
    - Example scenarios
    - Best practices
    """
    print(f"\n{'='*60}")
    print(f"[EMOJI] ANSWER GENERATION REQUEST")
    print(f"{'='*60}")
    print(f"User: {current_user.email if current_user else 'Anonymous'}")
    print(f"Question: {request.question[:100]}...")
    print(f"{'='*60}\n")
    
    try:
        # Generate answer using Gemini AI
        answer = question_generator.generate_answer(request.question)
        
        print(f"\n[SYMBOL] Answer generated successfully!")
        print(f"Length: {len(answer)} characters")
        print(f"Preview: {answer[:150]}...")
        print(f"{'='*60}\n")
        
        return {
            "question": request.question,
            "answer": answer,
            "status": "success"
        }
    
    except Exception as e:
        print(f"\n[SYMBOL] ERROR generating answer: {str(e)}")
        print(f"{'='*60}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate answer: {str(e)}"
        )


class ImprovedResumeRequest(BaseModel):
    personal_info: dict
    experience: str
    education: str
    skills: str
    projects: Optional[str] = ""
    certifications: Optional[str] = ""
    target_role: Optional[str] = ""
    improvements_to_include: Optional[str] = ""
    template: Optional[str] = "modern"  # Template style: modern, professional, creative, ats, tech


@router.post("/analyze-resume")
def analyze_resume(
    request: ResumeAnalysisRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Analyze resume with AI and provide feedback
    
    Returns comprehensive analysis including:
    - Overall score and feedback
    - Strengths and weaknesses
    - Specific improvement suggestions
    - ATS optimization tips
    """
    try:
        # Use the interview generator's Gemini AI to analyze resume
        analysis = question_generator.analyze_resume(request.resume_content)
        
        return {
            "analysis": analysis,
            "status": "success"
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze resume: {str(e)}"
        )


@router.post("/generate-improved-resume")
def generate_improved_resume(
    request: ImprovedResumeRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Generate an improved resume based on user's data and analysis feedback
    
    Takes user's information and generates a professional, ATS-optimized resume
    using AI to improve formatting, wording, and content based on best practices
    """
    print(f"\n{'='*70}")
    print(f"[EMOJI] IMPROVED RESUME GENERATION REQUEST")
    print(f"{'='*70}")
    print(f"User: {current_user.email}")
    print(f"Target Role: {request.target_role}")
    print(f"{'='*70}\n")
    
    try:
        # Generate improved resume using Gemini AI with selected template
        improved_resume = question_generator.generate_improved_resume(
            personal_info=request.personal_info,
            experience=request.experience,
            education=request.education,
            skills=request.skills,
            projects=request.projects,
            certifications=request.certifications,
            target_role=request.target_role,
            improvements=request.improvements_to_include,
            template=request.template  # Pass selected template
        )
        
        print(f"\n[SYMBOL] Improved resume generated successfully!")
        print(f"Template used: {request.template}")
        print(f"Length: {len(improved_resume)} characters")
        print(f"{'='*70}\n")
        
        return {
            "improved_resume": improved_resume,
            "status": "success"
        }
    
    except Exception as e:
        print(f"\n[SYMBOL] ERROR generating improved resume: {str(e)}")
        print(f"{'='*70}\n")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate improved resume: {str(e)}"
        )


def generate_interview_tips(
    job_title: str,
    job_description: str,
    phase_type: str,
    company_name: str = "",
    user_notes: str = "",
    is_day_of: bool = False
) -> str:
    """
    Generate AI-powered personalized tips for interview/assessment preparation
    
    Args:
        job_title: The position title
        job_description: Job description text
        phase_type: Type of phase (e.g., "Technical Interview", "HR Round")
        company_name: Company name (optional)
        user_notes: User's personal notes and context (NEW - makes tips highly personalized!)
        is_day_of: If True, generates day-of tips; otherwise 24h before tips
    
    Returns:
        HTML-formatted tips string
    """
    try:
        import google.generativeai as genai
        import os
        
        # Configure Gemini AI
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return generate_fallback_tips(phase_type, is_day_of)
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        # Create prompt based on timing
        timing = "day-of last-minute" if is_day_of else "24-hour preparation"
        company_context = f" at {company_name}" if company_name else ""
        
        # Build job context - prioritize what we have
        job_context = f"**Position:** {job_title}{company_context}\n**Phase Type:** {phase_type}"
        
        if job_description:
            job_context += f"\n**Job Description (excerpt):** {job_description[:500]}"
        
        # Build notes context if provided - THIS IS KEY for personalization!
        notes_context = ""
        if user_notes:
            notes_context = f"\n\n[EMOJI] **CANDIDATE'S PERSONAL CONTEXT/NOTES:**\n{user_notes[:500]}\n\n[SYMBOL] CRITICAL: Use the candidate's notes above to make tips HIGHLY PERSONALIZED! Address their specific background, experience level, career goals, and what they mentioned about this opportunity."
        
        prompt = f"""
Generate {timing} tips for a candidate preparing for a {phase_type} for {job_title}{company_context}.

{job_context}{notes_context}

Provide 5-7 specific, actionable tips formatted as HTML list items (<li> tags).

IMPORTANT REQUIREMENTS:
1. Make tips SPECIFIC to the role type ("{job_title}") and phase ("{phase_type}")
2. Use the candidate's personal context/notes to make tips highly relevant to THEIR situation
3. Focus on practical, immediately actionable advice
4. Be encouraging and confidence-building
5. {"Focus on last-minute preparation and mental readiness" if is_day_of else "Focus on thorough preparation over 24 hours"}

For example, if candidate mentions they're switching from testing to another role, address transition strategies.
If they mention experience level or specific technologies, incorporate those.

Format your response as clean HTML list items only (no <ul> wrapper needed).
Example format:
<li><strong>Leverage your testing background:</strong> Emphasize your attention to detail and systematic approach from 4 years in QA</li>
<li><strong>Prepare STAR stories:</strong> Have 2-3 specific examples ready showing your testing expertise and impact</li>

Generate {len([i for i in range(5, 8)])} tips now:
"""
        
        response = model.generate_content(prompt)
        tips_html = response.text.strip()
        
        # Clean up the response - remove markdown code blocks and ul tags
        tips_html = tips_html.replace('```html', '').replace('```', '')
        if '<ul>' in tips_html:
            tips_html = tips_html.replace('<ul>', '').replace('</ul>', '')
        tips_html = tips_html.strip()
        
        return f"<ul style='margin: 0; padding-left: 20px;'>{tips_html}</ul>"
    
    except Exception as e:
        print(f"[SYMBOL] AI tip generation failed: {e}")
        return generate_fallback_tips(phase_type, is_day_of)


def generate_fallback_tips(phase_type: str, is_day_of: bool = False) -> str:
    """Generate fallback tips when AI is unavailable"""
    if is_day_of:
        tips = [
            "<li><strong>Stay calm and confident:</strong> Take deep breaths and remember you've prepared well</li>",
            "<li><strong>Review your resume:</strong> Quickly scan your key achievements and be ready to discuss them</li>",
            "<li><strong>Test your setup:</strong> If virtual, check camera, microphone, and internet connection</li>",
            "<li><strong>Have materials ready:</strong> Keep water, notepad, pen, and your questions list nearby</li>",
            "<li><strong>Arrive early:</strong> Log in 5-10 minutes early or arrive 10-15 minutes before if in-person</li>"
        ]
    else:
        tips = [
            "<li><strong>Research the company:</strong> Study their products, recent news, culture, and values</li>",
            "<li><strong>Review the job description:</strong> Match your experience to their requirements</li>",
            "<li><strong>Prepare your stories:</strong> Use STAR method for behavioral questions</li>",
            "<li><strong>Practice common questions:</strong> Rehearse your answers out loud</li>",
            "<li><strong>Prepare questions:</strong> Have 3-5 thoughtful questions ready to ask</li>",
            "<li><strong>Plan logistics:</strong> Know the location/login details and test your setup</li>"
        ]
    
    return f"<ul style='margin: 0; padding-left: 20px;'>{''.join(tips)}</ul>"


# Skills Gap Analyzer Endpoints

class SkillsGapRequest(BaseModel):
    user_skills: Optional[List[str]] = []
    target_role: Optional[str] = ""
    target_ctc: Optional[str] = ""
    use_ai: bool = True


@router.get("/extract-resume-skills")
async def extract_resume_skills(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract skills from user's saved resume using AI for intelligent parsing
    Returns skills automatically for quick analysis
    """
    try:
        user_skills = []
        resume_content = ""
        
        # Method 1: Get resume content from User.resume_data (simple resume builder)
        if hasattr(current_user, 'resume_data') and current_user.resume_data:
            try:
                resume_dict = json.loads(current_user.resume_data)
                
                # Build complete resume text from all fields for AI analysis
                resume_parts = []
                if resume_dict.get('summary'):
                    resume_parts.append(f"Professional Summary: {resume_dict['summary']}")
                if resume_dict.get('experience'):
                    resume_parts.append(f"Experience: {resume_dict['experience']}")
                if resume_dict.get('skills'):
                    resume_parts.append(f"Skills: {resume_dict['skills']}")
                if resume_dict.get('education'):
                    resume_parts.append(f"Education: {resume_dict['education']}")
                if resume_dict.get('projects'):
                    resume_parts.append(f"Projects: {resume_dict['projects']}")
                if resume_dict.get('certifications'):
                    resume_parts.append(f"Certifications: {resume_dict['certifications']}")
                
                resume_content = "\n\n".join(resume_parts)
                print(f"[SYMBOL] Found resume data ({len(resume_content)} chars)")
                print(f"[EMOJI] Resume preview (first 300 chars): {resume_content[:300]}")
                
            except Exception as e:
                print(f"[SYMBOL]️ Error parsing resume_data: {e}")
        
        # Method 2: Get content from EnhancedResume if Method 1 didn't work
        if not resume_content:
            enhanced_resume = db.query(EnhancedResume).filter(
                EnhancedResume.user_id == current_user.id,
                EnhancedResume.is_active == 1
            ).order_by(EnhancedResume.created_at.desc()).first()
            
            if enhanced_resume and enhanced_resume.enhanced_resume_text:
                resume_content = enhanced_resume.enhanced_resume_text
                print(f"[SYMBOL] Found enhanced resume ({len(resume_content)} chars)")
                print(f"[EMOJI] Resume preview (first 300 chars): {resume_content[:300]}")
        
        # Method 3: Use AI to intelligently extract skills from resume content
        if resume_content:
            print("[EMOJI] Using AI to extract skills from resume...")
            print(f"[EMOJI] Sending {len(resume_content)} chars to AI for analysis")
            user_skills = await _extract_skills_with_ai(resume_content)
            
            if user_skills:
                print(f"[SYMBOL] AI extracted {len(user_skills)} skills from resume")
                
                # Estimate CTC based on extracted skills
                ctc_estimation = await _estimate_ctc_from_skills(user_skills, resume_content)
                
                # Add skill gap to target if CTC is provided in query params
                # This allows showing "skills needed to reach X LPA" even without full analysis
                response_data = {
                    "success": True,
                    "skills": user_skills,
                    "ctc_estimation": ctc_estimation,
                    "message": f"AI extracted {len(user_skills)} skills from your resume"
                }
                
                return response_data
        
        # Method 4: Fallback - Simple text parsing if AI fails
        if not user_skills and resume_content:
            print("[SYMBOL]️ AI failed, using keyword extraction fallback...")
            # Use simple keyword extraction from resume text
            resume_text = resume_content.lower()
            
            # Common technical skills to look for
            common_skills = [
                'python', 'java', 'javascript', 'typescript', 'react', 'angular', 'vue',
                'node.js', 'express', 'django', 'flask', 'fastapi', 'spring boot',
                'sql', 'postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch',
                'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'jenkins', 'git',
                'html', 'css', 'rest api', 'graphql', 'microservices',
                'selenium', 'pytest', 'junit', 'ci/cd', 'agile', 'scrum',
                'machine learning', 'data analysis', 'pandas', 'numpy', 'tensorflow'
            ]
            
            for skill in common_skills:
                if skill in resume_text:
                    # Capitalize properly
                    if skill == 'node.js':
                        user_skills.append('Node.js')
                    elif skill == 'html':
                        user_skills.append('HTML')
                    elif skill == 'css':
                        user_skills.append('CSS')
                    elif skill == 'rest api':
                        user_skills.append('REST API')
                    elif skill == 'graphql':
                        user_skills.append('GraphQL')
                    elif skill == 'ci/cd':
                        user_skills.append('CI/CD')
                    else:
                        user_skills.append(skill.title())
            
            # Remove duplicates while preserving order
            seen = set()
            user_skills = [x for x in user_skills if not (x.lower() in seen or seen.add(x.lower()))]
            
            if user_skills:
                print(f"[SYMBOL] Keyword extraction found {len(user_skills)} skills")
        
        # Method 5: Last resort - extract from job applications
        if not user_skills:
            applications = db.query(Application).filter(
                Application.user_id == current_user.id
            ).limit(10).all()
            
            # Extract unique skills mentioned across applications
            skills_set = set()
            for app in applications:
                if app.skills_required:
                    # Try parsing as JSON first
                    try:
                        skills = json.loads(app.skills_required)
                        if isinstance(skills, list):
                            skills_set.update([s.strip() for s in skills if s.strip()])
                    except:
                        # Comma-separated
                        skills_set.update([s.strip() for s in app.skills_required.split(',') if s.strip()])
            
            user_skills = sorted(list(skills_set))[:20]  # Limit to top 20
        
        return {
            "success": True,
            "skills": user_skills,
            "message": f"Extracted {len(user_skills)} skills from your profile" if user_skills else "No skills found. Try applying to jobs first!"
        }
    except Exception as e:
        print(f"Error extracting skills: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract skills: {str(e)}"
        )


@router.get("/skills-for-target-ctc")
async def get_skills_for_target_ctc(
    target_ctc: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze what skills are needed to reach a target CTC
    Shows the gap between current earning potential and target salary
    """
    try:
        # First, get user's current skills
        user_skills = []
        resume_content = ""
        
        # Get resume content
        if hasattr(current_user, 'resume_data') and current_user.resume_data:
            try:
                resume_dict = json.loads(current_user.resume_data)
                resume_parts = []
                if resume_dict.get('summary'):
                    resume_parts.append(f"Professional Summary: {resume_dict['summary']}")
                if resume_dict.get('experience'):
                    resume_parts.append(f"Experience: {resume_dict['experience']}")
                if resume_dict.get('skills'):
                    resume_parts.append(f"Skills: {resume_dict['skills']}")
                if resume_dict.get('education'):
                    resume_parts.append(f"Education: {resume_dict['education']}")
                if resume_dict.get('projects'):
                    resume_parts.append(f"Projects: {resume_dict['projects']}")
                if resume_dict.get('certifications'):
                    resume_parts.append(f"Certifications: {resume_dict['certifications']}")
                
                resume_content = "\n\n".join(resume_parts)
            except Exception as e:
                print(f"[SYMBOL]️ Error parsing resume_data: {e}")
        
        # Extract skills using AI
        if resume_content:
            user_skills = await _extract_skills_with_ai(resume_content)
        
        if not user_skills:
            return {
                "success": False,
                "message": "No skills found in your resume. Please add your resume first."
            }
        
        # Analyze what skills are needed to reach target CTC
        gap_analysis = await _analyze_skills_for_target_ctc(user_skills, target_ctc, resume_content)
        
        if not gap_analysis.get("success", True):
            raise HTTPException(
                status_code=500,
                detail=gap_analysis.get("message", "Analysis failed")
            )
        
        return {
            "success": True,
            "current_skills": user_skills,
            "target_ctc": target_ctc,
            "gap_analysis": gap_analysis
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SYMBOL] Target CTC analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze target CTC: {str(e)}"
        )


@router.post("/skills-gap-analysis")
async def analyze_skills_gap(
    request: SkillsGapRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze skills gap between user's resume and job market requirements
    Now includes target role and CTC for personalized analysis
    
    Returns:
    - Summary of skills analysis
    - Missing skills ranked by importance
    - Learning recommendations with training platforms
    - Skill priorities
    - Salary insights based on target CTC
    """
    try:
        # Get all user's job applications
        applications = db.query(Application).filter(
            Application.user_id == current_user.id
        ).all()
        
        # Two modes: Job-based analysis OR Target role analysis
        job_apps = []
        
        if applications:
            # Convert to dict format
            for app in applications:
                job_apps.append({
                    "id": app.id,
                    "job_title": app.job_title,
                    "company": app.company,
                    "job_description": app.job_description or ""
                })
        
        # If no job applications but target role provided, use target role analysis
        if not job_apps and not request.target_role:
            raise HTTPException(
                status_code=400,
                detail="Please either: 1) Save some job applications, OR 2) Enter a Target Role for analysis"
            )
        
        # If target role provided but no/few jobs, create synthetic job for analysis
        if request.target_role and len(job_apps) < 3:
            # Add a synthetic job based on target role for better analysis
            job_apps.append({
                "id": 0,
                "job_title": request.target_role,
                "company": "General Market",
                "job_description": f"Looking for {request.target_role} with relevant skills and experience."
            })
        
        # Perform analysis with target role and CTC
        analysis = await skills_gap_analyzer.analyze_gap(
            user_skills=request.user_skills,
            job_applications=job_apps,
            target_role=request.target_role,
            target_ctc=request.target_ctc,
            use_ai=request.use_ai
        )
        
        # Add training platforms
        analysis["training_platforms"] = skills_gap_analyzer.get_training_platforms(
            analysis.get("missing_skills", [])[:10]  # Top 10 missing skills
        )
        
        # Add salary insights if CTC provided
        if request.target_ctc:
            analysis["salary_insights"] = skills_gap_analyzer.get_salary_insights(
                target_role=request.target_role,
                target_ctc=request.target_ctc,
                user_skills=request.user_skills,
                missing_skills=analysis.get("missing_skills", [])[:5]
            )
        
        return {
            "success": True,
            "analysis": analysis,
            "target_role": request.target_role,
            "target_ctc": request.target_ctc,
            "timestamp": datetime.now().isoformat()
        }
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SYMBOL] Skills gap analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze skills gap: {str(e)}"
        )


@router.get("/extract-skills-from-jobs")
async def extract_skills_from_jobs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Extract all skills from user's saved job applications
    Useful for seeing what skills are in demand
    """
    try:
        applications = db.query(Application).filter(
            Application.user_id == current_user.id
        ).all()
        
        if not applications:
            return {
                "success": False,
                "message": "No job applications found"
            }
        
        all_skills = []
        for app in applications:
            job_desc = app.job_description or ""
            skills = skills_gap_analyzer.extract_skills_from_text(job_desc)
            all_skills.extend(skills)
        
        # Count frequency
        from collections import Counter
        skill_counts = Counter(all_skills)
        
        # Get top 20 skills
        top_skills = [
            {"skill": skill, "count": count}
            for skill, count in skill_counts.most_common(20)
        ]
        
        return {
            "success": True,
            "total_jobs": len(applications),
            "unique_skills": len(skill_counts),
            "top_skills": top_skills
        }
    
    except Exception as e:
        print(f"[SYMBOL] Skill extraction error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract skills: {str(e)}"
        )


@router.post("/extract-skills-from-text")
async def extract_skills_from_text(
    text: str,
    current_user: User = Depends(get_current_user)
):
    """
    Extract skills from any text (resume, job description, etc.)
    """
    try:
        skills = skills_gap_analyzer.extract_skills_from_text(text)
        
        return {
            "success": True,
            "skills": skills,
            "count": len(skills)
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract skills: {str(e)}"
        )
