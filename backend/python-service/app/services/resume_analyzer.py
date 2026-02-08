"""
Resume Analyzer Service - Extract skills and profile from resumes using Gemini AI
"""

import os
import json
import google.generativeai as genai
from typing import Dict, List, Optional

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("[SYMBOL] Gemini AI enabled for resume analysis")
else:
    print("[SYMBOL]️ GEMINI_API_KEY not found - Resume analysis will use fallback")


class ResumeAnalyzer:
    """Analyze resumes and extract structured profile data for job matching"""
    
    def __init__(self):
        self.ai_enabled = GEMINI_API_KEY is not None
        if self.ai_enabled:
            try:
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("[SYMBOL] Resume Analyzer initialized with Gemini AI")
            except Exception as e:
                print(f"[SYMBOL] Failed to initialize Gemini model: {e}")
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
            prompt = f"""
            Analyze this resume and extract key information for job matching.
            
            Resume:
            {resume_text}
            
            Extract the following information and return as JSON:
            1. skills: Array of technical skills, tools, and technologies (be comprehensive)
            2. experience_years: Total years of professional experience (integer)
            3. job_titles: Array of job titles/roles the person has held or is qualified for
            4. location_preference: Preferred work location (city/country) or "Remote"
            5. education: Array of degrees/qualifications
            6. certifications: Array of certifications and credentials
            
            Be thorough in extracting ALL skills mentioned (programming languages, frameworks, tools, methodologies).
            
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
            
            print(f"[SYMBOL] Profile extracted: {len(profile.get('skills', []))} skills, "
                  f"{profile.get('experience_years', 0)} years experience")
            
            return profile
            
        except json.JSONDecodeError as e:
            print(f"[SYMBOL] Failed to parse AI response as JSON: {e}")
            print(f"Raw response: {result_text[:200]}...")
            return self._fallback_extract(resume_text)
        except Exception as e:
            print(f"[SYMBOL] Profile extraction failed: {e}")
            return self._fallback_extract(resume_text)
    
    def _fallback_extract(self, resume_text: str) -> Dict:
        """
        Fallback extraction using keyword matching (when AI is unavailable)
        """
        print("[SYMBOL]️ Using fallback extraction (basic keyword matching)")
        
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
            print("[SYMBOL]️ AI not available, returning original resume")
            return original_text
        
        try:
            target_context = f" for {target_job_title} positions" if target_job_title else ""
            
            prompt = f"""
            Improve this resume{target_context} by:
            1. Enhancing descriptions to be more impactful and achievement-focused
            2. Adding relevant keywords that ATS systems look for
            3. Improving formatting and structure
            4. Highlighting quantifiable achievements
            5. Making skills and experience more prominent
            
            Keep the same core information but present it more effectively.
            DO NOT add fake information or experiences.
            
            Original Resume:
            {original_text}
            
            Return the enhanced resume text (not JSON, just the text):
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=4096
                )
            )
            
            enhanced_text = response.text.strip()
            
            print(f"[SYMBOL] Resume enhanced: {len(original_text)} → {len(enhanced_text)} characters")
            
            return enhanced_text
            
        except Exception as e:
            print(f"[SYMBOL] Resume enhancement failed: {e}")
            return original_text


# Singleton instance
resume_analyzer = ResumeAnalyzer()

