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
        
        print(f"[KEY] Loaded {len(GEMINI_API_KEYS)} Gemini API key(s)")
    return GEMINI_API_KEYS

def _get_next_gemini_key():
    """Get next Gemini API key in rotation"""
    global CURRENT_GEMINI_INDEX
    keys = _load_gemini_keys()
    if not keys:
        return None
    
    key = keys[CURRENT_GEMINI_INDEX]
    CURRENT_GEMINI_INDEX = (CURRENT_GEMINI_INDEX + 1) % len(keys)
    print(f"[EMOJI] Using Gemini key #{CURRENT_GEMINI_INDEX + 1}/{len(keys)}")
    return key

def _init_openai():
    global OPENAI_CLIENT
    if OPENAI_CLIENT is None:
        try:
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                OPENAI_CLIENT = OpenAI(api_key=api_key)
                print("[SYMBOL] OpenAI client ready")
        except Exception as e:
            print(f"[SYMBOL]️ OpenAI init failed: {e}")
    return OPENAI_CLIENT

def _init_groq():
    global GROQ_CLIENT
    if GROQ_CLIENT is None:
        try:
            from groq import Groq
            api_key = os.getenv('GROQ_API_KEY')
            if api_key:
                GROQ_CLIENT = Groq(api_key=api_key)
                print("[SYMBOL] Groq client ready")
        except Exception as e:
            print(f"[SYMBOL]️ Groq init failed: {e}")
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
                print("[SYMBOL] HuggingFace client ready")
        except Exception as e:
            print(f"[SYMBOL]️ HuggingFace init failed: {e}")
    return HF_CLIENT

def _init_cohere():
    global COHERE_CLIENT
    if COHERE_CLIENT is None:
        try:
            import cohere
            api_key = os.getenv('COHERE_API_KEY')
            if api_key:
                COHERE_CLIENT = cohere.Client(api_key, timeout=15)  # 15 second timeout
                print("[SYMBOL] Cohere client ready")
        except Exception as e:
            print(f"[SYMBOL]️ Cohere init failed: {e}")
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
            print(f"[SYMBOL]️ Grok API non-200 status: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        print(f"[SYMBOL]️ Grok call failed: {e}")
    return ""

# Try to import Gemini AI
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    print("[SYMBOL]️ google-generativeai not installed. Using template questions.")

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
                self.ai_model = genai.GenerativeModel('gemini-2.0-flash-exp')
                self.use_ai = True
                print(f"[SYMBOL] Gemini AI initialized with {len(self.gemini_keys)} account(s) for rotation!")
            except Exception as e:
                print(f"[SYMBOL]️ Gemini initialization failed: {e}")
                self.ai_model = None
        else:
            print("[INFO]️ No GEMINI_API_KEY found. Using fallback providers.")

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
        print(f"[EMOJI] AI provider fallback chain: {self.providers_order or ['templates only']}")
        
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
                print(f"\n[EMOJI] Attempting provider: {provider} for {prompt_job_title}")
                if provider == 'openrouter':
                    content = self._call_openrouter(job_title, job_description, company_name)
                    if content:
                        parsed = self._parse_questions_json(content)
                        if parsed and len(parsed.get('technical', [])) >= 8:
                            print(f"[SYMBOL] OpenRouter generated {sum(len(v) for v in parsed.values())} questions successfully!")
                            return parsed
                        else:
                            print(f"[SYMBOL]️ OpenRouter response incomplete or invalid, trying next provider")
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
                print(f"[SYMBOL]️ Provider {provider} failed: {provider_errors[provider]}")

        if provider_errors:
            print("\n[SYMBOL] All AI providers failed; errors summary:")
            for p, msg in provider_errors.items():
                print(f"   - {p}: {msg}")
        
        # Template-based generation (fallback)
        print(f"[EMOJI] Using template generation for: {job_title}")
        return self._generate_with_templates(job_title, job_description, company_name, num_questions)

    # ---- Provider-specific helpers ----
    def _build_core_prompt(self, job_title: str, job_description: str, company_name: str) -> str:
        return (
            f"Generate structured JSON interview questions for job '{job_title}' at '{company_name or 'Unknown Company'}'. "
            f"Job description: {job_description[:600] if job_description else 'N/A'}. "
            "Return ONLY valid JSON with keys: technical (10 items), behavioral (5 items), company (3 items), general (2 items). "
            "No explanations, no markdown."
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
            print(f"[SYMBOL]️ Cohere call failed: {e}")
            return ""

    def _call_openrouter(self, job_title: str, job_description: str, company_name: str) -> str:
        """Call OpenRouter API with better models for interview generation"""
        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            print("[SYMBOL]️ No OpenRouter API key found")
            return ""
        
        # Build comprehensive prompt
        prompt = f"""Generate interview questions as valid JSON for this position:

Job Title: {job_title}
Company: {company_name or 'Not specified'}
Job Description: {job_description[:800] if job_description else 'Not provided - use industry standards for this role'}

Generate UNIQUE, SPECIFIC questions based on the job description. Extract technologies, tools, and skills mentioned.

Return ONLY valid JSON (no markdown, no explanations):
{{
  "technical": ["10 technical questions based on job requirements"],
  "behavioral": ["5 behavioral questions for this role"],
  "company": ["3 questions about the company/role fit"],
  "general": ["2 general career questions"]
}}

Make questions varied and avoid repetition. Timestamp: {int(time.time())}"""
        
        # Try multiple models for best quality
        models_to_try = [
            "deepseek/deepseek-chat",  # Best for technical content
            "meta-llama/llama-3.1-70b-instruct",  # High quality, good reasoning
            "google/gemini-2.0-flash-exp:free",  # Free Gemini via OpenRouter
            "meta-llama/llama-3.2-3b-instruct:free"  # Fallback free model
        ]
        
        for model in models_to_try:
            try:
                print(f"[EMOJI] Trying OpenRouter with model: {model}")
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
                        print(f"[SYMBOL] OpenRouter ({model}) generated response ({len(content)} chars)")
                        return content
                else:
                    print(f"[SYMBOL]️ OpenRouter {model} returned {resp.status_code}: {resp.text[:200]}")
                    # Try next model
                    continue
            except Exception as e:
                print(f"[SYMBOL]️ OpenRouter {model} failed: {e}")
                # Try next model
                continue
        
        print("[SYMBOL]️ All OpenRouter models failed")
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
            print(f"[SYMBOL]️ OpenAI call failed: {e}")
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
            print(f"[SYMBOL]️ Groq call failed: {e}")
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
            print(f"[SYMBOL]️ HuggingFace call failed: {e}")
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
        print(f"\n{'='*60}")
        print(f"[EMOJI] GENERATING AI QUESTIONS")
        print(f"{'='*60}")
        print(f"Job Title: {job_title}")
        print(f"Company: {company_name}")
        print(f"Description Length: {len(job_description)} chars")
        print(f"Description Preview: {job_description[:200] if job_description else 'None'}...")
        print(f"{'='*60}\n")
        
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
        
        # Create simplified but explicit prompt
        prompt = f"""You are a professional technical interviewer conducting an interview. Generate UNIQUE and VARIED questions.

[EMOJI] POSITION DETAILS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JOB TITLE: {job_title}
COMPANY: {company_name if company_name else 'Not specified'}

JOB DESCRIPTION:
{job_description if job_description and len(job_description.strip()) > 0 else 'Not provided - generate general questions for this role'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[SYMBOL]️ CRITICAL INSTRUCTIONS:
1. READ THE JOB DESCRIPTION CAREFULLY - Extract specific requirements, technologies, and responsibilities
2. Generate questions that are DIRECTLY RELEVANT to what's written in the job description
3. If job description mentions specific tools/technologies (e.g., Guidewire, Selenium, Python), ASK ABOUT THEM
4. If job description is empty/minimal, generate industry-standard questions for "{job_title}" role
5. Generate DIFFERENT questions each time - avoid repetitive patterns
6. Match the technical depth to the role (junior vs senior)

[EMOJI] VARIETY SEED: {timestamp % 1000} - Use this to add randomness to your questions

EXAMPLES OF CORRECT MATCHING:
- If title is "Manual Tester" and description mentions "Guidewire" → Ask about Guidewire testing, test case design, bug tracking
- If title is "Python Developer" and description mentions "Django, PostgreSQL" → Ask about Django ORM, PostgreSQL optimization
- If title is "QA Engineer" and description mentions "Selenium" → Ask about automation frameworks, Page Object Model
- If title is "Data Analyst" and description mentions "SQL, Tableau" → Ask about SQL queries, data visualization

[EMOJI] YOUR TASK:

STEP 1: ANALYZE THE JOB
- Job Title: "{job_title}"
- Job Description Length: {len(job_description) if job_description else 0} characters
- Key Technologies: Extract from description above (e.g., Guidewire, Python, React, AWS, Selenium, etc.)
- Role Type: Identify if Testing/QA, Development, Data, DevOps, Management, etc.
- Seniority: Junior, Mid-level, or Senior based on title

STEP 2: EXTRACT REQUIREMENTS FROM JOB DESCRIPTION
Look for these in the job description:
[SYMBOL] Specific tools/platforms (Guidewire, Salesforce, SAP, etc.)
[SYMBOL] Programming languages (Python, Java, JavaScript, etc.)
[SYMBOL] Frameworks (React, Django, Spring, etc.)
[SYMBOL] Testing types (Manual, Automation, API, Performance, etc.)
[SYMBOL] Methodologies (Agile, Scrum, TDD, BDD, etc.)
[SYMBOL] Domain knowledge (Finance, Healthcare, E-commerce, etc.)

STEP 3: GENERATE TAILORED QUESTIONS
Create questions that directly test the skills mentioned in the job description.

[SYMBOL]️ CRITICAL RULES:
[SYMBOL] DO NOT ask programming/coding questions for MANUAL TESTING roles
[SYMBOL] DO NOT ask about technologies NOT mentioned in the description
[SYMBOL] DO NOT use generic template questions - be specific
[SYMBOL] DO ask about specific tools mentioned (e.g., if "Guidewire" → ask about Guidewire modules)
[SYMBOL] DO match question difficulty to seniority level
[SYMBOL] DO generate VARIED questions - avoid patterns

[EMOJI] GENERATE EXACTLY 20 QUESTIONS IN THESE CATEGORIES:

**Technical (10 questions)** - Based on ACTUAL requirements from job description:

IF TESTING/QA ROLE:
- Test strategy and planning questions
- Questions about specific testing types mentioned (functional, regression, integration, etc.)
- Tool-specific questions (JIRA, TestRail, Postman, Selenium - only if mentioned)
- Defect lifecycle and documentation
- Test case design techniques (boundary value, equivalence partitioning)
- If "Guidewire" in description: Ask about PolicyCenter/BillingCenter/ClaimCenter testing workflows
- If "API testing" mentioned: Ask about REST APIs, HTTP methods, status codes, Postman
- If automation mentioned: Then ask about frameworks (Selenium, Cypress, TestNG)
- If NO automation: Focus on manual testing, exploratory testing, test documentation

IF DEVELOPMENT ROLE:
- Language-specific questions (Python, Java, JavaScript - from description)
- Framework questions (React, Django, Spring - from description)
- Database questions (SQL, PostgreSQL, MongoDB - from description)
- Architecture and design patterns
- Code quality and best practices

**Behavioral (5 questions)** - Scenarios relevant to THIS specific role:
- For testers: Bug discovery, working with developers, test planning under pressure
- For developers: Code reviews, technical debt, debugging complex issues
- For leads: Team management, conflict resolution, technical decisions

**Company (3 questions)** - About {company_name if company_name else 'the company'}:
- Why this company?
- What do you know about our products/services?
- How does this role align with your career goals?

**General (2 questions)** - Career and motivation:
- Career progression and goals
- Learning approach and staying updated

RETURN ONLY THIS JSON (no extra text, no markdown):
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
                print(f"[EMOJI] Attempting Gemini account {attempt + 1}/{len(self.gemini_keys)}...")
                
                # Initialize model with current key
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                
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
                print(f"[SYMBOL] Gemini API responded successfully!")
                
                # Clean the response text
                text = response.text.strip()
                print(f"[EMOJI] Response length: {len(text)} chars")
                
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
                print(f"\n[SYMBOL] Generated {sum(len(q) for q in questions_dict.values())} AI-powered questions!")
                print(f"[EMOJI] Sample Technical Questions:")
                for i, q in enumerate(questions_dict.get('technical', [])[:3], 1):
                    print(f"   {i}. {q[:80]}...")
                print(f"{'='*60}\n")
                
                return questions_dict
                
            except json.JSONDecodeError as e:
                print(f"[SYMBOL] JSON parse error with account {attempt + 1}: {e}")
                if attempt < len(self.gemini_keys) - 1:
                    print("⏭️ Trying next Gemini account...")
                    continue
                else:
                    print("[SYMBOL] All Gemini accounts failed JSON parsing")
                    raise
                    
            except Exception as e:
                error_msg = str(e).lower()
                # Check if it's a quota/rate limit error
                if '429' in error_msg or 'quota' in error_msg or 'rate limit' in error_msg or 'resourceexhausted' in error_msg:
                    print(f"[SYMBOL]️ Gemini account {attempt + 1} quota exceeded: {str(e)[:100]}")
                    if attempt < len(self.gemini_keys) - 1:
                        print("[EMOJI] Rotating to next Gemini account...")
                        continue
                    else:
                        print("[SYMBOL] All Gemini accounts exhausted")
                        raise
                else:
                    # Other error - don't retry
                    print(f"[SYMBOL] Gemini error: {type(e).__name__}: {str(e)[:200]}")
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
            print(f"[EMOJI] Detected TESTING role - using testing-specific questions")
            questions['technical'].extend(random.sample(testing_questions, min(6, len(testing_questions))))
            
            if has_guidewire:
                print(f"[EMOJI] Guidewire mentioned - adding Guidewire questions")
                questions['technical'].extend(random.sample(guidewire_questions, min(3, len(guidewire_questions))))
            
            if has_api_testing:
                print(f"[EMOJI] API testing mentioned - adding API questions")
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
        
        print(f"[EMOJI] Generated {sum(len(q) for q in questions.values())} randomized template questions")
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
                prompt = f"""You are an expert resume reviewer and career counselor. Analyze the following resume and provide comprehensive feedback.

RESUME:
{resume_content}

Please provide a detailed analysis covering:

1. **Overall Score (0-100)**: Rate the resume overall and explain the score

2. **Strengths**: What are the strong points of this resume?

3. **Weaknesses**: What areas need improvement?

4. **Content Analysis**:
   - Is the professional summary compelling?
   - Are work experiences quantified with achievements?
   - Are skills relevant and well-organized?
   - Is education information complete?

5. **Formatting & Structure**:
   - Is the layout professional and easy to read?
   - Are sections well-organized?
   - Is the length appropriate?

6. **ATS Optimization**:
   - Does it use relevant keywords?
   - Will it pass Applicant Tracking Systems?
   - Suggestions for better keyword usage

7. **Specific Improvements**: Provide 5-7 actionable suggestions with examples

8. **Industry Alignment**: How well does this resume align with current industry standards?

9. **Red Flags**: Any concerning elements that should be addressed?

10. **Next Steps**: What should the candidate do to improve this resume?

Please be constructive, specific, and provide examples where possible. Format your response in a clear, organized manner."""

                response = self.ai_model.generate_content(prompt)
                return response.text
                
            except Exception as e:
                print(f"AI resume analysis error: {e}")
                return self._generate_template_analysis(resume_content)
        else:
            return self._generate_template_analysis(resume_content)
    
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
        
        analysis = f"""[EMOJI] **Resume Analysis Results**

**Overall Score: {score}/100**

{'[SYMBOL] Good' if score >= 75 else '[SYMBOL]️ Needs Improvement' if score >= 60 else '[SYMBOL] Significant Improvement Needed'}

---

**[EMOJI] Structure Analysis**

[SYMBOL] Contact Information: {'Present' if (has_email and has_phone) else 'Missing or Incomplete'}
[SYMBOL] Professional Summary: {'Present' if sections['summary'] else 'Missing'}
[SYMBOL] Work Experience: {'Present' if sections['experience'] else 'Missing'}
[SYMBOL] Education: {'Present' if sections['education'] else 'Missing'}
[SYMBOL] Skills Section: {'Present' if sections['skills'] else 'Missing'}

---

**[EMOJI] Strengths Identified:**

{f'• Strong quantifiable achievements ({achievement_count} found)' if achievement_count >= 3 else ''}
{f'• Comprehensive resume with all major sections' if sum(sections.values()) >= 4 else ''}
{f'• Appropriate length ({word_count} words)' if 300 <= word_count <= 800 else ''}

---

**[SYMBOL]️ Areas for Improvement:**

{f'• Add contact information (email and phone)' if not (has_email and has_phone) else ''}
{f'• Include a professional summary at the top' if not sections['summary'] else ''}
{f'• Add quantifiable achievements (use numbers, percentages, metrics)' if achievement_count < 3 else ''}
{f'• Resume is too {"short" if word_count < 300 else "long"} - aim for 300-800 words' if not (300 <= word_count <= 800) else ''}

---

**[EMOJI] Specific Recommendations:**

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

**[EMOJI] ATS (Applicant Tracking System) Tips:**

• Use standard fonts (Arial, Calibri, Times New Roman)
• Avoid headers/footers, tables, and text boxes
• Save as .docx or PDF
• Include relevant keywords naturally in context
• Use full acronyms first (e.g., "Application Programming Interface (API)")

---

**[EMOJI] Next Steps:**

1. Review each section and ensure it's complete and well-formatted
2. Add 3-5 quantifiable achievements to each role
3. Tailor your resume for specific job applications
4. Have someone proofread for typos and grammar
5. Test with ATS resume scanners online

---

**[EMOJI] Pro Tip:** Keep multiple versions of your resume tailored to different types of roles or industries. This increases your chances of passing ATS screening and catching the recruiter's attention.

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
        print(f"\n{'='*70}")
        print(f"[EMOJI] ANSWER GENERATION WITH MULTI-PROVIDER FALLBACK")
        print(f"{'='*70}")
        print(f"Question: {question}")
        print(f"Available providers: {self.providers_order}")
        print(f"{'='*70}\n")
        
        provider_errors = {}
        
        # Try each provider in order
        for provider in self.providers_order:
            try:
                print(f"\n[EMOJI] Attempting {provider} for answer generation...")
                
                if provider == 'gemini' and self.ai_model:
                    answer = self._generate_answer_with_gemini(question)
                    if answer and len(answer) > 50:
                        print(f"[SYMBOL] {provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'cohere':
                    answer = self._generate_answer_with_cohere(question)
                    if answer and len(answer) > 50:
                        print(f"[SYMBOL] {provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'openai':
                    answer = self._generate_answer_with_openai(question)
                    if answer and len(answer) > 50:
                        print(f"[SYMBOL] {provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'groq':
                    answer = self._generate_answer_with_groq(question)
                    if answer and len(answer) > 50:
                        print(f"[SYMBOL] {provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'xai':
                    answer = self._generate_answer_with_xai(question)
                    if answer and len(answer) > 50:
                        print(f"[SYMBOL] {provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
                elif provider == 'huggingface':
                    answer = self._generate_answer_with_huggingface(question)
                    if answer and len(answer) > 50:
                        print(f"[SYMBOL] {provider.upper()} SUCCESS! Answer: {len(answer)} chars")
                        return answer
                        
            except Exception as e:
                error_msg = f"{type(e).__name__}: {str(e)}"[:200]
                provider_errors[provider] = error_msg
                print(f"[SYMBOL]️ {provider} failed: {error_msg}")
        
        # All providers failed - use template-based answer
        print("\n[SYMBOL] All AI providers failed for answer generation")
        for p, err in provider_errors.items():
            print(f"   - {p}: {err}")
        
        print("[EMOJI] Falling back to template-based answer generation")
        return self._generate_template_answer(question)
    
    def _generate_answer_with_gemini(self, question: str) -> str:
        """Generate answer using Gemini AI with account rotation"""
        
        # Enhanced prompt that demands specific, complete answers
        prompt = f"""You are a senior interview coach. Answer this interview question as if YOU are the candidate being interviewed. Give a complete, specific answer.

Question: {question}

Requirements:
[SYMBOL] Answer AS the candidate (first person: "I would...", "In my experience...")
[SYMBOL] Give COMPLETE answer (minimum 200 words)
[SYMBOL] Include 2-3 specific examples or scenarios
[SYMBOL] For behavioral questions: Use full STAR format with real scenario
[SYMBOL] For technical questions: Explain concept + give code example or detailed use case
[SYMBOL] Format with markdown: **bold** for emphasis, bullet points for lists
[SYMBOL] End with a brief summary or key takeaway

CRITICAL: Do NOT give advice on "how to answer". Give the ACTUAL ANSWER as if you're in the interview.

Answer:"""

        # Try each Gemini account
        for attempt in range(len(self.gemini_keys)):
            try:
                api_key = _get_next_gemini_key()
                print(f"[EMOJI] Gemini account {attempt + 1}/{len(self.gemini_keys)} for answer...")
                
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.0-flash-exp')
                
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
                print(f"[SYMBOL] Answer generated: {len(answer)} chars")
                
                if len(answer) < 50:
                    raise Exception("Answer too short")
                
                return answer
                
            except Exception as e:
                error_msg = str(e).lower()
                if '429' in error_msg or 'quota' in error_msg or 'rate limit' in error_msg or 'resourceexhausted' in error_msg:
                    print(f"[SYMBOL]️ Gemini account {attempt + 1} quota exceeded")
                    if attempt < len(self.gemini_keys) - 1:
                        print("[EMOJI] Trying next account...")
                        continue
                    else:
                        print("[SYMBOL] All Gemini accounts exhausted for answers")
                        raise
                else:
                    print(f"[SYMBOL] Gemini error: {str(e)[:100]}")
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
        
        prompt = f"""Answer this interview question as an experienced candidate. Give a complete, unique answer (200+ words).

Question: {question}

Style: {style}
Generation ID: {seed}{int(time.time())}

Answer in first person with genuine, specific scenarios. Make it unique and authentic."""
        
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
        """Generate template-based answer for common question patterns"""
        
        question_lower = question.lower()
        
        # Check for common question patterns
        if any(word in question_lower for word in ['tell me about yourself', 'introduce yourself']):
            return """**Structured Approach:**

Start with your current role and highlight 2-3 key achievements. Then briefly mention your professional background (1-2 previous roles). Finally, explain why you're interested in this position and what you bring to the team.

**Example Framework:**
"I'm currently a [Role] at [Company] where I [key achievement]. Before this, I spent [X years] working on [relevant experience]. I'm particularly excited about this opportunity because [specific reason], and I believe my experience in [relevant skill] would contribute significantly to your team."

**Key Tips:**
- Keep it to 60-90 seconds
- Focus on professional highlights, not personal life
- Connect your experience to the role you're applying for
- End with enthusiasm about the opportunity"""

        elif any(word in question_lower for word in ['strength', 'strengths']):
            return """**How to Answer:**

Choose a strength that's directly relevant to the job. Support it with specific examples and quantifiable results.

**Structure:**
1. State the strength clearly
2. Explain why it's valuable in your field
3. Give a concrete example with results
4. Connect it to the role you're applying for

**Example:**
"One of my key strengths is problem-solving. In my previous role, I identified a bottleneck in our deployment process and implemented an automated solution that reduced deployment time by 60%. I believe this analytical approach would be valuable for tackling the challenges mentioned in this role."

**Tips:**
- Be specific, not generic ("I'm good at communication" is too vague)
- Use the STAR method (Situation, Task, Action, Result)
- Choose strengths mentioned in the job description"""

        elif any(word in question_lower for word in ['weakness', 'weaknesses', 'areas of improvement']):
            return """**The Right Approach:**

Choose a real weakness (not a strength in disguise), but show how you're actively working to improve it.

**Structure:**
1. Name the weakness honestly
2. Explain the context or why it's challenging
3. Describe specific steps you're taking to improve
4. Share progress you've made

**Example:**
"I've found that I can sometimes focus too much on perfecting details, which affected my efficiency. I've been working on this by setting clear priorities and timeboxing tasks. For example, I now use the 80/20 rule - getting 80% done quickly, then evaluating if the remaining 20% is truly necessary. This has helped me deliver projects faster while maintaining quality."

**Avoid:**
- "I'm a perfectionist" or "I work too hard" (clichés)
- Critical weaknesses for the role
- Not showing self-awareness or improvement efforts"""

        elif 'handle' in question_lower and any(word in question_lower for word in ['conflict', 'disagreement', 'difficult']):
            return """**Use the STAR Method:**

**Situation:** Briefly set the context
**Task:** Explain your responsibility
**Action:** Detail the specific steps you took
**Result:** Share the positive outcome

**Example Answer Framework:**
"In my previous role, I had a disagreement with a colleague about [specific situation]. Instead of letting it escalate, I scheduled a one-on-one meeting to understand their perspective. I actively listened to their concerns and found that we actually wanted the same outcome but had different approaches. We compromised by [specific solution], which led to [positive result]. This experience taught me the importance of direct communication and finding common ground."

**Key Principles:**
- Stay professional and focus on resolution
- Show emotional intelligence and empathy
- Emphasize positive outcomes
- Demonstrate your communication skills
- Never badmouth colleagues"""

        else:
            # Generic answer structure
            return """**Suggested Approach:**

**1. Understand the Question:**
Take a moment to think about what they're really asking. Are they testing your technical knowledge, problem-solving ability, or cultural fit?

**2. Structure Your Answer:**
- Start with a clear, direct response
- Provide specific examples from your experience
- Explain your thought process
- End with results or lessons learned

**3. Use the STAR Method:**
- **Situation:** Set the context
- **Task:** Explain your responsibility
- **Action:** Detail what you did
- **Result:** Share the outcome

**4. Keep It Relevant:**
Connect your answer to the role and company. Show how your experience applies to their needs.

**5. Be Concise:**
Aim for 1-2 minutes. Provide enough detail to be credible, but don't ramble.

**Pro Tip:** Practice your answer out loud. This helps you refine it and builds confidence for the actual interview."""

        return answer
    
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
        print(f"\n{'='*70}")
        print(f"[EMOJI] COVER LETTER GENERATION CALLED")
        print(f"{'='*70}")
        print(f"Company: {company_name}")
        print(f"Position: {job_title}")
        print(f"Tone: {tone}")
        print(f"use_ai: {self.use_ai}")
        print(f"ai_model exists: {self.ai_model is not None}")
        print(f"{'='*70}\n")
        
        # FORCE AI if model exists
        if self.ai_model is not None:
            try:
                print(f"[EMOJI] Calling Gemini AI for cover letter...")
                letter = self._generate_cover_letter_with_gemini(
                    company_name,
                    job_title,
                    job_description,
                    user_experience,
                    tone
                )
                print(f"[SYMBOL] AI SUCCESS! Cover letter length: {len(letter)} chars")
                return letter
            except Exception as e:
                print(f"[SYMBOL] AI FAILED: {type(e).__name__}: {str(e)}")
                import traceback
                traceback.print_exc()
                print("[EMOJI] Falling back to template...")
        else:
            print(f"[SYMBOL]️ AI MODEL IS NONE - Cannot use AI")
        
        # Template fallback
        print("Using template cover letter")
        return self._generate_template_cover_letter(
            company_name,
            job_title,
            job_description,
            user_experience,
            tone
        )
    
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
        prompt = f"""Write a personalized cover letter for a job application.

JOB DETAILS:
- Company: {company_name}
- Position: {job_title}
- Job Description: {job_description if job_description else 'Not provided'}

APPLICANT BACKGROUND:
{user_experience if user_experience else 'Not provided - use general professional experience'}

TONE: {tone_guide}

REQUIREMENTS:
1. Start with professional header (Date, Company, Greeting)
2. Opening paragraph: Express interest and briefly state why you're a fit
3. Body paragraphs (2-3):
   - Highlight relevant skills matching the job
   - Provide specific examples of achievements
   - Show knowledge about {company_name}
   - Explain what you can contribute
4. Closing: Express enthusiasm, thank them, call to action
5. Professional sign-off

STYLE GUIDELINES:
- Length: 300-400 words
- Tone: {tone_guide}
- Be specific and personalized to {company_name} and {job_title}
- Use active voice and strong action verbs
- Avoid generic phrases like "I am writing to apply"
- Show passion and knowledge about the company
- Quantify achievements when possible

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
            print(f"[EMOJI] Calling Gemini AI for cover letter...")
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
            print(f"[SYMBOL] AI generated {len(letter)} chars")
            return letter
            
        except Exception as e:
            print(f"[SYMBOL] Gemini API error: {str(e)}")
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
        """Generate template-based cover letter"""
        
        from datetime import datetime
        date_str = datetime.now().strftime("%B %d, %Y")
        
        # Adjust language based on tone
        if tone == 'enthusiastic':
            opening = f"I am thrilled to apply for the {job_title} position at {company_name}!"
            closing = "I would be absolutely delighted to discuss how my passion and skills can contribute to your team's success."
        elif tone == 'confident':
            opening = f"I am writing to express my strong interest in the {job_title} role at {company_name}."
            closing = "I am confident that my experience and expertise make me an excellent fit for this position."
        else:  # professional
            opening = f"I am writing to apply for the {job_title} position at {company_name}."
            closing = "I would welcome the opportunity to discuss how my qualifications align with your needs."
        
        # Build experience section
        experience_section = ""
        if user_experience:
            experience_section = f"My background includes {user_experience}, which I believe aligns well with the requirements of this role."
        else:
            experience_section = f"With my extensive experience and proven track record, I am well-prepared to contribute to {company_name}'s success."
        
        # Build job-specific section
        job_section = ""
        if job_description:
            if 'python' in job_description.lower():
                job_section = "I notice your emphasis on Python development. I have extensive experience with Python, including building scalable applications, data processing pipelines, and API development."
            elif 'javascript' in job_description.lower() or 'react' in job_description.lower():
                job_section = "I see that frontend development is crucial for this role. I have strong expertise in modern JavaScript frameworks and creating responsive, user-friendly interfaces."
            elif 'test' in job_description.lower() or 'qa' in job_description.lower():
                job_section = "I understand the importance of quality assurance in your team. My experience in designing comprehensive test strategies and ensuring software reliability would be valuable."
            else:
                job_section = f"After reviewing the job description, I am confident that my skills and experience align perfectly with what {company_name} is seeking."
        else:
            job_section = f"I am particularly drawn to this opportunity at {company_name} because of your commitment to excellence and innovation."
        
        letter = f"""{date_str}

Hiring Manager
{company_name}

Dear Hiring Manager,

{opening} {experience_section}

{job_section} Throughout my career, I have consistently delivered results by combining technical expertise with strong problem-solving abilities. I take pride in writing clean, maintainable code and collaborating effectively with cross-functional teams.

What particularly excites me about {company_name} is your dedication to innovation and creating impactful solutions. I am eager to bring my skills, enthusiasm, and commitment to excellence to your team. I believe my experience would enable me to make immediate contributions while continuing to grow professionally.

{closing} Thank you for considering my application. I look forward to the possibility of discussing this exciting opportunity with you.

Sincerely,
[Your Name]

---
Note: This is a template-generated cover letter. For best results, please review and personalize with specific details about your experience and achievements."""

        return letter

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
        print(f"\n{'='*70}")
        print(f"[EMOJI] Generating Improved Resume")
        print(f"Template: {template}")
        print(f"Target Role: {target_role if target_role else 'General'}")
        print(f"{'='*70}\n")
        
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
            prompt = f"""You are an expert resume writer and career coach. Generate a professional, ATS-optimized resume based on the following information.

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

**INSTRUCTIONS:**
1. Create a professional resume using the "{template}" template style
2. Follow the template layout style: {selected_template['style']}
3. Use the specified color scheme (primary: {selected_template['color']}, accent: {selected_template['accent_color']})
4. Use strong action verbs and quantifiable achievements
5. Optimize for the target role (if specified)
6. Include all the improvements suggested in the analysis
7. Format the resume with clear sections and professional structure
8. Use bullet points for experience and achievements
9. Make it concise yet comprehensive (1-2 pages worth of content)
10. Include relevant keywords for the target role
11. Ensure it's ATS-friendly (especially for the 'ats' template)

**OUTPUT FORMAT:**
Generate the resume as clean, structured HTML with inline CSS for styling. Include:
- Professional header with contact information (styled according to template)
- Professional summary/objective
- Work experience with bullet points
- Education section
- Skills section (organized by category if applicable)
- Projects section (if provided)
- Certifications section (if provided)

Use the template's styling that looks good on screen and prints well. Include proper spacing, typography, and layout matching the template style.

**IMPORTANT:** 
- For "modern" template: Use two-column layout with sidebar
- For "professional" template: Use traditional single-column format
- For "creative" template: Use bold colors and unique section designs
- For "ats" template: Use simple, clean formatting with no fancy styling (ATS systems priority)
- For "tech" template: Emphasize projects and GitHub, use tech-friendly layout

Generate the complete, improved resume now in the {template} style:"""

            # Generate improved resume using Gemini AI
            response = self.model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,  # Balanced creativity and consistency
                    max_output_tokens=2500,  # Longer output for full resume
                )
            )
            
            improved_resume = response.text.strip()
            
            print(f"[SYMBOL] Successfully generated improved resume")
            print(f"Resume length: {len(improved_resume)} characters")
            
            return improved_resume
            
        except Exception as e:
            print(f"[SYMBOL] Error generating improved resume: {str(e)}")
            # Return a formatted template as fallback
            return self._generate_template_resume(
                personal_info, experience, education, skills, 
                projects, certifications, target_role
            )
    
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
