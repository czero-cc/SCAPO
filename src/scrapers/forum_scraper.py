"""Forum scraper for Discourse-based forums."""

import httpx
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.core.models import ScrapedPost, SourceType
from src.scrapers.base import BaseScraper

logger = get_logger(__name__)


class ForumScraper(BaseScraper):
    """Scraper for Discourse forums (OpenAI, Hugging Face, etc.)."""
    
    def __init__(self):
        super().__init__(SourceType.FORUM)
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "SOTA-Practices-Bot/1.0",
                "Accept": "application/json",
            },
            timeout=30.0,
        )
    
    async def authenticate(self) -> None:
        """No authentication needed for public Discourse forums."""
        logger.info("Accessing public Discourse forums")
    
    async def fetch_posts(
        self,
        subreddit: Optional[str] = None,  # Forum name
        limit: int = 100,
        time_filter: str = "week",
    ) -> List[ScrapedPost]:
        """Fetch posts from Discourse forums."""
        from src.scrapers.source_manager import SourceManager
        
        manager = SourceManager()
        sources = manager.get_forum_sources()
        
        all_posts = []
        
        for source in sources:
            if source.get("priority") in ["high", "medium"]:
                try:
                    if subreddit and source["name"].lower() != subreddit.lower():
                        continue
                    
                    posts = await self._fetch_forum_posts(source, limit)
                    all_posts.extend(posts)
                except Exception as e:
                    logger.error(f"Error fetching from {source['name']}: {e}")
        
        return all_posts[:limit]
    
    async def _fetch_forum_posts(
        self, source: Dict[str, Any], limit: int
    ) -> List[ScrapedPost]:
        """Fetch posts from a specific forum."""
        posts = []
        base_url = source["url"].rstrip("/")
        
        # Fetch latest topics
        latest_url = f"{base_url}/latest.json"
        
        try:
            response = await self.client.get(latest_url)
            response.raise_for_status()
            
            data = response.json()
            topics = data.get("topic_list", {}).get("topics", [])
            
            for topic in topics[:limit]:
                # Skip if not relevant
                if not self._is_relevant_topic(topic):
                    continue
                
                # Fetch full topic content
                topic_post = await self._fetch_topic_content(base_url, topic)
                if topic_post:
                    posts.append(topic_post)
            
        except Exception as e:
            logger.error(f"Error fetching forum posts: {e}")
        
        return posts
    
    async def _fetch_topic_content(
        self, base_url: str, topic: Dict[str, Any]
    ) -> Optional[ScrapedPost]:
        """Fetch full content for a topic."""
        topic_id = topic["id"]
        topic_url = f"{base_url}/t/{topic_id}.json"
        
        try:
            response = await self.client.get(topic_url)
            response.raise_for_status()
            
            data = response.json()
            
            # Get first post (topic content)
            posts = data.get("post_stream", {}).get("posts", [])
            if not posts:
                return None
            
            first_post = posts[0]
            
            # Extract practices
            practices = self._extract_practices_from_post(first_post, posts[1:])
            
            # Calculate relevance
            relevance_score = self._calculate_topic_relevance(topic, first_post)
            
            return ScrapedPost(
                source_type=self.source_type,
                post_id=f"forum_{topic_id}",
                url=f"{base_url}/t/{topic['slug']}/{topic_id}",
                title=topic["title"],
                content=first_post.get("cooked", ""),  # HTML content
                author=first_post.get("username", "anonymous"),
                created_at=datetime.fromisoformat(
                    topic["created_at"].replace("Z", "+00:00")
                ),
                score=topic.get("like_count", 0) + topic.get("reply_count", 0),
                relevance_score=relevance_score,
                extracted_practices=practices,
                metadata={
                    "forum": base_url,
                    "views": topic.get("views", 0),
                    "reply_count": topic.get("reply_count", 0),
                    "category_id": topic.get("category_id"),
                    "tags": topic.get("tags", []),
                    "pinned": topic.get("pinned", False),
                }
            )
        except Exception as e:
            logger.error(f"Error fetching topic {topic_id}: {e}")
            return None
    
    def _is_relevant_topic(self, topic: Dict[str, Any]) -> bool:
        """Check if a topic is relevant to AI practices."""
        title = topic.get("title", "").lower()
        
        # Skip closed/archived topics
        if topic.get("closed") or topic.get("archived"):
            return False
        
        # Check for relevant keywords
        keywords = [
            "prompt", "best practice", "guide", "tutorial", "tip",
            "how to", "parameter", "setting", "config", "optimization"
        ]
        
        return any(keyword in title for keyword in keywords)
    
    def _calculate_topic_relevance(
        self, topic: Dict[str, Any], post: Dict[str, Any]
    ) -> float:
        """Calculate relevance score for a forum topic."""
        score = 0.0
        
        title = topic.get("title", "").lower()
        content = post.get("cooked", "").lower()
        
        # Title relevance
        title_keywords = ["prompt", "guide", "tutorial", "best practice", "tips"]
        title_matches = sum(1 for kw in title_keywords if kw in title)
        score += min(title_matches * 0.2, 0.4)
        
        # Content relevance
        content_keywords = [
            "example", "code", "parameter", "setting", "recommend",
            "optimal", "avoid", "mistake", "improve", "performance"
        ]
        content_matches = sum(1 for kw in content_keywords if kw in content)
        score += min(content_matches * 0.1, 0.3)
        
        # Engagement score
        engagement = topic.get("like_count", 0) + topic.get("reply_count", 0)
        if engagement > 10:
            score += 0.1
        if engagement > 50:
            score += 0.1
        
        # Pinned topics are usually important
        if topic.get("pinned"):
            score += 0.1
        
        return min(score, 1.0)
    
    def _extract_practices_from_post(
        self, post: Dict[str, Any], replies: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Extract practices from forum post and replies."""
        import re
        from bs4 import BeautifulSoup
        
        practices = {
            "code_snippets": [],
            "recommendations": [],
            "solutions": [],
            "warnings": [],
        }
        
        # Parse HTML content
        soup = BeautifulSoup(post.get("cooked", ""), "html.parser")
        
        # Extract code blocks
        code_blocks = soup.find_all("pre")
        for block in code_blocks[:5]:  # Limit to 5
            code = block.get_text().strip()
            if len(code) > 20:
                practices["code_snippets"].append({
                    "code": code,
                    "language": block.get("class", [""])[0] if block.get("class") else "unknown",
                })
        
        # Extract recommendations (often in lists)
        lists = soup.find_all(["ul", "ol"])
        for lst in lists:
            items = lst.find_all("li")
            for item in items:
                text = item.get_text().strip()
                if any(kw in text.lower() for kw in ["recommend", "suggest", "should", "best"]):
                    practices["recommendations"].append(text)
        
        # Look for solution patterns in replies
        for reply in replies[:10]:  # Check first 10 replies
            reply_soup = BeautifulSoup(reply.get("cooked", ""), "html.parser")
            reply_text = reply_soup.get_text().lower()
            
            if any(kw in reply_text for kw in ["solution", "fixed", "solved", "works"]):
                practices["solutions"].append({
                    "text": reply_soup.get_text().strip()[:500],
                    "author": reply.get("username"),
                    "likes": reply.get("like_count", 0),
                })
        
        # Extract warnings
        warning_patterns = [
            r"(?:warning|caution|note|important):\s*(.+?)(?:\.|$)",
            r"(?:don't|avoid|never)\s+(.+?)(?:\.|$)",
        ]
        
        text = soup.get_text()
        for pattern in warning_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            practices["warnings"].extend(matches[:5])
        
        return practices
    
    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Extract and consolidate best practices from forum posts."""
        consolidated = {
            "solutions": [],
            "code_examples": [],
            "recommendations": [],
            "common_issues": [],
            "popular_topics": [],
        }
        
        for post in posts:
            practices = post.extracted_practices
            
            # Collect solutions
            for solution in practices.get("solutions", []):
                if solution.get("likes", 0) > 0:  # Validated solutions
                    consolidated["solutions"].append({
                        "problem": post.title,
                        "solution": solution["text"],
                        "author": solution["author"],
                        "url": post.url,
                        "likes": solution["likes"],
                    })
            
            # Collect code examples
            for snippet in practices.get("code_snippets", []):
                consolidated["code_examples"].append({
                    "code": snippet["code"],
                    "language": snippet["language"],
                    "context": post.title,
                    "url": post.url,
                })
            
            # Collect recommendations
            consolidated["recommendations"].extend(
                practices.get("recommendations", [])
            )
            
            # Track popular topics
            if post.metadata.get("views", 0) > 100 or post.score > 10:
                consolidated["popular_topics"].append({
                    "title": post.title,
                    "url": post.url,
                    "views": post.metadata.get("views", 0),
                    "engagement": post.score,
                })
        
        # Sort by popularity/relevance
        consolidated["solutions"] = sorted(
            consolidated["solutions"],
            key=lambda x: x["likes"],
            reverse=True
        )[:20]
        
        consolidated["popular_topics"] = sorted(
            consolidated["popular_topics"],
            key=lambda x: x["engagement"],
            reverse=True
        )[:10]
        
        # Deduplicate recommendations
        consolidated["recommendations"] = list(set(consolidated["recommendations"]))[:30]
        
        return consolidated
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()