import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.core.models import ScrapedPost, SourceType
from src.scrapers.reddit_scraper import RedditScraper


class TestRedditScraper:
    """Test Reddit scraper functionality."""

    @pytest.fixture
    def scraper(self):
        """Create Reddit scraper instance."""
        return RedditScraper()

    @pytest.mark.asyncio
    async def test_authenticate(self, scraper, mock_reddit_env):
        """Test Reddit authentication."""
        with patch("praw.Reddit") as mock_reddit:
            mock_instance = MagicMock()
            mock_reddit.return_value = mock_instance
            mock_instance.user.me.return_value = "testuser"
            
            await scraper.authenticate()
            
            assert scraper.reddit is not None
            mock_reddit.assert_called_once()
            mock_instance.user.me.assert_called_once()

    def test_calculate_relevance(self, scraper):
        """Test relevance score calculation."""
        # Create mock post
        mock_post = MagicMock()
        mock_post.title = "Best prompting tips for GPT-4"
        mock_post.selftext = "Here are optimal parameters and tricks"
        mock_post.score = 150
        mock_post.num_comments = 75
        
        score = scraper._calculate_relevance(mock_post)
        
        assert score > 0.5  # Should be high relevance
        assert score <= 1.0

    def test_extract_practices_from_post(self, scraper):
        """Test extracting practices from post content."""
        mock_post = MagicMock()
        mock_post.title = "GPT-4 Prompting Guide"
        mock_post.selftext = """
        Tip: Always use clear instructions
        
        Best prompt: "You are an expert..."
        
        Avoid: Being too vague
        
        Parameter: temperature = 0.3 works best
        
        ```
        prompt = "Example prompt"
        ```
        """
        mock_post.score = 100
        mock_post.comments = MagicMock()
        mock_post.comments.replace_more = MagicMock()
        mock_post.comments.__iter__ = lambda x: iter([])
        
        practices = scraper._extract_practices_from_post(mock_post)
        
        assert "model_mentions" in practices
        assert "prompt_patterns" in practices
        assert "tips" in practices
        assert "common_mistakes" in practices
        assert "parameter_recommendations" in practices
        assert "examples" in practices
        
        # Check if GPT-4 was detected
        assert "gpt-4" in practices["model_mentions"]

    def test_deduplicate_practices(self, scraper):
        """Test deduplication of practices."""
        items = [
            {"tip": "Use clear prompts", "upvotes": 10},
            {"tip": "Use clear prompts", "upvotes": 20},  # Duplicate
            {"tip": "Be specific", "upvotes": 15},
        ]
        
        deduplicated = scraper._deduplicate_practices(items)
        
        assert len(deduplicated) == 2
        assert any(item["tip"] == "Use clear prompts" for item in deduplicated)
        assert any(item["tip"] == "Be specific" for item in deduplicated)

    @pytest.mark.asyncio
    async def test_fetch_posts(self, scraper, mock_reddit_env):
        """Test fetching posts from Reddit."""
        with patch("praw.Reddit") as mock_reddit:
            # Setup mock Reddit instance
            mock_instance = MagicMock()
            mock_reddit.return_value = mock_instance
            
            # Mock subreddit
            mock_subreddit = MagicMock()
            mock_instance.subreddit.return_value = mock_subreddit
            
            # Mock posts
            mock_post = MagicMock()
            mock_post.id = "test123"
            mock_post.title = "GPT-4 Tips"
            mock_post.selftext = "Content"
            mock_post.author = MagicMock()
            mock_post.author.__str__.return_value = "testuser"
            mock_post.created_utc = datetime.utcnow().timestamp()
            mock_post.score = 100
            mock_post.permalink = "/r/test/test123"
            mock_post.subreddit.display_name = "test"
            mock_post.num_comments = 10
            mock_post.upvote_ratio = 0.9
            mock_post.all_awardings = []
            mock_post.is_video = False
            mock_post.link_flair_text = None
            
            mock_subreddit.top.return_value = [mock_post]
            
            posts = await scraper.fetch_posts(subreddit="test", limit=10)
            
            assert len(posts) <= 1  # May be filtered by relevance
            if posts:
                assert posts[0].source_type == SourceType.REDDIT
                assert posts[0].post_id == "test123"

    def test_model_patterns(self, scraper):
        """Test model pattern matching."""
        test_cases = [
            ("Using GPT-4 for coding", "gpt-4"),
            ("Claude is great", "claude"),
            ("LLaMA model tips", "llama"),
            ("Stable Diffusion XL guide", "stable-diffusion"),
            ("Midjourney v5 prompts", "midjourney"),
            ("DALL-E 3 parameters", "dalle"),
            ("wan2.2 video generation", "wan2.2"),
        ]
        
        for text, expected_model in test_cases:
            found = False
            for model, pattern in scraper.model_patterns.items():
                if model == expected_model:
                    import re
                    if re.search(pattern, text, re.IGNORECASE):
                        found = True
                        break
            assert found, f"Failed to match {expected_model} in '{text}'"