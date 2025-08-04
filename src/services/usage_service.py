"""Service for managing model usage patterns and recommendations."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from src.core.config import settings
from src.core.logging import get_logger
from src.core.models import ModelCategory, ModelBestPractices
from src.services.model_service import ModelService

logger = get_logger(__name__)


class UsageService:
    """Service for querying models by usage patterns."""
    
    # Common usage patterns and their keywords
    USAGE_PATTERNS = {
        # Text generation use cases
        "code_generation": {
            "keywords": ["code", "programming", "coding", "function", "algorithm", "debug"],
            "categories": [ModelCategory.TEXT],
            "preferred_models": ["gpt-4", "codellama", "starcoder", "deepseek"],
        },
        "creative_writing": {
            "keywords": ["story", "creative", "fiction", "narrative", "poem", "novel"],
            "categories": [ModelCategory.TEXT],
            "preferred_models": ["gpt-4", "claude-3", "llama-3"],
        },
        "chat_conversation": {
            "keywords": ["chat", "conversation", "dialogue", "assistant", "help"],
            "categories": [ModelCategory.TEXT],
            "preferred_models": ["gpt-4", "claude-3", "llama-3", "mistral"],
        },
        "summarization": {
            "keywords": ["summary", "summarize", "tldr", "brief", "overview"],
            "categories": [ModelCategory.TEXT],
            "preferred_models": ["gpt-4", "claude-3", "llama-3"],
        },
        "translation": {
            "keywords": ["translate", "translation", "language", "multilingual"],
            "categories": [ModelCategory.TEXT],
            "preferred_models": ["gpt-4", "claude-3", "gemini"],
        },
        "question_answering": {
            "keywords": ["qa", "question", "answer", "faq", "knowledge"],
            "categories": [ModelCategory.TEXT],
            "preferred_models": ["gpt-4", "claude-3", "llama-3"],
        },
        
        # Image generation use cases
        "image_generation": {
            "keywords": ["image", "picture", "art", "illustration", "draw"],
            "categories": [ModelCategory.IMAGE],
            "preferred_models": ["stable-diffusion", "midjourney", "dalle-3"],
        },
        "photo_realistic": {
            "keywords": ["photorealistic", "realistic", "photo", "photography"],
            "categories": [ModelCategory.IMAGE],
            "preferred_models": ["stable-diffusion", "midjourney", "dalle-3"],
        },
        "artistic_style": {
            "keywords": ["artistic", "style", "painting", "abstract", "stylized"],
            "categories": [ModelCategory.IMAGE],
            "preferred_models": ["midjourney", "stable-diffusion", "dalle-3"],
        },
        "logo_design": {
            "keywords": ["logo", "brand", "icon", "design", "vector"],
            "categories": [ModelCategory.IMAGE],
            "preferred_models": ["midjourney", "dalle-3", "ideogram"],
        },
        
        # Video generation use cases
        "video_generation": {
            "keywords": ["video", "animation", "motion", "animate", "clip"],
            "categories": [ModelCategory.VIDEO],
            "preferred_models": ["runway", "pika", "stable-video"],
        },
        "video_editing": {
            "keywords": ["edit", "cut", "transition", "effects", "post-production"],
            "categories": [ModelCategory.VIDEO],
            "preferred_models": ["runway", "pika"],
        },
        
        # Audio use cases
        "speech_to_text": {
            "keywords": ["transcribe", "speech", "stt", "voice", "dictation"],
            "categories": [ModelCategory.AUDIO],
            "preferred_models": ["whisper"],
        },
        "text_to_speech": {
            "keywords": ["tts", "voice", "speak", "narration", "audio"],
            "categories": [ModelCategory.AUDIO],
            "preferred_models": ["elevenlabs", "bark", "tortoise"],
        },
        "music_generation": {
            "keywords": ["music", "melody", "song", "compose", "beat"],
            "categories": [ModelCategory.AUDIO],
            "preferred_models": ["musicgen", "audiogen"],
        },
        
        # Multimodal use cases
        "image_understanding": {
            "keywords": ["analyze", "describe", "vision", "ocr", "understand image"],
            "categories": [ModelCategory.MULTIMODAL],
            "preferred_models": ["gpt-4v", "claude-3", "llava", "gemini-vision"],
        },
        "visual_qa": {
            "keywords": ["visual question", "image qa", "picture question"],
            "categories": [ModelCategory.MULTIMODAL],
            "preferred_models": ["gpt-4v", "llava", "blip"],
        },
    }
    
    # Model capability mappings
    MODEL_CAPABILITIES = {
        # Text models
        "gpt-4": ["code_generation", "creative_writing", "chat_conversation", "summarization", "translation", "question_answering"],
        "claude-3": ["code_generation", "creative_writing", "chat_conversation", "summarization", "translation", "question_answering"],
        "llama-3": ["chat_conversation", "creative_writing", "summarization", "question_answering"],
        "codellama": ["code_generation"],
        "starcoder": ["code_generation"],
        "deepseek": ["code_generation"],
        "mistral": ["chat_conversation", "creative_writing"],
        "gemini": ["translation", "chat_conversation", "summarization"],
        
        # Image models
        "stable-diffusion": ["image_generation", "photo_realistic", "artistic_style"],
        "midjourney": ["image_generation", "photo_realistic", "artistic_style", "logo_design"],
        "dalle-3": ["image_generation", "photo_realistic", "artistic_style", "logo_design"],
        "ideogram": ["logo_design", "image_generation"],
        
        # Video models
        "runway": ["video_generation", "video_editing"],
        "pika": ["video_generation", "video_editing"],
        "stable-video": ["video_generation"],
        
        # Audio models
        "whisper": ["speech_to_text"],
        "elevenlabs": ["text_to_speech"],
        "bark": ["text_to_speech"],
        "musicgen": ["music_generation"],
        
        # Multimodal models
        "gpt-4v": ["image_understanding", "visual_qa"],
        "claude-3-vision": ["image_understanding", "visual_qa"],
        "llava": ["image_understanding", "visual_qa"],
        "gemini-vision": ["image_understanding", "visual_qa"],
    }
    
    def __init__(self):
        self.model_service = ModelService()
        self._usage_index = self._build_usage_index()
    
    def _build_usage_index(self) -> Dict[str, Set[str]]:
        """Build reverse index from usage to models."""
        usage_index = defaultdict(set)
        
        for model, capabilities in self.MODEL_CAPABILITIES.items():
            for capability in capabilities:
                usage_index[capability].add(model)
        
        return dict(usage_index)
    
    async def search_models_by_usage(
        self,
        usage: str,
        limit: int = 10,
        min_confidence: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for models optimized for a specific usage pattern."""
        usage_lower = usage.lower()
        results = []
        
        # Direct usage pattern match
        matched_pattern = None
        for pattern_name, pattern_info in self.USAGE_PATTERNS.items():
            if pattern_name == usage_lower or any(
                keyword in usage_lower for keyword in pattern_info["keywords"]
            ):
                matched_pattern = pattern_name
                break
        
        if matched_pattern:
            # Get models for this usage pattern
            pattern_info = self.USAGE_PATTERNS[matched_pattern]
            
            # Get all models in relevant categories
            all_models = await self.model_service.list_models()
            
            for category in pattern_info["categories"]:
                category_models = all_models.get(category.value, [])
                
                for model_id in category_models:
                    # Calculate relevance score
                    score = await self._calculate_usage_relevance(
                        model_id, category, matched_pattern, usage_lower
                    )
                    
                    if score >= min_confidence:
                        # Get model practices to check if it has relevant examples
                        practices = await self.model_service.get_model_practices(
                            category, model_id
                        )
                        
                        if practices:
                            # Check if model has examples for this usage
                            has_relevant_examples = self._has_relevant_examples(
                                practices, usage_lower
                            )
                            
                            results.append({
                                "model_id": model_id,
                                "category": category.value,
                                "usage_pattern": matched_pattern,
                                "relevance_score": score,
                                "confidence_score": practices.confidence_score if hasattr(practices, 'confidence_score') else 0.8,
                                "has_examples": has_relevant_examples,
                                "preferred": model_id in pattern_info.get("preferred_models", []),
                                "capabilities": self.MODEL_CAPABILITIES.get(model_id, []),
                            })
        else:
            # Fuzzy search through all models
            all_models = await self.model_service.list_models()
            
            for category_name, model_list in all_models.items():
                category = ModelCategory(category_name)
                
                for model_id in model_list:
                    practices = await self.model_service.get_model_practices(
                        category, model_id
                    )
                    
                    if practices:
                        # Search in prompt examples and tips
                        relevance = self._calculate_content_relevance(
                            practices, usage_lower
                        )
                        
                        if relevance > 0:
                            results.append({
                                "model_id": model_id,
                                "category": category_name,
                                "usage_pattern": "custom",
                                "relevance_score": relevance,
                                "confidence_score": practices.confidence_score if hasattr(practices, 'confidence_score') else 0.8,
                                "has_examples": True,
                                "preferred": False,
                                "capabilities": self.MODEL_CAPABILITIES.get(model_id, []),
                            })
        
        # Sort by relevance and preferred status
        results.sort(
            key=lambda x: (x["preferred"], x["relevance_score"], x["confidence_score"]),
            reverse=True
        )
        
        return results[:limit]
    
    async def get_recommended_models(
        self,
        usage: str,
        category: Optional[ModelCategory] = None
    ) -> List[Dict[str, Any]]:
        """Get top recommended models for a usage pattern."""
        results = await self.search_models_by_usage(usage, limit=5)
        
        if category:
            results = [r for r in results if r["category"] == category.value]
        
        # Enhance with specific recommendations
        enhanced_results = []
        for result in results:
            model_id = result["model_id"]
            category_enum = ModelCategory(result["category"])
            
            practices = await self.model_service.get_model_practices(
                category_enum, model_id
            )
            
            if practices:
                # Find best parameters for this usage
                usage_params = self._get_usage_specific_params(
                    practices, usage
                )
                
                # Find relevant examples
                relevant_examples = self._get_relevant_examples(
                    practices, usage
                )
                
                result["recommended_params"] = usage_params
                result["example_prompts"] = relevant_examples[:2]  # Top 2 examples
                
            enhanced_results.append(result)
        
        return enhanced_results
    
    async def get_usage_patterns(self) -> Dict[str, Any]:
        """Get all available usage patterns with descriptions."""
        patterns = {}
        
        for pattern_name, pattern_info in self.USAGE_PATTERNS.items():
            patterns[pattern_name] = {
                "name": pattern_name.replace("_", " ").title(),
                "categories": [cat.value for cat in pattern_info["categories"]],
                "keywords": pattern_info["keywords"],
                "model_count": len(pattern_info.get("preferred_models", [])),
                "description": self._generate_pattern_description(pattern_name),
            }
        
        return patterns
    
    async def get_model_usages(
        self,
        model_id: str,
        category: ModelCategory
    ) -> List[str]:
        """Get all usage patterns a model is good for."""
        # Check MODEL_CAPABILITIES first
        if model_id in self.MODEL_CAPABILITIES:
            return self.MODEL_CAPABILITIES[model_id]
        
        # Infer from practices
        practices = await self.model_service.get_model_practices(
            category, model_id
        )
        
        if not practices:
            return []
        
        usages = []
        
        # Check which usage patterns match this model's content
        for pattern_name, pattern_info in self.USAGE_PATTERNS.items():
            if category in pattern_info["categories"]:
                # Check if model has relevant examples or content
                relevance = self._calculate_content_relevance(
                    practices, " ".join(pattern_info["keywords"])
                )
                
                if relevance > 0.3:  # Threshold for inclusion
                    usages.append(pattern_name)
        
        return usages
    
    def _calculate_usage_relevance(
        self,
        model_id: str,
        category: ModelCategory,
        usage_pattern: str,
        query: str
    ) -> float:
        """Calculate relevance score for a model and usage pattern."""
        score = 0.0
        
        # Base score from category match
        pattern_info = self.USAGE_PATTERNS.get(usage_pattern, {})
        if category in pattern_info.get("categories", []):
            score += 0.3
        
        # Preferred model bonus
        if model_id in pattern_info.get("preferred_models", []):
            score += 0.4
        
        # Capability match bonus
        if usage_pattern in self.MODEL_CAPABILITIES.get(model_id, []):
            score += 0.3
        
        return min(score, 1.0)
    
    def _calculate_content_relevance(
        self,
        practices: ModelBestPractices,
        query: str
    ) -> float:
        """Calculate relevance based on content matching."""
        query_words = set(query.lower().split())
        score = 0.0
        matches = 0
        
        # Check prompt examples
        for example in practices.prompt_examples:
            example_text = f"{example.prompt} {example.explanation}".lower()
            if any(word in example_text for word in query_words):
                matches += 1
        
        if practices.prompt_examples:
            score += (matches / len(practices.prompt_examples)) * 0.4
        
        # Check tips
        tips_text = " ".join(practices.prompt_tips).lower()
        if any(word in tips_text for word in query_words):
            score += 0.2
        
        # Check tags
        if any(word in " ".join(practices.tags).lower() for word in query_words):
            score += 0.2
        
        # Check prompt structure
        if any(word in practices.prompt_structure.lower() for word in query_words):
            score += 0.2
        
        return min(score, 1.0)
    
    def _has_relevant_examples(
        self,
        practices: ModelBestPractices,
        usage: str
    ) -> bool:
        """Check if model has examples relevant to the usage."""
        usage_words = set(usage.lower().split())
        
        for example in practices.prompt_examples:
            example_text = f"{example.prompt} {example.explanation}".lower()
            if any(word in example_text for word in usage_words):
                return True
        
        # Check tags
        return any(word in " ".join(practices.tags).lower() for word in usage_words)
    
    def _get_usage_specific_params(
        self,
        practices: ModelBestPractices,
        usage: str
    ) -> Dict[str, Any]:
        """Get parameter recommendations for specific usage."""
        params = {}
        
        # Default parameters
        for param in practices.parameters:
            params[param.name] = param.recommended
        
        # Adjust based on usage pattern
        usage_lower = usage.lower()
        
        if "creative" in usage_lower or "story" in usage_lower:
            # Higher temperature for creative tasks
            if "temperature" in params:
                params["temperature"] = min(params.get("temperature", 0.7) * 1.3, 1.5)
            if "top_p" in params:
                params["top_p"] = min(params.get("top_p", 0.9) * 1.1, 0.95)
        
        elif "code" in usage_lower or "factual" in usage_lower:
            # Lower temperature for factual/code tasks
            if "temperature" in params:
                params["temperature"] = params.get("temperature", 0.7) * 0.7
            if "top_p" in params:
                params["top_p"] = params.get("top_p", 0.9) * 0.8
        
        return params
    
    def _get_relevant_examples(
        self,
        practices: ModelBestPractices,
        usage: str
    ) -> List[Dict[str, str]]:
        """Get examples relevant to the usage pattern."""
        usage_words = set(usage.lower().split())
        relevant = []
        
        for example in practices.prompt_examples:
            example_text = f"{example.prompt} {example.explanation}".lower()
            relevance = sum(1 for word in usage_words if word in example_text)
            
            if relevance > 0:
                relevant.append({
                    "prompt": example.prompt,
                    "explanation": example.explanation,
                    "relevance": relevance,
                })
        
        # Sort by relevance
        relevant.sort(key=lambda x: x["relevance"], reverse=True)
        
        # Remove relevance score from output
        return [{"prompt": r["prompt"], "explanation": r["explanation"]} for r in relevant]
    
    def _generate_pattern_description(self, pattern_name: str) -> str:
        """Generate description for a usage pattern."""
        descriptions = {
            "code_generation": "Generate, debug, and optimize code in various programming languages",
            "creative_writing": "Create stories, poems, scripts, and other creative content",
            "chat_conversation": "Engage in natural conversations and provide helpful assistance",
            "summarization": "Condense long texts into concise summaries",
            "translation": "Translate text between different languages",
            "question_answering": "Answer questions based on provided context or knowledge",
            "image_generation": "Create images from text descriptions",
            "photo_realistic": "Generate photorealistic images",
            "artistic_style": "Create artistic and stylized images",
            "logo_design": "Design logos and brand graphics",
            "video_generation": "Generate videos from text or images",
            "video_editing": "Edit and enhance video content",
            "speech_to_text": "Transcribe audio to text",
            "text_to_speech": "Convert text to natural-sounding speech",
            "music_generation": "Create music and audio compositions",
            "image_understanding": "Analyze and describe image content",
            "visual_qa": "Answer questions about images",
        }
        
        return descriptions.get(pattern_name, pattern_name.replace("_", " ").capitalize())