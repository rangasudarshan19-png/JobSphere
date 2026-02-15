"""
Resume Analyzer Service - Extract skills and profile from resumes using Gemini AI
"""

import os
import json
import google.generativeai as genai
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logger.info("Gemini AI enabled for resume analysis")
else:
    logger.info("GEMINI_API_KEY not found - Resume analysis will use fallback")


class ResumeAnalyzer:
    """Analyze resumes and extract structured profile data for job matching"""
    
    def __init__(self):
        self.ai_enabled = GEMINI_API_KEY is not None
        if self.ai_enabled:
            try:
                self.model = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("Resume Analyzer initialized with Gemini AI")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini model: {e}")
                self.ai_enabled = False
    
    async def extract_profile(self, resume_text: str) -> Dict:
        """
        Extract structured profile from resume text
        
        Returns:
        {
            "skills": ["Python", "Selenium", "API Testing", ...],
            "experience_years": 3,
            "job_titles": ["QA Engineer", "Software Tester"],
            "location_preference": "Bangalore",
            "education": ["B.Tech in Computer Science"],
            "certifications": ["ISTQB", "AWS Certified"]
        }
        """
        if not self.ai_enabled:
            return self._fallback_extract(resume_text)
        
        try:
            # Truncate resume to avoid token overflow
            truncated_resume = resume_text[:8000] if len(resume_text) > 8000 else resume_text
            
            prompt = f"""
You are a senior technical recruiter with 15+ years of experience analyzing resumes across the tech industry (as of 2026).

Analyze this resume and extract key information for job matching.

Resume:
{truncated_resume}

EXTRACTION RULES:
1. skills: Extract ALL technical skills, tools, frameworks, languages, and technologies explicitly mentioned. Be comprehensive but only include what is stated.
2. experience_years: Calculate total years of professional experience from dates listed. If unclear, estimate conservatively.
3. job_titles: Extract ONLY job titles the person has actually held (listed in their experience section). Do NOT infer titles they haven't held.
4. location_preference: Extract from their listed location or any stated preference. Default to "Not specified" if absent.
5. education: Extract degrees, institutions, and years exactly as stated.
6. certifications: Extract certifications and credentials exactly as stated.

Return ONLY valid JSON in this exact format:
{{
    "skills": ["skill1", "skill2", ...],
    "experience_years": 3,
    "job_titles": ["title1", "title2"],
    "location_preference": "City/Remote",
    "education": ["degree1", "degree2"],
    "certifications": ["cert1", "cert2"]
}}
"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower temperature for factual extraction
                    max_output_tokens=2048
                )
            )
            
            result_text = response.text.strip()
            
            # Clean up markdown formatting if present
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            profile = json.loads(result_text)
            
            logger.info(f"Profile extracted: {len(profile.get('skills', []))} skills, "
                  f"{profile.get('experience_years', 0)} years experience")
            
            return profile
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.info(f"Raw response: {result_text[:200]}...")
            return self._fallback_extract(resume_text)
        except Exception as e:
            logger.error(f"Profile extraction failed: {e}")
            return self._fallback_extract(resume_text)
    
    def _fallback_extract(self, resume_text: str) -> Dict:
        """
        Fallback extraction using keyword matching (when AI is unavailable)
        """
        logger.info("Using fallback extraction (basic keyword matching)")
        
        text_lower = resume_text.lower()
        
        # Common tech skills to look for
        tech_skills = [
            "python", "java", "javascript", "c++", "c#", "ruby", "php", "golang", "rust",
            "react", "angular", "vue", "node.js", "django", "flask", "spring", "express",
            "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
            "aws", "azure", "gcp", "docker", "kubernetes", "jenkins", "ci/cd",
            "selenium", "pytest", "junit", "testng", "cucumber", "postman",
            "git", "github", "gitlab", "jira", "agile", "scrum",
            "rest api", "graphql", "microservices", "api testing", "automation"
        ]
        
        found_skills = [skill for skill in tech_skills if skill in text_lower]
        
        # Extract experience years (look for patterns like "3 years", "5+ years")
        experience_years = 0
        import re
        exp_pattern = r'(\d+)\+?\s*(?:years?|yrs?)'
        matches = re.findall(exp_pattern, text_lower)
        if matches:
            experience_years = int(matches[0])
        
        # Common job titles
        job_titles = []
        title_keywords = {
            "software engineer": ["software engineer", "developer", "programmer"],
            "qa engineer": ["qa engineer", "tester", "quality assurance", "sdet"],
            "data scientist": ["data scientist", "ml engineer", "data analyst"],
            "devops engineer": ["devops", "sre", "site reliability"],
            "product manager": ["product manager", "pm"]
        }
        
        for title, keywords in title_keywords.items():
            if any(kw in text_lower for kw in keywords):
                job_titles.append(title.title())
        
        return {
            "skills": found_skills,
            "experience_years": experience_years,
            "job_titles": job_titles if job_titles else ["Software Engineer"],
            "location_preference": "Not specified",
            "education": [],
            "certifications": []
        }
    
    async def enhance_resume(self, original_text: str, target_job_title: str = None) -> str:
        """
        Use AI to enhance resume for better job matching
        
        Args:
            original_text: Original resume text
            target_job_title: Optional job title to optimize for
        
        Returns:
            Enhanced resume text
        """
        if not self.ai_enabled:
            logger.info("AI not available, returning original resume")
            return original_text
        
        try:
            target_context = f" for {target_job_title} positions" if target_job_title else ""
            # Truncate to avoid token overflow
            truncated_text = original_text[:8000] if len(original_text) > 8000 else original_text
            
            prompt = f"""
You are a certified professional resume writer (CPRW) with expertise in ATS optimization and modern hiring trends (2026).

Improve this resume{target_context} by:
1. Rewriting descriptions to be achievement-focused using strong action verbs (Led, Spearheaded, Optimized, Delivered, etc.)
2. Adding relevant ATS keywords{' for ' + target_job_title + ' roles' if target_job_title else ' for the candidate\'s field'}
3. Improving section structure and professional flow
4. Highlighting quantifiable achievements (add metrics where data supports it)
5. Enhancing skills presentation for maximum recruiter impact

CRITICAL CONSTRAINTS:
- Preserve ALL factual information (companies, dates, job titles, education)
- Do NOT add fabricated experiences, companies, or achievements
- Only enhance language, structure, and keyword density
- Keep the output to approximately the same length as the original

Original Resume:
{truncated_text}

Return the enhanced resume text (not JSON, plain text with clear sections):
"""
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=4096
                )
            )
            
            enhanced_text = response.text.strip()
            
            logger.info(f"Resume enhanced: {len(original_text)} → {len(enhanced_text)} characters")
            
            return enhanced_text
            
        except Exception as e:
            logger.error(f"Resume enhancement failed: {e}")
            return original_text


# Singleton instance
resume_analyzer = ResumeAnalyzer()

