"""
OpenRouter Context Window Fetcher - Gets actual context limits from OpenRouter API
"""
import os
import json
import logging
import requests
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class OpenRouterContextManager:
    """Fetches and caches model context information from OpenRouter"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        self.models_url = "https://openrouter.ai/api/v1/models"
        self.cache = {}
        self.cache_time = None
        self.cache_duration = timedelta(hours=1)  # Cache for 1 hour
    
    def fetch_models(self) -> Dict[str, Dict]:
        """Fetch model information from OpenRouter API"""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            response = requests.get(self.models_url, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            models = {}
            
            for model in data.get("data", []):
                model_id = model.get("id", "")
                models[model_id] = {
                    "context_length": model.get("context_length", 4096),
                    "max_completion_tokens": model.get("max_completion_tokens"),
                    "name": model.get("name", model_id),
                    "pricing": model.get("pricing", {})
                }
            
            logger.info(f"Fetched context info for {len(models)} models from OpenRouter")
            return models
            
        except Exception as e:
            logger.error(f"Failed to fetch OpenRouter models: {e}")
            return {}
    
    def get_context_length(self, model_name: str) -> int:
        """Get context length for a specific model"""
        # Check if cache is expired or empty
        if not self.cache or not self.cache_time or \
           datetime.now() - self.cache_time > self.cache_duration:
            self.cache = self.fetch_models()
            self.cache_time = datetime.now()
        
        # Try exact match first
        if model_name in self.cache:
            return self.cache[model_name]["context_length"]
        
        # Try partial match (e.g., "gpt-4" might match "openai/gpt-4")
        for model_id, info in self.cache.items():
            if model_name in model_id or model_id.endswith(f"/{model_name}"):
                logger.info(f"Found context length for {model_name}: {info['context_length']}")
                return info["context_length"]
        
        # Fallback to conservative defaults based on known patterns
        model_lower = model_name.lower()
        if "gpt-4-turbo" in model_lower or "gpt-4-1106" in model_lower:
            return 128000
        elif "gpt-4-32k" in model_lower:
            return 32768
        elif "gpt-4" in model_lower:
            return 8192
        elif "gpt-3.5-turbo-16k" in model_lower:
            return 16384
        elif "gpt-3.5" in model_lower:
            return 4096
        elif "claude-3" in model_lower:
            return 200000
        elif "claude-2" in model_lower:
            return 100000
        elif "glm" in model_lower or "z-ai" in model_lower:
            return 128000
        elif "deepseek" in model_lower:
            return 32768
        elif "mistral" in model_lower:
            return 32768
        
        # Default fallback
        logger.warning(f"Unknown model {model_name}, using default context length of 8192")
        return 8192
    
    def get_all_models(self) -> Dict[str, Dict]:
        """Get all cached model information"""
        if not self.cache or not self.cache_time or \
           datetime.now() - self.cache_time > self.cache_duration:
            self.cache = self.fetch_models()
            self.cache_time = datetime.now()
        return self.cache
    
    def save_cache(self, filepath: str = "data/cache/openrouter_models.json"):
        """Save model cache to file"""
        data = {
            "models": self.get_all_models(),
            "fetched_at": datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(data['models'])} models to {filepath}")
    
    def load_cache(self, filepath: str = "data/cache/openrouter_models.json") -> bool:
        """Load model cache from file"""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    data = json.load(f)
                self.cache = data.get("models", {})
                fetched_str = data.get("fetched_at")
                if fetched_str:
                    self.cache_time = datetime.fromisoformat(fetched_str)
                logger.info(f"Loaded {len(self.cache)} models from cache")
                return True
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")
        return False


def test_context_manager():
    """Test the OpenRouter context manager"""
    manager = OpenRouterContextManager()
    
    # Test fetching models
    models = manager.get_all_models()
    print(f"Found {len(models)} models")
    
    # Show some example models with large context
    large_context_models = [
        (model_id, info) for model_id, info in models.items() 
        if info["context_length"] > 100000
    ]
    
    print(f"\nModels with >100k context:")
    for model_id, info in sorted(large_context_models, 
                                 key=lambda x: x[1]["context_length"], 
                                 reverse=True)[:10]:
        print(f"  {model_id}: {info['context_length']:,} tokens")
    
    # Test getting specific model context
    test_models = [
        "gpt-4-turbo",
        "claude-3-opus",
        "z-ai/glm-4-air-plus",
        "deepseek/deepseek-chat",
        "unknown-model-xyz"
    ]
    
    print("\nTesting specific models:")
    for model in test_models:
        context = manager.get_context_length(model)
        print(f"  {model}: {context:,} tokens")
    
    # Save cache
    manager.save_cache()


if __name__ == "__main__":
    test_context_manager()