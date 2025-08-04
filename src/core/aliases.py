"""Model name aliases and variations mapping."""

# Model aliases - maps common variations to canonical model IDs
MODEL_ALIASES = {
    # GPT variants
    "gpt4": "gpt-4",
    "gpt-4-turbo": "gpt-4",
    "gpt-4-vision": "gpt-4v",
    "gpt4v": "gpt-4v",
    "gpt-3.5": "gpt-3.5",
    "gpt3.5": "gpt-3.5",
    "gpt-3.5-turbo": "gpt-3.5",
    "chatgpt": "gpt-3.5",
    
    # Claude variants
    "claude3": "claude-3",
    "claude-3-opus": "claude-3",
    "claude-3-sonnet": "claude-3",
    "claude-3-haiku": "claude-3",
    "claude2": "claude-2",
    "claude-2.1": "claude-2",
    "claude": "claude-3",  # Default to latest
    
    # Llama variants
    "llama3": "llama-3",
    "llama-3-70b": "llama-3",
    "llama-3-8b": "llama-3",
    "llama2": "llama-2",
    "llama-2-70b": "llama-2",
    "llama-2-13b": "llama-2",
    "llama-2-7b": "llama-2",
    
    # Code models
    "code-llama": "codellama",
    "codellama-34b": "codellama",
    "star-coder": "starcoder",
    "starcoder-15b": "starcoder",
    "deepseek-coder": "deepseek",
    
    # Mistral variants
    "mistral-7b": "mistral",
    "mistral-medium": "mistral",
    "mixtral-8x7b": "mixtral",
    
    # Stable Diffusion variants
    "sd": "stable-diffusion",
    "sdxl": "stable-diffusion",
    "stable-diffusion-xl": "stable-diffusion",
    "stable-diffusion-v2": "stable-diffusion",
    "stable-diffusion-2.1": "stable-diffusion",
    "sd-v2": "stable-diffusion",
    "sd-2.1": "stable-diffusion",
    
    # Midjourney variants
    "mj": "midjourney",
    "mj-v6": "midjourney",
    "mj-v5": "midjourney",
    "midjourney-v6": "midjourney",
    "midjourney-v5": "midjourney",
    
    # DALL-E variants
    "dalle": "dalle-3",
    "dall-e": "dalle-3",
    "dalle3": "dalle-3",
    "dalle2": "dalle-2",
    
    # Video models
    "runway-gen2": "runway",
    "runway-gen3": "runway",
    "pika-labs": "pika",
    "pika-1.0": "pika",
    "stable-video-diffusion": "stable-video",
    "svd": "stable-video",
    
    # Audio models
    "whisper-large": "whisper",
    "whisper-medium": "whisper",
    "whisper-small": "whisper",
    "11labs": "elevenlabs",
    "eleven-labs": "elevenlabs",
    "bark-v0": "bark",
    "music-gen": "musicgen",
    "audio-gen": "audiogen",
    
    # Multimodal models
    "gpt4-vision": "gpt-4v",
    "gpt-4-v": "gpt-4v",
    "gemini-pro-vision": "gemini-vision",
    "llava-1.5": "llava",
    "llava-v1.5": "llava",
    "blip2": "blip",
    "blip-2": "blip",
    
    # Common shortcuts
    "gpt": "gpt-4",  # Default to latest GPT
    "claude": "claude-3",  # Default to latest Claude
    "llama": "llama-3",  # Default to latest Llama
    "sd": "stable-diffusion",
    "mj": "midjourney",
}


def normalize_model_name(model_name: str) -> str:
    """Normalize a model name to its canonical form."""
    if not model_name:
        return model_name
    
    # Convert to lowercase and strip whitespace
    normalized = model_name.lower().strip()
    
    # Remove common prefixes/suffixes
    normalized = normalized.replace("model:", "").strip()
    normalized = normalized.replace("model/", "").strip()
    
    # Check aliases
    if normalized in MODEL_ALIASES:
        return MODEL_ALIASES[normalized]
    
    return normalized


def get_all_variations(canonical_name: str) -> list[str]:
    """Get all known variations of a canonical model name."""
    variations = [canonical_name]
    
    # Find all aliases that map to this canonical name
    for alias, canonical in MODEL_ALIASES.items():
        if canonical == canonical_name and alias not in variations:
            variations.append(alias)
    
    return variations


def is_valid_model_name(model_name: str) -> bool:
    """Check if a model name is valid (either canonical or alias)."""
    normalized = normalize_model_name(model_name)
    
    # Check if it's a known alias or a canonical name
    return (
        normalized in MODEL_ALIASES or
        normalized in MODEL_ALIASES.values()
    )


# Category inference from model names
MODEL_CATEGORY_PATTERNS = {
    "text": [
        "gpt", "claude", "llama", "mistral", "mixtral", "gemini",
        "phi", "falcon", "vicuna", "alpaca", "dolly", "starcoder",
        "codellama", "deepseek"
    ],
    "image": [
        "stable-diffusion", "sd", "midjourney", "mj", "dalle",
        "imagen", "playground", "leonardo", "ideogram", "flux"
    ],
    "video": [
        "runway", "pika", "stable-video", "svd", "modelscope",
        "zeroscope", "animatediff", "wan", "cogvideo"
    ],
    "audio": [
        "whisper", "bark", "musicgen", "audiogen", "elevenlabs",
        "11labs", "tortoise", "valle"
    ],
    "multimodal": [
        "gpt-4v", "gpt4v", "vision", "llava", "blip", "clip", "flamingo"
    ]
}


def infer_category(model_name: str) -> str:
    """Infer the category of a model from its name."""
    normalized = normalize_model_name(model_name)
    
    for category, patterns in MODEL_CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in normalized:
                return category
    
    # Default to text if unable to infer
    return "text"