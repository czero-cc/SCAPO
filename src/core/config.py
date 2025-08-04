from pathlib import Path
from typing import Optional

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Reddit API
    reddit_client_id: Optional[str] = Field(None, description="Reddit API client ID")
    reddit_client_secret: Optional[str] = Field(None, description="Reddit API client secret")
    reddit_user_agent: str = Field(
        default="sota-practices-bot/1.0 by Fiefworks",
        description="Reddit user agent",
    )

    # Discord
    discord_bot_token: Optional[str] = Field(None, description="Discord bot token")
    
    # GitHub
    github_token: Optional[str] = Field(None, description="GitHub personal access token")

    # Database
    database_url: str = Field(default="sqlite:///./sota_practices.db", description="Database connection URL")
    redis_url: str = Field(default="redis://localhost:6379", description="Redis connection URL")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_prefix: str = Field(default="/api/v1", description="API prefix")

    # Security
    api_key: str = Field(default="dev_api_key_change_in_production", description="API key for authentication")
    secret_key: str = Field(default="dev_secret_key_change_in_production", description="Secret key for JWT")

    # Monitoring
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    otel_exporter_otlp_endpoint: Optional[str] = Field(
        None, description="OpenTelemetry exporter endpoint"
    )

    # Scraping Configuration
    scraping_interval_hours: int = Field(
        default=6, description="Hours between scraping runs"
    )
    max_posts_per_scrape: int = Field(
        default=100, description="Maximum posts to scrape per run"
    )
    min_upvote_ratio: float = Field(
        default=0.8, description="Minimum upvote ratio for posts"
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
    llm_max_chars: int = Field(default=4000, description="Maximum characters to send to LLM (user-friendly)")
    llm_char_hard_limit: int = Field(default=50000, description="Absolute maximum characters (safety limit)")

    @field_validator("models_dir", "scrapers_dir")
    @classmethod
    def validate_paths(cls, v: Path) -> Path:
        return v.resolve()


settings = Settings()