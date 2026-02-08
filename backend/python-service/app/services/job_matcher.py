"""
Job Matcher Service - Use AI to match jobs with resume profiles
"""

import os
import json
import google.generativeai as genai
from typing import Dict, List

# Configure Gemini AI
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)


class JobMatcher:
    """Match jobs with resume profiles using AI"""
    
    def __init__(self):
        self.ai_enabled = GEMINI_API_KEY is not None
        if self.ai_enabled:
            try:
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
                print("[SYMBOL] Job Matcher initialized with Gemini AI")
            except Exception as e:
                print(f"[SYMBOL] Failed to initialize Gemini model: {e}")
                self.ai_enabled = False
    
    async def calculate_match(self, profile: Dict, job: Dict) -> Dict:
        """
        Calculate how well a job matches a resume profile
        
        Args:
            profile: User's extracted profile (skills, experience, etc.)
            job: Job details (title, description, requirements)
        
        Returns:
        {
            "score": 85,  # 0-100
            "matching_skills": ["Python", "Selenium", "API Testing"],
            "missing_skills": ["AWS", "Docker"],
            "reason": "Strong match based on...",
            "confidence": "high"  # high, medium, low
        }
        """
        if not self.ai_enabled:
            return self._fallback_match(profile, job)
        
        try:
            prompt = f"""
            You are an expert job matcher. Analyze how well this candidate's profile matches the job posting.
            
            CANDIDATE PROFILE:
            - Skills: {', '.join(profile.get('skills', []))}
            - Experience: {profile.get('experience_years', 0)} years
            - Job Titles: {', '.join(profile.get('job_titles', []))}
            - Location Preference: {profile.get('location_preference', 'Not specified')}
            - Education: {', '.join(profile.get('education', []))}
            - Certifications: {', '.join(profile.get('certifications', []))}
            
            JOB POSTING:
            - Title: {job.get('title', '')}
            - Company: {job.get('company', '')}
            - Location: {job.get('location', '')}
            - Type: {job.get('job_type', '')}
            - Description: {job.get('description', '')[:500]}...
            - Requirements: {job.get('requirements', [])}
            
            Calculate a match score (0-100) based on:
            1. Skills overlap (40% weight) - How many required skills does candidate have?
            2. Experience level (30% weight) - Does experience match job seniority?
            3. Job title relevance (20% weight) - Do previous titles align?
            4. Location fit (10% weight) - Does location match preferences?
            
            Return ONLY valid JSON in this exact format:
            {{
                "score": 85,
                "matching_skills": ["skill1", "skill2", "skill3"],
                "missing_skills": ["skill4", "skill5"],
                "reason": "Brief explanation of why this is a good/bad match",
                "confidence": "high"
            }}
            
            Be realistic with scores:
            - 90-100: Excellent match, highly qualified
            - 80-89: Strong match, well qualified
            - 70-79: Good match, qualified with minor gaps
            - 60-69: Fair match, some gaps
            - Below 60: Weak match, significant gaps
            """
            
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower for consistent scoring
                    max_output_tokens=1024
                )
            )
            
            result_text = response.text.strip()
            
            # Clean up markdown
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.startswith("```"):
                result_text = result_text[3:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            result_text = result_text.strip()
            
            match_data = json.loads(result_text)
            
            print(f"[SYMBOL] Match score calculated: {match_data.get('score', 0)}% for {job.get('title', 'Unknown')}")
            
            return match_data
            
        except json.JSONDecodeError as e:
            print(f"[SYMBOL] Failed to parse AI response: {e}")
            return self._fallback_match(profile, job)
        except Exception as e:
            print(f"[SYMBOL] Match calculation failed: {e}")
            return self._fallback_match(profile, job)
    
    def _fallback_match(self, profile: Dict, job: Dict) -> Dict:
        """
        Fallback matching using simple keyword overlap (when AI unavailable)
        """
        print("[SYMBOL]️ Using fallback matching (keyword-based)")
        
        profile_skills = set(s.lower() for s in profile.get('skills', []))
        
        # Extract keywords from job description and requirements
        job_text = f"{job.get('description', '')} {str(job.get('requirements', []))}"
        job_text_lower = job_text.lower()
        
        # Find matching skills
        matching_skills = [
            skill for skill in profile.get('skills', [])
            if skill.lower() in job_text_lower
        ]
        
        # Calculate basic score
        skill_match_ratio = len(matching_skills) / max(len(profile_skills), 1)
        experience_score = min(profile.get('experience_years', 0) * 10, 30)
        
        total_score = int((skill_match_ratio * 40) + experience_score + 30)  # Base 30 points
        total_score = min(100, max(0, total_score))
        
        return {
            "score": total_score,
            "matching_skills": matching_skills[:5],  # Top 5
            "missing_skills": [],
            "reason": f"Keyword-based match: {len(matching_skills)} skills overlap",
            "confidence": "medium" if total_score >= 70 else "low"
        }
    
    async def batch_match(self, profile: Dict, jobs: List[Dict], min_score: int = 80) -> List[Dict]:
        """
        Match multiple jobs with profile and filter by minimum score
        
        Args:
            profile: User's profile
            jobs: List of job dictionaries
            min_score: Minimum match score to include (0-100)
        
        Returns:
            List of jobs with match data, sorted by score (highest first)
        """
        matched_jobs = []
        
        for i, job in enumerate(jobs):
            print(f"[EMOJI] Matching job {i+1}/{len(jobs)}: {job.get('title', 'Unknown')}")
            
            match_data = await self.calculate_match(profile, job)
            score = match_data.get('score', 0)
            
            if score >= min_score:
                matched_jobs.append({
                    **job,
                    "match_score": score,
                    "matching_skills": match_data.get('matching_skills', []),
                    "missing_skills": match_data.get('missing_skills', []),
                    "match_reason": match_data.get('reason', ''),
                    "match_confidence": match_data.get('confidence', 'medium')
                })
        
        # Sort by score (highest first)
        matched_jobs.sort(key=lambda x: x['match_score'], reverse=True)
        
        print(f"[SYMBOL] Found {len(matched_jobs)} jobs with {min_score}%+ match score")
        
        return matched_jobs


# Singleton instance
job_matcher = JobMatcher()

