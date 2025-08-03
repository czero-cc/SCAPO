"""Hacker News scraper for AI/ML discussions."""

import httpx
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.core.logging import get_logger
from src.core.models import ScrapedPost, SourceType
from src.scrapers.base import BaseScraper

logger = get_logger(__name__)


class HackerNewsScraper(BaseScraper):
    """Scraper for Hacker News using Firebase API."""
    
    def __init__(self):
        super().__init__(SourceType.FORUM)  # Treating HN as a forum
        self.client = httpx.AsyncClient(
            headers={"User-Agent": "SOTA-Practices-Bot/1.0"},
            timeout=30.0,
        )
        self.base_url = "https://hacker-news.firebaseio.com/v0"
        self.algolia_url = "https://hn.algolia.com/api/v1"
    
    async def authenticate(self) -> None:
        """No authentication needed for HN API."""
        logger.info("Accessing Hacker News API")
    
    async def fetch_posts(
        self,
        subreddit: Optional[str] = None,  # Search query
        limit: int = 100,
        time_filter: str = "week",
    ) -> List[ScrapedPost]:
        """Fetch posts from Hacker News."""
        posts = []
        
        # Use Algolia search for AI-related content
        search_queries = [
            "prompt engineering",
            "LLM best practices",
            "GPT tips",
            "stable diffusion guide",
            "AI prompting",
            "generative AI tutorial",
        ]
        
        if subreddit:  # Use as search query if provided
            search_queries = [subreddit]
        
        for query in search_queries:
            try:
                search_posts = await self._search_posts(query, limit=20)
                posts.extend(search_posts)
            except Exception as e:
                logger.error(f"Error searching HN for '{query}': {e}")
        
        # Also fetch from top stories and filter
        try:
            top_posts = await self._fetch_top_stories(limit=50)
            posts.extend(top_posts)
        except Exception as e:
            logger.error(f"Error fetching HN top stories: {e}")
        
        # Deduplicate by ID
        seen_ids = set()
        unique_posts = []
        for post in posts:
            if post.post_id not in seen_ids:
                seen_ids.add(post.post_id)
                unique_posts.append(post)
        
        # Sort by relevance score
        unique_posts.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return unique_posts[:limit]
    
    async def _search_posts(self, query: str, limit: int = 20) -> List[ScrapedPost]:
        """Search for posts using Algolia API."""
        posts = []
        
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": limit,
        }
        
        try:
            response = await self.client.get(f"{self.algolia_url}/search", params=params)
            response.raise_for_status()
            
            data = response.json()
            hits = data.get("hits", [])
            
            for hit in hits:
                post = await self._process_algolia_hit(hit)
                if post:
                    posts.append(post)
        
        except Exception as e:
            logger.error(f"Error searching Algolia: {e}")
        
        return posts
    
    async def _fetch_top_stories(self, limit: int = 50) -> List[ScrapedPost]:
        """Fetch top stories and filter for AI content."""
        posts = []
        
        try:
            # Get top story IDs
            response = await self.client.get(f"{self.base_url}/topstories.json")
            response.raise_for_status()
            
            story_ids = response.json()[:limit]
            
            # Fetch stories in parallel
            tasks = [self._fetch_item(item_id) for item_id in story_ids]
            items = await asyncio.gather(*tasks, return_exceptions=True)
            
            for item in items:
                if isinstance(item, Exception):
                    continue
                if item and self._is_ai_related(item):
                    post = await self._process_hn_item(item)
                    if post:
                        posts.append(post)
        
        except Exception as e:
            logger.error(f"Error fetching top stories: {e}")
        
        return posts
    
    async def _fetch_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single HN item."""
        try:
            response = await self.client.get(f"{self.base_url}/item/{item_id}.json")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching item {item_id}: {e}")
            return None
    
    def _is_ai_related(self, item: Dict[str, Any]) -> bool:
        """Check if an item is related to AI/ML."""
        title = item.get("title", "").lower()
        text = item.get("text", "").lower()
        url = item.get("url", "").lower()
        
        ai_keywords = [
            "ai", "ml", "llm", "gpt", "claude", "prompt", "generative",
            "stable diffusion", "midjourney", "langchain", "hugging face",
            "machine learning", "neural", "transformer", "fine-tun"
        ]
        
        combined_text = f"{title} {text} {url}"
        return any(keyword in combined_text for keyword in ai_keywords)
    
    async def _process_algolia_hit(self, hit: Dict[str, Any]) -> Optional[ScrapedPost]:
        """Process an Algolia search hit into ScrapedPost."""
        try:
            # Fetch full item details including comments
            item_id = hit["objectID"]
            item = await self._fetch_item(int(item_id))
            
            if not item:
                return None
            
            # Extract practices from comments
            practices = await self._extract_practices_from_comments(item)
            
            # Calculate relevance
            relevance_score = self._calculate_relevance(hit, practices)
            
            return ScrapedPost(
                source_type=self.source_type,
                post_id=f"hn_{item_id}",
                url=f"https://news.ycombinator.com/item?id={item_id}",
                title=hit.get("title", ""),
                content=hit.get("story_text") or hit.get("comment_text") or "",
                author=hit.get("author", "unknown"),
                created_at=datetime.fromtimestamp(hit.get("created_at_i", 0)),
                score=hit.get("points", 0),
                relevance_score=relevance_score,
                extracted_practices=practices,
                metadata={
                    "num_comments": hit.get("num_comments", 0),
                    "url": hit.get("url"),
                    "tags": hit.get("_tags", []),
                }
            )
        except Exception as e:
            logger.error(f"Error processing Algolia hit: {e}")
            return None
    
    async def _process_hn_item(self, item: Dict[str, Any]) -> Optional[ScrapedPost]:
        """Process a HN item into ScrapedPost."""
        try:
            # Extract practices from comments
            practices = await self._extract_practices_from_comments(item)
            
            # Calculate relevance
            relevance_score = self._calculate_relevance(item, practices)
            
            return ScrapedPost(
                source_type=self.source_type,
                post_id=f"hn_{item['id']}",
                url=f"https://news.ycombinator.com/item?id={item['id']}",
                title=item.get("title", ""),
                content=item.get("text", ""),
                author=item.get("by", "unknown"),
                created_at=datetime.fromtimestamp(item.get("time", 0)),
                score=item.get("score", 0),
                relevance_score=relevance_score,
                extracted_practices=practices,
                metadata={
                    "type": item.get("type"),
                    "url": item.get("url"),
                    "descendants": item.get("descendants", 0),
                }
            )
        except Exception as e:
            logger.error(f"Error processing HN item: {e}")
            return None
    
    async def _extract_practices_from_comments(
        self, item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract practices from HN comments."""
        practices = {
            "insights": [],
            "code_snippets": [],
            "recommendations": [],
            "criticisms": [],
            "resources": [],
        }
        
        # Get top-level comments
        kid_ids = item.get("kids", [])[:20]  # Limit to top 20 comments
        
        if not kid_ids:
            return practices
        
        # Fetch comments in parallel
        tasks = [self._fetch_item(kid_id) for kid_id in kid_ids]
        comments = await asyncio.gather(*tasks, return_exceptions=True)
        
        for comment in comments:
            if isinstance(comment, Exception) or not comment:
                continue
            
            text = comment.get("text", "")
            if not text:
                continue
            
            # Extract insights (high-score comments)
            if comment.get("score", 0) > 10:
                practices["insights"].append({
                    "text": text[:500],
                    "author": comment.get("by"),
                    "score": comment.get("score", 0),
                })
            
            # Extract code snippets
            import re
            code_blocks = re.findall(r"<pre><code>(.*?)</code></pre>", text, re.DOTALL)
            for code in code_blocks:
                if len(code) > 20:
                    practices["code_snippets"].append(code.strip())
            
            # Extract recommendations
            if any(kw in text.lower() for kw in ["recommend", "suggest", "should use", "try"]):
                practices["recommendations"].append(text[:300])
            
            # Extract resources (links)
            links = re.findall(r"https?://[^\s<>\"]+", text)
            for link in links:
                if any(domain in link for domain in ["github.com", "arxiv.org", "huggingface.co"]):
                    practices["resources"].append(link)
        
        return practices
    
    def _calculate_relevance(
        self, item: Dict[str, Any], practices: Dict[str, Any]
    ) -> float:
        """Calculate relevance score for HN item."""
        score = 0.0
        
        title = item.get("title", "").lower()
        
        # Title relevance
        ai_terms = ["prompt", "llm", "gpt", "ai", "ml", "generative"]
        practice_terms = ["guide", "tutorial", "best practice", "tips", "how to"]
        
        ai_matches = sum(1 for term in ai_terms if term in title)
        practice_matches = sum(1 for term in practice_terms if term in title)
        
        score += min(ai_matches * 0.15, 0.3)
        score += min(practice_matches * 0.2, 0.4)
        
        # Engagement score
        points = item.get("points", 0) or item.get("score", 0)
        comments = item.get("num_comments", 0) or item.get("descendants", 0)
        
        if points > 50:
            score += 0.1
        if points > 200:
            score += 0.1
        if comments > 20:
            score += 0.1
        
        # Practice extraction success
        if practices.get("insights"):
            score += 0.1
        if practices.get("code_snippets"):
            score += 0.1
        
        return min(score, 1.0)
    
    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Extract and consolidate best practices from HN posts."""
        consolidated = {
            "trending_topics": [],
            "expert_insights": [],
            "code_examples": [],
            "recommended_resources": [],
            "discussions": [],
        }
        
        for post in posts:
            practices = post.extracted_practices
            
            # Track trending topics
            if post.score > 50:
                consolidated["trending_topics"].append({
                    "title": post.title,
                    "url": post.url,
                    "score": post.score,
                    "comments": post.metadata.get("num_comments", 0),
                    "date": post.created_at.isoformat(),
                })
            
            # Collect expert insights
            for insight in practices.get("insights", []):
                if insight["score"] > 20:
                    consolidated["expert_insights"].append({
                        "insight": insight["text"],
                        "author": insight["author"],
                        "score": insight["score"],
                        "context": post.title,
                        "url": post.url,
                    })
            
            # Collect code examples
            for code in practices.get("code_snippets", []):
                consolidated["code_examples"].append({
                    "code": code,
                    "context": post.title,
                    "url": post.url,
                })
            
            # Collect resources
            for resource in practices.get("resources", []):
                consolidated["recommended_resources"].append({
                    "url": resource,
                    "found_in": post.title,
                    "discussion_url": post.url,
                })
        
        # Sort and limit
        consolidated["trending_topics"] = sorted(
            consolidated["trending_topics"],
            key=lambda x: x["score"],
            reverse=True
        )[:20]
        
        consolidated["expert_insights"] = sorted(
            consolidated["expert_insights"],
            key=lambda x: x["score"],
            reverse=True
        )[:30]
        
        # Deduplicate resources
        seen_resources = set()
        unique_resources = []
        for resource in consolidated["recommended_resources"]:
            if resource["url"] not in seen_resources:
                seen_resources.add(resource["url"])
                unique_resources.append(resource)
        consolidated["recommended_resources"] = unique_resources[:50]
        
        return consolidated
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()