"""GitHub scraper for awesome lists and documentation."""

import re
import httpx
import yaml
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path

from src.core.logging import get_logger
from src.core.models import ScrapedPost, SourceType
from src.scrapers.base import BaseScraper

logger = get_logger(__name__)


class GitHubScraper(BaseScraper):
    """Scraper for GitHub repositories with AI best practices."""
    
    def __init__(self):
        super().__init__(SourceType.GITHUB)
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "SOTA-Practices-Bot/1.0",
                "Accept": "application/vnd.github.v3+json",
            },
            timeout=30.0,
        )
        self.github_token = None  # Set via authenticate()
    
    async def authenticate(self) -> None:
        """Authenticate with GitHub API using PAT if available."""
        # In production, load from settings
        # For now, we'll use unauthenticated requests
        logger.info("Using unauthenticated GitHub access")
    
    async def fetch_posts(
        self,
        subreddit: Optional[str] = None,  # Not used for GitHub
        limit: int = 100,
        time_filter: str = "week",  # Not used for GitHub
    ) -> List[ScrapedPost]:
        """Fetch content from GitHub repositories."""
        from src.scrapers.source_manager import SourceManager
        
        manager = SourceManager()
        sources = manager.get_github_sources()
        
        all_posts = []
        
        for source in sources:
            if source.get("priority") in ["high", "medium"]:
                try:
                    post = await self._fetch_github_content(source)
                    if post:
                        all_posts.append(post)
                except Exception as e:
                    logger.error(f"Error fetching {source['name']}: {e}")
        
        return all_posts[:limit]
    
    async def _fetch_github_content(self, source: Dict[str, Any]) -> Optional[ScrapedPost]:
        """Fetch content from a GitHub repository."""
        raw_url = source.get("raw_url")
        if not raw_url:
            return None
        
        try:
            response = await self.client.get(raw_url)
            response.raise_for_status()
            
            content = response.text
            
            # Extract practices from markdown
            practices = self._extract_practices_from_markdown(content, source)
            
            # Calculate relevance based on content
            relevance_score = self._calculate_relevance_score(content, practices)
            
            return ScrapedPost(
                source_type=self.source_type,
                post_id=f"github_{source['name'].replace(' ', '_').lower()}",
                url=source["url"],
                title=source["name"],
                content=content[:5000],  # Limit content size
                author=source["url"].split("/")[3],  # Extract org/user from URL
                created_at=datetime.utcnow(),  # Would need GitHub API for real date
                score=100,  # GitHub repos don't have scores
                relevance_score=relevance_score,
                extracted_practices=practices,
                metadata={
                    "license": source.get("license", "Unknown"),
                    "focus": source.get("focus", ""),
                    "update_frequency": source.get("update_frequency", "unknown"),
                    "source_type": "awesome_list",
                }
            )
        except Exception as e:
            logger.error(f"Error fetching GitHub content from {raw_url}: {e}")
            return None
    
    def _extract_practices_from_markdown(
        self, content: str, source: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract best practices from markdown content."""
        practices = {
            "sections": [],
            "links": [],
            "code_examples": [],
            "tips": [],
            "tools": [],
        }
        
        # Extract sections
        sections = re.findall(r"^#{1,3}\s+(.+)$", content, re.MULTILINE)
        practices["sections"] = sections[:20]  # Top sections
        
        # Extract links with descriptions
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)(?:\s*[-–]\s*(.+))?"
        links = re.findall(link_pattern, content)
        for text, url, desc in links[:50]:  # Limit to 50 links
            if any(keyword in text.lower() for keyword in ["prompt", "guide", "best", "practice", "tip"]):
                practices["links"].append({
                    "text": text,
                    "url": url,
                    "description": desc or "",
                })
        
        # Extract code blocks
        code_blocks = re.findall(r"```(?:\w+)?\n(.*?)```", content, re.DOTALL)
        for code in code_blocks[:10]:  # Limit to 10 examples
            if len(code.strip()) > 20:  # Skip trivial examples
                practices["code_examples"].append(code.strip())
        
        # Extract tips (lines starting with tip indicators)
        tip_pattern = r"^[\*\-]\s*\*\*(Tip|Note|Important|Best Practice):\*\*\s*(.+)$"
        tips = re.findall(tip_pattern, content, re.MULTILINE | re.IGNORECASE)
        for tip_type, tip_text in tips:
            practices["tips"].append({
                "type": tip_type.lower(),
                "text": tip_text.strip(),
            })
        
        # Extract tools/libraries mentioned
        tool_pattern = r"`([a-zA-Z0-9\-_\.]+)`"
        tools = re.findall(tool_pattern, content)
        # Filter to likely tool names
        practices["tools"] = list(set(
            tool for tool in tools 
            if len(tool) > 2 and not tool.replace(".", "").isdigit()
        ))[:30]
        
        return practices
    
    def _calculate_relevance_score(
        self, content: str, practices: Dict[str, Any]
    ) -> float:
        """Calculate relevance score for GitHub content."""
        score = 0.5  # Base score for being curated
        
        # Check for relevant keywords
        keywords = [
            "prompt", "prompting", "best practice", "guide", "tutorial",
            "tips", "techniques", "patterns", "examples", "cookbook"
        ]
        
        content_lower = content.lower()
        keyword_count = sum(1 for kw in keywords if kw in content_lower)
        score += min(keyword_count * 0.05, 0.3)
        
        # Boost for having many examples
        if len(practices.get("code_examples", [])) > 5:
            score += 0.1
        
        # Boost for having structured content
        if len(practices.get("sections", [])) > 10:
            score += 0.1
        
        return min(score, 1.0)
    
    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Extract and consolidate best practices from GitHub sources."""
        consolidated = {
            "guides": [],
            "tools": {},
            "code_patterns": [],
            "resources": [],
        }
        
        for post in posts:
            practices = post.extracted_practices
            metadata = post.metadata
            
            # Add as a guide
            consolidated["guides"].append({
                "name": post.title,
                "url": post.url,
                "license": metadata.get("license"),
                "focus": metadata.get("focus"),
                "sections": practices.get("sections", [])[:5],
            })
            
            # Aggregate tools
            for tool in practices.get("tools", []):
                if tool not in consolidated["tools"]:
                    consolidated["tools"][tool] = {
                        "mentions": 0,
                        "sources": [],
                    }
                consolidated["tools"][tool]["mentions"] += 1
                consolidated["tools"][tool]["sources"].append(post.title)
            
            # Collect code patterns
            for code in practices.get("code_examples", []):
                if len(code) < 500:  # Reasonable size
                    consolidated["code_patterns"].append({
                        "code": code,
                        "source": post.title,
                        "url": post.url,
                    })
            
            # Collect high-value resources
            for link in practices.get("links", []):
                if any(kw in link["text"].lower() for kw in ["guide", "tutorial", "course"]):
                    consolidated["resources"].append({
                        "title": link["text"],
                        "url": link["url"],
                        "description": link["description"],
                        "source": post.title,
                    })
        
        # Sort tools by popularity
        consolidated["tools"] = dict(
            sorted(
                consolidated["tools"].items(),
                key=lambda x: x[1]["mentions"],
                reverse=True
            )[:50]  # Top 50 tools
        )
        
        return consolidated
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()