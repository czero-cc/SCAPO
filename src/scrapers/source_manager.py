"""Source manager for handling all scraping sources."""

import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from src.core.logging import get_logger
from src.core.models import SourceType

logger = get_logger(__name__)


class SourceManager:
    """Manages all scraping sources and their configurations."""
    
    def __init__(self, sources_file: Path = None):
        if sources_file is None:
            # Get the path relative to this file
            sources_file = Path(__file__).parent / "sources.yaml"
        self.sources_file = sources_file
        self.sources_config = self._load_sources()
        self.last_scraped: Dict[str, datetime] = {}
    
    def _load_sources(self) -> Dict[str, Any]:
        """Load sources configuration from YAML file."""
        try:
            with open(self.sources_file, "r") as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load sources config: {e}")
            return {}
    
    def get_reddit_sources(self) -> List[Dict[str, Any]]:
        """Get all Reddit sources."""
        reddit_config = self.sources_config.get("reddit", {})
        return reddit_config.get("sources", [])
    
    def get_github_sources(self) -> List[Dict[str, Any]]:
        """Get all GitHub sources."""
        github_config = self.sources_config.get("github", {})
        return github_config.get("sources", [])
    
    def get_forum_sources(self) -> List[Dict[str, Any]]:
        """Get all forum sources."""
        forums_config = self.sources_config.get("forums", {})
        return forums_config.get("sources", [])
    
    def get_api_sources(self) -> List[Dict[str, Any]]:
        """Get all API sources."""
        apis_config = self.sources_config.get("apis", {})
        return apis_config.get("sources", [])
    
    def get_discord_sources(self) -> List[Dict[str, Any]]:
        """Get all Discord sources."""
        discord_config = self.sources_config.get("discord", {})
        return discord_config.get("sources", [])
    
    def get_rss_sources(self) -> List[Dict[str, Any]]:
        """Get all RSS feed sources."""
        rss_config = self.sources_config.get("rss_feeds", {})
        return rss_config.get("sources", [])
    
    def get_news_sources(self) -> List[Dict[str, Any]]:
        """Get all news aggregator sources."""
        news_config = self.sources_config.get("news_aggregators", {})
        return news_config.get("sources", [])
    
    def get_sources_by_priority(self, priority: str = "high") -> List[Dict[str, Any]]:
        """Get all sources filtered by priority."""
        all_sources = []
        
        # Collect from all source types
        for source_type in ["reddit", "github", "forums", "apis", "discord", "rss_feeds", "news_aggregators"]:
            config = self.sources_config.get(source_type, {})
            sources = config.get("sources", [])
            for source in sources:
                if source.get("priority") == priority:
                    source["source_type"] = source_type
                    all_sources.append(source)
        
        return all_sources
    
    def get_sources_for_model(self, model_id: str) -> List[Dict[str, Any]]:
        """Get sources relevant to a specific model."""
        relevant_sources = []
        
        # Check Reddit sources
        for source in self.get_reddit_sources():
            models = source.get("models", [])
            if model_id in models or "general" in models:
                source["source_type"] = "reddit"
                relevant_sources.append(source)
        
        # GitHub sources are generally applicable
        for source in self.get_github_sources():
            source["source_type"] = "github"
            relevant_sources.append(source)
        
        return relevant_sources
    
    def should_scrape(self, source_id: str, update_frequency_hours: int = 24) -> bool:
        """Check if a source should be scraped based on last scrape time."""
        last_scrape = self.last_scraped.get(source_id)
        if not last_scrape:
            return True
        
        time_since_scrape = datetime.utcnow() - last_scrape
        return time_since_scrape > timedelta(hours=update_frequency_hours)
    
    def mark_scraped(self, source_id: str):
        """Mark a source as scraped."""
        self.last_scraped[source_id] = datetime.utcnow()
    
    def get_scraping_config(self) -> Dict[str, Any]:
        """Get general scraping configuration."""
        return self.sources_config.get("scraping_config", {})
    
    def get_content_filters(self) -> Dict[str, Any]:
        """Get content filtering configuration."""
        return self.sources_config.get("content_filters", {})
    
    def get_rate_limit(self, source_type: str) -> Optional[str]:
        """Get rate limit for a source type."""
        config = self.sources_config.get(source_type, {})
        return config.get("rate_limit")
    
    def validate_sources(self) -> Dict[str, List[str]]:
        """Validate all sources configuration."""
        issues = {
            "missing_urls": [],
            "missing_priority": [],
            "invalid_source_type": [],
        }
        
        for source_type in ["reddit", "github", "forums", "apis", "discord", "rss_feeds", "news_aggregators"]:
            config = self.sources_config.get(source_type, {})
            sources = config.get("sources", [])
            
            for source in sources:
                name = source.get("name", "Unknown")
                
                # Check URL
                if not source.get("url") and not source.get("raw_url"):
                    issues["missing_urls"].append(f"{source_type}/{name}")
                
                # Check priority
                if not source.get("priority"):
                    issues["missing_priority"].append(f"{source_type}/{name}")
        
        return issues
    
    def get_all_sources_summary(self) -> Dict[str, int]:
        """Get summary of all available sources."""
        summary = {}
        
        for source_type in ["reddit", "github", "forums", "apis", "discord", "rss_feeds", "news_aggregators"]:
            config = self.sources_config.get(source_type, {})
            sources = config.get("sources", [])
            summary[source_type] = len(sources)
        
        summary["total"] = sum(summary.values())
        return summary