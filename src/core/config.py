from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    log_format: str = Field(default="json", description="Log format (json or text)")

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


settings = Settings()