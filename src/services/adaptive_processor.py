"""Adaptive content processor that handles both local and cloud LLMs intelligently."""

import json
import re
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from src.core.logging import get_logger
from src.core.config import settings

logger = get_logger(__name__)


@dataclass
class LLMCapabilities:
    """Track capabilities of different LLM providers."""
    provider: str
    model: str
    max_context: int
    supports_json_mode: bool
    optimal_chunk_size: int
    
    @classmethod
    def detect_capabilities(cls, provider: str, model: str) -> 'LLMCapabilities':
        """Detect LLM capabilities based on provider and model."""
        
        # Local LLMs (limited context)
        if provider == "local":
            if "llama" in model.lower():
                if "3" in model:
                    return cls(provider, model, 8192, False, 2000)
                elif "2" in model:
                    return cls(provider, model, 4096, False, 1500)
                else:
                    return cls(provider, model, 2048, False, 1000)
            elif "mistral" in model.lower():
                return cls(provider, model, 8192, False, 2000)
            elif "phi" in model.lower():
                return cls(provider, model, 4096, False, 1500)
            elif "qwen" in model.lower():
                if "32k" in model.lower():
                    return cls(provider, model, 32768, True, 8000)
                else:
                    return cls(provider, model, 8192, True, 2000)
            else:
                # Conservative defaults for unknown local models
                return cls(provider, model, 2048, False, 1000)
        
        # Cloud providers (larger context)
        elif provider == "openrouter":
            if "claude" in model.lower():
                if "3-opus" in model.lower():
                    return cls(provider, model, 200000, True, 50000)
                elif "3.5" in model.lower():
                    return cls(provider, model, 200000, True, 50000)
                else:
                    return cls(provider, model, 100000, True, 25000)
            elif "gpt-4" in model.lower():
                if "turbo" in model.lower() or "128k" in model.lower():
                    return cls(provider, model, 128000, True, 32000)
                else:
                    return cls(provider, model, 8192, True, 4000)
            elif "gemini" in model.lower():
                if "1.5" in model.lower():
                    return cls(provider, model, 1000000, True, 100000)
                else:
                    return cls(provider, model, 32000, True, 8000)
            else:
                # Default for cloud models
                return cls(provider, model, 32000, True, 8000)
        
        # Default fallback
        return cls(provider, model, 4096, False, 2000)


class AdaptiveContentProcessor:
    """
    Intelligently processes content based on LLM capabilities.
    Adapts chunking strategy, prompt complexity, and extraction depth.
    """
    
    def __init__(self, llm_processor):
        self.llm_processor = llm_processor
        self.capabilities = LLMCapabilities.detect_capabilities(
            llm_processor.provider,
            llm_processor.model
        )
        logger.info(f"Initialized adaptive processor for {self.capabilities.model} with {self.capabilities.max_context} token context")
    
    async def process_for_mcp(self, content: str, source_type: str) -> Dict[str, Any]:
        """
        Process content optimized for MCP (Model Context Protocol) delivery.
        Returns structured data ready for direct file serving.
        """
        
        # Determine processing strategy based on content size and LLM capabilities
        content_size = len(content)
        strategy = self._determine_strategy(content_size)
        
        logger.info(f"Using {strategy} strategy for {content_size} chars with {self.capabilities.model}")
        
        if strategy == "single_pass":
            return await self._process_single_pass(content, source_type)
        elif strategy == "multi_chunk":
            return await self._process_multi_chunk(content, source_type)
        elif strategy == "summary_first":
            return await self._process_summary_first(content, source_type)
        else:  # extract_key_only
            return await self._process_extract_key_only(content, source_type)
    
    def _determine_strategy(self, content_size: int) -> str:
        """Determine the best processing strategy based on content size and LLM capabilities."""
        
        # For very capable models (Claude, GPT-4-turbo, Gemini 1.5)
        if self.capabilities.max_context > 100000:
            if content_size <= 50000:
                return "single_pass"
            else:
                return "multi_chunk"
        
        # For medium capability models (GPT-4, most cloud models)
        elif self.capabilities.max_context > 8000:
            if content_size <= self.capabilities.optimal_chunk_size:
                return "single_pass"
            elif content_size <= self.capabilities.optimal_chunk_size * 3:
                return "multi_chunk"
            else:
                return "summary_first"
        
        # For local/small models (Llama, Phi, etc.)
        else:
            if content_size <= self.capabilities.optimal_chunk_size:
                return "single_pass"
            else:
                return "extract_key_only"
    
    async def _process_single_pass(self, content: str, source_type: str) -> Dict[str, Any]:
        """Process entire content in a single pass (for capable models)."""
        
        # Truncate to optimal size if needed
        if len(content) > self.capabilities.optimal_chunk_size:
            content = content[:self.capabilities.optimal_chunk_size]
            logger.info(f"Truncated to {self.capabilities.optimal_chunk_size} chars for single pass")
        
        prompt = self._create_comprehensive_prompt(content, source_type)
        response = await self.llm_processor.process_raw_prompt(prompt)
        
        try:
            result = json.loads(response)
            return self._format_for_mcp(result, source_type)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON response in single pass")
            return self._create_empty_mcp_structure(source_type)
    
    async def _process_multi_chunk(self, content: str, source_type: str) -> Dict[str, Any]:
        """Process content in multiple chunks and merge results."""
        
        chunk_size = self.capabilities.optimal_chunk_size
        chunks = self._create_smart_chunks(content, chunk_size)
        
        all_results = []
        for i, chunk in enumerate(chunks):
            logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            prompt = self._create_chunk_prompt(chunk, i, len(chunks), source_type)
            response = await self.llm_processor.process_raw_prompt(prompt)
            
            try:
                result = json.loads(response)
                all_results.append(result)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse chunk {i+1}")
                continue
        
        merged = self._merge_chunk_results(all_results)
        return self._format_for_mcp(merged, source_type)
    
    async def _process_summary_first(self, content: str, source_type: str) -> Dict[str, Any]:
        """First summarize content, then extract practices from summary."""
        
        # Step 1: Create summary
        summary_prompt = f"""Summarize the key AI/ML practices and insights from this {source_type} content.
Focus on actionable information about models, services, and techniques.

Content (first {self.capabilities.optimal_chunk_size // 2} chars):
{content[:self.capabilities.optimal_chunk_size // 2]}

Provide a structured summary focusing on:
1. Models/services mentioned
2. Key techniques
3. Important parameters
4. Best practices

Keep the summary under {self.capabilities.optimal_chunk_size // 4} characters."""
        
        summary = await self.llm_processor.process_raw_prompt(summary_prompt)
        
        # Step 2: Extract structured data from summary
        extraction_prompt = self._create_extraction_from_summary_prompt(summary, source_type)
        response = await self.llm_processor.process_raw_prompt(extraction_prompt)
        
        try:
            result = json.loads(response)
            return self._format_for_mcp(result, source_type)
        except json.JSONDecodeError:
            return self._create_empty_mcp_structure(source_type)
    
    async def _process_extract_key_only(self, content: str, source_type: str) -> Dict[str, Any]:
        """Extract only the most important information (for small models)."""
        
        # Take the most relevant portion
        relevant_content = self._extract_most_relevant_section(content)
        
        # Use simplified prompt for small models
        prompt = f"""Extract AI/ML information from this text.

Text: {relevant_content[:self.capabilities.optimal_chunk_size]}

Return JSON with:
- models: [list of AI models mentioned]
- services: [list of AI services mentioned]  
- tips: [list of 3-5 key tips or practices]

Keep it simple and concise."""
        
        response = await self.llm_processor.process_raw_prompt(prompt)
        
        try:
            result = json.loads(response)
            # Expand the simple result into full MCP structure
            expanded = {
                "models": result.get("models", []),
                "services": result.get("services", []),
                "practices": [
                    {"type": "tip", "content": tip, "confidence": 0.6}
                    for tip in result.get("tips", [])
                ]
            }
            return self._format_for_mcp(expanded, source_type)
        except json.JSONDecodeError:
            return self._create_empty_mcp_structure(source_type)
    
    def _create_smart_chunks(self, content: str, chunk_size: int) -> List[str]:
        """Create intelligent chunks that preserve context."""
        
        if len(content) <= chunk_size:
            return [content]
        
        chunks = []
        # Look for natural break points
        sentences = re.split(r'(?<=[.!?])\s+', content)
        
        current_chunk = []
        current_size = 0
        
        for sentence in sentences:
            sentence_size = len(sentence)
            
            if current_size + sentence_size > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                # Keep last sentence for context
                current_chunk = [current_chunk[-1]] if len(current_chunk) > 1 else []
                current_size = len(current_chunk[0]) if current_chunk else 0
            
            current_chunk.append(sentence)
            current_size += sentence_size
        
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks
    
    def _extract_most_relevant_section(self, content: str) -> str:
        """Extract the most relevant section for processing."""
        
        # Priority patterns to look for
        priority_patterns = [
            r'best practice[s]?.*?(?:\n\n|\Z)',
            r'tip[s]?\s*:.*?(?:\n\n|\Z)',
            r'recommend.*?(?:\n\n|\Z)',
            r'parameter[s]?.*?(?:\n\n|\Z)',
            r'prompt.*?(?:\n\n|\Z)',
        ]
        
        for pattern in priority_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.DOTALL)
            if matches:
                return ' '.join(matches[:3])  # Return up to 3 matching sections
        
        # Fallback to beginning of content
        return content
    
    def _create_comprehensive_prompt(self, content: str, source_type: str) -> str:
        """Create a comprehensive extraction prompt for capable models."""
        
        if self.capabilities.supports_json_mode:
            json_instruction = "You MUST respond with valid JSON only."
        else:
            json_instruction = "Respond with JSON format. Start with { and end with }."
        
        return f"""Analyze this {source_type} content and extract AI/ML service best practices.

Content:
{content}

Extract and structure the following information:
1. AI models and services mentioned (be specific about versions)
2. Best practices for each model/service
3. Parameters and configurations
4. Common pitfalls and how to avoid them
5. Tips and techniques

{json_instruction}

Structure:
{{
  "services": [
    {{
      "name": "service or model name",
      "type": "llm|video|image|audio|agent",
      "practices": [
        {{
          "type": "prompting|parameter|pitfall|tip",
          "content": "specific practice description",
          "confidence": 0.0-1.0,
          "example": "optional code/prompt example"
        }}
      ],
      "parameters": {{"param": "value"}},
      "metadata": {{
        "mentions": 1,
        "context_quality": "high|medium|low"
      }}
    }}
  ],
  "general_insights": ["insight1", "insight2"],
  "quality_score": 0.0-1.0
}}"""
    
    def _create_chunk_prompt(self, chunk: str, index: int, total: int, source_type: str) -> str:
        """Create prompt for processing a chunk."""
        
        return f"""Analyze chunk {index + 1}/{total} of {source_type} content.

Chunk content:
{chunk}

Extract AI/ML services and practices mentioned in this chunk.

Return JSON:
{{
  "services": ["service1", "service2"],
  "practices": [
    {{
      "service": "which service this applies to",
      "type": "prompting|parameter|tip",
      "content": "practice description"
    }}
  ]
}}

Be concise and specific."""
    
    def _create_extraction_from_summary_prompt(self, summary: str, source_type: str) -> str:
        """Create prompt to extract structured data from summary."""
        
        return f"""Convert this summary into structured JSON format.

Summary:
{summary}

Create JSON with:
{{
  "services": [
    {{
      "name": "service name",
      "type": "category",
      "practices": []
    }}
  ]
}}"""
    
    def _merge_chunk_results(self, results: List[Dict]) -> Dict:
        """Merge results from multiple chunks."""
        
        merged = {
            "services": {},
            "general_insights": [],
            "quality_score": 0.0
        }
        
        for result in results:
            # Merge services
            for service in result.get("services", []):
                if isinstance(service, dict):
                    name = service.get("name", "unknown")
                    if name not in merged["services"]:
                        merged["services"][name] = service
                    else:
                        # Merge practices
                        existing = merged["services"][name]
                        existing["practices"].extend(service.get("practices", []))
                elif isinstance(service, str):
                    # Simple string mention
                    if service not in merged["services"]:
                        merged["services"][service] = {
                            "name": service,
                            "type": "unknown",
                            "practices": []
                        }
            
            # Collect insights
            merged["general_insights"].extend(result.get("general_insights", []))
        
        # Convert services dict back to list
        merged["services"] = list(merged["services"].values())
        
        # Calculate average quality score
        scores = [r.get("quality_score", 0.5) for r in results if "quality_score" in r]
        merged["quality_score"] = sum(scores) / len(scores) if scores else 0.5
        
        return merged
    
    def _format_for_mcp(self, data: Dict, source_type: str) -> Dict:
        """Format extracted data for MCP file serving."""
        
        timestamp = datetime.now().isoformat()
        
        # Structure for direct file serving via MCP
        mcp_structure = {
            "metadata": {
                "source_type": source_type,
                "processed_at": timestamp,
                "llm_model": self.capabilities.model,
                "llm_provider": self.capabilities.provider,
                "processing_strategy": "adaptive",
                "version": "2.0"
            },
            "services": data.get("services", []),
            "insights": data.get("general_insights", []),
            "quality_metrics": {
                "overall_score": data.get("quality_score", 0.0),
                "extraction_confidence": self._calculate_extraction_confidence(data),
                "service_count": len(data.get("services", [])),
                "practice_count": sum(len(s.get("practices", [])) for s in data.get("services", []))
            }
        }
        
        return mcp_structure
    
    def _create_empty_mcp_structure(self, source_type: str) -> Dict:
        """Create empty MCP structure when extraction fails."""
        
        return {
            "metadata": {
                "source_type": source_type,
                "processed_at": datetime.now().isoformat(),
                "llm_model": self.capabilities.model,
                "llm_provider": self.capabilities.provider,
                "processing_strategy": "adaptive",
                "version": "2.0",
                "error": "extraction_failed"
            },
            "services": [],
            "insights": [],
            "quality_metrics": {
                "overall_score": 0.0,
                "extraction_confidence": 0.0,
                "service_count": 0,
                "practice_count": 0
            }
        }
    
    def _calculate_extraction_confidence(self, data: Dict) -> float:
        """Calculate confidence score for the extraction."""
        
        service_count = len(data.get("services", []))
        practice_count = sum(len(s.get("practices", [])) for s in data.get("services", []))
        
        # Base confidence on amount of extracted data
        if service_count == 0:
            return 0.0
        elif service_count == 1 and practice_count < 3:
            return 0.3
        elif service_count < 3 and practice_count < 5:
            return 0.5
        elif service_count < 5 and practice_count < 10:
            return 0.7
        else:
            return 0.9