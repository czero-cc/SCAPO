import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.config import settings
from src.core.logging import get_logger
from src.core.models import SourceType
from src.scrapers.intelligent_browser_scraper import IntelligentBrowserScraper
from src.services.practice_updater import PracticeUpdater
# Database imports removed - focusing on scraping pipeline
from src.utils.metrics import (
    scraper_last_run,
    scraper_posts_processed,
    scraper_practices_extracted,
    scraper_runs_counter,
)

logger = get_logger(__name__)


class ScraperService:
    """Service for managing the intelligent web scraper."""

    def __init__(self):
        self.intelligent_scraper = IntelligentBrowserScraper()
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
        self.practice_updater = PracticeUpdater()

    async def run_scrapers(
        self,
        sources: List[str] = None,
        max_posts_per_source: int = 10,
        llm_max_chars: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Run intelligent scraper on specified sources."""
        
        # Default sources if not specified
        if sources is None:
            sources = ["reddit:LocalLLaMA", "reddit:OpenAI", "hackernews"]
        
        # Override LLM max chars if provided
        if llm_max_chars is not None:
            settings.llm_max_chars = llm_max_chars
            logger.info(f"Using custom LLM character limit: {llm_max_chars}")
        
        status = self.scraper_status["intelligent"]
        
        # Update status
        status["status"] = "running"
        status["last_run"] = datetime.utcnow()
        status["error"] = None
        
        try:
            logger.info(f"Starting intelligent scraper", sources=sources, max_posts=max_posts_per_source)
            scraper_runs_counter.labels(source="intelligent", status="started").inc()
            
            # Database operations removed - focusing on scraping pipeline
            
            # Run the intelligent scraper
            start_time = datetime.utcnow()
            await self.intelligent_scraper.scrape_sources(
                sources=sources,
                max_posts_per_source=max_posts_per_source
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
            
            # Update metrics
            scraper_posts_processed.labels(source="intelligent").inc(total_posts)
            scraper_practices_extracted.labels(
                source="intelligent",
                type="all"
            ).inc(total_practices)
            
            # Update status
            status["status"] = "idle"
            status["last_success"] = datetime.utcnow()
            status["total_runs"] += 1
            status["total_posts"] += total_posts
            
            scraper_runs_counter.labels(source="intelligent", status="success").inc()
            scraper_last_run.labels(source="intelligent").set_to_current_time()
            
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
            
            scraper_runs_counter.labels(source="intelligent", status="failed").inc()
            
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
        """List available scraping sources."""
        return {
            "reddit": [
                "reddit:LocalLLaMA",
                "reddit:OpenAI", 
                "reddit:StableDiffusion",
                "reddit:midjourney",
                "reddit:ClaudeAI",
                "reddit:singularity",
                "reddit:MachineLearning",
                "reddit:artificial",
                "reddit:ArtificialIntelligence",
                "reddit:deeplearning",
                "reddit:PromptEngineering",
                "reddit:LLMOps",
                "reddit:LocalLLM",
                "reddit:comfyui",
            ],
            "hackernews": ["hackernews"],
            "github": [
                "github:dair-ai/Prompt-Engineering-Guide",
                "github:brexhq/prompt-engineering",
                "github:openai/openai-cookbook",
                "github:f/awesome-chatgpt-prompts",
            ],
        }

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
                    "hackernews",
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