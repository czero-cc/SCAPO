import re
from datetime import datetime
from typing import Any, Dict, List, Optional

import praw
from praw.models import Submission

from src.core.config import settings
from src.core.logging import get_logger
from src.core.models import ScrapedPost, Source, SourceType
from src.scrapers.base import BaseScraper


class RedditScraper(BaseScraper):
    """Scraper for Reddit using PRAW."""

    def __init__(self) -> None:
        super().__init__(SourceType.REDDIT)
        self.reddit: Optional[praw.Reddit] = None
        self.logger = get_logger(__name__)
        
        # AI model patterns to look for
        self.model_patterns = {
            "gpt-4": r"gpt-?4|gpt4|chatgpt.*4",
            "claude": r"claude|anthropic",
            "llama": r"llama|meta.*llama",
            "stable-diffusion": r"stable.*diffusion|sd\s*x?l?|sdxl",
            "midjourney": r"midjourney|mj\s*v?\d*",
            "dalle": r"dall-?e|dalle",
            "wan2.2": r"wan.*2\.2|wan22",
        }
        
        # Practice extraction patterns
        self.practice_patterns = {
            "prompt_pattern": [
                r"prompt[:\s]+[\"']([^\"']+)[\"']",
                r"try.*prompt[:\s]+(.+?)(?:\n|$)",
                r"best.*prompt.*:(.+?)(?:\n|$)",
            ],
            "parameter": [
                r"set.*(\w+)\s*=\s*([\d.]+)",
                r"parameter[:\s]+(\w+)\s*[=:]\s*([\w.]+)",
                r"(\w+):\s*([\d.]+).*(?:works|best|optimal)",
            ],
            "tip": [
                r"tip[:\s]+(.+?)(?:\n|$)",
                r"pro\s*tip[:\s]+(.+?)(?:\n|$)",
                r"trick[:\s]+(.+?)(?:\n|$)",
            ],
            "pitfall": [
                r"avoid[:\s]+(.+?)(?:\n|$)",
                r"don't[:\s]+(.+?)(?:\n|$)",
                r"mistake[:\s]+(.+?)(?:\n|$)",
                r"pitfall[:\s]+(.+?)(?:\n|$)",
            ],
        }

    async def authenticate(self) -> None:
        """Authenticate with Reddit API."""
        try:
            self.reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                user_agent=settings.reddit_user_agent,
            )
            # Test authentication
            self.reddit.user.me()
            self.logger.info("Successfully authenticated with Reddit")
        except Exception as e:
            self.logger.error("Failed to authenticate with Reddit", error=str(e))
            raise

    async def fetch_posts(
        self,
        subreddit: Optional[str] = None,
        limit: int = 100,
        time_filter: str = "week",
    ) -> List[ScrapedPost]:
        """Fetch posts from Reddit subreddit."""
        if not self.reddit:
            await self.authenticate()
        
        if not subreddit:
            # Default subreddits for AI practices
            subreddits = [
                "LocalLLaMA", "StableDiffusion", "midjourney",
                "OpenAI", "ClaudeAI", "singularity", "MachineLearning"
            ]
        else:
            subreddits = [subreddit]
        
        all_posts = []
        
        for sub_name in subreddits:
            try:
                subreddit_obj = self.reddit.subreddit(sub_name)
                
                # Fetch top posts
                posts = subreddit_obj.top(time_filter=time_filter, limit=limit)
                
                for post in posts:
                    if post.score < settings.min_upvote_ratio * 100:
                        continue
                    
                    scraped_post = await self._process_reddit_post(post)
                    if scraped_post:
                        all_posts.append(scraped_post)
                
                self.logger.info(
                    f"Fetched posts from r/{sub_name}",
                    count=len([p for p in all_posts if p.metadata.get("subreddit") == sub_name])
                )
                
            except Exception as e:
                self.logger.error(f"Error fetching from r/{sub_name}", error=str(e))
                continue
        
        return all_posts

    async def _process_reddit_post(self, post: Submission) -> Optional[ScrapedPost]:
        """Process a Reddit post into ScrapedPost format."""
        try:
            # Calculate relevance based on keywords and patterns
            relevance_score = self._calculate_relevance(post)
            
            if relevance_score < 0.3:  # Skip low relevance posts
                return None
            
            # Extract practices from post and top comments
            practices = self._extract_practices_from_post(post)
            
            return ScrapedPost(
                source_type=self.source_type,
                post_id=post.id,
                url=f"https://reddit.com{post.permalink}",
                title=post.title,
                content=post.selftext or "",
                author=str(post.author) if post.author else "deleted",
                created_at=datetime.fromtimestamp(post.created_utc),
                score=post.score,
                relevance_score=relevance_score,
                extracted_practices=practices,
                metadata={
                    "subreddit": post.subreddit.display_name,
                    "num_comments": post.num_comments,
                    "upvote_ratio": post.upvote_ratio,
                    "awards": len(post.all_awardings),
                    "is_video": post.is_video,
                    "link_flair_text": post.link_flair_text,
                },
            )
        except Exception as e:
            self.logger.error(f"Error processing post {post.id}", error=str(e))
            return None

    def _calculate_relevance(self, post: Submission) -> float:
        """Calculate relevance score for a post."""
        score = 0.0
        text = f"{post.title} {post.selftext}".lower()
        
        # Check for AI model mentions
        for model, pattern in self.model_patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                score += 0.3
        
        # Check for practice-related keywords
        practice_keywords = [
            "prompt", "parameter", "setting", "config", "tip", "trick",
            "best practice", "optimal", "recommend", "avoid", "mistake",
            "guide", "tutorial", "how to", "workflow"
        ]
        
        keyword_count = sum(1 for kw in practice_keywords if kw in text)
        score += min(keyword_count * 0.1, 0.5)
        
        # Boost for high engagement
        if post.score > 100:
            score += 0.1
        if post.num_comments > 50:
            score += 0.1
        
        return min(score, 1.0)

    def _extract_practices_from_post(self, post: Submission) -> Dict[str, Any]:
        """Extract best practices from post content and comments."""
        practices = {
            "prompt_patterns": [],
            "parameter_recommendations": [],
            "tips": [],
            "common_mistakes": [],
            "examples": [],
            "model_mentions": [],
        }
        
        # Combine post content and top comments
        full_text = f"{post.title}\n{post.selftext}"
        
        # Get top comments
        post.comments.replace_more(limit=0)
        top_comments = sorted(post.comments, key=lambda x: x.score, reverse=True)[:10]
        
        for comment in top_comments:
            if hasattr(comment, "body"):
                full_text += f"\n{comment.body}"
        
        # Extract model mentions
        for model, pattern in self.model_patterns.items():
            if re.search(pattern, full_text, re.IGNORECASE):
                practices["model_mentions"].append(model)
        
        # Extract prompts
        for pattern in self.practice_patterns["prompt_pattern"]:
            matches = re.findall(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                practices["prompt_patterns"].append({
                    "pattern": match.strip(),
                    "source": "reddit",
                    "confidence": 0.7,
                })
        
        # Extract parameters
        for pattern in self.practice_patterns["parameter"]:
            matches = re.findall(pattern, full_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    practices["parameter_recommendations"].append({
                        "name": match[0],
                        "value": match[1],
                        "source": "reddit",
                        "confidence": 0.6,
                    })
        
        # Extract tips
        for pattern in self.practice_patterns["tip"]:
            matches = re.findall(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                practices["tips"].append({
                    "tip": match.strip(),
                    "source": "reddit",
                    "upvotes": post.score,
                })
        
        # Extract pitfalls
        for pattern in self.practice_patterns["pitfall"]:
            matches = re.findall(pattern, full_text, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                practices["common_mistakes"].append({
                    "mistake": match.strip(),
                    "source": "reddit",
                    "upvotes": post.score,
                })
        
        # Extract code examples
        code_blocks = re.findall(r"```(.*?)```", full_text, re.DOTALL)
        for code in code_blocks:
            if any(kw in code.lower() for kw in ["prompt", "parameter", "config"]):
                practices["examples"].append({
                    "code": code.strip(),
                    "source": "reddit",
                    "context": post.title,
                })
        
        return practices

    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Extract and consolidate best practices from multiple posts."""
        consolidated = {
            "prompting": {},
            "parameters": {},
            "pitfalls": [],
            "tips": [],
            "examples": [],
            "models": {},
        }
        
        for post in posts:
            practices = post.extracted_practices
            
            # Group by model
            for model in practices.get("model_mentions", []):
                if model not in consolidated["models"]:
                    consolidated["models"][model] = {
                        "prompts": [],
                        "parameters": [],
                        "tips": [],
                        "sources": [],
                    }
                
                consolidated["models"][model]["sources"].append({
                    "url": post.url,
                    "score": post.score,
                    "date": post.created_at.isoformat(),
                })
                
                # Add model-specific practices
                for prompt in practices.get("prompt_patterns", []):
                    consolidated["models"][model]["prompts"].append(prompt)
                
                for param in practices.get("parameter_recommendations", []):
                    consolidated["models"][model]["parameters"].append(param)
                
                for tip in practices.get("tips", []):
                    consolidated["models"][model]["tips"].append(tip)
            
            # Add to general collections
            consolidated["tips"].extend(practices.get("tips", []))
            consolidated["pitfalls"].extend(practices.get("common_mistakes", []))
            consolidated["examples"].extend(practices.get("examples", []))
        
        # Sort and deduplicate
        for model_data in consolidated["models"].values():
            model_data["prompts"] = self._deduplicate_practices(model_data["prompts"])
            model_data["parameters"] = self._deduplicate_practices(model_data["parameters"])
            model_data["tips"] = sorted(
                model_data["tips"],
                key=lambda x: x.get("upvotes", 0),
                reverse=True
            )[:20]
        
        consolidated["tips"] = sorted(
            self._deduplicate_practices(consolidated["tips"]),
            key=lambda x: x.get("upvotes", 0),
            reverse=True
        )[:50]
        
        consolidated["pitfalls"] = self._deduplicate_practices(consolidated["pitfalls"])[:30]
        
        return consolidated

    def _deduplicate_practices(self, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate practices based on content similarity."""
        seen = set()
        unique = []
        
        for item in items:
            # Create a simple hash of the main content
            content = str(item.get("pattern", "")) + str(item.get("tip", "")) + str(item.get("mistake", ""))
            content_hash = hash(content.lower().strip())
            
            if content_hash not in seen:
                seen.add(content_hash)
                unique.append(item)
        
        return unique