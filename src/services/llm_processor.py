"""LLM processor for cleaning and structuring scraped content using LiteLLM."""

import json
import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
from pydantic import BaseModel, Field
import litellm
from litellm import acompletion, RateLimitError, AuthenticationError

from src.core.logging import get_logger
from src.core.config import settings
from src.services.adaptive_processor import LLMCapabilities
from src.services.content_processor import ContentChunker

logger = get_logger(__name__)

# Configure LiteLLM
litellm.drop_params = True  # Drop unsupported params instead of failing
litellm.set_verbose = False  # Set to True for debugging


class ProcessedPractice(BaseModel):
    """Structured output from LLM processing."""
    
    practice_type: str = Field(..., description="Type: prompting, parameter, pitfall, tip")
    content: str = Field(..., description="The actual practice/tip/parameter description")
    model_name: str = Field(..., description="Specific model this applies to")
    confidence: float = Field(..., description="Confidence score 0-1")
    source: str = Field(..., description="Where this was found")
    timestamp: datetime = Field(default_factory=datetime.now)
    category: str = Field(default="general", description="Category: prompting, performance, etc")


class BaseLLMProcessor(ABC):
    """Base class for LLM processors using LiteLLM."""
    
    def __init__(self, max_chars: Optional[int] = None):
        self.max_chars = max_chars or settings.llm_max_chars
        self.logger = logger
        
    @abstractmethod
    async def process_content(self, content: str, content_type: str) -> List[ProcessedPractice]:
        """Process content and extract practices."""
        pass
    
    @abstractmethod
    async def process_raw_prompt(self, prompt: str) -> str:
        """Process a raw prompt and return the response as a string."""
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
    
    def create_extraction_prompt(self, content: str, content_type: str) -> str:
        """Create a prompt for extracting practices from content."""
        return f"""Analyze this {content_type} content and extract ONLY model-specific best practices.

Content to analyze:
{content}

Extract actionable practices in this JSON format:
{{
  "practices": [
    {{
      "practice_type": "prompting|parameter|pitfall|tip",
      "content": "specific practice description",
      "model_name": "exact model name (e.g., gpt-4, llama-3-8b)",
      "confidence": 0.0-1.0,
      "source": "{content_type}",
      "category": "prompting|performance|deployment|fine-tuning|general"
    }}
  ]
}}

Guidelines:
1. ONLY extract practices that are SPECIFIC to a named model
2. Include exact model names and versions
3. Focus on actionable, concrete advice
4. Set confidence based on how definitive the advice is
5. Ignore general AI/ML advice that applies to all models
6. Extract parameters with their recommended values

Return ONLY valid JSON."""


class UnifiedLLMProcessor(BaseLLMProcessor):
    """Unified LLM processor using LiteLLM for all providers."""
    
    def __init__(self, 
                 provider: str = None,
                 model: str = None,
                 api_key: str = None,
                 base_url: str = None,
                 max_chars: Optional[int] = None):
        super().__init__(max_chars)
        
        # Set up provider-specific configuration
        self.provider = provider or settings.llm_provider
        self.model_name = model or (settings.openrouter_model if self.provider == "openrouter" else settings.local_llm_model)
        
        # Initialize smart processors
        self.capabilities = LLMCapabilities.detect_capabilities(self.provider, self.model_name)
        self.content_processor = ContentChunker(
            chunk_size=self.capabilities.optimal_chunk_size,
            overlap_size=200,
            min_chunk_size=500
        )
        
        if self.provider == "openrouter":
            self.model = f"openrouter/{model or settings.openrouter_model}"
            self.api_key = api_key or settings.openrouter_api_key
            # Set OpenRouter specific settings
            litellm.api_key = self.api_key
            litellm.openrouter_api_key = self.api_key
        elif self.provider == "local":
            if settings.local_llm_type == "ollama":
                self.model = f"ollama/{model or settings.local_llm_model}"
                self.api_base = base_url or settings.local_llm_url
                litellm.api_base = self.api_base
            else:  # lmstudio
                self.model = f"openai/{model or settings.local_llm_model}"
                self.api_base = base_url or settings.local_llm_url
                self.api_key = "lm-studio"  # LM Studio doesn't need a real key
                litellm.api_key = self.api_key
                litellm.api_base = self.api_base
        else:
            raise ValueError(f"Unknown provider: {self.provider}")
        
        self.logger.info(f"Initialized LLM processor with model: {self.model}")
    
    def _supports_json_mode(self) -> bool:
        """Check if model supports structured JSON mode."""
        return False  # Disabled for now - using system prompts only
    
    async def _make_completion(self, messages: List[Dict[str, str]], 
                             temperature: float = 0.3,
                             max_tokens: int = 2000,
                             response_format: Optional[Dict] = None) -> str:
        """Make a completion request using LiteLLM with retry logic."""
        
        # Build kwargs
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "timeout": 120.0,  # 2 minute timeout
        }
        
        # Add response format if supported by the model
        if response_format and self._supports_json_mode():
            kwargs["response_format"] = response_format
        
        # Add API key/base if needed
        if hasattr(self, 'api_key'):
            kwargs["api_key"] = self.api_key
        if hasattr(self, 'api_base'):
            kwargs["api_base"] = self.api_base
        
        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await acompletion(**kwargs)
                return response.choices[0].message.content
                
            except RateLimitError as e:
                if attempt < max_retries - 1:
                    wait_time = min(60, 2 ** attempt)  # Exponential backoff
                    self.logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}")
                    await asyncio.sleep(wait_time)
                else:
                    raise
                    
            except AuthenticationError:
                self.logger.error(f"Authentication failed for {self.provider}")
                raise
                
            except Exception as e:
                self.logger.error(f"LLM request failed: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise
    
    
    async def process_content(self, content: str, content_type: str) -> List[ProcessedPractice]:
        """Process content using smart chunking and LiteLLM."""
        # Use smart content processor instead of basic truncation
        all_practices = []
        
        try:
            chunks = self.content_processor.chunk_with_overlap(content)
            self.logger.info(f"Content split into {len(chunks)} chunks for processing")
            
            for chunk in chunks:
                prompt = self.create_extraction_prompt(chunk.text, content_type)
                practices = await self._extract_practices_from_chunk(prompt, content_type)
                all_practices.extend(practices)
                
        except Exception as e:
            self.logger.error(f"Smart processing failed, falling back to basic truncation: {e}")
            # Fallback to basic truncation
            content, was_truncated = self.truncate_to_limit(content)
            if was_truncated:
                self.logger.info(f"Content truncated to {self.max_chars} characters for {content_type}")
            
            prompt = self.create_extraction_prompt(content, content_type)
            practices = await self._extract_practices_from_chunk(prompt, content_type)
            all_practices.extend(practices)
        
        return all_practices
    
    async def _extract_practices_from_chunk(self, prompt: str, content_type: str) -> List[ProcessedPractice]:
        """Extract practices from a single chunk."""
        
        try:
            response = await self._make_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You MUST respond with valid JSON only. Start with { and end with }. No explanations before or after the JSON."
                    },
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            # Parse JSON response with multiple strategies
            practices_data = None
            try:
                # Try direct parsing
                practices_data = json.loads(response)
            except json.JSONDecodeError:
                # Clean and retry
                cleaned_response = response.strip()
                
                # Remove common prefixes
                for prefix in ["Here is the JSON:", "Here's the JSON:", "JSON:", "Based on the analysis:"]:
                    if cleaned_response.lower().startswith(prefix.lower()):
                        cleaned_response = cleaned_response[len(prefix):].strip()
                
                # Try to extract JSON from various formats
                import re
                json_patterns = [
                    r'```(?:json)?\s*([\[{].*?[\]}])\s*```',  # Markdown code block
                    r'([\[{][^\[{]*(?:[\[{][^\[{\]}]*[\]}][^\[{\]}]*)*[\]}])',  # Nested JSON
                    r'([\[{].*[\]}])'  # Any JSON-like structure
                ]
                
                for pattern in json_patterns:
                    matches = re.findall(pattern, cleaned_response, re.DOTALL)
                    for match in matches:
                        try:
                            practices_data = json.loads(match)
                            break
                        except:
                            continue
                    if practices_data:
                        break
                
                if not practices_data:
                    # Last resort: try to construct minimal valid response
                    self.logger.warning(f"No valid JSON found in LLM response. Attempting text extraction fallback...")
                    self.logger.debug(f"Raw response: {response[:500]}...")
                    
                    # Try to extract useful information from plain text
                    if any(keyword in response.lower() for keyword in ['tip', 'practice', 'recommend', 'use', 'avoid', 'setting', 'parameter']):
                        # Create a basic practice from the text
                        practices_data = {
                            "practices": [{
                                "practice_type": "tip",
                                "content": response[:200] + "..." if len(response) > 200 else response,
                                "model_name": "general",
                                "confidence": 0.3,
                                "source": content_type,
                                "category": "general"
                            }]
                        }
                        self.logger.info("Created fallback practice from non-JSON response")
                    else:
                        # Return empty list but continue processing
                        return []
            
            # Extract practices list
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
                    continue
            
            return practices
            
        except Exception as e:
            self.logger.error(f"Failed to process content: {str(e)}", exc_info=True)
            return []
    
    async def process_raw_prompt(self, prompt: str) -> str:
        """Process a raw prompt and return the response as a string."""
        try:
            # For JSON requests, add stronger instructions
            messages = []
            if "json" in prompt.lower():
                messages.append({
                    "role": "system",
                    "content": "You are a JSON generator. You MUST respond with ONLY valid JSON, no explanations or text before/after. Start your response with { or [ and end with } or ]."
                })
            
            messages.append({"role": "user", "content": prompt})
            
            response = await self._make_completion(
                messages=messages,
                temperature=0.1,  # Lower temperature for more consistent JSON
                max_tokens=2000,
            )
            
            # Clean response if it contains non-JSON prefix/suffix
            if "json" in prompt.lower():
                response = response.strip()
                
                # Remove common prefixes that models add
                json_prefixes = [
                    "Here is the JSON:", "Here's the JSON:", "JSON:", "```json", "```",
                    "The JSON response is:", "Here is the extracted JSON:",
                    "Based on the analysis, here is the JSON:"
                ]
                for prefix in json_prefixes:
                    if response.lower().startswith(prefix.lower()):
                        response = response[len(prefix):].strip()
                
                # Remove common suffixes
                json_suffixes = ["```", "\n\nI hope this helps!", "\n\nLet me know if"]
                for suffix in json_suffixes:
                    if suffix in response:
                        response = response[:response.find(suffix)].strip()
                
                # Final cleanup - ensure we have JSON
                if response and not response.startswith(('[', '{')):
                    # Try to find JSON in the response
                    import re
                    json_match = re.search(r'[\[{].*[\]}]', response, re.DOTALL)
                    if json_match:
                        response = json_match.group()
                    else:
                        self.logger.warning(f"Model {self.model} returned non-JSON response after cleanup: {response[:200]}...")
            
            return response
            
        except Exception as e:
            self.logger.error(f"Raw prompt processing failed: {str(e)}", exc_info=True)
            return "{}"
    
    async def close(self):
        """Cleanup (no longer needed with LiteLLM)."""
        pass


class LLMProcessorFactory:
    """Factory for creating appropriate LLM processor."""
    
    @staticmethod
    def create_processor(provider: str = None, **kwargs) -> BaseLLMProcessor:
        """Create LLM processor based on provider using LiteLLM.
        
        Args:
            provider: Provider name (openrouter, local, etc.)
            **kwargs: Additional arguments for the processor
        
        Returns:
            BaseLLMProcessor instance
        """
        return UnifiedLLMProcessor(provider=provider, **kwargs)