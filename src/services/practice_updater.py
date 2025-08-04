"""Service for updating model practices with scraped content."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import hashlib

from src.core.config import settings
from src.core.logging import get_logger
from src.core.models import (
    ModelBestPractices,
    ModelCategory,
    Parameter,
    Pitfall,
    PromptExample,
    ScrapedPost,
)
from src.services.model_service import ModelService

logger = get_logger(__name__)


class PracticeUpdater:
    """Updates model documentation with new practices from scrapers."""
    
    def __init__(self):
        self.model_service = ModelService()
        self.models_dir = settings.models_dir
        
    async def update_from_posts(
        self,
        posts: List[ScrapedPost],
        source_name: str
    ) -> Dict[str, Any]:
        """Update model practices from scraped posts."""
        results = {
            "models_updated": 0,
            "practices_added": 0,
            "practices_skipped": 0,
            "errors": [],
        }
        
        # Group posts by mentioned models
        model_posts = self._group_posts_by_model(posts)
        
        for model_id, model_posts_list in model_posts.items():
            try:
                updated = await self._update_model_practices(
                    model_id, 
                    model_posts_list,
                    source_name
                )
                
                if updated:
                    results["models_updated"] += 1
                    results["practices_added"] += updated["added"]
                    results["practices_skipped"] += updated["skipped"]
                    
            except Exception as e:
                logger.error(f"Error updating model {model_id}: {e}")
                results["errors"].append(f"{model_id}: {str(e)}")
        
        return results
    
    def _group_posts_by_model(
        self, 
        posts: List[ScrapedPost]
    ) -> Dict[str, List[ScrapedPost]]:
        """Group posts by the models they mention."""
        model_posts = {}
        
        # Model detection patterns
        model_patterns = {
            "gpt-4": ["gpt-4", "gpt4", "chatgpt-4"],
            "gpt-3.5": ["gpt-3.5", "gpt3.5", "chatgpt"],
            "claude": ["claude", "claude-3", "anthropic"],
            "claude-3": ["claude-3", "claude 3", "opus", "sonnet", "haiku"],
            "llama": ["llama", "llama2", "llama-2"],
            "llama-3": ["llama3", "llama-3", "llama 3"],
            "stable-diffusion": ["stable diffusion", "sd", "sdxl"],
            "midjourney": ["midjourney", "mj", "mid journey"],
            "dalle": ["dall-e", "dalle", "dall e"],
            "gemini": ["gemini", "bard", "palm"],
            "mistral": ["mistral", "mixtral"],
            "general": [],  # Catch-all for general practices
        }
        
        for post in posts:
            # Check title and content for model mentions
            text = f"{post.title} {post.content}".lower()
            
            # Also check extracted practices
            models_mentioned = set(post.extracted_practices.get("model_mentions", []))
            
            # Detect models from text
            for model_id, patterns in model_patterns.items():
                if any(pattern in text for pattern in patterns):
                    models_mentioned.add(model_id)
            
            # If no specific model mentioned, assign to general
            if not models_mentioned:
                models_mentioned.add("general")
            
            # Add post to each mentioned model
            for model_id in models_mentioned:
                if model_id not in model_posts:
                    model_posts[model_id] = []
                model_posts[model_id].append(post)
        
        return model_posts
    
    async def _update_model_practices(
        self,
        model_id: str,
        posts: List[ScrapedPost],
        source_name: str
    ) -> Optional[Dict[str, Any]]:
        """Update practices for a specific model."""
        # Determine category (simplified - in production, use better mapping)
        category = self._determine_category(model_id)
        
        # Ensure model directory exists
        model_dir = self.models_dir / category.value / model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing practices or create new
        existing = await self.model_service.get_model_practices(category, model_id)
        if not existing:
            existing = self._create_empty_practices(model_id, category)
        
        # Extract and merge new practices
        new_practices = self._extract_practices_from_posts(posts)
        
        # Merge with existing
        update_stats = self._merge_practices(existing, new_practices, source_name)
        
        # Save updated practices
        if update_stats["added"] > 0:
            await self._save_model_practices(existing, model_dir)
            logger.info(
                f"Updated {model_id}: {update_stats['added']} new practices, "
                f"{update_stats['skipped']} duplicates skipped"
            )
        
        return update_stats
    
    def _determine_category(self, model_id: str) -> ModelCategory:
        """Determine model category from ID."""
        text_models = ["gpt", "claude", "llama", "mistral", "gemini", "general"]
        image_models = ["stable-diffusion", "midjourney", "dalle", "sdxl"]
        video_models = ["runway", "pika", "stable-video"]
        audio_models = ["whisper", "elevenlabs", "bark"]
        
        model_lower = model_id.lower()
        
        if any(m in model_lower for m in text_models):
            return ModelCategory.TEXT
        elif any(m in model_lower for m in image_models):
            return ModelCategory.IMAGE
        elif any(m in model_lower for m in video_models):
            return ModelCategory.VIDEO
        elif any(m in model_lower for m in audio_models):
            return ModelCategory.AUDIO
        else:
            return ModelCategory.MULTIMODAL
    
    def _create_empty_practices(
        self, 
        model_id: str, 
        category: ModelCategory
    ) -> ModelBestPractices:
        """Create empty practices structure for new model."""
        return ModelBestPractices(
            model_id=model_id,
            model_name=model_id.replace("-", " ").title(),
            category=category,
            version="1.0.0",
            prompt_structure="",
            prompt_examples=[],
            parameters=[],
            pitfalls=[],
            tips=[],
            sources=[],
            tags=[],
            related_models=[],
            last_updated=datetime.utcnow(),
        )
    
    def _extract_practices_from_posts(
        self, 
        posts: List[ScrapedPost]
    ) -> Dict[str, Any]:
        """Extract consolidated practices from posts."""
        practices = {
            "prompts": [],
            "parameters": [],
            "tips": [],
            "pitfalls": [],
            "examples": [],
        }
        
        for post in posts:
            extracted = post.extracted_practices
            
            # Extract prompts
            for prompt in extracted.get("prompt_patterns", []):
                practices["prompts"].append({
                    "text": prompt.get("pattern", prompt) if isinstance(prompt, dict) else prompt,
                    "source_url": post.url,
                    "author": post.author,
                    "score": post.score,
                    "date": post.created_at.isoformat(),
                })
            
            # Extract parameters
            for param in extracted.get("parameter_recommendations", []):
                practices["parameters"].append({
                    "name": param.get("name", ""),
                    "value": param.get("value", ""),
                    "description": param.get("description", ""),
                    "source_url": post.url,
                    "confidence": param.get("confidence", 0.5),
                })
            
            # Extract tips
            for tip in extracted.get("tips", []):
                tip_text = tip.get("tip", tip) if isinstance(tip, dict) else tip
                practices["tips"].append({
                    "text": tip_text,
                    "source_url": post.url,
                    "upvotes": post.score,
                })
            
            # Extract pitfalls
            for mistake in extracted.get("common_mistakes", []):
                mistake_text = mistake.get("mistake", mistake) if isinstance(mistake, dict) else mistake
                practices["pitfalls"].append({
                    "text": mistake_text,
                    "source_url": post.url,
                })
            
            # Extract code examples
            for example in extracted.get("examples", []):
                practices["examples"].append({
                    "code": example.get("code", example) if isinstance(example, dict) else example,
                    "context": post.title,
                    "source_url": post.url,
                })
        
        return practices
    
    def _merge_practices(
        self,
        existing: ModelBestPractices,
        new_practices: Dict[str, Any],
        source_name: str
    ) -> Dict[str, Any]:
        """Merge new practices with existing ones."""
        stats = {"added": 0, "skipped": 0}
        
        # Track existing content hashes to avoid duplicates
        existing_hashes = self._get_existing_hashes(existing)
        
        # Merge prompt examples
        for prompt in new_practices["prompts"]:
            content_hash = self._hash_content(prompt["text"])
            if content_hash not in existing_hashes:
                example = PromptExample(
                    title=f"Example from {source_name}",
                    prompt=prompt["text"],
                    description=f"Contributed by {prompt['author']}",
                    tags=[source_name],
                    use_case="general",
                    effectiveness_score=min(prompt["score"] / 100, 1.0),
                )
                existing.prompt_examples.append(example)
                existing_hashes.add(content_hash)
                stats["added"] += 1
            else:
                stats["skipped"] += 1
        
        # Merge parameters (deduplicate by name)
        existing_params = {p.name: p for p in existing.parameters}
        for param in new_practices["parameters"]:
            param_name = param["name"]
            if param_name and param_name not in existing_params:
                parameter = Parameter(
                    name=param_name,
                    recommended_value=str(param["value"]),
                    description=param.get("description", ""),
                    value_type="float" if "." in str(param["value"]) else "integer",
                    min_value=None,
                    max_value=None,
                )
                existing.parameters.append(parameter)
                existing_params[param_name] = parameter
                stats["added"] += 1
            else:
                stats["skipped"] += 1
        
        # Merge tips (deduplicate similar content)
        for tip in new_practices["tips"]:
            content_hash = self._hash_content(tip["text"][:100])  # Hash first 100 chars
            if content_hash not in existing_hashes:
                existing.tips.append(tip["text"])
                existing_hashes.add(content_hash)
                stats["added"] += 1
            else:
                stats["skipped"] += 1
        
        # Merge pitfalls
        existing_pitfalls_texts = {p.title for p in existing.pitfalls}
        for pitfall in new_practices["pitfalls"]:
            # Create title from first sentence
            title = pitfall["text"].split(".")[0][:100]
            if title not in existing_pitfalls_texts:
                pitfall_obj = Pitfall(
                    title=title,
                    description=pitfall["text"],
                    solution="See source for details",
                    severity="medium",
                    example=None,
                )
                existing.pitfalls.append(pitfall_obj)
                existing_pitfalls_texts.add(title)
                stats["added"] += 1
            else:
                stats["skipped"] += 1
        
        # Update sources
        source_entry = {
            "name": source_name,
            "last_updated": datetime.utcnow().isoformat(),
            "posts_processed": len(new_practices["prompts"]),
        }
        
        # Update or add source
        source_updated = False
        for i, source in enumerate(existing.sources):
            if source.get("name") == source_name:
                existing.sources[i] = source_entry
                source_updated = True
                break
        
        if not source_updated:
            existing.sources.append(source_entry)
        
        # Update last_updated
        existing.last_updated = datetime.utcnow()
        
        return stats
    
    def _get_existing_hashes(self, practices: ModelBestPractices) -> Set[str]:
        """Get hashes of existing content to check for duplicates."""
        hashes = set()
        
        # Hash prompt examples
        for example in practices.prompt_examples:
            hashes.add(self._hash_content(example.prompt))
        
        # Hash tips
        for tip in practices.tips:
            hashes.add(self._hash_content(tip[:100]))
        
        # Hash pitfall titles
        for pitfall in practices.pitfalls:
            hashes.add(self._hash_content(pitfall.title))
        
        return hashes
    
    def _hash_content(self, content: str) -> str:
        """Create hash of content for deduplication."""
        # Normalize content
        normalized = content.lower().strip()
        # Remove extra whitespace
        normalized = " ".join(normalized.split())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    async def _save_model_practices(
        self, 
        practices: ModelBestPractices,
        model_dir: Path
    ) -> None:
        """Save updated practices to files."""
        # Save prompting guide
        prompting_file = model_dir / "prompting.md"
        prompting_content = self._generate_prompting_guide(practices)
        prompting_file.write_text(prompting_content)
        
        # Save parameters
        if practices.parameters:
            params_file = model_dir / "parameters.json"
            params_data = [p.model_dump() for p in practices.parameters]
            with open(params_file, "w") as f:
                json.dump(params_data, f, indent=2, default=str)
        
        # Save pitfalls
        if practices.pitfalls:
            pitfalls_file = model_dir / "pitfalls.md"
            pitfalls_content = self._generate_pitfalls_content(practices.pitfalls)
            pitfalls_file.write_text(pitfalls_content)
        
        # Save examples
        if practices.prompt_examples:
            examples_dir = model_dir / "examples"
            examples_dir.mkdir(exist_ok=True)
            
            examples_file = examples_dir / "prompts.json"
            examples_data = [e.model_dump() for e in practices.prompt_examples]
            with open(examples_file, "w") as f:
                json.dump(examples_data, f, indent=2, default=str)
        
        # Save metadata
        metadata_file = model_dir / "metadata.json"
        metadata = {
            "model_id": practices.model_id,
            "version": practices.version,
            "last_updated": practices.last_updated.isoformat(),
            "sources_count": len(practices.sources),
            "tags": practices.tags,
            "related_models": practices.related_models,
            "update_history": practices.sources,
        }
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2, default=str)
    
    def _generate_prompting_guide(self, practices: ModelBestPractices) -> str:
        """Generate prompting guide markdown."""
        content = f"# {practices.model_name} Prompting Guide\n\n"
        content += f"*Last updated: {practices.last_updated.strftime('%Y-%m-%d')}*\n\n"
        
        if practices.prompt_structure:
            content += "## Prompt Structure\n\n"
            content += practices.prompt_structure + "\n\n"
        
        if practices.tips:
            content += "## Tips and Best Practices\n\n"
            for i, tip in enumerate(practices.tips[:20], 1):  # Top 20 tips
                content += f"{i}. {tip}\n"
            content += "\n"
        
        if practices.prompt_examples:
            content += "## Example Prompts\n\n"
            for example in practices.prompt_examples[:10]:  # Top 10 examples
                content += f"### {example.title}\n\n"
                content += f"**Use case**: {example.use_case}\n\n"
                content += "```\n"
                content += example.prompt
                content += "\n```\n\n"
                if example.description:
                    content += f"*{example.description}*\n\n"
        
        return content
    
    def _generate_pitfalls_content(self, pitfalls: List[Pitfall]) -> str:
        """Generate pitfalls markdown."""
        content = "# Common Pitfalls and Mistakes\n\n"
        
        for pitfall in pitfalls:
            content += f"## {pitfall.title}\n\n"
            content += f"{pitfall.description}\n\n"
            
            if pitfall.example:
                content += f"**Example**: {pitfall.example}\n\n"
            
            content += f"**Severity**: {pitfall.severity}\n\n"
            content += f"**Solution**: {pitfall.solution}\n\n"
            content += "---\n\n"
        
        return content