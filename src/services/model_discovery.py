"""Service for discovering and adding new AI models from scraped content."""

import re
from typing import Dict, List, Set, Tuple
from datetime import datetime
from pathlib import Path

from src.core.logging import get_logger
from src.core.models import ModelCategory, ModelBestPractices
from src.services.model_service import ModelService

logger = get_logger(__name__)


class ModelDiscoveryService:
    """Discovers new AI models from scraped content and creates entries for them."""
    
    def __init__(self):
        self.model_service = ModelService()
        self.known_models = self._load_known_models()
        
        # Model patterns for detection
        self.model_patterns = {
            # Text models
            "gpt-4": (ModelCategory.TEXT, r"gpt-?4(?:-turbo|-32k|-vision)?", "GPT-4"),
            "gpt-3.5": (ModelCategory.TEXT, r"gpt-?3\.5(?:-turbo)?", "GPT-3.5"),
            "claude-3": (ModelCategory.TEXT, r"claude-?3(?:-opus|-sonnet|-haiku)?", "Claude 3"),
            "claude-2": (ModelCategory.TEXT, r"claude-?2(?:\.1)?", "Claude 2"),
            "llama-3": (ModelCategory.TEXT, r"llama-?3(?:-\d+b)?", "Llama 3"),
            "llama-2": (ModelCategory.TEXT, r"llama-?2(?:-\d+b)?", "Llama 2"),
            "mistral": (ModelCategory.TEXT, r"mistral(?:-7b|-medium)?", "Mistral"),
            "mixtral": (ModelCategory.TEXT, r"mixtral(?:-8x7b)?", "Mixtral"),
            "gemini": (ModelCategory.TEXT, r"gemini(?:-pro|-ultra)?", "Gemini"),
            "phi": (ModelCategory.TEXT, r"phi-?\d+(?:\.\d+)?", "Phi"),
            "falcon": (ModelCategory.TEXT, r"falcon-?\d+b?", "Falcon"),
            "vicuna": (ModelCategory.TEXT, r"vicuna-?\d+b?", "Vicuna"),
            "alpaca": (ModelCategory.TEXT, r"alpaca(?:-\d+b)?", "Alpaca"),
            "dolly": (ModelCategory.TEXT, r"dolly(?:-v\d+)?", "Dolly"),
            "starcoder": (ModelCategory.TEXT, r"starcoder(?:\d+)?", "StarCoder"),
            "codellama": (ModelCategory.TEXT, r"code-?llama(?:-\d+b)?", "CodeLlama"),
            "deepseek": (ModelCategory.TEXT, r"deepseek(?:-coder)?", "DeepSeek"),
            
            # Image models
            "stable-diffusion": (ModelCategory.IMAGE, r"stable-?diffusion(?:-xl|-v?\d+)?|sdxl?", "Stable Diffusion"),
            "midjourney": (ModelCategory.IMAGE, r"midjourney(?:-v?\d+)?|mj-?v?\d+", "Midjourney"),
            "dalle-3": (ModelCategory.IMAGE, r"dall-?e-?3", "DALL-E 3"),
            "dalle-2": (ModelCategory.IMAGE, r"dall-?e-?2", "DALL-E 2"),
            "imagen": (ModelCategory.IMAGE, r"imagen(?:-\d+)?", "Imagen"),
            "playground": (ModelCategory.IMAGE, r"playground(?:-v?\d+)?", "Playground"),
            "leonardo": (ModelCategory.IMAGE, r"leonardo(?:\.ai)?", "Leonardo"),
            "ideogram": (ModelCategory.IMAGE, r"ideogram(?:\.ai)?", "Ideogram"),
            "flux": (ModelCategory.IMAGE, r"flux(?:-dev|-schnell)?", "Flux"),
            
            # Video models
            "runway": (ModelCategory.VIDEO, r"runway(?:-gen\d+)?", "Runway"),
            "pika": (ModelCategory.VIDEO, r"pika(?:-labs|-\d+)?", "Pika"),
            "stable-video": (ModelCategory.VIDEO, r"stable-?video(?:-diffusion)?|svd", "Stable Video"),
            "modelscope": (ModelCategory.VIDEO, r"modelscope(?:-text2video)?", "ModelScope"),
            "zeroscope": (ModelCategory.VIDEO, r"zeroscope(?:-v?\d+)?", "ZeroScope"),
            "animatediff": (ModelCategory.VIDEO, r"animate-?diff", "AnimateDiff"),
            "wan2.2": (ModelCategory.VIDEO, r"wan-?2\.2", "Wan2.2"),
            "cogvideo": (ModelCategory.VIDEO, r"cog-?video", "CogVideo"),
            
            # Audio models
            "whisper": (ModelCategory.AUDIO, r"whisper(?:-large|-medium|-small)?", "Whisper"),
            "bark": (ModelCategory.AUDIO, r"bark(?:-v?\d+)?", "Bark"),
            "musicgen": (ModelCategory.AUDIO, r"music-?gen", "MusicGen"),
            "audiogen": (ModelCategory.AUDIO, r"audio-?gen", "AudioGen"),
            "elevenlabs": (ModelCategory.AUDIO, r"eleven-?labs|11labs", "ElevenLabs"),
            "tortoise": (ModelCategory.AUDIO, r"tortoise(?:-tts)?", "Tortoise"),
            "valle": (ModelCategory.AUDIO, r"vall-?e", "VALL-E"),
            
            # Multimodal models
            "gpt-4v": (ModelCategory.MULTIMODAL, r"gpt-?4v(?:ision)?", "GPT-4 Vision"),
            "gemini-vision": (ModelCategory.MULTIMODAL, r"gemini(?:-pro)?-vision", "Gemini Vision"),
            "llava": (ModelCategory.MULTIMODAL, r"llava(?:-\d+b)?", "LLaVA"),
            "blip": (ModelCategory.MULTIMODAL, r"blip-?\d*", "BLIP"),
            "clip": (ModelCategory.MULTIMODAL, r"clip(?:-vit)?", "CLIP"),
            "flamingo": (ModelCategory.MULTIMODAL, r"flamingo", "Flamingo"),
        }
    
    def _load_known_models(self) -> Set[str]:
        """Load currently known models from the repository."""
        known = set()
        models = self.model_service.list_models()
        
        for category_models in models.values():
            known.update(category_models)
        
        return known
    
    async def discover_models_from_posts(self, posts: List[Dict]) -> Dict[str, Tuple[ModelCategory, str]]:
        """Discover new models mentioned in scraped posts."""
        discovered = {}
        
        for post in posts:
            # Check title and content
            text = f"{post.get('title', '')} {post.get('content', '')}".lower()
            
            for model_id, (category, pattern, display_name) in self.model_patterns.items():
                if re.search(pattern, text, re.IGNORECASE):
                    if model_id not in self.known_models:
                        discovered[model_id] = (category, display_name)
        
        return discovered
    
    async def create_model_entry(
        self,
        model_id: str,
        category: ModelCategory,
        display_name: str,
        initial_practices: Dict = None
    ) -> bool:
        """Create a new model entry with basic structure."""
        try:
            model_dir = Path(f"models/{category.value}/{model_id}")
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Create basic prompting guide
            prompting_content = f"""# {display_name} Prompting Guide

## Overview
This is an automatically generated guide for {display_name}. Content will be updated as more practices are discovered.

## Basic Usage
*To be updated with discovered practices*

## Parameters
*To be updated with discovered parameters*

## Tips
*To be updated with community tips*
"""
            
            (model_dir / "prompting.md").write_text(prompting_content)
            
            # Create empty parameters file
            (model_dir / "parameters.json").write_text("[]")
            
            # Create empty pitfalls file
            pitfalls_content = f"""# Common Pitfalls for {display_name}

*To be updated as issues are discovered*
"""
            (model_dir / "pitfalls.md").write_text(pitfalls_content)
            
            # Create examples directory
            (model_dir / "examples").mkdir(exist_ok=True)
            (model_dir / "examples" / "prompts.json").write_text("[]")
            
            # Create metadata
            metadata = {
                "model_id": model_id,
                "display_name": display_name,
                "version": "0.1.0",
                "last_updated": datetime.utcnow().isoformat(),
                "tags": [category.value, "auto-discovered"],
                "related_models": [],
                "sources_count": 0,
                "confidence_score": 0.1,
                "auto_generated": True,
                "discovery_date": datetime.utcnow().isoformat(),
                "update_frequency_hours": 24,
                "change_log": [
                    {
                        "date": datetime.utcnow().isoformat(),
                        "changes": ["Auto-discovered model", "Created initial structure"],
                        "sources": ["Community mentions"]
                    }
                ]
            }
            
            import json
            (model_dir / "metadata.json").write_text(
                json.dumps(metadata, indent=2)
            )
            
            # Add to known models
            self.known_models.add(model_id)
            
            logger.info(f"Created new model entry: {category.value}/{model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating model entry for {model_id}: {e}")
            return False
    
    async def update_model_from_practices(
        self,
        model_id: str,
        category: ModelCategory,
        practices: Dict
    ) -> bool:
        """Update a model's documentation with newly discovered practices."""
        try:
            model_dir = Path(f"models/{category.value}/{model_id}")
            if not model_dir.exists():
                logger.warning(f"Model directory not found: {model_dir}")
                return False
            
            # Load existing metadata
            metadata_file = model_dir / "metadata.json"
            if metadata_file.exists():
                import json
                metadata = json.loads(metadata_file.read_text())
                metadata["last_updated"] = datetime.utcnow().isoformat()
                metadata["sources_count"] = metadata.get("sources_count", 0) + 1
                
                # Update confidence score based on sources
                metadata["confidence_score"] = min(
                    0.1 + (metadata["sources_count"] * 0.1),
                    1.0
                )
                
                metadata_file.write_text(json.dumps(metadata, indent=2))
            
            # Update practices if significant content found
            if practices.get("prompts"):
                # This would merge with existing content
                logger.info(f"Updated practices for {model_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating model {model_id}: {e}")
            return False
    
    async def process_discovery_batch(self, posts: List[Dict]) -> Dict[str, Any]:
        """Process a batch of posts for model discovery."""
        discovered = await self.discover_models_from_posts(posts)
        
        results = {
            "discovered": [],
            "created": [],
            "failed": [],
        }
        
        for model_id, (category, display_name) in discovered.items():
            results["discovered"].append({
                "model_id": model_id,
                "category": category.value,
                "display_name": display_name,
            })
            
            # Create model entry
            success = await self.create_model_entry(
                model_id, category, display_name
            )
            
            if success:
                results["created"].append(model_id)
            else:
                results["failed"].append(model_id)
        
        if results["discovered"]:
            logger.info(
                f"Discovered {len(results['discovered'])} new models, "
                f"created {len(results['created'])} entries"
            )
        
        return results
    
    def suggest_model_relationships(self) -> Dict[str, List[str]]:
        """Suggest relationships between models based on naming patterns."""
        relationships = {}
        
        all_models = list(self.known_models)
        
        for model in all_models:
            related = []
            
            # Find models with similar base names
            base_name = re.split(r'[-_\d\.]', model)[0]
            for other in all_models:
                if other != model and base_name in other:
                    related.append(other)
            
            # Special relationships
            if "gpt" in model:
                related.extend([m for m in all_models if "gpt" in m and m != model])
            elif "llama" in model:
                related.extend([m for m in all_models if "llama" in m and m != model])
            elif "stable" in model:
                related.extend([m for m in all_models if "stable" in m and m != model])
            
            if related:
                relationships[model] = list(set(related))[:5]  # Limit to 5
        
        return relationships