import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.models import SourceType
from src.scrapers.intelligent_browser_scraper import IntelligentBrowserScraper
from src.scrapers.source_manager import SourceManager
# Database and practice updater imports removed - focusing on scraping pipeline

logger = get_logger(__name__)


class ScraperService:
    """Service for managing the intelligent web scraper."""

    def __init__(self):
        self.intelligent_scraper = IntelligentBrowserScraper()
        self.source_manager = SourceManager()
        self.scraper_status = {
            "intelligent": {
                "last_run": None,
                "last_success": None,
                "total_runs": 0,
                "total_posts": 0,
                "status": "idle",
                "error": None,
            }
        }
        # Practice updater removed - data saved directly by intelligent scraper

    def _get_default_sources(self, limit: int = 5) -> List[str]:
        """Get default high-priority sources from sources.yaml."""
        default_sources = []
        
        # Get high priority sources
        high_priority = self.source_manager.get_sources_by_priority("high")
        
        # Convert to scraper format
        for source in high_priority[:limit]:
            source_type = source.get('source_type', '')
            if source_type == 'reddit':
                name = source['name'].split('/')[-1]
                default_sources.append(f"reddit:{name}")
            elif source_type == 'github':
                url = source.get('url', '')
                if 'github.com/' in url:
                    repo_path = url.split('github.com/')[-1].rstrip('/')
                    default_sources.append(f"github:{repo_path}")
            # News aggregators not yet implemented
            # elif source_type == 'news_aggregators':
            #     default_sources.append("hackernews")
        
        # Fallback to hardcoded if no high priority sources
        if not default_sources:
            default_sources = ["reddit:LocalLLaMA", "reddit:OpenAI"]
            
        logger.info(f"Using default sources: {default_sources}")
        return default_sources

    async def run_scrapers(
        self,
        sources: List[str] = None,
        max_posts_per_source: int = 10,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """Run intelligent scraper on specified sources."""
        
        # Default sources if not specified - use high priority sources from sources.yaml
        if sources is None:
            sources = self._get_default_sources()
        
        
        status = self.scraper_status["intelligent"]
        
        # Update status
        status["status"] = "running"
        status["last_run"] = datetime.utcnow()
        status["error"] = None
        
        try:
            logger.info(f"Starting intelligent scraper", sources=sources, max_posts=max_posts_per_source)
            
            # Run the intelligent scraper
            start_time = datetime.utcnow()
            await self.intelligent_scraper.scrape_sources(
                sources=sources,
                max_posts_per_source=max_posts_per_source,
                progress_callback=progress_callback
            )
            end_time = datetime.utcnow()
            processing_time = (end_time - start_time).total_seconds()
            
            # Get results from scraper
            total_posts = len(self.intelligent_scraper.processed_content)
            total_practices = sum(
                len(content.best_practices) 
                for content in self.intelligent_scraper.processed_content
            )
            
            # Extract all models found
            all_models = set()
            for content in self.intelligent_scraper.processed_content:
                all_models.update(content.entities.models_mentioned)
            
            # Database operations removed - data is saved directly to model directories
            
            # Update status
            status["status"] = "idle"
            status["last_success"] = datetime.utcnow()
            status["total_runs"] += 1
            status["total_posts"] += total_posts
            
            # Metrics removed - using direct file logging
            
            logger.info(
                f"Completed intelligent scraper",
                posts_count=total_posts,
                practices_count=total_practices,
                models_found=len(all_models),
                processing_time=processing_time
            )
            
            return {
                "status": "success",
                "source": "intelligent",
                "posts_scraped": total_posts,
                "practices_extracted": total_practices,
                "models_found": sorted(list(all_models)),
                "processing_time": processing_time,
                "timestamp": datetime.utcnow().isoformat(),
                "sources_processed": sources,
                "errors": []
            }
            
        except Exception as e:
            logger.error(f"Intelligent scraper failed", error=str(e), exc_info=True)
            
            # Update status
            status["status"] = "error"
            status["error"] = str(e)
            
            # Metrics removed - using direct file logging
            
            # Database operations removed
            
            return {
                "status": "error",
                "source": "intelligent",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
                "sources_processed": sources,
            }

    async def get_status(self) -> Dict[str, Any]:
        """Get status of the scraper."""
        return {
            "scrapers": self.scraper_status,
            "total_scrapers": 1,
            "active_scrapers": 1 if self.scraper_status["intelligent"]["status"] == "running" else 0,
        }

    async def list_sources(self) -> Dict[str, List[str]]:
        """List available scraping sources from sources.yaml."""
        sources_dict = {}
        
        # Get Reddit sources (functional)
        reddit_sources = self.source_manager.get_reddit_sources()
        sources_dict["reddit"] = [f"reddit:{s['name'].split('/')[-1]}" for s in reddit_sources]
        
        # Get summary (only shows functional sources now)
        summary = self.source_manager.get_all_sources_summary()
        if summary:
            sources_dict["_summary"] = summary
        
        return sources_dict

    async def schedule_periodic_scraping(self):
        """Schedule periodic scraping based on configuration."""
        while True:
            try:
                logger.info("Running scheduled scraping")
                
                # Define sources to scrape periodically
                sources = [
                    "reddit:LocalLLaMA",
                    "reddit:OpenAI",
                    "reddit:StableDiffusion",
                    # "hackernews",  # Not yet implemented
                    "github:dair-ai/Prompt-Engineering-Guide"
                ]
                
                await self.run_scrapers(
                    sources=sources,
                    max_posts_per_source=settings.max_posts_per_scrape // len(sources)
                )
                
                # Wait for next run
                await asyncio.sleep(settings.scraping_interval_hours * 3600)
                
            except Exception as e:
                logger.error("Scheduled scraping failed", error=str(e))
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes