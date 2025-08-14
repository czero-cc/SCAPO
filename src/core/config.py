from pathlib import Path
from typing import Optional, Any
import sys

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_core import ValidationError


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Browser scraping doesn't need API keys or database

    # API Configuration (for future API server)
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")

    # Scraping Configuration
    scraping_interval_hours: int = Field(
        default=6, description="Hours between scraping runs"
    )
    max_posts_per_scrape: int = Field(
        default=100, description="Maximum posts to scrape per run"
    )
    scraping_delay_seconds: float = Field(
        default=2.0, description="Delay between scraping pages/posts (be respectful to servers)"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="pretty", description="Log format (json, text, or pretty)")

    # Paths
    models_dir: Path = Field(default=Path("models"), description="Models directory")
    scrapers_dir: Path = Field(default=Path("scrapers"), description="Scrapers directory")
    
    # LLM Processing
    llm_provider: str = Field(default="local", description="LLM provider: local, openrouter")
    openrouter_api_key: Optional[str] = Field(None, description="OpenRouter API key")
    openrouter_model: str = Field(default="anthropic/claude-3-haiku", description="OpenRouter model")
    local_llm_url: str = Field(default="http://localhost:11434", description="Local LLM URL")
    local_llm_model: str = Field(default="llama3", description="Local LLM model")
    local_llm_type: str = Field(default="ollama", description="Local LLM type: ollama, lmstudio")
    llm_processing_enabled: bool = Field(default=True, description="Enable LLM processing of content")
    llm_quality_threshold: float = Field(default=0.6, description="Minimum quality score for practices (0.0-1.0)")
    
    # Local LLM context configuration
    local_llm_max_context: Optional[int] = Field(None, description="Maximum context tokens for local LLM (e.g., 4096, 8192, 32768)")
    local_llm_optimal_chunk: Optional[int] = Field(None, description="Optimal chunk size for local LLM processing")
    
    # LLM timeout configuration
    llm_timeout_seconds: float = Field(default=120.0, description="Timeout for LLM requests in seconds")
    local_llm_timeout_seconds: Optional[float] = Field(None, description="Override timeout for local LLM requests (defaults to llm_timeout_seconds if not set)")

    @field_validator("models_dir", "scrapers_dir")
    @classmethod
    def validate_paths(cls, v: Path) -> Path:
        return v.resolve()
    
    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(
                f"❌ Invalid LOG_LEVEL: '{v}'\n"
                f"   Valid options: {', '.join(valid_levels)}\n"
                f"   Please update your .env file."
            )
        return v.upper()
    
    @field_validator("log_format")
    @classmethod
    def validate_log_format(cls, v: str) -> str:
        valid_formats = ["json", "text", "pretty"]
        if v.lower() not in valid_formats:
            raise ValueError(
                f"❌ Invalid LOG_FORMAT: '{v}'\n"
                f"   Valid options: {', '.join(valid_formats)}\n"
                f"   Recommended: 'pretty' for terminal output\n"
                f"   Please update your .env file."
            )
        return v.lower()
    
    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        valid_providers = ["local", "openrouter"]
        if v.lower() not in valid_providers:
            raise ValueError(
                f"❌ Invalid LLM_PROVIDER: '{v}'\n"
                f"   Valid options: {', '.join(valid_providers)}\n"
                f"   - 'openrouter': Use cloud AI models (requires API key)\n"
                f"   - 'local': Use local models via Ollama/LM Studio\n"
                f"   Please update your .env file."
            )
        return v.lower()
    
    @field_validator("local_llm_type")
    @classmethod
    def validate_local_llm_type(cls, v: str) -> str:
        valid_types = ["ollama", "lmstudio"]
        if v.lower() not in valid_types:
            raise ValueError(
                f"❌ Invalid LOCAL_LLM_TYPE: '{v}'\n"
                f"   Valid options: {', '.join(valid_types)}\n"
                f"   - 'ollama': Ollama server (default port 11434)\n"
                f"   - 'lmstudio': LM Studio server (default port 1234)\n"
                f"   Please update your .env file."
            )
        return v.lower()
    
    @model_validator(mode='after')
    def validate_llm_configuration(self) -> 'Settings':
        """Validate LLM configuration based on provider."""
        
        # Check OpenRouter configuration
        if self.llm_provider == "openrouter":
            if not self.openrouter_api_key:
                raise ValueError(
                    "❌ OpenRouter API key is missing!\n"
                    "   You have set LLM_PROVIDER=openrouter but OPENROUTER_API_KEY is not set.\n"
                    "   \n"
                    "   To fix this:\n"
                    "   1. Get your API key from https://openrouter.ai/keys\n"
                    "   2. Add to your .env file: OPENROUTER_API_KEY=sk-or-v1-...\n"
                    "   \n"
                    "   Or switch to local LLM:\n"
                    "   Set LLM_PROVIDER=local in your .env file"
                )
            
            # Validate API key format
            if not self.openrouter_api_key.startswith("sk-or-"):
                raise ValueError(
                    f"❌ Invalid OpenRouter API key format!\n"
                    f"   Your key: {self.openrouter_api_key[:10]}...\n"
                    f"   Expected format: sk-or-v1-...\n"
                    f"   \n"
                    f"   Please check your API key at https://openrouter.ai/keys"
                )
        
        # Check local LLM configuration
        if self.llm_provider == "local":
            if self.local_llm_type == "ollama":
                # Check if URL matches expected Ollama port
                if "11434" not in self.local_llm_url:
                    # Only warn if it doesn't look like it could be LM Studio either
                    if "1234" in self.local_llm_url:
                        print(
                            "⚠️  Warning: You have LOCAL_LLM_TYPE=ollama but URL looks like LM Studio.\n"
                            f"   Current URL: {self.local_llm_url}\n"
                            f"   Current Type: ollama\n"
                            f"   \n"
                            f"   If using LM Studio, set: LOCAL_LLM_TYPE=lmstudio\n"
                            f"   If using Ollama, set: LOCAL_LLM_URL=http://localhost:11434"
                        )
                    else:
                        print(
                            "⚠️  Warning: LOCAL_LLM_URL may not be correctly configured for Ollama.\n"
                            f"   Current: {self.local_llm_url}\n"
                            f"   Expected: http://localhost:11434\n"
                            f"   \n"
                            f"   Make sure Ollama is running: 'ollama serve'"
                        )
            elif self.local_llm_type == "lmstudio":
                # Check if URL matches expected LM Studio port
                if "1234" not in self.local_llm_url:
                    # Only warn if it doesn't look like it could be Ollama either
                    if "11434" in self.local_llm_url:
                        print(
                            "⚠️  Warning: You have LOCAL_LLM_TYPE=lmstudio but URL looks like Ollama.\n"
                            f"   Current URL: {self.local_llm_url}\n"
                            f"   Current Type: lmstudio\n"
                            f"   \n"
                            f"   If using Ollama, set: LOCAL_LLM_TYPE=ollama\n"
                            f"   If using LM Studio, set: LOCAL_LLM_URL=http://localhost:1234"
                        )
                    else:
                        print(
                            "⚠️  Warning: LOCAL_LLM_URL may not be correctly configured for LM Studio.\n"
                            f"   Current: {self.local_llm_url}\n"
                            f"   Expected: http://localhost:1234\n"
                            f"   \n"
                            f"   Make sure LM Studio server is running (Start Server in LM Studio)"
                        )
        
        # Validate quality threshold
        if not 0.0 <= self.llm_quality_threshold <= 1.0:
            raise ValueError(
                f"❌ Invalid LLM_QUALITY_THRESHOLD: {self.llm_quality_threshold}\n"
                f"   Must be between 0.0 and 1.0\n"
                f"   - 0.0 = Accept all content (faster)\n"
                f"   - 0.6 = Moderate filtering (default)\n"
                f"   - 1.0 = Very strict filtering"
            )
        
        return self


def load_settings() -> Settings:
    """Load settings with nice error handling."""
    try:
        return Settings()
    except ValidationError as e:
        print("\n" + "="*60)
        print("⚠️  CONFIGURATION ERROR")
        print("="*60)
        
        for error in e.errors():
            # Pydantic validation errors already have our custom messages
            if 'ctx' in error and 'error' in error['ctx']:
                print(f"\n{error['ctx']['error']}")
            else:
                # Fallback for other errors
                field = " -> ".join(str(x) for x in error['loc'])
                print(f"\n❌ Error in {field}: {error['msg']}")
        
        print("\n" + "="*60)
        print("Please fix the configuration issues in your .env file")
        print("="*60 + "\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error loading configuration: {e}")
        print("Please check your .env file")
        sys.exit(1)


# Load settings with validation
settings = load_settings()