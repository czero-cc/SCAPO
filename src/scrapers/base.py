from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

from tenacity import retry, stop_after_attempt, wait_exponential

from src.core.logging import LogContext, get_logger
from src.core.models import ModelBestPractices, ScrapedPost, SourceType
from src.core.config import settings


class BaseScraper(ABC):
    """Base class for all scrapers."""

    def __init__(self, source_type: SourceType) -> None:
        self.source_type = source_type
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        self._processed_ids: Set[str] = set()

    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the platform."""
        pass

    @abstractmethod
    async def fetch_posts(
        self,
        subreddit: Optional[str] = None,
        limit: int = 100,
        time_filter: str = "week",
    ) -> List[ScrapedPost]:
        """Fetch posts from the platform."""
        pass

    @abstractmethod
    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Extract best practices from posts."""
        pass

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        reraise=True,
    )
    async def scrape(
        self,
        target: Optional[str] = None,
        limit: int = 100,
        time_filter: str = "week",
    ) -> Dict[str, Any]:
        """Main scraping method with retry logic."""
        with LogContext(
            scraper=self.__class__.__name__,
            target=target,
            limit=limit,
            time_filter=time_filter,
        ):
            self.logger.info("Starting scrape")
            
            try:
                # Authenticate if needed
                await self.authenticate()
                
                # Fetch posts
                posts = await self.fetch_posts(
                    subreddit=target,
                    limit=limit,
                    time_filter=time_filter,
                )
                
                # Filter out already processed posts
                new_posts = [
                    p for p in posts
                    if p.post_id not in self._processed_ids
                ]
                
                self.logger.info(
                    "Fetched posts",
                    total_posts=len(posts),
                    new_posts=len(new_posts),
                )
                
                if not new_posts:
                    return {"status": "no_new_posts", "posts": []}
                
                # Extract best practices
                practices = self.extract_best_practices(new_posts)
                
                # Optional: Process through LLM for better extraction
                if settings.llm_processing_enabled:
                    practices = await self._enhance_with_llm(new_posts, practices)
                
                # Mark posts as processed
                self._processed_ids.update(p.post_id for p in new_posts)
                
                return {
                    "status": "success",
                    "posts": new_posts,
                    "practices": practices,
                    "timestamp": datetime.utcnow().isoformat(),
                }
                
            except Exception as e:
                self.logger.error("Scraping failed", error=str(e), exc_info=True)
                raise

    def filter_relevant_posts(
        self,
        posts: List[ScrapedPost],
        keywords: Optional[List[str]] = None,
        min_score: int = 10,
        min_relevance: float = 0.5,
    ) -> List[ScrapedPost]:
        """Filter posts by relevance criteria."""
        if keywords is None:
            keywords = [
                "prompt", "prompting", "best practice", "tip", "trick",
                "parameter", "setting", "config", "guide", "how to",
                "optimal", "recommended", "avoid", "mistake", "pitfall",
            ]
        
        filtered = []
        for post in posts:
            # Check score threshold
            if post.score < min_score:
                continue
            
            # Check relevance score
            if post.relevance_score < min_relevance:
                continue
            
            # Check keyword presence
            content_lower = (post.content + (post.title or "")).lower()
            if any(keyword.lower() in content_lower for keyword in keywords):
                filtered.append(post)
        
        return filtered

    def categorize_practices(
        self,
        posts: List[ScrapedPost],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize extracted practices."""
        categories = {
            "prompting": [],
            "parameters": [],
            "pitfalls": [],
            "examples": [],
            "general_tips": [],
        }
        
        for post in posts:
            practices = post.extracted_practices
            
            # Categorize based on content
            if practices.get("prompt_patterns"):
                categories["prompting"].extend(practices["prompt_patterns"])
            
            if practices.get("parameter_recommendations"):
                categories["parameters"].extend(practices["parameter_recommendations"])
            
            if practices.get("common_mistakes"):
                categories["pitfalls"].extend(practices["common_mistakes"])
            
            if practices.get("examples"):
                categories["examples"].extend(practices["examples"])
            
            if practices.get("tips"):
                categories["general_tips"].extend(practices["tips"])
        
        return categories

    async def update_model_docs(
        self,
        model_id: str,
        practices: Dict[str, Any],
    ) -> ModelBestPractices:
        """Update model documentation with new practices."""
        # This would typically interact with a database
        # For now, we'll create a new instance
        self.logger.info(
            "Updating model docs",
            model_id=model_id,
            practices_count=len(practices),
        )
        
        # Implementation would merge with existing practices
        # and update files/database
        raise NotImplementedError("Subclasses must implement update_model_docs")
    
    async def _enhance_with_llm(
        self,
        posts: List[ScrapedPost],
        initial_practices: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance extracted practices using LLM processing."""
        try:
            from src.services.llm_processor import LLMProcessorFactory, ProcessedPractice
            
            # Create processor with character limit
            processor = LLMProcessorFactory.create_processor(
                provider=settings.llm_provider,
                base_url=settings.local_llm_url,
                model=settings.local_llm_model,
                api_type=settings.local_llm_type,
                api_key=settings.openrouter_api_key,
            )
            
            enhanced_practices = initial_practices.copy()
            enhanced_practices["llm_processed"] = []
            
            # Process top posts
            for post in posts[:5]:  # Limit to top 5 to manage costs/time
                try:
                    # Combine title and content
                    full_content = f"Title: {post.title}\n\nContent: {post.content}"
                    
                    # Process through LLM
                    processed = await processor.process_content(
                        full_content,
                        self.source_type.value
                    )
                    
                    # Add to enhanced practices
                    for practice in processed:
                        enhanced_practices["llm_processed"].append({
                            "type": practice.practice_type,
                            "content": practice.content,
                            "confidence": practice.confidence,
                            "models": practice.applicable_models,
                            "source_post": post.post_id,
                            "parameters": practice.extracted_parameters,
                            "example": practice.example_code,
                        })
                    
                except Exception as e:
                    self.logger.warning(f"Failed to process post {post.post_id}: {e}")
            
            await processor.close()
            
            # Merge LLM insights with initial extraction
            if enhanced_practices["llm_processed"]:
                self.logger.info(
                    f"LLM enhanced {len(enhanced_practices['llm_processed'])} practices"
                )
            
            return enhanced_practices
            
        except Exception as e:
            self.logger.error(f"LLM enhancement failed: {e}")
            # Return original practices on failure
            return initial_practices