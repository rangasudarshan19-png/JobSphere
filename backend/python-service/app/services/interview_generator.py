"""
AI-Powered Interview Question Generator
Generates relevant interview questions based on job description and position
Supports multi-account rotation for Gemini API to handle quota limits
"""
from typing import List, Dict
import re
import os
import json
import random
import time
import requests
import logging

logger = logging.getLogger(__name__)

# Optional provider clients (lazy initialization)
OPENAI_CLIENT = None
GROQ_CLIENT = None
HF_CLIENT = None
COHERE_CLIENT = None

# Multi-account Gemini API keys (rotates when quota exceeded)
GEMINI_API_KEYS = []
CURRENT_GEMINI_INDEX = 0

def _load_gemini_keys():
    """Load all Gemini API keys from environment"""
    global GEMINI_API_KEYS
    if not GEMINI_API_KEYS:
        # Primary key
        primary = os.getenv('GEMINI_API_KEY')
        if primary:
            GEMINI_API_KEYS.append(primary)
        
        # Additional keys (GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.)
        i = 2
        while True:
            key = os.getenv(f'GEMINI_API_KEY_{i}')
            if key:
                GEMINI_API_KEYS.append(key)
                i += 1
            else:
                break
        
        logger.info(f"[KEY] Loaded {len(GEMINI_API_KEYS)} Gemini API key(s)")
    return GEMINI_API_KEYS

def _get_next_gemini_key():
    """Get next Gemini API key in rotation"""
    global CURRENT_GEMINI_INDEX
    keys = _load_gemini_keys()
    if not keys:
        return None
    
    key = keys[CURRENT_GEMINI_INDEX]
    CURRENT_GEMINI_INDEX = (CURRENT_GEMINI_INDEX + 1) % len(keys)
    logger.info(f"Using Gemini key #{CURRENT_GEMINI_INDEX + 1}/{len(keys)}")
    return key

def _init_openai():
    global OPENAI_CLIENT
    if OPENAI_CLIENT is None:
        try:
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                OPENAI_CLIENT = OpenAI(api_key=api_key)
                logger.info("OpenAI client ready")
        except Exception as e:
            logger.error(f"OpenAI init failed: {e}")
    return OPENAI_CLIENT

def _init_groq():
    global GROQ_CLIENT
    if GROQ_CLIENT is None:
        try:
            from groq import Groq
            api_key = os.getenv('GROQ_API_KEY')
            if api_key:
                GROQ_CLIENT = Groq(api_key=api_key)
                logger.info("Groq client ready")
        except Exception as e:
            logger.error(f"Groq init failed: {e}")
    return GROQ_CLIENT

def _init_hf():
    global HF_CLIENT
    if HF_CLIENT is None:
        try:
            from huggingface_hub import InferenceClient
            api_key = os.getenv('HUGGINGFACE_API_KEY')
            if api_key:
                # Use a general instruct model (adjust as needed)
                HF_CLIENT = InferenceClient(token=api_key, model="meta-llama/Meta-Llama-3-8B-Instruct")
                logger.info("HuggingFace client ready")
        except Exception as e:
            logger.error(f"HuggingFace init failed: {e}")
    return HF_CLIENT

def _init_cohere():
    global COHERE_CLIENT
    if COHERE_CLIENT is None:
        try:
            import cohere
            api_key = os.getenv('COHERE_API_KEY')
            if api_key:
                COHERE_CLIENT = cohere.Client(api_key, timeout=15)  # 15 second timeout
                logger.info("Cohere client ready")
        except Exception as e:
            logger.error(f"Cohere init failed: {e}")
    return COHERE_CLIENT

def _call_xai_grok(prompt: str) -> str:
    """Call xAI Grok (assuming OpenAI-compatible style)."""
    api_key = os.getenv('XAI_API_KEY')
    if not api_key:
        return ""
    try:
        url = "https://api.x.ai/v1/chat/completions"  # Placeholder; adjust if different
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "grok-beta",  # adjust to available model name
            "messages": [
                {"role": "system", "content": "You are an interview question generator."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        resp = requests.post(url, headers=headers, json=body, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            # Attempt to extract content path similar to OpenAI
            return data.get('choices', [{}])[0].get('message', {}).get('content', '')
        else:
            logger.info(f"Grok API non-200 status: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.error(f"Grok call failed: {e}")
    return ""

# Try to import Gemini AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.info("google-generativeai not installed. Using template questions.")
class InterviewQuestionGenerator:
    """Generate interview questions using Gemini AI with multi-account rotation or pattern matching"""
    
    def __init__(self):
        # Try to initialize Gemini AI with rotation support
        self.use_ai = False
        self.ai_model = None
        self.gemini_keys = _load_gemini_keys()
        
        if GEMINI_AVAILABLE and self.gemini_keys:
            # Initialize Gemini model with first key
            try:
                genai.configure(api_key=self.gemini_keys[0])
                self.ai_model = genai.GenerativeModel('gemini-2.0-flash')
                self.use_ai = True
                logger.info(f"Gemini AI initialized with {len(self.gemini_keys)} account(s) for rotation!")
            except Exception as e:
                logger.error(f"Gemini initialization failed: {e}")
                self.ai_model = None
        else:
            logger.info("[INFO]️ No GEMINI_API_KEY found. Using fallback providers.")
        # Detect availability of other providers for fallback sequence
        # Prioritize OpenRouter as it has better models for interview generation
        self.providers_order = []
        if os.getenv('OPENROUTER_API_KEY'): self.providers_order.append('openrouter')
        if self.gemini_keys and self.ai_model: self.providers_order.append('gemini')
        if os.getenv('GROQ_API_KEY'): self.providers_order.append('groq')
        if os.getenv('OPENAI_API_KEY'): self.providers_order.append('openai')
        if os.getenv('COHERE_API_KEY'): self.providers_order.append('cohere')
        if os.getenv('XAI_API_KEY'): self.providers_order.append('xai')
        if os.getenv('HUGGINGFACE_API_KEY'): self.providers_order.append('huggingface')
        logger.info(f"AI provider fallback chain: {self.providers_order or ['templates only']}")
        # Common technical keywords and their associated questions
        self.tech_keywords = {
            'python': [
                "Explain the difference between list and tuple in Python.",
                "What are decorators and how do you use them?",
                "Describe Python's GIL (Global Interpreter Lock).",
                "How does memory management work in Python?",
                "Explain list comprehensions and when to use them."
            ],
            'javascript': [
                "Explain closures in JavaScript with an example.",
                "What is the difference between `let`, `const`, and `var`?",
                "Describe how promises work and the async/await pattern.",
                "What is the event loop in JavaScript?",
                "Explain prototypal inheritance."
            ],
            'react': [
                "What are React hooks and why were they introduced?",
                "Explain the virtual DOM and how React uses it.",
                "What is the difference between state and props?",
                "Describe React's component lifecycle.",
                "How do you optimize performance in React applications?"
            ],
            'node': [
                "Explain the event-driven architecture of Node.js.",
                "What is the difference between process.nextTick() and setImmediate()?",
                "How does Node.js handle child processes?",
                "Describe streaming in Node.js.",
                "What are the best practices for error handling in Node.js?"
            ],
            'java': [
                "Explain the difference between abstract class and interface.",
                "What is the Java Memory Model?",
                "Describe the Collections framework in Java.",
                "What are the principles of OOP and how does Java implement them?",
                "Explain multithreading and synchronization in Java."
            ],
            'sql': [
                "Explain the difference between INNER JOIN and OUTER JOIN.",
                "What are indexes and how do they improve query performance?",
                "Describe ACID properties in databases.",
                "What is normalization and why is it important?",
                "Explain the difference between WHERE and HAVING clauses."
            ],
            'docker': [
                "What is the difference between Docker image and container?",
                "Explain Docker networking and the different network types.",
                "How do you optimize Docker images for production?",
                "What is Docker Compose and when would you use it?",
                "Describe the Docker container lifecycle."
            ],
            'kubernetes': [
                "Explain the architecture of Kubernetes.",
                "What are Pods, Deployments, and Services?",
                "How does Kubernetes handle container orchestration?",
                "Describe the concept of ConfigMaps and Secrets.",
                "What is a StatefulSet and when would you use it?"
            ],
            'aws': [
                "Explain the difference between EC2, ECS, and Lambda.",
                "What is the shared responsibility model in AWS?",
                "Describe how S3 bucket permissions work.",
                "What are the different types of load balancers in AWS?",
                "Explain VPC, subnets, and security groups."
            ],
            'machine learning': [
                "Explain the bias-variance tradeoff.",
                "What is the difference between supervised and unsupervised learning?",
                "Describe overfitting and how to prevent it.",
                "Explain cross-validation and why it's important.",
                "What are the different types of neural networks?"
            ],
            'data structure': [
                "Explain the difference between array and linked list.",
                "What is a hash table and how does it work?",
                "Describe the time complexity of common operations on binary search trees.",
                "Explain different graph traversal algorithms.",
                "What is the difference between stack and queue?"
            ],
            'algorithm': [
                "Explain different sorting algorithms and their time complexities.",
                "What is dynamic programming and when would you use it?",
                "Describe the difference between BFS and DFS.",
                "Explain Big O notation with examples.",
                "What is memoization and how does it optimize recursive functions?"
            ],
            'api': [
                "What is the difference between REST and GraphQL?",
                "Explain different HTTP methods and when to use each.",
                "What is API versioning and why is it important?",
                "Describe authentication methods for APIs (JWT, OAuth, API keys).",
                "What are idempotent operations in REST APIs?"
            ],
            'frontend': [
                "Explain the CSS box model.",
                "What are the differences between responsive and adaptive design?",
                "Describe how to optimize website performance.",
                "What is progressive enhancement vs graceful degradation?",
                "Explain different ways to center a div in CSS."
            ],
            'backend': [
                "Explain microservices architecture and its benefits.",
                "What is the difference between monolithic and microservices?",
                "Describe caching strategies and when to use them.",
                "What is rate limiting and how do you implement it?",
                "Explain the CAP theorem."
            ]
        }
        
        # Role-based behavioral questions
        self.role_questions = {
            'senior': [
                "Describe a time when you mentored junior developers.",
                "How do you make architectural decisions for large-scale systems?",
                "Tell me about a technical debt problem you resolved.",
                "How do you balance technical excellence with business requirements?",
                "Describe your approach to code reviews and maintaining code quality."
            ],
            'junior': [
                "What motivates you to learn new technologies?",
                "Describe a challenging bug you fixed and how you approached it.",
                "How do you stay updated with new technologies and best practices?",
                "Tell me about a project you're proud of.",
                "How do you handle feedback on your code?"
            ],
            'lead': [
                "How do you handle conflicts within your team?",
                "Describe your experience with Agile/Scrum methodologies.",
                "How do you prioritize technical work vs feature development?",
                "Tell me about a time you had to make a difficult technical decision.",
                "How do you ensure your team delivers high-quality code on time?"
            ],
            'manager': [
                "How do you measure team productivity and success?",
                "Describe your approach to hiring and building teams.",
                "How do you handle underperforming team members?",
                "What's your strategy for aligning technical goals with business objectives?",
                "How do you foster a culture of innovation and learning?"
            ],
            'intern': [
                "What programming languages and technologies are you comfortable with?",
                "Describe a personal project you've worked on.",
                "What areas of software development interest you most?",
                "How do you approach learning new technologies?",
                "What are your career goals in software development?"
            ]
        }
        
        # General interview questions
        self.general_questions = [
            "Tell me about yourself and your background.",
            "Why are you interested in this position?",
            "What are your greatest strengths as a developer?",
            "Describe a challenging project you worked on recently.",
            "Where do you see yourself in 5 years?",
            "Why are you looking to leave your current position?",
            "What is your ideal work environment?",
            "How do you handle tight deadlines and pressure?",
            "What's your approach to learning new technologies?",
            "Do you have any questions for us?"
        ]
        
        # Company culture questions
        self.culture_questions = [
            "How do you collaborate with team members?",
            "Describe a time when you had to work with a difficult colleague.",
            "How do you handle disagreements about technical approaches?",
            "What role do you usually take in team projects?",
            "How do you ensure your work aligns with team goals?"
        ]
    
    def extract_keywords(self, text: str) -> List[str]:
        """Extract relevant technical keywords from job description"""
        if not text:
            return []
        
        text_lower = text.lower()
        found_keywords = []
        
        for keyword in self.tech_keywords.keys():
            if keyword in text_lower:
                found_keywords.append(keyword)
        
        return found_keywords
    
    def determine_seniority(self, job_title: str) -> str:
        """Determine seniority level from job title"""
        if not job_title:
            return 'junior'
        
        title_lower = job_title.lower()
        
        if any(word in title_lower for word in ['senior', 'sr', 'principal', 'staff']):
            return 'senior'
        elif any(word in title_lower for word in ['lead', 'tech lead', 'team lead']):
            return 'lead'
        elif any(word in title_lower for word in ['manager', 'director', 'vp', 'head of']):
            return 'manager'
        elif any(word in title_lower for word in ['intern', 'trainee']):
            return 'intern'
        else:
            return 'junior'
    
    def generate_questions(
        self,
        job_title: str,
        job_description: str = "",
        company_name: str = "",
        num_questions: int = 15
    ) -> Dict[str, List[str]]:
        """
        Generate personalized interview questions using AI or templates
        
        Returns:
            Dict with categories: technical, behavioral, general, company
        """
        # Unified AI fallback sequence
        prompt_job_title = job_title.strip() or "Unknown Role"
        provider_errors = {}

        for provider in self.providers_order:
            try:
                logger.info(f"\nAttempting provider: {provider} for {prompt_job_title}")
                if provider == 'openrouter':
                    content = self._call_openrouter(job_title, job_description, company_name)
                    if content:
                        parsed = self._parse_questions_json(content)
                        if parsed and len(parsed.get('technical', [])) >= 8:
                            logger.info(f"OpenRouter generated {sum(len(v) for v in parsed.values())} questions successfully!")
                            return parsed
                        else:
                            logger.info(f"OpenRouter response incomplete or invalid, trying next provider")
                elif provider == 'gemini' and self.ai_model:
                    return self._generate_with_gemini(job_title, job_description, company_name)
                elif provider == 'groq':
                    client = _init_groq()
                    if client:
                        content = self._call_groq(job_title, job_description, company_name)
                        parsed = self._parse_questions_json(content)
                        if parsed: return parsed
                elif provider == 'cohere':
                    client = _init_cohere()
                    if client:
                        content = self._call_cohere(job_title, job_description, company_name)
                        parsed = self._parse_questions_json(content)
                        if parsed: return parsed
                elif provider == 'openai':
                    client = _init_openai()
                    if client:
                        content = self._call_openai(job_title, job_description, company_name)
                        parsed = self._parse_questions_json(content)
                        if parsed: return parsed
                elif provider == 'xai':
                    content = _call_xai_grok(self._build_core_prompt(job_title, job_description, company_name))
                    parsed = self._parse_questions_json(content)
                    if parsed: return parsed
                elif provider == 'huggingface':
                    client = _init_hf()
                    if client:
                        content = self._call_huggingface(job_title, job_description, company_name)
                        parsed = self._parse_questions_json(content)
                        if parsed: return parsed
            except Exception as e:
                provider_errors[provider] = f"{type(e).__name__}: {e}"[:180]
                logger.error(f"Provider {provider} failed: {provider_errors[provider]}")
        if provider_errors:
            logger.error("\nAll AI providers failed; errors summary:")
            for p, msg in provider_errors.items():
                logger.info(f"   - {p}: {msg}")
        # Template-based generation (fallback)
        logger.info(f"Using template generation for: {job_title}")
        return self._generate_with_templates(job_title, job_description, company_name, num_questions)

    # ---- Provider-specific helpers ----
    def _build_core_prompt(self, job_title: str, job_description: str, company_name: str) -> str:
        return (
            f"You are a senior technical interviewer. Generate realistic interview questions for '{job_title}' "
            f"at '{company_name or 'a leading company'}'. "
            f"Job description: {job_description[:800] if job_description else 'Not provided — use industry standards for this role'}. "
            "Extract specific technologies, tools, and skills from the description and tailor every technical question to them. "
            "Match question difficulty to the seniority implied by the title (e.g., 'Senior' = system design & architecture, 'Junior' = fundamentals). "
            "Return ONLY valid JSON with keys: technical (10 items), behavioral (5 items), company (3 items), general (2 items). "
            "No explanations, no markdown, no code fences."
        )

    def _call_cohere(self, job_title: str, job_description: str, company_name: str) -> str:
        client = _init_cohere()
        if not client:
            return ""
        prompt = self._build_core_prompt(job_title, job_description, company_name)
        # Add randomness to avoid identical questions
        import random
        seed = random.randint(1000, 9999)
        prompt += f"\n\nGeneration ID: {seed}{int(time.time())}\nGenerate UNIQUE, VARIED questions. Avoid common patterns."
        try:
            response = client.chat(
                model='command-r-08-2024',  # Latest command-r model available
                message=prompt,
                temperature=0.9,  # Increased for more variety
                max_tokens=2000,
                timeout=15  # 15 second timeout
            )
            return response.text
        except Exception as e:
            logger.error(f"Cohere call failed: {e}")
            return ""

    def _call_openrouter(self, job_title: str, job_description: str, company_name: str) -> str:
        """Call OpenRouter API with better models for interview generation"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.info("No OpenRouter API key found")
            return ""
        
        # Build comprehensive prompt
        prompt = f"""You are a senior hiring manager conducting real interviews (2026). Generate interview questions as valid JSON for this position:

Job Title: {job_title}
Company: {company_name or 'Not specified'}
Job Description: {job_description[:1200] if job_description else 'Not provided - use industry standards for this role'}

INSTRUCTIONS:
1. Extract specific technologies, tools, certifications, and domain knowledge from the job description
2. Tailor every technical question to the ACTUAL requirements listed (not generic questions)
3. Match difficulty to seniority: Senior → architecture & system design; Mid → implementation & best practices; Junior → fundamentals & concepts
4. Behavioral questions should use situational prompts relevant to THIS role (not generic "tell me about a time")
5. Each question must be distinct — no rephrasing of the same concept

Return ONLY valid JSON (no markdown, no explanations, no code fences):
{{
  "technical": ["10 technical questions directly from job requirements"],
  "behavioral": ["5 situational questions specific to this role"],
  "company": ["3 questions about company/role fit"],
  "general": ["2 career growth questions"]
}}

Variety seed: {int(time.time())}"""
        
        # Try multiple models for best quality
        models_to_try = [
            "deepseek/deepseek-chat",  # Best for technical content
            "meta-llama/llama-3.1-70b-instruct",  # High quality, good reasoning
            "google/gemini-2.0-flash:free",  # Free Gemini via OpenRouter
            "meta-llama/llama-3.2-3b-instruct:free"  # Fallback free model
        ]
        
        for model in models_to_try:
            try:
                logger.info(f"Trying OpenRouter with model: {model}")
                url = "https://openrouter.ai/api/v1/chat/completions"
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://jobsphere.app",
                    "X-Title": "JobSphere Interview Prep"
                }
                body = {
                    "model": model,
                    "messages": [
                        {
                            "role": "system", 
                            "content": "You are an expert technical interviewer. Generate high-quality, role-specific interview questions. Return only valid JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.8,
                    "max_tokens": 2000
                }
                resp = requests.post(url, headers=headers, json=body, timeout=20)
                if resp.status_code == 200:
                    data = resp.json()
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    if content:
                        logger.info(f"OpenRouter ({model}) generated response ({len(content)} chars)")
                        return content
                else:
                    logger.info(f"OpenRouter {model} returned {resp.status_code}: {resp.text[:200]}")
                    # Try next model
                    continue
            except Exception as e:
                logger.error(f"OpenRouter {model} failed: {e}")
                # Try next model
                continue
        
        logger.error("All OpenRouter models failed")
        return ""

    def _call_openai(self, job_title: str, job_description: str, company_name: str) -> str:
        client = _init_openai()
        if not client:
            return ""
        prompt = self._build_core_prompt(job_title, job_description, company_name)
        try:
            resp = client.chat.completions.create(
                model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
                messages=[
                    {"role": "system", "content": "You are an interview question generator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                timeout=15
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI call failed: {e}")
            return ""

    def _call_groq(self, job_title: str, job_description: str, company_name: str) -> str:
        client = _init_groq()
        if not client:
            return ""
        prompt = self._build_core_prompt(job_title, job_description, company_name)
        try:
            resp = client.chat.completions.create(
                model=os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768'),
                messages=[
                    {"role": "system", "content": "You generate concise JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                timeout=15
            )
            return resp.choices[0].message.content
        except Exception as e:
            logger.error(f"Groq call failed: {e}")
            return ""

    def _call_huggingface(self, job_title: str, job_description: str, company_name: str) -> str:
        client = _init_hf()
        if not client:
            return ""
        prompt = self._build_core_prompt(job_title, job_description, company_name) + "\nReturn JSON now:"
        try:
            # Generate streamed text and accumulate
            text = ""
            for chunk in client.text_generation(prompt, max_new_tokens=800, temperature=0.7, stream=True):
                text += chunk
            return text
        except Exception as e:
            logger.error(f"HuggingFace call failed: {e}")
            return ""

    def _parse_questions_json(self, raw: str) -> Dict[str, List[str]]:
        if not raw:
            return {}
        raw = raw.strip()
        # Attempt to isolate JSON
        match = re.search(r"\{[\s\S]*\}$", raw)
        if match:
            raw = match.group(0)
        try:
            data = json.loads(raw)
            if all(k in data for k in ["technical", "behavioral", "company", "general"]):
                # Basic normalization: ensure lists
                for k in data:
                    if not isinstance(data[k], list):
                        return {}
                return data
        except Exception:
            pass
        return {}
    
    def _generate_with_gemini(self, job_title: str, job_description: str, company_name: str) -> Dict[str, List[str]]:
        """Generate questions using Gemini AI"""
        
        # Debug logging
        logger.info(f"\n{'='*60}")
        logger.info(f"GENERATING AI QUESTIONS")
        logger.info(f"{'='*60}")
        logger.info(f"Job Title: {job_title}")
        logger.info(f"Company: {company_name}")
        logger.info(f"Description Length: {len(job_description)} chars")
        logger.info(f"Description Preview: {job_description[:200] if job_description else 'None'}...")
        logger.info(f"{'='*60}\n")
        # Detect job type and create appropriate context
        job_title_lower = job_title.lower()
        job_desc_lower = (job_description or "").lower()
        
        # Check if this is a testing/QA role
        is_testing_role = any(word in job_title_lower for word in ['test', 'qa', 'quality assurance'])
        is_manual_testing = 'manual' in job_title_lower or 'functional' in job_desc_lower
        is_automation = 'automation' in job_title_lower or 'selenium' in job_desc_lower or 'cypress' in job_desc_lower
        
        # Build context-aware description
        if not job_description or len(job_description.strip()) < 50:
            # Very short or no description - provide context based on job title
            if is_testing_role:
                context_note = f"\nNOTE: This is a {'MANUAL' if is_manual_testing else 'AUTOMATION' if is_automation else 'SOFTWARE'} TESTING role. Focus on QA, testing methodologies, test case design, bug tracking, and testing tools/frameworks. DO NOT ask generic programming questions unless the description specifically mentions coding."
            else:
                context_note = f"\nNOTE: Description is minimal. Focus on common responsibilities for {job_title} roles."
        else:
            context_note = ""
        
        # Add timestamp to ensure variety in responses
        import time
        timestamp = int(time.time())
        
        # Create comprehensive, role-adaptive prompt
        prompt = f"""You are a senior hiring manager at a top-tier company conducting a real interview (2026). Generate UNIQUE, SPECIFIC questions tailored to the exact role.

POSITION DETAILS:
JOB TITLE: {job_title}
COMPANY: {company_name if company_name else 'Not specified'}
JOB DESCRIPTION:
{job_description[:2000] if job_description and len(job_description.strip()) > 0 else 'Not provided - generate industry-standard questions for this role'}

INSTRUCTIONS:
1. READ THE JOB DESCRIPTION CAREFULLY - extract specific technologies, responsibilities, and domain requirements
2. Every technical question MUST map to a skill, tool, or technology mentioned in the description
3. If the description is empty/minimal, generate standard questions for "{job_title}" roles
4. Match depth to seniority: Senior = architecture, system design, trade-offs; Mid = implementation, best practices; Junior = fundamentals, concepts
5. Generate DIFFERENT questions each time (variety seed: {timestamp % 1000})

ROLE-ADAPTIVE EXAMPLES:
- "Python Developer" + "Django, PostgreSQL" -> Django ORM queries, PostgreSQL indexing, REST API design
- "DevOps Engineer" + "Kubernetes, Terraform" -> container orchestration, IaC patterns, CI/CD pipelines
- "Data Scientist" + "PyTorch, SQL" -> model training, feature engineering, SQL window functions
- "Frontend Developer" + "React, TypeScript" -> component lifecycle, state management, type inference
- "QA Engineer" + "Selenium, API testing" -> test automation frameworks, API contract testing, defect triage
- "Project Manager" + "Agile, JIRA" -> sprint planning, stakeholder management, risk mitigation
{context_note}

QUESTION DESIGN RULES:
- DO NOT ask about technologies NOT mentioned in the description (unless the description is empty)
- DO NOT ask generic "tell me about yourself" questions as technical questions
- DO ask about specific tools/platforms listed (e.g., if "AWS Lambda" is mentioned, ask about serverless patterns)
- DO match question style to the role: testing roles get test design questions (not coding); development roles get implementation questions; leadership roles get architecture and decision-making questions
- DO make each question distinct - no rephrasing the same concept

GENERATE EXACTLY 20 QUESTIONS:

Technical (10): Questions directly testing skills from the job description. Include tool-specific, concept, and scenario-based questions.

Behavioral (5): Situational questions relevant to THIS role (not generic). Use "Describe a situation where..." or "How would you handle..." phrased for the specific domain.

Company (3): About {company_name if company_name else 'the company'} - role fit, motivation, and understanding of the business.

General (2): Career growth and professional development relevant to this field.

RETURN ONLY THIS JSON (no extra text, no markdown, no code fences):
{{
  "technical": ["q1", "q2", "q3", "q4", "q5", "q6", "q7", "q8", "q9", "q10"],
  "behavioral": ["q1", "q2", "q3", "q4", "q5"],
  "company": ["q1", "q2", "q3"],
  "general": ["q1", "q2"]
}}"""

        # Try each Gemini account in rotation
        for attempt in range(len(self.gemini_keys)):
            try:
                api_key = _get_next_gemini_key()
                logger.info(f"Attempting Gemini account {attempt + 1}/{len(self.gemini_keys)}...")
                # Initialize model with current key
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                # Generate content with timeout
                generation_config = genai.types.GenerationConfig(
                    temperature=0.9,
                    max_output_tokens=2000
                )
                response = model.generate_content(
                    prompt,
                    generation_config=generation_config,
                    request_options={"timeout": 15}  # 15 second timeout
                )
                logger.info(f"Gemini API responded successfully!")
                # Clean the response text
                text = response.text.strip()
                logger.info(f"Response length: {len(text)} chars")
                # Remove markdown code blocks if present
                if text.startswith('```'):
                    # Extract JSON from code block
                    lines = text.split('\n')
                    json_lines = []
                    in_json = False
                    for line in lines:
                        if line.startswith('```'):
                            in_json = not in_json
                            continue
                        if in_json or (not line.startswith('```') and '{' in text):
                            json_lines.append(line)
                    text = '\n'.join(json_lines)
                
                # Parse JSON
                questions_dict = json.loads(text)
                
                # Validate structure
                if not all(key in questions_dict for key in ['technical', 'behavioral', 'company', 'general']):
                    raise ValueError("Invalid JSON structure from AI")
                
                # Debug: Show sample questions
                logger.info(f"\nGenerated {sum(len(q) for q in questions_dict.values())} AI-powered questions!")
                logger.info(f"Sample Technical Questions:")
                for i, q in enumerate(questions_dict.get('technical', [])[:3], 1):
                    logger.info(f"   {i}. {q[:80]}...")
                logger.info(f"{'='*60}\n")
                return questions_dict
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON parse error with account {attempt + 1}: {e}")
                if attempt < len(self.gemini_keys) - 1:
                    logger.info("⏭️ Trying next Gemini account...")
                    continue
                else:
                    logger.error("All Gemini accounts failed JSON parsing")
                    raise
                    
            except Exception as e:
                error_msg = str(e).lower()
                # Check if it's a quota/rate limit error
                if '429' in error_msg or 'quota' in error_msg or 'rate limit' in error_msg or 'resourceexhausted' in error_msg:
                    logger.info(f"Gemini account {attempt + 1} quota exceeded: {str(e)[:100]}")
                    if attempt < len(self.gemini_keys) - 1:
                        logger.info("Rotating to next Gemini account...")
                        continue
                    else:
                        logger.info("All Gemini accounts exhausted")
                        raise
                else:
                    # Other error - don't retry
                    logger.error(f"Gemini error: {type(e).__name__}: {str(e)[:200]}")
                    raise
        
        # If we get here, all accounts failed
        raise Exception("All Gemini API accounts failed")
    
    def _generate_with_templates(
        self,
        job_title: str,
        job_description: str,
        company_name: str,
        num_questions: int
    ) -> Dict[str, List[str]]:
        """Generate questions using template matching with role awareness"""
        questions = {
            'technical': [],
            'behavioral': [],
            'general': [],
            'company': []
        }
        
        # Detect job type
        job_title_lower = job_title.lower()
        job_desc_lower = (job_description or "").lower()
        
        is_testing = any(word in job_title_lower for word in ['test', 'qa', 'quality'])
        is_manual_testing = 'manual' in job_title_lower or 'functional' in job_desc_lower
        has_guidewire = 'guidewire' in job_desc_lower
        has_api_testing = 'api' in job_desc_lower and 'test' in job_desc_lower
        
        # Testing-specific questions
        testing_questions = [
            "How do you design test cases for functional testing?",
            "Explain the difference between functional and non-functional testing.",
            "What is your approach to exploratory testing?",
            "Describe the bug lifecycle from discovery to closure.",
            "How do you prioritize which tests to run when time is limited?",
            "What is the difference between smoke testing and regression testing?",
            "How do you document test cases and test results?",
            "Explain boundary value analysis and equivalence partitioning.",
            "How do you test an application when requirements are not clear?",
            "What tools do you use for defect tracking and test management?"
        ]
        
        guidewire_questions = [
            "What are the main modules in Guidewire PolicyCenter?",
            "How do you test policy workflows in Guidewire?",
            "Explain the difference between PolicyCenter, BillingCenter, and ClaimCenter.",
            "How do you perform end-to-end testing in Guidewire applications?",
            "What challenges have you faced testing Guidewire applications?"
        ]
        
        api_testing_questions = [
            "How do you test REST APIs?",
            "What tools do you use for API testing (Postman, SoapUI)?",
            "Explain the difference between GET, POST, PUT, and DELETE methods.",
            "How do you validate API responses and status codes?",
            "What is the difference between API testing and UI testing?"
        ]
        
        # Choose appropriate questions based on role
        if is_testing:
            logger.info(f"Detected TESTING role - using testing-specific questions")
            questions['technical'].extend(random.sample(testing_questions, min(6, len(testing_questions))))
            
            if has_guidewire:
                logger.info(f"Guidewire mentioned - adding Guidewire questions")
                questions['technical'].extend(random.sample(guidewire_questions, min(3, len(guidewire_questions))))
            
            if has_api_testing:
                logger.info(f"API testing mentioned - adding API questions")
                questions['technical'].extend(random.sample(api_testing_questions, min(2, len(api_testing_questions))))
        else:
            # For development roles, use keyword extraction
            keywords = self.extract_keywords(job_description + " " + job_title)
            for keyword in keywords[:5]:
                if keyword in self.tech_keywords:
                    available_questions = self.tech_keywords[keyword]
                    num_to_select = min(random.randint(2, 3), len(available_questions))
                    selected = random.sample(available_questions, num_to_select)
                    questions['technical'].extend(selected)
            
            if not questions['technical']:
                all_tech_questions = []
                for tech_list in self.tech_keywords.values():
                    all_tech_questions.extend(tech_list)
                questions['technical'] = random.sample(all_tech_questions, min(8, len(all_tech_questions)))
        
        # Determine seniority level for behavioral questions
        seniority = self.determine_seniority(job_title)
        
        # Add role-specific behavioral questions (RANDOMIZED)
        if seniority in self.role_questions:
            available_behavioral = self.role_questions[seniority]
            questions['behavioral'].extend(random.sample(available_behavioral, min(5, len(available_behavioral))))
        else:
            # Mix questions from different seniority levels
            all_behavioral = []
            for role_list in self.role_questions.values():
                all_behavioral.extend(role_list)
            questions['behavioral'] = random.sample(all_behavioral, min(5, len(all_behavioral)))
        
        # Add general questions (RANDOMIZED)
        questions['general'].extend(random.sample(self.general_questions, min(5, len(self.general_questions))))
        
        # Add company culture questions (RANDOMIZED)
        questions['company'].extend(random.sample(self.culture_questions, min(3, len(self.culture_questions))))
        
        # Add company-specific questions if company name provided
        if company_name:
            questions['company'].append(f"What do you know about {company_name}?")
            questions['company'].append(f"Why do you want to work at {company_name}?")
            questions['company'].append(f"How do you think you can contribute to {company_name}'s success?")
        
        logger.info(f"Generated {sum(len(q) for q in questions.values())} randomized template questions")
        return questions
    
    def generate_tips(self, job_title: str) -> List[str]:
        """Generate interview preparation tips"""
        tips = [
            "Research the company's products, culture, and recent news.",
            "Prepare specific examples from your experience using the STAR method.",
            "Practice coding problems on platforms like LeetCode or HackerRank.",
            "Prepare questions to ask the interviewer about the role and team.",
            "Review your resume and be ready to discuss each project in detail.",
            "Test your internet connection and equipment if it's a remote interview.",
            "Dress appropriately and arrive/login 5-10 minutes early.",
            "Have a notepad ready to take notes during the interview."
        ]
        
        seniority = self.determine_seniority(job_title)
        
        if seniority in ['senior', 'lead', 'manager']:
            tips.extend([
                "Prepare to discuss system design and architectural decisions.",
                "Be ready to talk about leadership experiences and team management.",
                "Think about how you've mentored others or improved processes."
            ])
        
        return tips

    def analyze_resume(self, resume_content: str) -> str:
        """
        Analyze a resume using AI and provide comprehensive feedback
        
        Args:
            resume_content: The full resume text to analyze
            
        Returns:
            Detailed analysis with scores, strengths, weaknesses, and suggestions
        """
        if self.use_ai and self.ai_model:
            try:
                # Truncate to avoid token overflow
                truncated_resume = resume_content[:8000] if len(resume_content) > 8000 else resume_content
                prompt = f"""You are a certified professional resume writer (CPRW) and ATS optimization expert with 15+ years of experience reviewing resumes across all industries (2026).

RESUME:
{truncated_resume}

Provide a comprehensive, structured analysis covering:

1. **Overall Score (0-100)**: Rate the resume and justify with specific observations

2. **Strengths** (3-5 items): What the candidate does well - cite specific sections or phrases

3. **Weaknesses** (3-5 items): What needs improvement - be specific, not generic

4. **Content Analysis**:
   - Professional summary: Is it compelling and tailored, or generic?
   - Work experience: Are achievements quantified (metrics, percentages, dollar amounts)?
   - Skills: Are they relevant, organized, and ATS-optimized?
   - Education: Complete and properly formatted?

5. **ATS Optimization** (critical for modern job search):
   - Keyword density for likely target roles
   - Formatting issues that break ATS parsers (tables, images, headers/footers)
   - Missing standard section headers
   - Score estimate: Would this pass a typical ATS? (Yes/Likely/Unlikely)

6. **Actionable Improvements** (5-7 specific suggestions):
   - For each suggestion, provide a BEFORE/AFTER example using actual content from the resume
   - Prioritize by impact (highest impact first)

7. **Red Flags**: Any gaps, inconsistencies, or concerning elements

8. **Next Steps**: Top 3 actions the candidate should take immediately

Be constructive, specific, and reference actual content from the resume. Avoid generic advice.
Format your response in clear markdown with headers and bullet points."""

                response = self.ai_model.generate_content(prompt)
                return response.text
                
            except Exception as e:
                logger.error(f"Gemini resume analysis error: {e}")
                logger.info("Trying OpenRouter for resume analysis...")
        
        # Try OpenRouter as fallback
        try:
            truncated_resume = resume_content[:5000] if len(resume_content) > 5000 else resume_content
            analysis = self._analyze_resume_with_openrouter(truncated_resume)
            if analysis and len(analysis) > 100:
                return analysis
        except Exception as e:
            logger.error(f"OpenRouter resume analysis failed: {e}")
        
        # Last resort - template analysis
        return self._generate_template_analysis(resume_content)
    
    def _analyze_resume_with_openrouter(self, resume_content: str) -> str:
        """Analyze resume using OpenRouter API as fallback"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise Exception("No OpenRouter API key")
        
        prompt = f"""You are a certified professional resume writer (CPRW) and ATS optimization expert.

RESUME:
{resume_content}

Provide a comprehensive analysis covering:
1. **Overall Score (0-100)**: Rate and justify
2. **Strengths** (3-5 items): What's done well
3. **Weaknesses** (3-5 items): What needs improvement
4. **Content Analysis**: Summary, experience, skills, education quality
5. **ATS Optimization**: Keyword density, formatting issues, pass estimate
6. **Actionable Improvements** (5-7 specific BEFORE/AFTER suggestions)
7. **Red Flags**: Gaps or inconsistencies
8. **Next Steps**: Top 3 immediate actions

Be constructive and specific. Format in clear markdown."""

        import requests
        models_to_try = ["deepseek/deepseek-chat", "meta-llama/llama-3.1-70b-instruct"]
        
        for model in models_to_try:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://jobsphere.app",
                        "X-Title": "JobSphere Resume Analysis"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an expert resume reviewer and ATS optimization specialist."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.6,
                        "max_tokens": 3000,
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    analysis = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if analysis and len(analysis) > 100:
                        logger.info(f"OpenRouter ({model}) resume analysis: {len(analysis)} chars")
                        return analysis
            except Exception as e:
                logger.error(f"OpenRouter ({model}) resume analysis failed: {str(e)[:100]}")
                continue
        
        raise Exception("All OpenRouter models failed for resume analysis")

    def _generate_template_analysis(self, resume_content: str) -> str:
        """Generate template-based resume analysis when AI is not available"""
        
        # Basic analysis
        word_count = len(resume_content.split())
        has_email = '@' in resume_content
        has_phone = any(char.isdigit() for char in resume_content[:200])
        
        # Check for sections
        sections = {
            'summary': any(keyword in resume_content.lower() for keyword in ['summary', 'objective', 'profile']),
            'experience': any(keyword in resume_content.lower() for keyword in ['experience', 'work history', 'employment']),
            'education': 'education' in resume_content.lower(),
            'skills': 'skills' in resume_content.lower()
        }
        
        # Count achievements (lines with numbers or percentages)
        achievement_count = len(re.findall(r'\d+%|\$\d+|\d+\s*(years?|months?)', resume_content, re.IGNORECASE))
        
        # Calculate basic score
        score = 50
        if has_email: score += 5
        if has_phone: score += 5
        if sum(sections.values()) >= 4: score += 15
        if word_count >= 300: score += 10
        if achievement_count >= 3: score += 15
        
        score = min(score, 100)
        
        analysis = f"""**Resume Analysis Results**

**Overall Score: {score}/100**

{'Good' if score >= 75 else 'Needs Improvement' if score >= 60 else 'Significant Improvement Needed'}

---

**Structure Analysis**

Contact Information: {'Present' if (has_email and has_phone) else 'Missing or Incomplete'}
Professional Summary: {'Present' if sections['summary'] else 'Missing'}
Work Experience: {'Present' if sections['experience'] else 'Missing'}
Education: {'Present' if sections['education'] else 'Missing'}
Skills Section: {'Present' if sections['skills'] else 'Missing'}

---

**Strengths Identified:**

{f'• Strong quantifiable achievements ({achievement_count} found)' if achievement_count >= 3 else ''}
{f'• Comprehensive resume with all major sections' if sum(sections.values()) >= 4 else ''}
{f'• Appropriate length ({word_count} words)' if 300 <= word_count <= 800 else ''}

---

**Areas for Improvement:**

{f'• Add contact information (email and phone)' if not (has_email and has_phone) else ''}
{f'• Include a professional summary at the top' if not sections['summary'] else ''}
{f'• Add quantifiable achievements (use numbers, percentages, metrics)' if achievement_count < 3 else ''}
{f'• Resume is too {"short" if word_count < 300 else "long"} - aim for 300-800 words' if not (300 <= word_count <= 800) else ''}

---

**Specific Recommendations:**

1. **Quantify Your Achievements**: 
   - Instead of: "Improved system performance"
   - Write: "Improved system performance by 40%, reducing load time from 5s to 3s"

2. **Use Action Verbs**: 
   - Start bullet points with: Led, Developed, Implemented, Designed, Optimized, etc.

3. **Tailor to Job Description**: 
   - Include keywords from target job postings
   - Highlight relevant skills and experiences

4. **ATS Optimization**: 
   - Use standard section headings (Experience, Education, Skills)
   - Avoid tables, images, or complex formatting
   - Include relevant industry keywords

5. **Professional Summary**: 
   - 3-4 sentences highlighting your expertise
   - Include years of experience and key skills
   - Mention career goals or value proposition

6. **Education Details**: 
   - Include degree, major, institution, and graduation year
   - Add GPA if above 3.5 and recent graduate
   - List relevant coursework or honors

7. **Skills Organization**: 
   - Group by category (Programming, Tools, Soft Skills)
   - List most relevant skills first
   - Be specific (not just "Python" but "Python (Django, Flask, Pandas)")

---

**ATS (Applicant Tracking System) Tips:**

• Use standard fonts (Arial, Calibri, Times New Roman)
• Avoid headers/footers, tables, and text boxes
• Save as .docx or PDF
• Include relevant keywords naturally in context
• Use full acronyms first (e.g., "Application Programming Interface (API)")

---

**Next Steps:**

1. Review each section and ensure it's complete and well-formatted
2. Add 3-5 quantifiable achievements to each role
3. Tailor your resume for specific job applications
4. Have someone proofread for typos and grammar
5. Test with ATS resume scanners online

---

**Pro Tip:** Keep multiple versions of your resume tailored to different types of roles or industries. This increases your chances of passing ATS screening and catching the recruiter's attention.

{'Note: AI analysis is not available. This is a template-based analysis. For more detailed feedback, please ensure Gemini AI is properly configured.' if not self.use_ai else ''}"""

        return analysis
    
    def generate_answer(self, question: str) -> str:
        """
        Generate comprehensive answer to an interview question using AI with multi-provider fallback
        
        Args:
            question: The interview question to answer
            
        Returns:
            Detailed answer with explanation, key points, and examples
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"ANSWER GENERATION WITH MULTI-PROVIDER FALLBACK")
        logger.info(f"{'='*70}")
        logger.info(f"Question: {question}")
        logger.info(f"Available providers: {self.providers_order}")
        logger.info(f"{'='*70}\n")
        provider_errors = {}
        
        # Try each provider in order
        for provider in self.providers_order:
            try:
                logger.info(f"\nAttempting {provider} for answer generation...")
                if provider == 'openrouter':
                    answer = self._generate_answer_with_openrouter(question)
                    if answer and len(answer) > 50:
                        logger.info(f"{provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer

                elif provider == 'gemini' and self.ai_model:
                    answer = self._generate_answer_with_gemini(question)
                    if answer and len(answer) > 50:
                        logger.info(f"{provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'cohere':
                    answer = self._generate_answer_with_cohere(question)
                    if answer and len(answer) > 50:
                        logger.info(f"{provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'openai':
                    answer = self._generate_answer_with_openai(question)
                    if answer and len(answer) > 50:
                        logger.info(f"{provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'groq':
                    answer = self._generate_answer_with_groq(question)
                    if answer and len(answer) > 50:
                        logger.info(f"{provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'xai':
                    answer = self._generate_answer_with_xai(question)
                    if answer and len(answer) > 50:
                        logger.info(f"{provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'huggingface':
                    answer = self._generate_answer_with_huggingface(question)
                    if answer and len(answer) > 50:
                        logger.info(f"{provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"[:200]
                provider_errors[provider] = error_msg
                logger.error(f"{provider} failed: {error_msg}")
        # All providers failed - use template-based answer
        logger.error("\nAll AI providers failed for answer generation")
        for p, err in provider_errors.items():
            logger.info(f"   - {p}: {err}")
        logger.info("Falling back to last-resort answer generation")
        return self._generate_template_answer(question)
    
    def _generate_answer_with_openrouter(self, question: str) -> str:
        """Generate answer using OpenRouter API"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise Exception("No OpenRouter API key")
        
        prompt = f"""You are a senior professional with 8+ years of industry experience. Answer this interview question as if YOU are the candidate in a real interview.

Question: {question}

RULES:
1. Answer in FIRST PERSON ("I", "In my experience", "At my previous company")
2. Minimum 200 words with substantive, specific content
3. For behavioral questions: Use STAR format (Situation, Task, Action, Result) with a realistic scenario
4. For technical questions: Explain the concept clearly, then provide a concrete example or code snippet
5. Include 2-3 quantified achievements (e.g., "reduced latency by 40%", "managed a team of 6")
6. Format with markdown: **bold** for key terms, bullet points for lists
7. End with a concise takeaway

CRITICAL: Give the ACTUAL ANSWER as the candidate - do NOT give tips or advice on how to answer.

Answer:"""

        import requests
        models_to_try = [
            "deepseek/deepseek-chat",
            "meta-llama/llama-3.1-70b-instruct",
        ]
        
        for model in models_to_try:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://jobsphere.app",
                        "X-Title": "JobSphere Interview Prep"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an experienced professional answering interview questions as the candidate."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.8,
                        "max_tokens": 2048,
                    },
                    timeout=20
                )
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if answer and len(answer) > 50:
                        logger.info(f"OpenRouter ({model}) answer: {len(answer)} chars")
                        return answer
            except Exception as e:
                logger.error(f"OpenRouter ({model}) answer failed: {str(e)[:100]}")
                continue
        
        raise Exception("All OpenRouter models failed for answer generation")

    def _generate_answer_with_gemini(self, question: str) -> str:
        """Generate answer using Gemini AI with account rotation"""
        
        # Enhanced prompt that demands specific, complete answers
        prompt = f"""You are a senior professional with 8+ years of experience interviewing at top companies. Answer this interview question as if YOU are the candidate in a real interview.

Question: {question}

ANSWER RULES:
1. Speak in FIRST PERSON ("I", "In my experience", "At my previous company")
2. Minimum 200 words - give a thorough, complete answer
3. For behavioral questions: Use the STAR format (Situation, Task, Action, Result) with a realistic scenario
4. For technical questions: Explain the concept clearly, then provide a concrete example or code snippet
5. Include 2-3 specific, quantified achievements or scenarios (e.g., "reduced latency by 40%", "managed a team of 6")
6. Format with markdown: **bold** for key terms, bullet points for lists, code blocks for code
7. End with a concise takeaway or lesson learned

CRITICAL: Give the ACTUAL ANSWER as the candidate - do NOT give tips or coaching on how to answer.

Answer:"""

        # Try each Gemini account
        for attempt in range(len(self.gemini_keys)):
            try:
                api_key = _get_next_gemini_key()
                logger.info(f"Gemini account {attempt + 1}/{len(self.gemini_keys)} for answer...")
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                response = model.generate_content(
                    prompt,
                    generation_config={
                        'temperature': 0.8,
                        'top_p': 0.9,
                        'top_k': 40,
                        'max_output_tokens': 2048,
                        'stop_sequences': None
                    }
                )
                answer = response.text.strip()
                logger.info(f"Answer generated: {len(answer)} chars")
                if len(answer) < 50:
                    raise Exception("Answer too short")
                
                return answer
                
            except Exception as e:
                error_msg = str(e).lower()
                if '429' in error_msg or 'quota' in error_msg or 'rate limit' in error_msg or 'resourceexhausted' in error_msg:
                    logger.info(f"Gemini account {attempt + 1} quota exceeded")
                    if attempt < len(self.gemini_keys) - 1:
                        logger.info("Trying next account...")
                        continue
                    else:
                        logger.info("All Gemini accounts exhausted for answers")
                        raise
                else:
                    logger.error(f"Gemini error: {str(e)[:100]}")
                    raise
        
        raise Exception("All Gemini accounts failed for answer")
    
    def _generate_answer_with_cohere(self, question: str) -> str:
        """Generate answer using Cohere"""
        client = _init_cohere()
        if not client:
            raise Exception("Cohere client not initialized")
        
        # Add variety to answers
        import random
        perspectives = [
            "Answer with 2-3 specific real-world examples and quantifiable results.",
            "Structure your answer using the STAR method with detailed scenarios.",
            "Provide a comprehensive answer with pros/cons and lessons learned.",
            "Answer with specific technical details and implementation examples."
        ]
        style = random.choice(perspectives)
        seed = random.randint(1000, 9999)
        
        prompt = f"""You are an experienced professional answering in a real job interview. Respond to this question with a complete, authentic answer.

Question: {question}

Style: {style}

RULES:
- Answer in first person as the candidate ("I", "In my role at...", "When I led...")
- Minimum 200 words with substantive content
- Include 2-3 specific scenarios with quantified outcomes (percentages, team sizes, timelines)
- For behavioral questions: Use STAR format (Situation → Task → Action → Result)
- For technical questions: Explain the concept, then give a practical implementation example
- Be authentic and specific — avoid generic platitudes
- DO NOT give coaching or advice — give the actual answer

Generation ID: {seed}{int(time.time())}

Answer:"""
        
        response = client.chat(
            model='command-r-08-2024',  # Latest command-r model available
            message=prompt,
            temperature=0.95,  # High variety
            max_tokens=1500
        )
        return response.text.strip()

    def _generate_answer_with_openai(self, question: str) -> str:
        """Generate answer using OpenAI"""
        client = _init_openai()
        if not client:
            raise Exception("OpenAI client not initialized")
        
        prompt = f"""Answer this interview question as the candidate. Give a complete, specific answer (200+ words) with examples.

Question: {question}

Answer in first person with specific scenarios."""
        
        resp = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": "You are an experienced professional answering interview questions."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1500
        )
        return resp.choices[0].message.content.strip()
    
    def _generate_answer_with_groq(self, question: str) -> str:
        """Generate answer using Groq"""
        client = _init_groq()
        if not client:
            raise Exception("Groq client not initialized")
        
        prompt = f"""Answer this interview question as the candidate. Give a complete answer with examples.

Question: {question}"""
        
        resp = client.chat.completions.create(
            model=os.getenv('GROQ_MODEL', 'mixtral-8x7b-32768'),
            messages=[
                {"role": "system", "content": "You answer interview questions professionally."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.8,
            max_tokens=1500
        )
        return resp.choices[0].message.content.strip()
    
    def _generate_answer_with_xai(self, question: str) -> str:
        """Generate answer using xAI Grok"""
        prompt = f"""Answer this interview question as the candidate with specific examples.

Question: {question}"""
        
        return _call_xai_grok(prompt)
    
    def _generate_answer_with_huggingface(self, question: str) -> str:
        """Generate answer using HuggingFace"""
        client = _init_hf()
        if not client:
            raise Exception("HuggingFace client not initialized")
        
        prompt = f"""Answer this interview question professionally:

Question: {question}

Answer:"""
        
        response = client.text_generation(
            prompt,
            model=os.getenv('HF_MODEL', 'meta-llama/Meta-Llama-3-8B-Instruct'),
            max_new_tokens=1000,
            temperature=0.8
        )
        return response.strip()
    
    def _generate_template_answer(self, question: str) -> str:
        """Generate a dynamic answer when all AI providers fail - uses Gemini with a simplified prompt as last resort"""
        
        # Last-resort attempt with simplified prompt and fresh Gemini key
        for attempt in range(len(self.gemini_keys)):
            try:
                api_key = _get_next_gemini_key()
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                simple_prompt = f"""Answer this interview question directly as the candidate in first person. Be specific and give real examples.

Question: {question}

Answer (200+ words):"""
                
                response = model.generate_content(
                    simple_prompt,
                    generation_config={
                        'temperature': 0.9,
                        'max_output_tokens': 1500,
                    },
                    request_options={"timeout": 20}
                )
                answer = response.text.strip()
                if len(answer) > 50:
                    logger.info(f"Last-resort Gemini answer generated: {len(answer)} chars")
                    return answer
            except Exception as e:
                logger.error(f"Last-resort Gemini attempt {attempt + 1} failed: {str(e)[:100]}")
                continue
        
        # Absolute last resort - return a message asking user to retry
        return f"""**AI Answer Generation Temporarily Unavailable**

We were unable to generate an AI-powered answer for this question at the moment. All AI providers are currently experiencing high demand or rate limits.

**Your Question:** {question}

**Please try again in a few moments.** The AI service typically recovers within 30-60 seconds.

**In the meantime, here's a quick framework to structure your own answer:**
- Open with a direct response to the question
- Support with 1-2 specific examples from your experience
- Use the STAR method (Situation, Task, Action, Result) for behavioral questions
- End with a key takeaway or lesson learned"""
    
    def generate_cover_letter(
        self,
        company_name: str,
        job_title: str,
        job_description: str = "",
        user_experience: str = "",
        tone: str = "professional"
    ) -> str:
        """
        Generate AI-powered personalized cover letter
        
        Args:
            company_name: Target company name
            job_title: Position applying for
            job_description: Job posting details (optional)
            user_experience: User's skills and experience (optional)
            tone: Writing tone (professional, enthusiastic, confident)
            
        Returns:
            Complete formatted cover letter
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"COVER LETTER GENERATION CALLED")
        logger.info(f"{'='*70}")
        logger.info(f"Company: {company_name}")
        logger.info(f"Position: {job_title}")
        logger.info(f"Tone: {tone}")
        logger.info(f"use_ai: {self.use_ai}")
        logger.info(f"ai_model exists: {self.ai_model is not None}")
        logger.info(f"{'='*70}\n")
        # Try Gemini first
        if self.ai_model is not None:
            try:
                logger.info(f"Calling Gemini AI for cover letter...")
                letter = self._generate_cover_letter_with_gemini(
                    company_name,
                    job_title,
                    job_description,
                    user_experience,
                    tone
                )
                logger.info(f"AI SUCCESS! Cover letter length: {len(letter)} chars")
                return letter
            except Exception as e:
                logger.error(f"Gemini FAILED: {type(e).__name__}: {str(e)}")
                logger.info("Trying OpenRouter fallback...")
        else:
            logger.info(f"Gemini not available - trying OpenRouter...")
        
        # Try OpenRouter as fallback
        try:
            letter = self._generate_cover_letter_with_openrouter(
                company_name, job_title, job_description, user_experience, tone
            )
            if letter and len(letter) > 100:
                logger.info(f"OpenRouter SUCCESS! Cover letter length: {len(letter)} chars")
                return letter
        except Exception as e:
            logger.error(f"OpenRouter FAILED: {type(e).__name__}: {str(e)}")
        
        # Last resort fallback
        logger.info("All AI providers failed for cover letter")
        return self._generate_template_cover_letter(
            company_name,
            job_title,
            job_description,
            user_experience,
            tone
        )
    
    def _generate_cover_letter_with_openrouter(
        self,
        company_name: str,
        job_title: str,
        job_description: str,
        user_experience: str,
        tone: str
    ) -> str:
        """Generate cover letter using OpenRouter API as fallback"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise Exception("No OpenRouter API key")
        
        tone_guides = {
            'professional': 'formal, business-like, and respectful',
            'enthusiastic': 'energetic, passionate, and excited about the opportunity',
            'confident': 'bold, assertive, and self-assured while remaining professional'
        }
        tone_guide = tone_guides.get(tone, 'professional and engaging')
        
        prompt = f"""Write a professional cover letter for {job_title} at {company_name}.

Job Description: {job_description[:1000] if job_description else 'Not provided - tailor to the job title'}
Applicant Background: {user_experience if user_experience else 'Experienced professional'}
Tone: {tone_guide}

Requirements:
1. Opening: Hook the reader - avoid clichés like "I am writing to apply"
2. Body (2-3 paragraphs): Match skills to job requirements, include 2-3 quantified achievements
3. Closing: Express enthusiasm with a clear call to action
4. 300-400 words, active voice, strong verbs
5. Start with date, "Dear Hiring Manager,", end with "Sincerely, [Your Name]"

Generate the complete cover letter now."""

        import requests
        models_to_try = ["deepseek/deepseek-chat", "meta-llama/llama-3.1-70b-instruct"]
        
        for model in models_to_try:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://jobsphere.app",
                        "X-Title": "JobSphere Cover Letter"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an expert career coach and professional copywriter specializing in compelling cover letters."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 1500,
                    },
                    timeout=25
                )
                if response.status_code == 200:
                    data = response.json()
                    letter = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if letter and len(letter) > 100:
                        logger.info(f"OpenRouter ({model}) cover letter: {len(letter)} chars")
                        return letter
            except Exception as e:
                logger.error(f"OpenRouter ({model}) cover letter failed: {str(e)[:100]}")
                continue
        
        raise Exception("All OpenRouter models failed for cover letter generation")

    def _generate_cover_letter_with_gemini(
        self,
        company_name: str,
        job_title: str,
        job_description: str,
        user_experience: str,
        tone: str
    ) -> str:
        """Generate cover letter using Gemini AI"""
        
        # Define tone descriptions
        tone_guides = {
            'professional': 'formal, business-like, and respectful',
            'enthusiastic': 'energetic, passionate, and excited about the opportunity',
            'confident': 'bold, assertive, and self-assured while remaining professional'
        }
        
        tone_guide = tone_guides.get(tone, 'professional and engaging')
        
        # Build context-aware prompt
        prompt = f"""You are an expert career coach and professional copywriter who specializes in compelling, personalized cover letters that win interviews.

JOB DETAILS:
- Company: {company_name}
- Position: {job_title}
- Job Description: {job_description[:1500] if job_description else 'Not provided — tailor the letter to the job title and company'}

APPLICANT BACKGROUND:
{user_experience if user_experience else 'Not provided — write a strong letter based on the job requirements, using placeholder achievements the candidate can customize'}

TONE: {tone_guide}

COVER LETTER REQUIREMENTS:
1. Opening paragraph: Hook the reader immediately — avoid clichés like "I am writing to apply." Instead, lead with a compelling connection to the role or company.
2. Body paragraphs (2-3):
   - Match the candidate's skills and experience to the SPECIFIC requirements in the job description
   - Include 2-3 concrete, quantified achievements (e.g., "increased efficiency by 30%", "managed a team of 8")
   - Demonstrate genuine knowledge of {company_name} — reference their products, mission, or recent initiatives ONLY if you have reliable information; otherwise, keep it role-focused
   - Explain what unique value the candidate brings
3. Closing: Express enthusiasm, propose next steps, include a clear call to action
4. Professional sign-off

STYLE GUIDELINES:
- Length: 300-400 words (concise and impactful)
- Tone: {tone_guide}
- Use active voice throughout; favor strong verbs (spearheaded, delivered, optimized)
- Every sentence must earn its place — no filler or generic phrases
- Do NOT fabricate specific company details if unsure; focus on the role instead

FORMAT:
[Date]

Hiring Manager
{company_name}

Dear Hiring Manager,

[Letter content with paragraphs separated by blank lines]

Sincerely,
[Your Name]

Generate the complete cover letter now."""

        try:
            logger.info(f"Calling Gemini AI for cover letter...")
            response = self.ai_model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.9,
                    'top_k': 40,
                    'max_output_tokens': 1500,
                }
            )
            letter = response.text.strip()
            logger.info(f"AI generated {len(letter)} chars")
            return letter
            
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _generate_template_cover_letter(
        self,
        company_name: str,
        job_title: str,
        job_description: str,
        user_experience: str,
        tone: str
    ) -> str:
        """Last-resort cover letter generation - retry AI with simplified prompt, then return minimal dynamic letter"""
        
        # Last-resort: try Gemini with a simpler prompt
        for attempt in range(len(self.gemini_keys)):
            try:
                api_key = _get_next_gemini_key()
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash')
                
                simple_prompt = f"""Write a professional cover letter for {job_title} at {company_name}.
Applicant background: {user_experience if user_experience else 'Experienced professional'}
Job description: {job_description[:500] if job_description else 'Not provided'}
Tone: {tone}

Write 300-400 words. Start with the date, then "Dear Hiring Manager,". End with "Sincerely, [Your Name]"."""

                response = model.generate_content(
                    simple_prompt,
                    generation_config={'temperature': 0.8, 'max_output_tokens': 1500},
                    request_options={"timeout": 20}
                )
                letter = response.text.strip()
                if len(letter) > 100:
                    logger.info(f"Last-resort cover letter generated: {len(letter)} chars")
                    return letter
            except Exception as e:
                logger.error(f"Last-resort cover letter attempt {attempt + 1} failed: {str(e)[:100]}")
                continue
        
        # Absolute last resort - return error message
        return f"""AI Cover Letter Generation Temporarily Unavailable

We were unable to generate an AI-powered cover letter for {job_title} at {company_name} at this moment. 
All AI providers are currently experiencing high demand or rate limits.

Please try again in 30-60 seconds. The AI service typically recovers quickly."""

    def generate_improved_resume(
        self,
        personal_info: dict,
        experience: str,
        education: str,
        skills: str,
        projects: str = "",
        certifications: str = "",
        target_role: str = "",
        improvements: str = "",
        template: str = "modern"
    ) -> str:
        """
        Generate an improved, professional resume using AI
        
        Args:
            personal_info: Dict with name, email, phone, location, etc.
            experience: Work experience details
            education: Educational background
            skills: Skills list
            projects: Projects (optional)
            certifications: Certifications (optional)
            target_role: Target job role (optional)
            improvements: Specific improvements to include from analysis
            template: Resume template style (modern, professional, creative, ats, tech)
            
        Returns:
            str: Improved resume in structured HTML format
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"Generating Improved Resume")
        logger.info(f"Template: {template}")
        logger.info(f"Target Role: {target_role if target_role else 'General'}")
        logger.info(f"{'='*70}\n")
        # Define template styles
        template_styles = {
            "modern": {
                "description": "Modern Professional - Clean, minimalist two-column layout with color accents",
                "color": "#667eea",
                "accent_color": "#764ba2",
                "style": "two-column layout, modern typography, subtle color accents, clean sections"
            },
            "professional": {
                "description": "Classic Professional - Traditional corporate style, single column",
                "color": "#2c3e50",
                "accent_color": "#34495e",
                "style": "single column, traditional formatting, conservative colors, formal structure"
            },
            "creative": {
                "description": "Creative Designer - Bold, colorful design for creative professionals",
                "color": "#e74c3c",
                "accent_color": "#c0392b",
                "style": "creative layout, bold colors, unique sections, portfolio emphasis"
            },
            "ats": {
                "description": "ATS-Optimized - Maximum ATS compatibility with simple formatting",
                "color": "#27ae60",
                "accent_color": "#229954",
                "style": "simple single column, no complex formatting, keyword-optimized, high parse rate"
            },
            "tech": {
                "description": "Tech Engineer - Developer-focused with technical sections",
                "color": "#3498db",
                "accent_color": "#2980b9",
                "style": "tech-focused layout, projects section prominent, GitHub links, technical skills emphasis"
            }
        }
        
        selected_template = template_styles.get(template, template_styles["modern"])
        
        try:
            # Build comprehensive prompt for AI with template styling
            prompt = f"""You are an expert resume writer (CPRW-certified) specializing in ATS-optimized, visually compelling resumes (2026).

**PERSONAL INFORMATION:**
{self._format_dict(personal_info)}

**WORK EXPERIENCE:**
{experience}

**EDUCATION:**
{education}

**SKILLS:**
{skills}

**PROJECTS:**
{projects if projects else "Not provided"}

**CERTIFICATIONS:**
{certifications if certifications else "Not provided"}

**TARGET ROLE:**
{target_role if target_role else "General professional role"}

**IMPROVEMENTS TO INCLUDE:**
{improvements if improvements else "Apply general best practices"}

**TEMPLATE STYLE:** {selected_template['description']}
**Template Layout:** {selected_template['style']}
**Primary Color:** {selected_template['color']}
**Accent Color:** {selected_template['accent_color']}

**CRITICAL CONSTRAINTS:**
1. Use ONLY the information provided above - DO NOT fabricate companies, job titles, dates, degrees, or achievements
2. Enhance the LANGUAGE (stronger action verbs, better phrasing) but preserve ALL facts
3. If information is missing for a section, omit that section - do not invent content
4. Quantify achievements only where the source data supports it

**RESUME INSTRUCTIONS:**
1. Create a professional resume using the "{template}" template style
2. Follow the template layout: {selected_template['style']}
3. Use the color scheme (primary: {selected_template['color']}, accent: {selected_template['accent_color']})
4. Rewrite bullet points with strong action verbs (Led, Spearheaded, Architected, Delivered, Optimized)
5. Optimize keywords for the target role: {target_role if target_role else 'the candidate\'s field'}
6. Apply the improvements suggested above
7. Keep content concise: 1-2 pages worth, no filler
8. Ensure ATS compatibility (especially for 'ats' template)

**TEMPLATE-SPECIFIC LAYOUT:**
- "modern": Two-column layout with colored sidebar for contact/skills
- "professional": Traditional single-column, conservative formatting
- "creative": Bold section headers, accent colors, unique design elements
- "ats": Simple plain formatting, no tables/columns/graphics, standard section headers
- "tech": Projects section prominent, GitHub/portfolio links, technical skills grid

**OUTPUT FORMAT:**
Generate COMPLETE, VALID HTML with inline CSS. Include:
- Professional header with contact info (styled per template)
- Professional summary/objective
- Work experience with achievement-focused bullet points
- Education section
- Skills section (categorized if applicable)
- Projects section (if data provided)
- Certifications section (if data provided)

The HTML must render correctly in a browser and print cleanly. Use proper spacing, typography, and responsive layout.

Generate the complete resume now:"""

            # Generate improved resume using Gemini AI
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,  # Balanced creativity and consistency
                    max_output_tokens=4096,  # Full resume needs more tokens
                )
            )
            
            improved_resume = response.text.strip()
            
            logger.info(f"Successfully generated improved resume")
            logger.info(f"Resume length: {len(improved_resume)} characters")
            return improved_resume
            
        except Exception as e:
            logger.error(f"Gemini improved resume error: {str(e)}")
            logger.info("Trying OpenRouter for improved resume...")
        
        # Try OpenRouter as fallback
        try:
            resume = self._generate_improved_resume_with_openrouter(
                personal_info, experience, education, skills,
                projects, certifications, target_role, improvements, template
            )
            if resume and len(resume) > 200:
                return resume
        except Exception as e:
            logger.error(f"OpenRouter improved resume failed: {str(e)}")
        
        # Last resort - template
        return self._generate_template_resume(
            personal_info, experience, education, skills, 
            projects, certifications, target_role
        )
    
    def _generate_improved_resume_with_openrouter(
        self,
        personal_info: dict,
        experience: str,
        education: str,
        skills: str,
        projects: str,
        certifications: str,
        target_role: str,
        improvements: str,
        template: str
    ) -> str:
        """Generate improved resume using OpenRouter API as fallback"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            raise Exception("No OpenRouter API key")
        
        prompt = f"""You are an expert resume writer (CPRW-certified). Generate a professional resume in HTML format.

PERSONAL INFO: {', '.join(f'{k}: {v}' for k, v in personal_info.items())}
EXPERIENCE: {experience[:2000]}
EDUCATION: {education[:500]}
SKILLS: {skills[:500]}
PROJECTS: {projects[:500] if projects else 'Not provided'}
CERTIFICATIONS: {certifications[:300] if certifications else 'Not provided'}
TARGET ROLE: {target_role if target_role else 'General professional role'}
IMPROVEMENTS: {improvements[:500] if improvements else 'Apply best practices'}
TEMPLATE: {template}

CRITICAL: Use ONLY the information provided - do NOT fabricate any details.

Generate a complete, valid HTML resume with inline CSS that:
1. Has a professional header with contact info
2. Uses strong action verbs for bullet points
3. Organizes skills into categories
4. Is ATS-friendly
5. Looks professional when printed

Output ONLY the HTML code."""

        import requests
        models_to_try = ["deepseek/deepseek-chat", "meta-llama/llama-3.1-70b-instruct"]
        
        for model in models_to_try:
            try:
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://jobsphere.app",
                        "X-Title": "JobSphere Resume Builder"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are an expert resume writer. Output only valid HTML with inline CSS."},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4096,
                    },
                    timeout=30
                )
                if response.status_code == 200:
                    data = response.json()
                    resume = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if resume and len(resume) > 200:
                        logger.info(f"OpenRouter ({model}) improved resume: {len(resume)} chars")
                        return resume
            except Exception as e:
                logger.error(f"OpenRouter ({model}) improved resume failed: {str(e)[:100]}")
                continue
        
        raise Exception("All OpenRouter models failed for improved resume generation")

    def _format_dict(self, data: dict) -> str:
        """Format dictionary data for prompt"""
        return "\n".join([f"- {key}: {value}" for key, value in data.items()])
    
    def _generate_template_resume(
        self,
        personal_info: dict,
        experience: str,
        education: str,
        skills: str,
        projects: str,
        certifications: str,
        target_role: str
    ) -> str:
        """Generate a template resume as fallback"""
        
        name = personal_info.get('name', '[Your Name]')
        email = personal_info.get('email', '[email]')
        phone = personal_info.get('phone', '[phone]')
        location = personal_info.get('location', '[location]')
        linkedin = personal_info.get('linkedin', '')
        
        linkedin_section = f"<div>LinkedIn: {linkedin}</div>" if linkedin else ""
        
        template = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        .resume-container {{
            font-family: 'Segoe UI', Arial, sans-serif;
            max-width: 850px;
            margin: 0 auto;
            padding: 40px;
            background: white;
            color: #333;
            line-height: 1.6;
        }}
        .resume-header {{
            text-align: center;
            border-bottom: 3px solid #667eea;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .resume-name {{
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 10px;
        }}
        .resume-contact {{
            font-size: 14px;
            color: #666;
        }}
        .resume-section {{
            margin-bottom: 30px;
        }}
        .resume-section-title {{
            font-size: 20px;
            font-weight: bold;
            color: #667eea;
            border-bottom: 2px solid #e0e7ff;
            padding-bottom: 8px;
            margin-bottom: 15px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .resume-content {{
            padding-left: 10px;
        }}
        .resume-item {{
            margin-bottom: 15px;
        }}
        .resume-item-title {{
            font-weight: bold;
            color: #333;
            font-size: 16px;
        }}
        .resume-item-subtitle {{
            color: #666;
            font-style: italic;
            margin-bottom: 8px;
        }}
        ul {{
            margin: 8px 0;
            padding-left: 25px;
        }}
        li {{
            margin-bottom: 5px;
        }}
        .skills-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 10px;
        }}
        .skill-item {{
            background: #e0e7ff;
            padding: 8px 12px;
            border-radius: 5px;
            font-size: 14px;
        }}
        @media print {{
            .resume-container {{
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="resume-container">
        <!-- Header -->
        <div class="resume-header">
            <div class="resume-name">{name}</div>
            <div class="resume-contact">
                <div>{email} • {phone} • {location}</div>
                {linkedin_section}
            </div>
        </div>
        
        <!-- Professional Summary -->
        <div class="resume-section">
            <div class="resume-section-title">Professional Summary</div>
            <div class="resume-content">
                Results-driven professional with expertise in {target_role if target_role else 'various domains'}. 
                Proven track record of delivering high-quality results and collaborating effectively with teams. 
                Strong technical skills combined with excellent problem-solving abilities and commitment to continuous learning.
            </div>
        </div>
        
        <!-- Work Experience -->
        <div class="resume-section">
            <div class="resume-section-title">Work Experience</div>
            <div class="resume-content">
                {self._format_section_content(experience)}
            </div>
        </div>
        
        <!-- Education -->
        <div class="resume-section">
            <div class="resume-section-title">Education</div>
            <div class="resume-content">
                {self._format_section_content(education)}
            </div>
        </div>
        
        <!-- Skills -->
        <div class="resume-section">
            <div class="resume-section-title">Skills</div>
            <div class="resume-content">
                {self._format_section_content(skills)}
            </div>
        </div>
        
        {self._optional_section('Projects', projects)}
        {self._optional_section('Certifications', certifications)}
    </div>
</body>
</html>
"""
        return template.strip()
    
    def _format_section_content(self, content: str) -> str:
        """Format section content with proper HTML"""
        if not content:
            return "<p>No information provided</p>"
        
        # Convert line breaks to paragraphs
        lines = content.strip().split('\n')
        formatted = []
        for line in lines:
            line = line.strip()
            if line:
                if line.startswith('-') or line.startswith('•'):
                    formatted.append(f"<li>{line[1:].strip()}</li>")
                else:
                    formatted.append(f"<p>{line}</p>")
        
        return '\n'.join(formatted)
    
    def _optional_section(self, title: str, content: str) -> str:
        """Generate optional section if content exists"""
        if not content or content.strip() == "":
            return ""
        
        return f"""
        <div class="resume-section">
            <div class="resume-section-title">{title}</div>
            <div class="resume-content">
                {self._format_section_content(content)}
            </div>
        </div>
        """
