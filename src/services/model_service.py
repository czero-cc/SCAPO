import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.models import (
    ModelBestPractices,
    ModelCategory,
    ModelMetadata,
    Parameter,
    Pitfall,
    PromptExample,
)
from src.utils.metrics import model_queries_counter, models_total
from src.services.cache_service import cache_service, CACHE_CONFIG
from src.core.aliases import normalize_model_name, get_all_variations

logger = get_logger(__name__)


class ModelService:
    """Service for managing model best practices."""

    def __init__(self):
        self.models_dir = settings.models_dir
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all model category directories exist."""
        for category in ModelCategory:
            category_dir = self.models_dir / category.value
            category_dir.mkdir(parents=True, exist_ok=True)

    async def list_models(
        self, category: Optional[ModelCategory] = None
    ) -> Dict[str, List[str]]:
        """List all available models, optionally filtered by category."""
        # Cache key
        cache_key = f"list:{category.value if category else 'all'}"
        
        # Try cache first
        cached = await cache_service.get("models", cache_key)
        if cached is not None:
            return cached
        
        result = {}
        
        if category:
            categories = [category]
        else:
            categories = list(ModelCategory)
        
        for cat in categories:
            category_dir = self.models_dir / cat.value
            if category_dir.exists():
                models = [
                    d.name for d in category_dir.iterdir()
                    if d.is_dir() and not d.name.startswith(".")
                ]
                result[cat.value] = sorted(models)
                models_total.labels(category=cat.value).set(len(models))
        
        # Cache the result
        await cache_service.set(
            "models", cache_key, result,
            ttl=CACHE_CONFIG["model_list"]["ttl"]
        )
        
        return result

    async def search_models(
        self, query: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for models by name, tags, or content."""
        # Cache key
        cache_key = f"query:{query}:{limit}"
        
        # Try cache first
        cached = await cache_service.get("search", cache_key)
        if cached is not None:
            return cached
        
        results = []
        query_lower = query.lower()
        
        # Also check if query is a model alias
        normalized_query = normalize_model_name(query)
        
        for category in ModelCategory:
            category_dir = self.models_dir / category.value
            if not category_dir.exists():
                continue
            
            for model_dir in category_dir.iterdir():
                if not model_dir.is_dir() or model_dir.name.startswith("."):
                    continue
                
                # Check model name and aliases
                model_name = model_dir.name
                variations = get_all_variations(model_name)
                
                # Check direct name match or alias match
                if query_lower in model_name.lower() or normalized_query == model_name:
                    results.append({
                        "model_id": model_name,
                        "category": category.value,
                        "match_type": "name",
                        "score": 1.0,
                    })
                    continue
                
                # Check if query matches any variation
                elif any(query_lower in var.lower() for var in variations):
                    results.append({
                        "model_id": model_name,
                        "category": category.value,
                        "match_type": "alias",
                        "score": 0.9,
                    })
                    continue
                
                # Check metadata and content
                metadata_file = model_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, "r") as f:
                            metadata = json.load(f)
                        
                        # Check tags
                        tags = metadata.get("tags", [])
                        if any(query_lower in tag.lower() for tag in tags):
                            results.append({
                                "model_id": model_dir.name,
                                "category": category.value,
                                "match_type": "tags",
                                "score": 0.8,
                            })
                    except Exception as e:
                        logger.error(f"Error reading metadata for {model_dir.name}: {e}")
        
        # Sort by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        final_results = results[:limit]
        
        # Cache the results
        await cache_service.set(
            "search", cache_key, final_results,
            ttl=CACHE_CONFIG["search_results"]["ttl"]
        )
        
        return final_results

    async def get_model_practices(
        self, category: ModelCategory, model_id: str
    ) -> Optional[ModelBestPractices]:
        """Get complete best practices for a model."""
        # Handle both string and enum
        if isinstance(category, str):
            category = ModelCategory(category)
        
        # Normalize model name using aliases
        model_id = normalize_model_name(model_id)
        
        # Cache key
        cache_key = f"{category.value}/{model_id}"
        
        # Try cache first
        cached = await cache_service.get("practices", cache_key)
        if cached is not None:
            model_queries_counter.labels(model_id=model_id, query_type="all").inc()
            # Reconstruct ModelBestPractices from cached dict
            return ModelBestPractices(**cached)
        
        model_dir = self.models_dir / category.value / model_id
        
        if not model_dir.exists():
            return None
        
        model_queries_counter.labels(model_id=model_id, query_type="all").inc()
        
        try:
            # Load individual files
            practices_data = {
                "model_id": model_id,
                "model_name": model_id.replace("-", " ").title(),
                "category": category,
                "version": "1.0.0",
            }
            
            # Load prompting
            prompting_file = model_dir / "prompting.md"
            if prompting_file.exists():
                practices_data["prompt_structure"] = prompting_file.read_text()
            
            # Load prompt examples
            examples_file = model_dir / "examples" / "prompts.json"
            if examples_file.exists():
                with open(examples_file, "r") as f:
                    examples_data = json.load(f)
                    practices_data["prompt_examples"] = [
                        PromptExample(**ex) for ex in examples_data
                    ]
            
            # Load parameters
            params_file = model_dir / "parameters.json"
            if params_file.exists():
                with open(params_file, "r") as f:
                    params_data = json.load(f)
                    practices_data["parameters"] = [
                        Parameter(**param) for param in params_data
                    ]
            
            # Load pitfalls
            pitfalls_file = model_dir / "pitfalls.md"
            if pitfalls_file.exists():
                # Parse markdown to extract pitfalls
                pitfalls_content = pitfalls_file.read_text()
                practices_data["pitfalls"] = self._parse_pitfalls_markdown(pitfalls_content)
            
            # Load metadata
            metadata_file = model_dir / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    practices_data.update({
                        "tags": metadata.get("tags", []),
                        "related_models": metadata.get("related_models", []),
                    })
            
            practices = ModelBestPractices(**practices_data)
            
            # Cache the result
            await cache_service.set(
                "practices", cache_key,
                practices.model_dump(),
                ttl=CACHE_CONFIG["model_practices"]["ttl"]
            )
            
            return practices
            
        except Exception as e:
            logger.error(f"Error loading practices for {model_id}: {e}")
            return None

    async def get_prompting_file(
        self, category: ModelCategory, model_id: str
    ) -> Optional[Path]:
        """Get path to prompting markdown file."""
        # Handle both string and enum
        if isinstance(category, str):
            category = ModelCategory(category)
        file_path = self.models_dir / category.value / model_id / "prompting.md"
        if file_path.exists():
            model_queries_counter.labels(model_id=model_id, query_type="prompting").inc()
            return file_path
        return None

    async def get_model_metadata(
        self, category: ModelCategory, model_id: str
    ) -> Optional[ModelMetadata]:
        """Get metadata for a model."""
        # Handle both string and enum
        if isinstance(category, str):
            category = ModelCategory(category)
        metadata_file = self.models_dir / category.value / model_id / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, "r") as f:
                data = json.load(f)
            
            return ModelMetadata(
                model_id=model_id,
                version=data.get("version", "1.0.0"),
                last_updated=data.get("last_updated"),
                update_frequency_hours=data.get("update_frequency_hours", 24),
                sources_count=data.get("sources_count", 0),
                confidence_score=data.get("confidence_score", 0.8),
                change_log=data.get("change_log", []),
            )
        except Exception as e:
            logger.error(f"Error loading metadata for {model_id}: {e}")
            return None

    async def save_model_practices(
        self, practices: ModelBestPractices
    ) -> bool:
        """Save model best practices to files."""
        model_dir = self.models_dir / practices.category.value / practices.model_id
        model_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save prompting guide
            prompting_file = model_dir / "prompting.md"
            prompting_file.write_text(practices.prompt_structure)
            
            # Save prompt examples
            examples_dir = model_dir / "examples"
            examples_dir.mkdir(exist_ok=True)
            examples_file = examples_dir / "prompts.json"
            with open(examples_file, "w") as f:
                json.dump(
                    [ex.model_dump() for ex in practices.prompt_examples],
                    f,
                    indent=2,
                    default=str,
                )
            
            # Save parameters
            params_file = model_dir / "parameters.json"
            with open(params_file, "w") as f:
                json.dump(
                    [param.model_dump() for param in practices.parameters],
                    f,
                    indent=2,
                    default=str,
                )
            
            # Save pitfalls
            pitfalls_file = model_dir / "pitfalls.md"
            pitfalls_content = self._generate_pitfalls_markdown(practices.pitfalls)
            pitfalls_file.write_text(pitfalls_content)
            
            # Save metadata
            metadata_file = model_dir / "metadata.json"
            metadata = {
                "model_id": practices.model_id,
                "version": practices.version,
                "last_updated": practices.last_updated.isoformat(),
                "tags": practices.tags,
                "related_models": practices.related_models,
                "sources_count": len(practices.sources),
                "confidence_score": self._calculate_confidence_score(practices),
            }
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2, default=str)
            
            logger.info(f"Saved practices for {practices.model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving practices for {practices.model_id}: {e}")
            return False

    def _parse_pitfalls_markdown(self, content: str) -> List[Pitfall]:
        """Parse pitfalls from markdown content."""
        # Simple parser - in production, use a proper markdown parser
        pitfalls = []
        lines = content.split("\n")
        
        current_pitfall = None
        for line in lines:
            if line.startswith("## "):
                if current_pitfall:
                    pitfalls.append(Pitfall(**current_pitfall))
                current_pitfall = {
                    "title": line[3:].strip(),
                    "description": "",
                    "solution": "",
                    "severity": "medium",
                }
            elif current_pitfall and line.startswith("**Severity:**"):
                current_pitfall["severity"] = line.split(":", 1)[1].strip().lower()
            elif current_pitfall and line.startswith("**Solution:**"):
                current_pitfall["solution"] = line.split(":", 1)[1].strip()
            elif current_pitfall and line.strip():
                current_pitfall["description"] += line + " "
        
        if current_pitfall:
            pitfalls.append(Pitfall(**current_pitfall))
        
        return pitfalls

    def _generate_pitfalls_markdown(self, pitfalls: List[Pitfall]) -> str:
        """Generate markdown content from pitfalls."""
        content = "# Common Pitfalls\n\n"
        
        for pitfall in pitfalls:
            content += f"## {pitfall.title}\n\n"
            content += f"{pitfall.description}\n\n"
            if pitfall.example:
                content += f"**Example:** {pitfall.example}\n\n"
            content += f"**Severity:** {pitfall.severity}\n\n"
            content += f"**Solution:** {pitfall.solution}\n\n"
            content += "---\n\n"
        
        return content

    def _calculate_confidence_score(self, practices: ModelBestPractices) -> float:
        """Calculate confidence score based on completeness and sources."""
        score = 0.0
        
        # Check completeness
        if practices.prompt_structure:
            score += 0.2
        if practices.prompt_examples:
            score += 0.2
        if practices.parameters:
            score += 0.2
        if practices.pitfalls:
            score += 0.2
        if len(practices.sources) >= 3:
            score += 0.2
        
        return min(score, 1.0)