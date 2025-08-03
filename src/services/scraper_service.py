import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.models import SourceType
from src.scrapers.reddit_scraper import RedditScraper
from src.utils.metrics import (
    scraper_last_run,
    scraper_posts_processed,
    scraper_practices_extracted,
    scraper_runs_counter,
)

logger = get_logger(__name__)


class ScraperService:
    """Service for managing web scrapers."""

    def __init__(self):
        self.scrapers = {
            "reddit": RedditScraper(),
        }
        self.scraper_status = {}
        self._initialize_status()

    def _initialize_status(self):
        """Initialize scraper status tracking."""
        for name in self.scrapers:
            self.scraper_status[name] = {
                "last_run": None,
                "last_success": None,
                "total_runs": 0,
                "total_posts": 0,
                "status": "idle",
                "error": None,
            }

    async def run_scraper(
        self,
        source: str,
        target: Optional[str] = None,
        limit: int = 100,
        llm_max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run a specific scraper."""
        if source not in self.scrapers:
            raise ValueError(f"Unknown scraper source: {source}")
        
        # Override LLM max chars if provided
        if llm_max_chars is not None:
            settings.llm_max_chars = llm_max_chars
            logger.info(f"Using custom LLM character limit: {llm_max_chars}")
        
        scraper = self.scrapers[source]
        status = self.scraper_status[source]
        
        # Update status
        status["status"] = "running"
        status["last_run"] = datetime.utcnow()
        status["error"] = None
        
        try:
            logger.info(f"Starting {source} scraper", target=target, limit=limit)
            scraper_runs_counter.labels(source=source, status="started").inc()
            
            # Run the scraper
            result = await scraper.scrape(
                target=target,
                limit=limit,
                time_filter="week",
            )
            
            # Update metrics
            posts_count = len(result.get("posts", []))
            scraper_posts_processed.labels(source=source).inc(posts_count)
            
            practices = result.get("practices", {})
            for practice_type, items in practices.items():
                if isinstance(items, list):
                    scraper_practices_extracted.labels(
                        source=source,
                        type=practice_type
                    ).inc(len(items))
            
            # Update status
            status["status"] = "idle"
            status["last_success"] = datetime.utcnow()
            status["total_runs"] += 1
            status["total_posts"] += posts_count
            
            scraper_runs_counter.labels(source=source, status="success").inc()
            scraper_last_run.labels(source=source).set_to_current_time()
            
            logger.info(
                f"Completed {source} scraper",
                posts_count=posts_count,
                practices_count=len(practices),
            )
            
            return {
                "status": "success",
                "source": source,
                "posts_scraped": posts_count,
                "practices_extracted": self._count_practices(practices),
                "timestamp": datetime.utcnow().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Scraper {source} failed", error=str(e), exc_info=True)
            
            # Update status
            status["status"] = "error"
            status["error"] = str(e)
            
            scraper_runs_counter.labels(source=source, status="failed").inc()
            
            return {
                "status": "error",
                "source": source,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def run_all_scrapers(self, limit: int = 100) -> Dict[str, Any]:
        """Run all available scrapers concurrently."""
        tasks = []
        for source in self.scrapers:
            task = asyncio.create_task(
                self.run_scraper(source=source, limit=limit)
            )
            tasks.append((source, task))
        
        results = {}
        for source, task in tasks:
            try:
                result = await task
                results[source] = result
            except Exception as e:
                logger.error(f"Failed to run {source} scraper", error=str(e))
                results[source] = {
                    "status": "error",
                    "error": str(e),
                }
        
        return results

    async def get_status(self) -> Dict[str, Any]:
        """Get status of all scrapers."""
        return {
            "scrapers": self.scraper_status,
            "total_scrapers": len(self.scrapers),
            "active_scrapers": sum(
                1 for s in self.scraper_status.values()
                if s["status"] == "running"
            ),
        }

    async def list_sources(self) -> Dict[str, List[str]]:
        """List available scraping sources and their targets."""
        sources = {}
        
        # Reddit targets
        sources["reddit"] = [
            "LocalLLaMA",
            "StableDiffusion",
            "midjourney",
            "OpenAI",
            "ClaudeAI",
            "singularity",
            "MachineLearning",
            "artificial",
            "ArtificialIntelligence",
            "deeplearning",
        ]
        
        # Future sources
        sources["discord"] = ["Not implemented yet"]
        sources["forums"] = ["Not implemented yet"]
        
        return sources

    def _count_practices(self, practices: Dict[str, Any]) -> int:
        """Count total number of practices extracted."""
        count = 0
        for value in practices.values():
            if isinstance(value, list):
                count += len(value)
            elif isinstance(value, dict):
                count += self._count_practices(value)
        return count

    async def schedule_periodic_scraping(self):
        """Schedule periodic scraping based on configuration."""
        while True:
            try:
                logger.info("Running scheduled scraping")
                await self.run_all_scrapers(limit=settings.max_posts_per_scrape)
                
                # Wait for next run
                await asyncio.sleep(settings.scraping_interval_hours * 3600)
                
            except Exception as e:
                logger.error("Scheduled scraping failed", error=str(e))
                # Wait a bit before retrying
                await asyncio.sleep(300)  # 5 minutes