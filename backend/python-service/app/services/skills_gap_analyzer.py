"""
Skills Gap Analyzer Service
Analyzes user's skills vs. job market requirements and provides learning recommendations
"""

import os
from typing import Dict, List, Optional, Any
from collections import Counter
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


class SkillsGapAnalyzer:
    """
    Analyzes skills gap between user's resume and job requirements
    Provides learning recommendations and tracks progress
    """
    
    def __init__(self):
        self.ai_enabled = False
        
        # Initialize Gemini if available
        if GEMINI_AVAILABLE:
            api_key = os.getenv('GEMINI_API_KEY')
            if api_key:
                try:
                    genai.configure(api_key=api_key)
                    self.model = genai.GenerativeModel('gemini-2.0-flash')
                    self.ai_enabled = True
                    logger.info("[OK] Skills Gap Analyzer initialized with Gemini AI")
                except Exception as e:
                    logger.error(f"[WARNING] Gemini initialization failed: {e}")
        
        # Common tech skills database
        self.skills_database = self._load_skills_database()
    
    def _load_skills_database(self) -> Dict[str, List[str]]:
        """Load comprehensive skills database with categories"""
        
        return {
            "programming_languages": [
                "Python", "JavaScript", "Java", "C++", "C#", "TypeScript", "Go", 
                "Rust", "Swift", "Kotlin", "PHP", "Ruby", "Scala", "R", "MATLAB"
            ],
            "web_frameworks": [
                "React", "Angular", "Vue.js", "Next.js", "Django", "Flask", "FastAPI",
                "Express.js", "Spring Boot", "ASP.NET", "Ruby on Rails", "Laravel"
            ],
            "mobile": [
                "React Native", "Flutter", "Swift UI", "Android", "iOS", "Xamarin"
            ],
            "databases": [
                "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra",
                "Elasticsearch", "Oracle", "SQL Server", "DynamoDB", "Firebase"
            ],
            "cloud": [
                "AWS", "Azure", "Google Cloud", "GCP", "Docker", "Kubernetes",
                "Terraform", "CloudFormation", "Lambda", "EC2", "S3"
            ],
            "devops": [
                "CI/CD", "Jenkins", "GitLab CI", "GitHub Actions", "Ansible",
                "Docker", "Kubernetes", "Prometheus", "Grafana", "ELK Stack"
            ],
            "data_science": [
                "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
                "Pandas", "NumPy", "Scikit-learn", "Keras", "NLP", "Computer Vision"
            ],
            "tools": [
                "Git", "Jira", "Confluence", "Postman", "VS Code", "IntelliJ",
                "Linux", "Unix", "Bash", "PowerShell"
            ],
            "soft_skills": [
                "Communication", "Leadership", "Problem Solving", "Team Collaboration",
                "Agile", "Scrum", "Project Management", "Time Management"
            ]
        }
    
    def extract_skills_from_text(self, text: str) -> List[str]:
        """Extract skills from any text (resume, job description)"""
        
        if not text:
            return []
        
        text_lower = text.lower()
        found_skills = set()
        
        # Check against known skills database
        for category, skills in self.skills_database.items():
            for skill in skills:
                # Case-insensitive matching with word boundaries
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    found_skills.add(skill)
        
        return sorted(list(found_skills))
    
    async def analyze_gap(
        self,
        user_skills: List[str],
        job_applications: List[Dict[str, Any]],
        target_role: str = "",
        target_ctc: str = "",
        use_ai: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze skills gap between user's skills and job requirements
        
        Args:
            user_skills: List of skills from user's resume
            job_applications: List of saved job applications with descriptions
            target_role: Target job role (e.g., "Senior Python Developer")
            target_ctc: Target salary/CTC (e.g., "$120k" or "₹15 LPA")
            use_ai: Whether to use AI for enhanced analysis
        """
        
        if not job_applications:
            return {
                "error": "No job applications found for analysis"
            }
        
        # Extract required skills from all job descriptions
        all_required_skills = []
        job_skills_map = {}
        
        for job in job_applications:
            job_desc = job.get("job_description", "")
            required_skills = self.extract_skills_from_text(job_desc)
            all_required_skills.extend(required_skills)
            job_skills_map[job.get("id")] = required_skills
        
        # If target role provided and few skills found, use AI to generate expected skills
        if target_role and len(all_required_skills) < 10 and use_ai and self.ai_enabled:
            logger.info(f"Using AI to generate expected skills for: {target_role}")
            ai_skills = await self._generate_skills_for_role(target_role)
            if ai_skills:
                all_required_skills.extend(ai_skills)
                logger.info(f"AI generated {len(ai_skills)} expected skills for {target_role}")
        
        # Count frequency of each skill across all jobs
        skill_frequency = Counter(all_required_skills)
        
        # Identify missing skills (required but not in user's skills)
        user_skills_lower = [s.lower() for s in user_skills]
        missing_skills = {}
        
        for skill, count in skill_frequency.items():
            if skill.lower() not in user_skills_lower:
                missing_skills[skill] = {
                    "count": count,
                    "percentage": round((count / len(job_applications)) * 100, 1)
                }
        
        # Sort missing skills by frequency (most important first)
        sorted_missing = sorted(
            missing_skills.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )
        
        # Get matching skills
        matching_skills = [
            skill for skill in skill_frequency.keys()
            if skill.lower() in user_skills_lower
        ]
        
        # Calculate match percentage
        total_unique_skills = len(set(all_required_skills))
        matched_count = len(matching_skills)
        match_percentage = round((matched_count / total_unique_skills * 100), 1) if total_unique_skills > 0 else 0
        
        # Categorize missing skills
        categorized_missing = self._categorize_skills(
            [skill for skill, _ in sorted_missing]
        )
        
        # Generate learning recommendations with target role context
        recommendations = await self._generate_recommendations(
            sorted_missing[:10],  # Top 10 missing skills
            target_role=target_role,
            target_ctc=target_ctc,
            use_ai=use_ai and self.ai_enabled
        )
        
        return {
            "summary": {
                "total_jobs_analyzed": len(job_applications),
                "total_skills_found": total_unique_skills,
                "skills_you_have": matched_count,
                "skills_you_need": len(missing_skills),
                "match_percentage": match_percentage,
                "target_role": target_role,
                "target_ctc": target_ctc
            },
            "your_skills": user_skills,
            "matching_skills": matching_skills,
            "missing_skills": sorted_missing[:20],  # Top 20 missing
            "categorized_missing": categorized_missing,
            "recommendations": recommendations,
            "trending_skills": self._get_trending_skills(skill_frequency),
            "skill_priority": self._calculate_skill_priority(sorted_missing[:10])
        }
    
    def _categorize_skills(self, skills: List[str]) -> Dict[str, List[str]]:
        """Categorize skills into technical domains"""
        
        categorized = {}
        skills_lower = [s.lower() for s in skills]
        
        for category, category_skills in self.skills_database.items():
            matched = []
            for skill in skills:
                if skill in category_skills:
                    matched.append(skill)
            
            if matched:
                # Convert category name to readable format
                readable_category = category.replace("_", " ").title()
                categorized[readable_category] = matched
        
        return categorized
    
    def _get_trending_skills(self, skill_frequency: Counter) -> List[Dict[str, Any]]:
        """Get top trending skills from job market"""
        
        # Get top 10 most frequent skills
        top_skills = skill_frequency.most_common(10)
        
        return [
            {
                "skill": skill,
                "demand": count,
                "trend": "High Demand" if count > 5 else "Growing"
            }
            for skill, count in top_skills
        ]
    
    def _calculate_skill_priority(
        self, 
        missing_skills: List[tuple]
    ) -> List[Dict[str, Any]]:
        """
        Calculate learning priority for missing skills
        High priority = appears in many jobs + easy to learn
        """
        
        priority_list = []
        
        for skill, data in missing_skills:
            count = data["count"]
            percentage = data["percentage"]
            
            # Simple priority calculation
            if percentage >= 50:
                priority = "Critical"
                priority_score = 3
            elif percentage >= 30:
                priority = "High"
                priority_score = 2
            else:
                priority = "Medium"
                priority_score = 1
            
            priority_list.append({
                "skill": skill,
                "appears_in": f"{count} jobs ({percentage}%)",
                "priority": priority,
                "priority_score": priority_score
            })
        
        # Sort by priority score
        return sorted(priority_list, key=lambda x: x["priority_score"], reverse=True)
    
    async def _generate_recommendations(
        self,
        missing_skills: List[tuple],
        target_role: str = "",
        target_ctc: str = "",
        use_ai: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Generate learning recommendations for missing skills
        Uses AI if available, otherwise provides template recommendations
        """
        
        if not missing_skills:
            return []
        
        if use_ai and self.ai_enabled:
            try:
                return await self._generate_ai_recommendations(
                    missing_skills,
                    target_role=target_role,
                    target_ctc=target_ctc
                )
            except Exception as e:
                logger.error(f"AI recommendation failed, using fallback: {e}")
        
        # Fallback: Template-based recommendations
        return self._generate_template_recommendations(missing_skills)
    
    async def _generate_skills_for_role(self, role: str) -> List[str]:
        """Use AI to generate expected skills for a specific role"""
        
        if not self.ai_enabled:
            return []
        
        try:
            prompt = f"""
You are a senior technical recruiter and skills-market analyst (2026). List the 15-20 most important technical skills required for a "{role}" position in the current job market.

Include skills across these categories (only where relevant to the role):
- Programming languages and scripting
- Frameworks, libraries, and SDKs
- Databases and data stores
- Cloud platforms and services (AWS, Azure, GCP)
- DevOps, CI/CD, and infrastructure tools
- Testing and QA tools (if relevant)
- Methodologies (Agile, Scrum, TDD, etc.)
- Domain-specific skills and certifications

Prioritize skills by market demand — list the most in-demand skills first.

Return ONLY a JSON array of skill names (strings), nothing else.
Example: ["Python", "SQL", "REST API", "Git", "Agile"]
"""
            
            response = await self.model.generate_content_async(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=500
                )
            )
            
            import json
            text = response.text.strip()
            
            # Extract JSON array from response
            if '```json' in text:
                text = text.split('```json')[1].split('```')[0].strip()
            elif '```' in text:
                text = text.split('```')[1].split('```')[0].strip()
            
            skills = json.loads(text)
            
            if isinstance(skills, list):
                return [str(skill).strip() for skill in skills if skill]
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to generate skills for role {role}: {e}")
            return []
    
    async def _generate_ai_recommendations(
        self,
        missing_skills: List[tuple],
        target_role: str = "",
        target_ctc: str = ""
    ) -> List[Dict[str, Any]]:
        """Generate personalized recommendations using AI"""
        
        skills_text = ", ".join([skill for skill, _ in missing_skills[:5]])
        
        role_context = f"\nTarget Role: {target_role}" if target_role else ""
        ctc_context = f"\nTarget CTC: {target_ctc}" if target_ctc else ""
        
        prompt = f"""
You are a senior career strategist and upskilling advisor (2026). Help a candidate close their skill gaps for job applications.
{role_context}{ctc_context}

They are missing these key skills: {skills_text}

For EACH skill, provide:
1. **Skill Name**
2. **Why Important**: 1-2 sentences on why this skill matters for their target role/salary in 2026
3. **Learning Path**: Specific, step-by-step progression (beginner → job-ready)
4. **Time Estimate**: Realistic time to reach job-ready level (assuming part-time learning)
5. **Best Resources**: 2-3 specific, currently available free resources (courses, tutorials, official docs) — verify these are real platforms
6. **Practice Project**: A concrete, portfolio-worthy project idea that demonstrates this skill

Format as JSON array:
[
  {{
    "skill": "Python",
    "why_important": "Most in-demand language...",
    "learning_path": "1. Learn basics... 2. Build projects...",
    "time_estimate": "2-3 months",
    "resources": ["freeCodeCamp Python Course", "Python.org Official Tutorial", "Real Python"],
    "practice_project": "Build a web scraper that..."
  }}
]

Provide recommendations for the top 5 skills only. Be practical and actionable — avoid generic advice.
"""
        
        response = await self.model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.7,
                max_output_tokens=2000
            )
        )
        
        # Parse JSON response
        import json
        text = response.text.strip()
        
        # Extract JSON from response (remove markdown if present)
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()
        
        try:
            recommendations = json.loads(text)
            return recommendations
        except json.JSONDecodeError:
            logger.error("Failed to parse AI response as JSON")
            return self._generate_template_recommendations(missing_skills)
    
    def _generate_template_recommendations(
        self,
        missing_skills: List[tuple]
    ) -> List[Dict[str, Any]]:
        """Generate basic recommendations without AI"""
        
        recommendations = []
        
        for skill, data in missing_skills[:5]:
            rec = {
                "skill": skill,
                "why_important": f"Appears in {data['count']} job postings ({data['percentage']}% of jobs)",
                "learning_path": self._get_learning_path(skill),
                "time_estimate": self._estimate_learning_time(skill),
                "resources": self._get_free_resources(skill),
                "practice_project": self._get_practice_project(skill)
            }
            recommendations.append(rec)
        
        return recommendations
    
    def _get_learning_path(self, skill: str) -> str:
        """Get learning path for a skill"""
        
        skill_lower = skill.lower()
        
        if any(lang in skill_lower for lang in ["python", "javascript", "java", "c++"]):
            return "1. Learn syntax basics 2. Practice with coding challenges 3. Build small projects 4. Contribute to open source"
        
        elif any(fw in skill_lower for fw in ["react", "angular", "vue", "django", "flask"]):
            return "1. Learn prerequisite language 2. Study framework docs 3. Build tutorial projects 4. Create portfolio project"
        
        elif any(db in skill_lower for db in ["sql", "mongodb", "postgresql"]):
            return "1. Understand database concepts 2. Practice queries 3. Design schemas 4. Build data-driven app"
        
        elif any(cloud in skill_lower for cloud in ["aws", "azure", "gcp", "docker", "kubernetes"]):
            return "1. Get free tier account 2. Complete official tutorials 3. Deploy sample applications 4. Study for certification"
        
        else:
            return "1. Watch introductory videos 2. Read official documentation 3. Complete hands-on tutorials 4. Build practice projects"
    
    def _estimate_learning_time(self, skill: str) -> str:
        """Estimate time to learn a skill"""
        
        skill_lower = skill.lower()
        
        # Programming languages
        if any(lang in skill_lower for lang in ["python", "javascript"]):
            return "2-3 months (basics), 6-12 months (proficiency)"
        
        elif any(lang in skill_lower for lang in ["java", "c++", "c#"]):
            return "3-4 months (basics), 8-12 months (proficiency)"
        
        # Frameworks
        elif any(fw in skill_lower for fw in ["react", "angular", "vue"]):
            return "1-2 months (if you know JavaScript)"
        
        # Cloud/DevOps
        elif any(cloud in skill_lower for cloud in ["aws", "docker", "kubernetes"]):
            return "2-3 months (basics), 4-6 months (certification-ready)"
        
        # Databases
        elif "sql" in skill_lower or "database" in skill_lower:
            return "1-2 months (basics), 3-4 months (advanced)"
        
        else:
            return "1-3 months (varies by complexity)"
    
    def _get_free_resources(self, skill: str) -> List[str]:
        """Get free learning resources for a skill"""
        
        skill_lower = skill.lower()
        
        resources_map = {
            "python": [
                "Python.org Official Tutorial",
                "freeCodeCamp Python Course (YouTube)",
                "Codecademy Python Track (free tier)"
            ],
            "javascript": [
                "MDN Web Docs JavaScript Guide",
                "freeCodeCamp JavaScript Algorithms",
                "JavaScript.info Tutorial"
            ],
            "react": [
                "React Official Docs (react.dev)",
                "freeCodeCamp React Course",
                "React Tutorial by Scrimba"
            ],
            "sql": [
                "SQLBolt Interactive Tutorial",
                "Khan Academy SQL Course",
                "W3Schools SQL Tutorial"
            ],
            "aws": [
                "AWS Free Tier (hands-on practice)",
                "AWS Skill Builder (free courses)",
                "freeCodeCamp AWS Course (YouTube)"
            ],
            "docker": [
                "Docker Official Docs",
                "Docker for Beginners (YouTube)",
                "Play with Docker (browser-based)"
            ]
        }
        
        # Find matching resources
        for key, resources in resources_map.items():
            if key in skill_lower:
                return resources
        
        # Default resources
        return [
            f"Search '{skill} tutorial' on YouTube",
            f"Official {skill} documentation",
            f"freeCodeCamp {skill} course"
        ]
    
    def _get_practice_project(self, skill: str) -> str:
        """Get practice project idea for a skill"""
        
        skill_lower = skill.lower()
        
        if "python" in skill_lower:
            return "Build a web scraper to collect job listings, then analyze salary trends"
        
        elif "javascript" in skill_lower or "react" in skill_lower:
            return "Create a todo app with CRUD operations and local storage"
        
        elif "sql" in skill_lower or "database" in skill_lower:
            return "Design a database for an e-commerce store with products, users, and orders"
        
        elif "aws" in skill_lower or "cloud" in skill_lower:
            return "Deploy a simple web app to AWS using EC2 and RDS"
        
        elif "docker" in skill_lower:
            return "Containerize your existing project and deploy with Docker Compose"
        
        elif "machine learning" in skill_lower:
            return "Build a house price predictor using scikit-learn"
        
        else:
            return f"Build a small project that uses {skill} as the main technology"
    
    def get_training_platforms(self, missing_skills: List[tuple]) -> Dict[str, List[Dict[str, str]]]:
        """
        Get recommended training platforms for missing skills
        Returns platform recommendations with links and skill coverage
        """
        
        if not missing_skills:
            return {}
        
        # Extract skill names
        skill_names = [skill for skill, _ in missing_skills]
        
        # Popular training platforms with their strengths
        platforms = {
            "YouTube (Free)": {
                "url": "https://youtube.com",
                "skills": skill_names,  # YouTube has tutorials for everything
                "pros": "Free, visual learning, multiple teachers, community support",
                "best_for": "Beginners, visual learners, quick concepts",
                "search_tip": f"Search: '{skill_names[0]} tutorial' or '{skill_names[0]} crash course'"
            },
            "Coursera (Free Audit)": {
                "url": "https://coursera.org",
                "skills": self._filter_skills_for_platform(skill_names, ["python", "java", "machine learning", "data science", "cloud", "aws"]),
                "pros": "University-level courses, certificates available, structured learning",
                "best_for": "In-depth learning, certifications, career switchers"
            },
            "Udemy (Paid, frequent sales)": {
                "url": "https://udemy.com",
                "skills": skill_names,
                "pros": "Comprehensive courses, lifetime access, project-based",
                "best_for": "Hands-on learners, complete beginners to advanced"
            },
            "freeCodeCamp (100% Free)": {
                "url": "https://freecodecamp.org",
                "skills": self._filter_skills_for_platform(skill_names, ["javascript", "python", "react", "node", "web", "frontend", "backend"]),
                "pros": "Completely free, hands-on, earn certificates, supportive community",
                "best_for": "Web development, programming fundamentals"
            },
            "Codecademy (Free + Pro)": {
                "url": "https://codecademy.com",
                "skills": self._filter_skills_for_platform(skill_names, ["python", "javascript", "java", "sql", "react", "git"]),
                "pros": "Interactive coding, immediate feedback, beginner-friendly",
                "best_for": "Absolute beginners, learn by doing"
            },
            "Udacity (Free courses available)": {
                "url": "https://udacity.com",
                "skills": self._filter_skills_for_platform(skill_names, ["python", "machine learning", "ai", "cloud", "devops"]),
                "pros": "Industry partnerships, project-based, career services",
                "best_for": "Career advancement, tech-focused learning"
            },
            "LinkedIn Learning (Free trial)": {
                "url": "https://linkedin.com/learning",
                "skills": skill_names,
                "pros": "Professional courses, add to LinkedIn profile, business focus",
                "best_for": "Professionals, soft skills + technical skills"
            },
            "Pluralsight (Free trial)": {
                "url": "https://pluralsight.com",
                "skills": self._filter_skills_for_platform(skill_names, ["cloud", "devops", "security", "data", "software development"]),
                "pros": "Tech-focused, skill assessments, learning paths",
                "best_for": "IT professionals, certification prep"
            },
            "The Odin Project (100% Free)": {
                "url": "https://theodinproject.com",
                "skills": self._filter_skills_for_platform(skill_names, ["javascript", "react", "node", "web", "frontend", "backend"]),
                "pros": "Completely free, full curriculum, project-based",
                "best_for": "Full-stack web development"
            },
            "Scrimba (Free + Pro)": {
                "url": "https://scrimba.com",
                "skills": self._filter_skills_for_platform(skill_names, ["javascript", "react", "vue", "frontend", "css"]),
                "pros": "Interactive screencasts, code along, modern UI/UX",
                "best_for": "Frontend development, modern JavaScript"
            },
            "Official Documentation": {
                "url": "Various",
                "skills": skill_names,
                "pros": "Most accurate, free, comprehensive, up-to-date",
                "best_for": "Reference, deep dives, best practices",
                "examples": [f"{skill} official docs" for skill in skill_names[:3]]
            }
        }
        
        # Filter platforms that have relevant skills
        relevant_platforms = {}
        for platform_name, platform_data in platforms.items():
            if platform_data.get("skills"):
                relevant_platforms[platform_name] = platform_data
        
        return relevant_platforms
    
    def _filter_skills_for_platform(self, skills: List[str], keywords: List[str]) -> List[str]:
        """Filter skills that match platform's strengths"""
        matching = []
        for skill in skills:
            skill_lower = skill.lower()
            if any(keyword in skill_lower for keyword in keywords):
                matching.append(skill)
        return matching if matching else skills[:3]  # Return first 3 if no match
    
    def get_salary_insights(
        self,
        target_role: str,
        target_ctc: str,
        user_skills: List[str],
        missing_skills: List[tuple]
    ) -> Dict[str, Any]:
        """
        Provide salary insights based on target CTC and skills gap
        Helps user understand earning potential with current vs. complete skillset
        """
        
        # Parse CTC (basic parsing, can be enhanced)
        ctc_value = self._parse_ctc(target_ctc)
        
        missing_skill_names = [skill for skill, _ in missing_skills]
        
        return {
            "target_ctc": target_ctc,
            "target_role": target_role,
            "current_skills_count": len(user_skills),
            "missing_skills_count": len(missing_skills),
            "insights": [
                {
                    "title": "Skill Completion Impact",
                    "message": f"Learning the top {min(len(missing_skills), 5)} missing skills can increase your chances of reaching {target_ctc} by 40-60%"
                },
                {
                    "title": "Market Readiness",
                    "message": f"For {target_role} at {target_ctc}, focus on: {', '.join(missing_skill_names[:3])}"
                },
                {
                    "title": "⏱️ Time to Target",
                    "message": f"Estimated learning time: {self._estimate_total_learning_time(missing_skills[:5])} to reach target readiness"
                },
                {
                    "title": "Strategy",
                    "message": f"Prioritize {'high-demand' if len(missing_skills) > 5 else 'essential'} skills first for fastest impact"
                }
            ],
            "skill_value": self._estimate_skill_value(missing_skills[:3]),
            "recommendation": self._get_ctc_recommendation(target_role, target_ctc, len(user_skills), len(missing_skills))
        }
    
    def _parse_ctc(self, ctc_str: str) -> Optional[float]:
        """Parse CTC string to numeric value"""
        import re
        
        if not ctc_str:
            return None
        
        # Remove currency symbols and common words
        clean = re.sub(r'[₹$£€,]', '', ctc_str.upper())
        
        # Extract number
        numbers = re.findall(r'\d+\.?\d*', clean)
        if not numbers:
            return None
        
        value = float(numbers[0])
        
        # Handle LPA (Lakhs Per Annum)
        if 'LPA' in clean or 'LAKHS' in clean:
            value = value * 100000  # Convert to actual value
        elif 'K' in clean:
            value = value * 1000
        elif 'M' in clean:
            value = value * 1000000
        
        return value
    
    def _estimate_total_learning_time(self, skills: List[tuple]) -> str:
        """Estimate total time needed to learn multiple skills"""
        if not skills:
            return "0 months"
        
        # Rough estimates in months
        total_months = 0
        for skill, _ in skills:
            if any(lang in skill.lower() for lang in ["python", "javascript"]):
                total_months += 2
            elif any(fw in skill.lower() for fw in ["react", "angular", "vue"]):
                total_months += 1.5
            elif any(cloud in skill.lower() for cloud in ["aws", "azure", "docker", "kubernetes"]):
                total_months += 2
            else:
                total_months += 1
        
        # Assume parallel learning reduces total time by 30%
        adjusted = total_months * 0.7
        
        if adjusted < 2:
            return "1-2 months"
        elif adjusted < 4:
            return "2-4 months"
        elif adjusted < 6:
            return "4-6 months"
        else:
            return "6-12 months"
    
    def _estimate_skill_value(self, skills: List[tuple]) -> List[Dict[str, str]]:
        """Estimate market value/demand for each skill"""
        value_estimates = []
        
        high_value_skills = ["aws", "kubernetes", "docker", "react", "python", "machine learning", "ai"]
        
        for skill, data in skills:
            skill_lower = skill.lower()
            
            if any(hv in skill_lower for hv in high_value_skills):
                value = "High Value"
                impact = "+15-25% salary potential"
            else:
                value = "Medium Value"
                impact = "+5-15% salary potential"
            
            value_estimates.append({
                "skill": skill,
                "value": value,
                "impact": impact,
                "demand": f"Appears in {data['count']} jobs"
            })
        
        return value_estimates
    
    def _get_ctc_recommendation(
        self,
        role: str,
        ctc: str,
        current_skills: int,
        missing_skills: int
    ) -> str:
        """Provide CTC-specific recommendation"""
        
        skill_ratio = current_skills / (current_skills + missing_skills) if (current_skills + missing_skills) > 0 else 0
        
        if skill_ratio >= 0.8:
            return f"You're well-positioned for {ctc}! Focus on interview preparation and portfolio building."
        elif skill_ratio >= 0.6:
            return f"Learn the top 3 missing skills to be competitive for {ctc} at {role} positions."
        elif skill_ratio >= 0.4:
            return f"Consider targeting slightly lower CTC initially, then upskill to reach {ctc} within 6-12 months."
        else:
            return f"Focus on building fundamental skills first. {ctc} at {role} is achievable with 6-12 months of dedicated learning."


# Global instance
skills_gap_analyzer = SkillsGapAnalyzer()
