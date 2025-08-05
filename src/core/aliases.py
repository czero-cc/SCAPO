"""Model name aliases and variations mapping for SCAPO."""

# Model aliases - maps common variations to canonical model IDs
# This is a simplified version focused on models actually being scraped
MODEL_ALIASES = {
    # Qwen variants (popular in scraped data)
    "qwen3": "Qwen3",
    "qwen-3": "Qwen3",
    "qwen3-coder": "Qwen3-Coder",
    "qwen3-coder-flash": "Qwen3-Coder-Flash",
    "qwen3coder": "Qwen3-Coder",
    "qwen": "Qwen3",  # Default to latest
    
    # Phi variants  
    "phi-4": "Phi-4",
    "phi4": "Phi-4",
    "phi-3": "Phi-3",
    "phi3": "Phi-3",
    "phi-3.1": "Phi-3.1",
    
    # Llama variants
    "llama3": "llama-3",
    "llama-3.2": "llama-3",
    "llama3.2": "llama-3",
    "llama-3-70b": "llama-3",
    "llama-3-8b": "llama-3",
    
    # GPT variants
    "gpt4": "gpt-4",
    "gpt-4": "gpt-4",
    "gpt5": "gpt-5",
    "gpt-5": "gpt-5",
    "chatgpt": "ChatGPT",
    
    # Claude variants
    "claude3": "claude-3",
    "claude-3": "claude-3",
    "claude-3-opus": "Claude 3 Opus",
    "claude": "claude-3",
    
    # DeepSeek variants
    "deepseek": "Deepseek",
    "deepseek-v3": "Deepseek v3",
    "deepseekcoder": "DeepCoder",
    
    # Hunyuan variants
    "hunyuan": "Hunyuan",
    "hunyuan-80b": "Hunyuan-80B-A13B",
    
    # Video models
    "wan": "wan2.2",
    "wan2": "wan2.2",
    "wan-2.2": "wan2.2",
    "sora": "Sora",
    
    # Common shortcuts
    "sd": "stable-diffusion",
    "mj": "midjourney",
}


def normalize_model_name(model_name: str) -> str:
    """
    Normalize a model name to its canonical form.
    This is a simplified version that preserves the actual model names from scraping.
    """
    if not model_name:
        return model_name
    
    # First check if it's already a known alias
    lower_name = model_name.lower().strip()
    if lower_name in MODEL_ALIASES:
        return MODEL_ALIASES[lower_name]
    
    # Otherwise return the original name with basic cleanup
    # Preserve case and special characters as they appear in scraped data
    return model_name.strip()


def get_all_variations(canonical_name: str) -> list[str]:
    """Get all known variations of a canonical model name."""
    variations = [canonical_name]
    
    # Find all aliases that map to this canonical name
    for alias, canonical in MODEL_ALIASES.items():
        if canonical.lower() == canonical_name.lower() and alias not in variations:
            variations.append(alias)
    
    return variations


def is_valid_model_name(model_name: str) -> bool:
    """
    Check if a model name is valid.
    In the current system, all scraped model names are considered valid.
    """
    return bool(model_name and model_name.strip())


# Category inference from model names
MODEL_CATEGORY_PATTERNS = {
    "text": [
        "gpt", "claude", "llama", "qwen", "phi", "gemma", "mistral",
        "deepseek", "falcon", "hunyuan", "glm", "ernie", "kimi",
        "coder", "starcoder", "codellama", "devstral", "miniCPM"
    ],
    "image": [
        "stable-diffusion", "sd", "midjourney", "mj", "dalle", "dall-e",
        "imagen", "flux", "qwen-image", "QWEN-IMAGE"
    ],
    "video": [
        "wan", "sora", "runway", "pika", "stable-video", "svd",
        "cogvideo", "animatediff"
    ],
    "audio": [
        "whisper", "bark", "musicgen", "audiogen", "elevenlabs",
        "11labs", "tortoise"
    ],
    "multimodal": [
        "gpt-4v", "gpt4v", "vision", "llava", "blip", "clip",
        "gemini", "omni", "o1", "o3", "o4"
    ]
}


def infer_category(model_name: str) -> str:
    """
    Infer the category of a model from its name.
    Uses pattern matching on the model name.
    """
    if not model_name:
        return "text"
        
    lower_name = model_name.lower()
    
    # Check each category's patterns
    for category, patterns in MODEL_CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in lower_name:
                return category
    
    # Default to text if unable to infer
    return "text"