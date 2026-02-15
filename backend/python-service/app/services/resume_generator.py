"""
AI-Powered Resume Generator with Company-Specific Optimization
Generates ATS-optimized resumes tailored to specific companies
"""

import os
import json
import asyncio
from typing import Dict, List, Optional

import google.generativeai as genai
from app.services.multi_ai_service import multi_ai_service
import logging

logger = logging.getLogger(__name__)


class ResumeGenerator:
    def __init__(self) -> None:
        self.gemini_keys = self._load_gemini_keys()
        self.current_key_index = 0
        if self.gemini_keys:
            logger.info(f" Resume Generator initialized with {len(self.gemini_keys)} Gemini account(s)")
        else:
            logger.info(" Resume Generator initialized without Gemini keys")

    def _load_gemini_keys(self) -> List[str]:
        """Load all available Gemini API keys"""
        keys: List[str] = []
        primary = os.getenv("GEMINI_API_KEY")
        if primary:
            keys.append(primary)
        for i in range(2, 6):
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if key:
                keys.append(key)
        return keys

    def _normalize_skills(self, skills_raw) -> List[str]:
        if isinstance(skills_raw, dict):
            technical = skills_raw.get("technical", []) or []
            soft = skills_raw.get("soft", []) or []
            return list(technical) + list(soft)
        if isinstance(skills_raw, list):
            return skills_raw
        return []

    def _normalize_education(self, education_raw, fallback_raw=None):
        """Normalize education entries to include institution/degree/year fields."""
        def normalize_entry(entry):
            if not isinstance(entry, dict):
                return None
            institution = (
                entry.get("institution")
                or entry.get("university")
                or entry.get("school")
                or entry.get("college")
                or entry.get("university_name")
                or entry.get("institution_name")
                or ""
            )
            degree = entry.get("degree") or entry.get("qualification") or entry.get("program") or ""
            year = entry.get("year") or entry.get("graduation_date") or entry.get("graduation_year") or ""
            return {
                "degree": degree,
                "institution": institution,
                "year": year,
                "field": entry.get("field") or entry.get("major") or "",
                "relevant_courses": entry.get("relevant_courses") or []
            }

        education_list = education_raw if isinstance(education_raw, list) else []
        fallback_list = fallback_raw if isinstance(fallback_raw, list) else []

        normalized = [e for e in (normalize_entry(e) for e in education_list) if e]

        if not normalized and fallback_list:
            normalized = [e for e in (normalize_entry(e) for e in fallback_list) if e]
        else:
            for i, fb in enumerate(fallback_list):
                if i >= len(normalized):
                    break
                if not normalized[i].get("institution"):
                    normalized[i]["institution"] = fb.get("institution") or fb.get("university") or ""
                if not normalized[i].get("degree"):
                    normalized[i]["degree"] = fb.get("degree") or ""
                if not normalized[i].get("year"):
                    normalized[i]["year"] = fb.get("year") or fb.get("graduation_date") or ""

        return normalized

    def _strip_json_block(self, text: str) -> str:
        if "```json" in text:
            return text.split("```json")[1].split("```")[0].strip()
        if "```" in text:
            return text.split("```", 1)[1].split("```")[0].strip()
        return text

    async def research_company(self, company_name: str) -> Dict:
        """
        Research company to understand culture, values, and resume preferences
        """
        logger.info(f"\n Researching company: {company_name}")

        prompt = f"""You are a senior career strategist with expertise in ATS-optimized resumes and hiring trends as of 2026.

Analyze the company "{company_name}" and provide resume formatting recommendations. If you don't have reliable information about this company, base your analysis on similar companies in the same industry.

Return ONLY valid JSON (no markdown, no code blocks):
{{
    "company_type": "Tech/Corporate/Startup/Consulting/Finance/Healthcare/etc",
    "culture_keywords": ["5 specific culture and value keywords for this company"],
    "recommended_template": "Modern/Professional/Creative/ATS-Optimized",
    "accepted_templates": ["primary choice", "secondary choice"],
    "resume_format_tips": ["3 specific formatting tips tailored to this company's hiring style"],
    "key_skills_to_highlight": ["4-6 skills this company values most based on their tech stack and culture"],
    "tone": "Professional/Conversational/Technical",
    "template_reasoning": "Brief explanation of why this template suits the company"
}}"""

        if self.gemini_keys:
            try:
                api_key = self.gemini_keys[0]
                genai.configure(api_key=api_key)
                model_candidates = [
                    "gemini-1.5-flash-002",
                    "gemini-1.5-flash-latest",
                    "gemini-1.5-flash",
                    "gemini-1.5-pro-002",
                    "gemini-1.0-pro",
                    "gemini-pro",
                    "text-bison-001",
                    "chat-bison-001",
                ]
                for model_name in model_candidates:
                    try:
                        model = genai.GenerativeModel(model_name)
                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                model.generate_content,
                                prompt,
                                generation_config={"temperature": 0.3, "max_output_tokens": 500}
                            ),
                            timeout=8.0
                        )
                        text = self._strip_json_block(response.text.strip())
                        result = json.loads(text)
                        logger.info(f" Gemini provided company research in <8s using {model_name}")
                        return result
                    except asyncio.TimeoutError:
                        logger.info(f" Gemini timeout with {model_name} - trying next")
                    except Exception as e:
                        logger.error(f" Gemini failed with {model_name}: {str(e)[:100]}")
            except Exception as e:
                logger.error(f" Gemini configuration failed: {str(e)[:100]}")

        if multi_ai_service.providers:
            try:
                alt = await multi_ai_service.generate_text(
                    prompt,
                    strategy="smart",
                    max_tokens=500,
                    temperature=0.3
                )
                if alt.get("success") and alt.get("text"):
                    text = self._strip_json_block(alt["text"].strip())
                    result = json.loads(text)
                    logger.info(" Company research generated via fallback provider")
                    return result
            except Exception as e:
                logger.error(f" Fallback AI research failed: {str(e)[:100]}")

        logger.info(" Using default company profile")
        return {
            "company_type": "General",
            "culture_keywords": ["professional", "collaborative", "results-driven", "innovative", "excellence"],
            "recommended_template": "Professional",
            "accepted_templates": ["Professional", "ATS-Optimized", "Modern"],
            "resume_format_tips": [
                "Use clear section headers",
                "Quantify achievements with metrics",
                "Keep formatting clean and ATS-friendly"
            ],
            "key_skills_to_highlight": ["Communication", "Problem Solving", "Team Collaboration", "Project Management"],
            "tone": "Professional",
            "template_reasoning": "Professional templates work well for most companies and ensure ATS compatibility"
        }

    async def generate_resume_content(
        self,
        user_info: Dict,
        company_research: Dict,
        job_title: Optional[str] = None,
        ai_suggestions: Optional[str] = None
    ) -> Dict:
        """Generate complete resume content optimized for the company"""
        logger.info("\n[AI] Attempting to generate AI-enhanced resume...")

        company_type = company_research.get("company_type", "General")
        keywords = company_research.get("culture_keywords", [])
        skills_list = self._normalize_skills(user_info.get("skills"))
        skills_str = ", ".join(skills_list[:10]) if skills_list else ""

        experience_items = user_info.get("experience") or []
        exp_str = "\n".join([
            f"- {e.get('title', '')} at {e.get('company', '')} ({e.get('duration', '')}): {e.get('description', '')}"
            for e in experience_items[:3]
            if isinstance(e, dict)
        ])

        education_items = user_info.get("education") or []
        edu_str = "\n".join([
            f"- {e.get('degree', '')} at {e.get('institution', '')} ({e.get('year', '')})"
            for e in education_items[:3]
            if isinstance(e, dict)
        ])

        keywords_str = json.dumps(keywords) if isinstance(keywords, list) else str(keywords)

        prompt = f"""You are a certified professional resume writer (CPRW) specializing in ATS-optimized resumes for {company_type} companies.

TARGET ROLE: {job_title or 'Not specified'}
COMPANY TYPE: {company_type}
ADDITIONAL INSTRUCTIONS: {ai_suggestions or 'None'}

CANDIDATE'S ACTUAL DATA:
Experience:
{exp_str if exp_str else 'No experience provided'}

Skills: {skills_str if skills_str else 'No skills provided'}

Education:
{edu_str if edu_str else 'No education provided'}

CRITICAL RULES:
1. DO NOT fabricate any work experience, companies, job titles, or achievements the candidate hasn't listed
2. ONLY enhance and reword the candidate's actual data — never invent new roles or employers
3. Quantify achievements where the candidate's data supports it (add metrics only if inferable)
4. Use strong action verbs and industry-relevant keywords for ATS optimization
5. Tailor the professional summary to the target role and company type

Return ONLY raw JSON (no markdown, no code blocks) with this structure:
{{
  "professional_summary": "2-3 impactful sentences positioning the candidate for a {company_type} {job_title or 'professional'} role",
  "experience": [
    {{
      "title": "<candidate's actual job title>",
      "company": "<candidate's actual company>",
      "duration": "<actual duration>",
      "achievements": ["Enhanced achievement 1 with metrics", "Enhanced achievement 2"]
    }}
  ],
  "skills": {{
    "technical": ["relevant technical skills from candidate's data"],
    "soft": ["relevant soft skills"]
  }},
  "education": [],
  "projects": [],
  "certifications": [],
  "keywords_optimized": {keywords_str}
}}"""

        logger.info("[AI] Calling Gemini API...")

        if self.gemini_keys:
            try:
                api_key = self.gemini_keys[0]
                logger.info(f"[AI] Using Gemini API key (length: {len(api_key)})")
                genai.configure(api_key=api_key)
                model_candidates = [
                    "gemini-1.5-flash-002",
                    "gemini-1.5-flash-latest",
                    "gemini-1.5-flash",
                    "gemini-1.5-pro-002",
                    "gemini-1.0-pro",
                    "gemini-pro",
                    "text-bison-001",
                    "chat-bison-001",
                ]
                for model_name in model_candidates:
                    try:
                        logger.info(f"[AI] Sending request to {model_name} with 10-second timeout...")
                        model = genai.GenerativeModel(model_name)
                        response = await asyncio.wait_for(
                            asyncio.to_thread(
                                model.generate_content,
                                prompt,
                                generation_config={"temperature": 0.7, "max_output_tokens": 2000}
                            ),
                            timeout=10.0
                        )
                        text = self._strip_json_block(response.text.strip())
                        result = json.loads(text)
                        logger.info("[AI] Successfully parsed AI response!")

                        if "experience" in result and result["experience"]:
                            for exp in result["experience"]:
                                if "achievements" not in exp:
                                    exp["achievements"] = []

                        if "skills" in result and isinstance(result["skills"], list):
                            result["skills"] = {"technical": result["skills"][:8], "soft": ["Communication"]}

                        result["education"] = self._normalize_education(
                            result.get("education"),
                            user_info.get("education")
                        )

                        return result
                    except asyncio.TimeoutError:
                        logger.info(f"[AI] Timeout after 10 seconds with {model_name}")
                    except Exception as e:
                        logger.error(f"[AI] Error with {model_name}: {str(e)}")
            except Exception as e:
                logger.error(f"[AI] Error: {str(e)[:100]}")
        else:
            logger.info("[AI] No API keys available")

        if multi_ai_service.providers:
            try:
                alt = await multi_ai_service.generate_text(
                    prompt,
                    strategy="smart",
                    max_tokens=2000,
                    temperature=0.7
                )
                if alt.get("success") and alt.get("text"):
                    text = self._strip_json_block(alt["text"].strip())
                    result = json.loads(text)
                    logger.info("[AI] Successfully parsed fallback provider response!")

                    if "experience" in result and result["experience"]:
                        for exp in result["experience"]:
                            if "achievements" not in exp:
                                exp["achievements"] = []

                    if "skills" in result and isinstance(result["skills"], list):
                        result["skills"] = {"technical": result["skills"][:8], "soft": ["Communication"]}

                    result["education"] = self._normalize_education(
                        result.get("education"),
                        user_info.get("education")
                    )

                    return result
            except Exception as e:
                logger.error(f"[AI] Fallback provider failed: {str(e)[:100]}")

        logger.info("[AI] Using fallback resume from user data")

        experience = []
        for exp in experience_items[:3]:
            if isinstance(exp, dict):
                experience.append({
                    "title": exp.get("title", ""),
                    "company": exp.get("company", ""),
                    "duration": exp.get("duration", ""),
                    "achievements": [exp.get("description", "Contributed")] if exp.get("description") else []
                })

        skills = {"technical": skills_list[:8], "soft": ["Communication", "Problem Solving"]}

        projects = []
        projects_source = user_info.get("projects") or []
        for proj in projects_source[:2]:
            if isinstance(proj, dict):
                techs = proj.get("technologies", "")
                if isinstance(techs, str):
                    tech_list = [t.strip() for t in techs.split(",") if t.strip()]
                else:
                    tech_list = techs if isinstance(techs, list) else []

                projects.append({
                    "name": proj.get("name", ""),
                    "description": proj.get("description", ""),
                    "technologies": tech_list
                })

        education = self._normalize_education(user_info.get("education"))
        certifications = user_info.get("certifications") or []

        summary_seed = (user_info.get("summary") or "").strip()
        if summary_seed:
            professional_summary = f"Results-driven professional with {summary_seed.rstrip('.')}."
            if skills_list:
                professional_summary += f" Demonstrated impact across {', '.join(skills_list[:3])}."
        else:
            professional_summary = f"Experienced professional with expertise in {', '.join(skills_list[:3])}."

        return {
            "professional_summary": professional_summary,
            "experience": experience,
            "skills": skills,
            "education": education,
            "projects": projects,
            "certifications": certifications[:3],
            "keywords_optimized": company_research.get("culture_keywords", [])
        }


resume_generator = ResumeGenerator()
