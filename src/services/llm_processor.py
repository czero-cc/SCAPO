"""LLM processor for cleaning and structuring scraped content."""

import json
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import httpx
from pydantic import BaseModel, Field

from src.core.logging import get_logger
from src.core.config import settings

logger = get_logger(__name__)


class ProcessedPractice(BaseModel):
    """Structured output from LLM processing."""
    
    practice_type: str = Field(..., description="Type: prompting, parameter, pitfall, tip")
    content: str = Field(..., description="Clean, actionable practice")
    confidence: float = Field(..., description="Confidence score 0-1")
    applicable_models: List[str] = Field(default_factory=list, description="Models this applies to")
    source_quality: str = Field(..., description="high, medium, low")
    extracted_parameters: Optional[Dict[str, Any]] = None
    example_code: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)


class LLMProcessor(ABC):
    """Base class for LLM processors."""
    
    def __init__(self, model_name: str, context_window: int, max_chars: Optional[int] = None):
        self.model_name = model_name
        self.context_window = context_window
        self.max_chars = max_chars or settings.llm_max_chars
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def process_content(self, content: str, content_type: str) -> List[ProcessedPractice]:
        """Process raw content and extract structured practices."""
        pass
    
    @abstractmethod
    async def process_raw_prompt(self, prompt: str) -> str:
        """Process a raw prompt and return the response as a string.
        This is used for entity extraction and other non-practice extraction tasks."""
        pass
    
    def truncate_to_limit(self, text: str) -> Tuple[str, bool]:
        """Truncate text to character limit.
        
        Returns:
            Tuple of (truncated_text, was_truncated)
        """
        # Apply hard limit first
        if len(text) > settings.llm_char_hard_limit:
            text = text[:settings.llm_char_hard_limit]
            self.logger.warning(f"Applied hard limit of {settings.llm_char_hard_limit} chars")
        
        # Apply user-specified limit
        if len(text) > self.max_chars:
            self.logger.info(f"Truncating content from {len(text)} to {self.max_chars} chars")
            return text[:self.max_chars] + "\n\n[Content truncated...]", True
        
        return text, False
    
    def truncate_to_context(self, text: str, reserve_tokens: int = 1000) -> str:
        """Legacy method - now uses character limit instead."""
        truncated, _ = self.truncate_to_limit(text)
        return truncated
    
    def create_extraction_prompt(self, content: str, content_type: str) -> str:
        """Create prompt for extracting practices from content."""
        return f"""Analyze this {content_type} content and extract actionable AI/LLM best practices.

Content:
{content}

Extract and structure the following:
1. Prompting techniques (specific patterns, templates, or strategies)
2. Parameter recommendations (with specific values and reasoning)
3. Common pitfalls or mistakes to avoid
4. Practical tips that are actually useful
5. Any code examples or templates

For each practice found:
- Determine confidence (high/medium/low) based on evidence
- Identify which models it applies to
- Clean up the language to be clear and actionable
- Remove noise, opinions, and off-topic content

Return as JSON array with this structure:
[
  {{
    "practice_type": "prompting|parameter|pitfall|tip",
    "content": "Clear, actionable description",
    "confidence": 0.0-1.0,
    "applicable_models": ["model1", "model2"],
    "source_quality": "high|medium|low",
    "extracted_parameters": {{"param": value}} or null,
    "example_code": "code snippet" or null,
    "warnings": ["any caveats"]
  }}
]

Focus on concrete, verifiable practices only. Ignore speculation and unverified claims."""


class OpenRouterProcessor(LLMProcessor):
    """Process content using OpenRouter API with rate limiting and retry logic."""
    
    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3-haiku",
        context_window: int = 200000,  # Claude 3 Haiku
        max_chars: Optional[int] = None,
    ):
        super().__init__(model, context_window, max_chars)
        self.api_key = api_key
        self.base_url = "https://openrouter.ai/api/v1"
        self.client = httpx.AsyncClient(
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/fiefworks/scapo",
                "X-Title": "SCAPO - Stay Calm and Prompt On",
            },
            timeout=30.0
        )
        
        # Rate limiting settings
        self.max_retries = 3
        self.base_delay = 1.0  # Base delay in seconds
        self.max_delay = 60.0  # Maximum delay in seconds
        self.min_request_interval = 0.5  # Minimum time between requests
        self.last_request_time = 0
    
    async def _make_request_with_retry(self, json_data: dict) -> httpx.Response:
        """Make HTTP request with exponential backoff retry logic."""
        # Implement minimum interval between requests
        import time
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last)
        
        for attempt in range(self.max_retries):
            try:
                self.last_request_time = time.time()
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=json_data
                )
                
                # If successful, return
                if response.status_code == 200:
                    return response
                
                # If rate limited, retry with backoff
                if response.status_code == 429:
                    if attempt < self.max_retries - 1:
                        # Calculate delay with exponential backoff
                        delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                        
                        # Check if response has Retry-After header
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            delay = float(retry_after)
                        
                        self.logger.warning(f"Rate limited. Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(delay)
                        continue
                
                # For other errors, raise immediately
                response.raise_for_status()
                
            except httpx.TimeoutException:
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    self.logger.warning(f"Request timeout. Retrying in {delay}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    continue
                raise
        
        # If all retries failed, raise the last response error
        response.raise_for_status()
        return response

    async def process_content(self, content: str, content_type: str) -> List[ProcessedPractice]:
        """Process content using OpenRouter with retry logic."""
        # Truncate if needed
        content, was_truncated = self.truncate_to_limit(content)
        if was_truncated:
            self.logger.info(f"Content truncated to {self.max_chars} characters for {content_type}")
        
        prompt = self.create_extraction_prompt(content, content_type)
        
        try:
            response = await self._make_request_with_retry({
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert at extracting actionable AI/LLM best practices from noisy community content. Be critical and only extract verified, useful practices."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
            })
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse JSON response
            practices_data = json.loads(content)
            if isinstance(practices_data, dict) and "practices" in practices_data:
                practices_data = practices_data["practices"]
            
            # Convert to ProcessedPractice objects
            practices = []
            for item in practices_data:
                try:
                    practice = ProcessedPractice(**item)
                    practices.append(practice)
                except Exception as e:
                    self.logger.error(f"Error parsing practice: {e}")
            
            return practices
            
        except Exception as e:
            self.logger.error(f"OpenRouter processing failed: {str(e)}", exc_info=True)
            return []
    
    async def process_raw_prompt(self, prompt: str) -> str:
        """Process a raw prompt and return the response as a string with retry logic."""
        try:
            response = await self._make_request_with_retry({
                "model": self.model_name,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            })
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            self.logger.error(f"OpenRouter raw prompt processing failed after {self.max_retries} attempts: {str(e)}", exc_info=True)
            return "{}"
        
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class LocalLLMProcessor(LLMProcessor):
    """Process content using local LLM (Ollama or LM Studio)."""
    
    # Known model context windows
    MODEL_CONTEXT_WINDOWS = {
        # Ollama models
        "llama2": 4096,
        "llama2:13b": 4096,
        "llama2:70b": 4096,
        "llama3": 8192,
        "llama3:70b": 8192,
        "llama3.1": 128000,
        "mistral": 8192,
        "mixtral": 32768,
        "phi": 2048,
        "phi3": 128000,
        "gemma": 8192,
        "gemma:7b": 8192,
        "qwen": 32768,
        "qwen:14b": 32768,
        "qwen:32b": 32768,
        "deepseek-coder": 16384,
        "codellama": 16384,
        # LM Studio common models
        "gpt4all-falcon": 2048,
        "orca-mini": 2048,
        "vicuna": 2048,
        "wizardlm": 2048,
        # Default fallback
        "default": 4096,
    }
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",  # Ollama default
        model: str = "llama3",
        context_window: Optional[int] = None,
        api_type: str = "ollama",  # "ollama" or "lmstudio"
        max_chars: Optional[int] = None,
    ):
        # Auto-detect context window if not provided
        if context_window is None:
            context_window = self.MODEL_CONTEXT_WINDOWS.get(
                model.lower(),
                self.MODEL_CONTEXT_WINDOWS["default"]
            )
            logger.info(f"Using context window {context_window} for model {model}")
        
        super().__init__(model, context_window, max_chars)
        self.base_url = base_url
        self.api_type = api_type
        self.client = httpx.AsyncClient(timeout=120.0)  # Longer timeout for local models
    
    async def check_model_availability(self) -> bool:
        """Check if the model is available locally."""
        try:
            if self.api_type == "ollama":
                response = await self.client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    available = any(m["name"] == self.model_name for m in models)
                    if not available:
                        self.logger.warning(f"Model {self.model_name} not found. Available: {[m['name'] for m in models]}")
                    return available
            else:  # lmstudio
                # LM Studio doesn't have a model list endpoint
                return True
        except Exception as e:
            self.logger.error(f"Error checking model availability: {e}")
            return False
    
    async def process_content(self, content: str, content_type: str) -> List[ProcessedPractice]:
        """Process content using local LLM."""
        # Check model availability
        if not await self.check_model_availability():
            self.logger.error(f"Model {self.model_name} not available")
            return []
        
        # Truncate content for local models
        content, was_truncated = self.truncate_to_limit(content)
        if was_truncated:
            self.logger.info(f"Content truncated to {self.max_chars} characters for local LLM")
        
        prompt = self.create_extraction_prompt(content, content_type)
        
        try:
            if self.api_type == "ollama":
                response = await self._process_ollama(prompt)
            else:
                response = await self._process_lmstudio(prompt)
            
            # Parse response
            practices = self._parse_llm_response(response)
            return practices
            
        except Exception as e:
            self.logger.error(f"Local LLM processing failed: {e}")
            return []
    
    async def _process_ollama(self, prompt: str) -> str:
        """Process using Ollama API."""
        response = await self.client.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model_name,
                "prompt": f"{prompt}\n\nRespond with valid JSON only:",
                "temperature": 0.3,
                "stream": False,
                "format": "json",  # Ollama JSON mode
            }
        )
        response.raise_for_status()
        return response.json()["response"]
    
    async def _process_lmstudio(self, prompt: str) -> str:
        """Process using LM Studio API (OpenAI compatible)."""
        response = await self.client.post(
            f"{self.base_url}/v1/chat/completions",
            json={
                "model": self.model_name,
                "messages": [
                    {
                        "role": "system",
                        "content": "Extract actionable AI best practices. Respond in JSON format only."
                    },
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 2000,
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    
    def _parse_llm_response(self, response: str) -> List[ProcessedPractice]:
        """Parse LLM response with fallback for imperfect JSON."""
        practices = []
        
        try:
            # Try to extract JSON from response
            import re
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                response = json_match.group()
            
            data = json.loads(response)
            if isinstance(data, dict) and "practices" in data:
                data = data["practices"]
            
            for item in data:
                try:
                    # Provide defaults for missing fields
                    item.setdefault("confidence", 0.5)
                    item.setdefault("source_quality", "medium")
                    item.setdefault("applicable_models", [])
                    
                    practice = ProcessedPractice(**item)
                    practices.append(practice)
                except Exception as e:
                    self.logger.warning(f"Error parsing practice item: {e}")
        
        except json.JSONDecodeError as e:
            self.logger.error(f"JSON parse error: {e}")
            # Fallback: try to extract any useful content
            if "practice_type" in response and "content" in response:
                try:
                    # Very basic extraction
                    practices.append(ProcessedPractice(
                        practice_type="tip",
                        content=response[:500],
                        confidence=0.3,
                        source_quality="low",
                        warnings=["Extracted with fallback parser"]
                    ))
                except:
                    pass
        
        return practices
    
    async def process_raw_prompt(self, prompt: str) -> str:
        """Process a raw prompt and return the response as a string."""
        try:
            if self.api_type == "ollama":
                response = await self._process_ollama(prompt)
            else:
                response = await self._process_lmstudio(prompt)
            return response
        except Exception as e:
            self.logger.error(f"Local LLM raw prompt processing failed: {e}")
            return "{}"
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


class LLMProcessorFactory:
    """Factory for creating appropriate LLM processor."""
    
    @staticmethod
    def create_processor(
        provider: str = "local",
        **kwargs
    ) -> LLMProcessor:
        """Create an LLM processor based on provider."""
        if provider == "openrouter":
            api_key = kwargs.get("api_key") or settings.openrouter_api_key
            if not api_key:
                raise ValueError("OpenRouter API key required")
            
            return OpenRouterProcessor(
                api_key=api_key,
                model=kwargs.get("model", "anthropic/claude-3-haiku"),
                context_window=kwargs.get("context_window", 200000),
                max_chars=kwargs.get("max_chars"),
            )
        
        elif provider == "local":
            return LocalLLMProcessor(
                base_url=kwargs.get("base_url", "http://localhost:11434"),
                model=kwargs.get("model", "llama3"),
                context_window=kwargs.get("context_window"),  # Auto-detected if None
                api_type=kwargs.get("api_type", "ollama"),
                max_chars=kwargs.get("max_chars"),
            )
        
        else:
            raise ValueError(f"Unknown provider: {provider}")


# Example usage function
async def process_scraped_content(
    content: Dict[str, Any],
    provider: str = "local",
    **processor_kwargs
) -> Dict[str, List[ProcessedPractice]]:
    """Process scraped content through LLM."""
    processor = LLMProcessorFactory.create_processor(provider, **processor_kwargs)
    
    results = {}
    
    try:
        # Process different content types
        for content_type, raw_content in content.items():
            if isinstance(raw_content, str):
                practices = await processor.process_content(raw_content, content_type)
                results[content_type] = practices
            elif isinstance(raw_content, dict) and "content" in raw_content:
                practices = await processor.process_content(
                    raw_content["content"],
                    content_type
                )
                results[content_type] = practices
    
    finally:
        await processor.close()
    
    return results