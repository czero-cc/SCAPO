"""Enhanced base scraper with better error handling."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from src.core.logging import get_logger
from src.core.models import ScrapedPost, SourceType


class EnhancedBaseScraper(ABC):
    """Enhanced base scraper with credential validation."""
    
    def __init__(self, source_type: SourceType):
        self.source_type = source_type
        self.logger = get_logger(self.__class__.__name__)
        self._is_authenticated = False
        self._auth_error = None
    
    def check_credentials(self) -> tuple[bool, Optional[str]]:
        """Check if required credentials are available."""
        try:
            return self._validate_credentials()
        except Exception as e:
            return False, str(e)
    
    @abstractmethod
    def _validate_credentials(self) -> tuple[bool, Optional[str]]:
        """Validate required credentials for this scraper."""
        pass
    
    async def scrape(
        self,
        target: Optional[str] = None,
        limit: int = 100,
        time_filter: str = "week",
    ) -> Dict[str, Any]:
        """Scrape with credential validation."""
        # Check credentials first
        is_valid, error_msg = self.check_credentials()
        if not is_valid:
            self.logger.warning(
                f"Skipping {self.source_type.value} scraper: {error_msg}"
            )
            return {
                "status": "skipped",
                "error": f"Missing credentials: {error_msg}",
                "posts": [],
                "practices_extracted": 0,
            }
        
        # Proceed with scraping
        try:
            await self._authenticate()
            posts = await self._fetch_posts(target, limit, time_filter)
            return {
                "status": "success",
                "posts": posts,
                "practices_extracted": len(posts),
            }
        except Exception as e:
            self.logger.error(f"Scraping failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "posts": [],
                "practices_extracted": 0,
            }
    
    @abstractmethod
    async def _authenticate(self) -> None:
        """Authenticate with the service."""
        pass
    
    @abstractmethod
    async def _fetch_posts(
        self,
        target: Optional[str],
        limit: int,
        time_filter: str,
    ) -> List[ScrapedPost]:
        """Fetch posts from the source."""
        pass