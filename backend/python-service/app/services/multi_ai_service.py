"""
Multi-AI Service - Unified AI orchestration with fallback support
Similar to multi_search_service for job APIs, this handles multiple AI providers
"""

import os
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import httpx
import logging

logger = logging.getLogger(__name__)

# Import all AI SDKs
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import cohere
    COHERE_AVAILABLE = True
except ImportError:
    COHERE_AVAILABLE = False


class MultiAIService:
    """
    Unified AI service with automatic fallback
    Tries multiple AI providers in order: Gemini → Groq → Cohere → Hugging Face
    """
    
    def __init__(self):
        self.providers = []
        self.usage_stats = {
            "gemini": {"requests": 0, "successes": 0, "failures": 0},
            "groq": {"requests": 0, "successes": 0, "failures": 0},
            "cohere": {"requests": 0, "successes": 0, "failures": 0},
            "huggingface": {"requests": 0, "successes": 0, "failures": 0},
            "openrouter": {"requests": 0, "successes": 0, "failures": 0}
        }
        
        # Initialize available providers
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all available AI providers"""
        
        # 1. Try Gemini (Primary)
        if GEMINI_AVAILABLE:
            gemini_key = os.getenv("GEMINI_API_KEY")
            if gemini_key:
                try:
                    genai.configure(api_key=gemini_key)
                    self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
                    self.providers.append("gemini")
                    logger.info("Gemini AI initialized")
                except Exception as e:
                    logger.error(f"Gemini initialization failed: {e}")
        # 2. Try Groq (Fast fallback)
        if GROQ_AVAILABLE:
            groq_key = os.getenv("GROQ_API_KEY")
            if groq_key:
                try:
                    self.groq_client = Groq(api_key=groq_key)
                    self.providers.append("groq")
                    logger.info("Groq AI initialized")
                except Exception as e:
                    logger.error(f"Groq initialization failed: {e}")
        # 3. Try Cohere (Backup)
        if COHERE_AVAILABLE:
            cohere_key = os.getenv("COHERE_API_KEY")
            if cohere_key:
                try:
                    self.cohere_client = cohere.Client(cohere_key)
                    self.providers.append("cohere")
                    logger.info("Cohere AI initialized")
                except Exception as e:
                    logger.error(f"Cohere initialization failed: {e}")
        # 4. Hugging Face (Final fallback)
        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if hf_key:
            self.hf_headers = {"Authorization": f"Bearer {hf_key}"}
            self.providers.append("huggingface")
            logger.info("Hugging Face API initialized")
        # 5. OpenRouter (Optional)
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if openrouter_key:
            self.openrouter_key = openrouter_key
            self.openrouter_model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
            self.providers.append("openrouter")
            logger.info("OpenRouter API initialized")
        if not self.providers:
            logger.info("No AI providers available! Please add API keys to .env")
        else:
            logger.info(f"Available AI providers: {', '.join(self.providers)}")
    async def generate_text(
        self, 
        prompt: str, 
        strategy: str = "smart",
        max_tokens: int = 1000,
        temperature: float = 0.7
    ) -> Dict[str, Any]:
        """
        Generate text using available AI providers with fallback
        
        Strategies:
        - "smart": Try providers in order, stop at first success (fastest)
        - "best": Always use Gemini (highest quality)
        - "fast": Always use Groq (fastest inference)
        - "aggregate": Try all providers and return best response
        """
        
        if strategy == "best":
            return await self._generate_with_provider("gemini", prompt, max_tokens, temperature)
        
        elif strategy == "fast":
            return await self._generate_with_provider("groq", prompt, max_tokens, temperature)
        
        elif strategy == "aggregate":
            return await self._aggregate_generate(prompt, max_tokens, temperature)
        
        else:  # "smart" - default
            return await self._smart_generate(prompt, max_tokens, temperature)
    
    async def _smart_generate(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float
    ) -> Dict[str, Any]:
        """
        Try providers in order: Gemini → Groq → Cohere → HuggingFace
        Stop at first successful response
        """
        
        for provider in self.providers:
            try:
                result = await self._generate_with_provider(
                    provider, prompt, max_tokens, temperature
                )
                if result["success"]:
                    return result
            except Exception as e:
                logger.error(f"{provider} failed: {e}")
                continue
        
        # All providers failed
        return {
            "success": False,
            "provider": None,
            "text": None,
            "error": "All AI providers failed"
        }
    
    async def _aggregate_generate(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float
    ) -> Dict[str, Any]:
        """
        Try all providers in parallel, return longest/best response
        Useful for critical tasks where quality matters
        """
        
        tasks = [
            self._generate_with_provider(provider, prompt, max_tokens, temperature)
            for provider in self.providers
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        successful = [r for r in results if isinstance(r, dict) and r.get("success")]
        
        if not successful:
            return {
                "success": False,
                "provider": None,
                "text": None,
                "error": "All AI providers failed"
            }
        
        # Return longest response (usually more detailed)
        best_result = max(successful, key=lambda x: len(x["text"]))
        best_result["aggregate"] = True
        best_result["providers_tried"] = len(self.providers)
        best_result["providers_succeeded"] = len(successful)
        
        return best_result
    
    async def _generate_with_provider(
        self,
        provider: str,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Generate text with specific provider"""
        
        self.usage_stats[provider]["requests"] += 1
        
        try:
            if provider == "gemini":
                text = await self._generate_gemini(prompt, max_tokens, temperature)
            elif provider == "groq":
                text = await self._generate_groq(prompt, max_tokens, temperature)
            elif provider == "cohere":
                text = await self._generate_cohere(prompt, max_tokens, temperature)
            elif provider == "huggingface":
                text = await self._generate_huggingface(prompt, max_tokens)
            elif provider == "openrouter":
                text = await self._generate_openrouter(prompt, max_tokens, temperature)
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            self.usage_stats[provider]["successes"] += 1
            
            return {
                "success": True,
                "provider": provider,
                "text": text,
                "error": None,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.usage_stats[provider]["failures"] += 1
            raise e
    
    async def _generate_gemini(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float
    ) -> str:
        """Generate with Gemini"""
        
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )
        
        response = await self.gemini_model.generate_content_async(
            prompt,
            generation_config=generation_config
        )
        
        return response.text
    
    async def _generate_groq(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float
    ) -> str:
        """Generate with Groq (fastest!)"""
        
        completion = self.groq_client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return completion.choices[0].message.content
    
    async def _generate_cohere(
        self, 
        prompt: str, 
        max_tokens: int, 
        temperature: float
    ) -> str:
        """Generate with Cohere"""
        
        response = self.cohere_client.generate(
            prompt=prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            model="command"
        )
        
        return response.generations[0].text
    
    async def _generate_huggingface(
        self, 
        prompt: str, 
        max_tokens: int
    ) -> str:
        """Generate with Hugging Face Inference API"""
        
        API_URL = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                API_URL,
                headers=self.hf_headers,
                json={
                    "inputs": prompt,
                    "parameters": {
                        "max_new_tokens": max_tokens,
                        "return_full_text": False
                    }
                }
            )
            response.raise_for_status()
            
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "")
            return ""

    async def _generate_openrouter(
        self,
        prompt: str,
        max_tokens: int,
        temperature: float
    ) -> str:
        """Generate with OpenRouter"""

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openrouter_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.openrouter_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics for all providers"""
        
        total_requests = sum(stats["requests"] for stats in self.usage_stats.values())
        total_successes = sum(stats["successes"] for stats in self.usage_stats.values())
        
        return {
            "providers_available": self.providers,
            "total_requests": total_requests,
            "total_successes": total_successes,
            "success_rate": f"{(total_successes/total_requests*100):.1f}%" if total_requests > 0 else "0%",
            "provider_stats": self.usage_stats
        }


# Global instance
multi_ai_service = MultiAIService()
