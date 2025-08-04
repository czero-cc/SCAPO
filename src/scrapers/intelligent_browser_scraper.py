"""Intelligent browser-based scraper with LLM entity extraction."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field

from playwright.async_api import Page, async_playwright
from pydantic import BaseModel

from src.core.logging import get_logger
from src.core.models import ScrapedPost, SourceType
from src.scrapers.browser_base import BrowserBaseScraper
from src.services.llm_processor import LLMProcessorFactory
from src.services.model_service import ModelService
from src.core.config import settings


logger = get_logger(__name__)


@dataclass
class ExtractedEntities:
    """Entities extracted from content by LLM."""
    models_mentioned: List[str] = field(default_factory=list)
    theme: str = "general"  # prompting, fine-tuning, deployment, benchmarks, etc.
    techniques: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_ai_related: bool = False
    relevance_score: float = 0.0
    summary: str = ""


@dataclass
class ProcessedContent:
    """Content after LLM processing."""
    original_text: str
    entities: ExtractedEntities
    best_practices: List[Dict[str, Any]] = field(default_factory=list)
    source_url: str = ""
    source_type: str = ""
    timestamp: str = ""


class IntelligentBrowserScraper(BrowserBaseScraper):
    """Smart scraper that uses LLM for entity extraction and content processing."""
    
    def __init__(self):
        super().__init__(SourceType.FORUM, headless=True)
        self.model_service = ModelService()
        self.processed_content: List[ProcessedContent] = []
        self.scrape_delay = 2.0  # Default polite delay
        
    async def fetch_posts(self, subreddit: Optional[str] = None, limit: int = 100, time_filter: str = "week") -> List[ScrapedPost]:
        """Required abstract method - handled by scrape_sources instead."""
        return []
    
    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Required abstract method - handled by LLM processing instead."""
        return {}
        
    async def extract_entities_with_llm(self, content: str, source: str) -> ExtractedEntities:
        """Use LLM to extract entities from content."""
        processor = LLMProcessorFactory.create_processor(
            provider=settings.llm_provider,
            base_url=settings.local_llm_url,
            api_type=settings.local_llm_type,
            max_chars=2000  # Smaller for entity extraction
        )
        
        try:
            # Create extraction prompt
            prompt = f"""Analyze this {source} content and extract key entities.

Content:
{content[:2000]}

Extract the following in JSON format:
{{
    "models_mentioned": ["exact model names as mentioned in the text, including version numbers"],
    "theme": "main theme: prompting|fine-tuning|deployment|benchmarks|tools|general",
    "techniques": ["specific techniques mentioned in the text"],
    "parameters": {{"parameter_name": "value as mentioned"}},
    "is_ai_related": true/false,
    "relevance_score": 0.0-1.0 (how relevant to AI/ML best practices),
    "summary": "one sentence summary of the content"
}}

Be specific about model names and versions. Only mark as ai_related if it discusses AI/ML models or techniques."""

            # Get LLM response
            response = await processor._process_lmstudio(prompt)
            
            # Parse response (handle markdown-wrapped JSON)
            try:
                # Try direct parsing first
                data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if not json_match:
                    # Try without code block markers
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                
                if json_match:
                    try:
                        data = json.loads(json_match.group(1) if '```' in response else json_match.group())
                    except:
                        logger.error(f"Failed to parse LLM response for entity extraction")
                        return ExtractedEntities()
                else:
                    logger.error(f"No JSON found in LLM response")
                    return ExtractedEntities()
            
            return ExtractedEntities(
                models_mentioned=data.get("models_mentioned", []),
                theme=data.get("theme", "general"),
                techniques=data.get("techniques", []),
                parameters=data.get("parameters", {}),
                is_ai_related=data.get("is_ai_related", False),
                relevance_score=float(data.get("relevance_score", 0.0)),
                summary=data.get("summary", "")
            )
                
        finally:
            await processor.close()
    
    async def extract_best_practices_with_llm(self, content: str, entities: ExtractedEntities) -> List[Dict[str, Any]]:
        """Extract best practices using LLM, guided by entities."""
        if not entities.is_ai_related or entities.relevance_score < 0.3:
            return []
            
        processor = LLMProcessorFactory.create_processor(
            provider=settings.llm_provider,
            base_url=settings.local_llm_url,
            api_type=settings.local_llm_type,
            max_chars=3000
        )
        
        try:
            # Use entities to create focused prompt
            models_context = f"Models discussed: {', '.join(entities.models_mentioned)}" if entities.models_mentioned else ""
            theme_context = f"Theme: {entities.theme}"
            
            prompt = f"""Extract actionable AI/ML best practices from this content.
{models_context}
{theme_context}

Content:
{content[:3000]}

Focus on extracting practices related to: {', '.join(entities.techniques) if entities.techniques else 'general AI/ML techniques'}

Return a JSON array of practices:
[
  {{
    "practice_type": "prompting|parameter|pitfall|tip",
    "content": "clear, actionable description",
    "confidence": 0.0-1.0,
    "applicable_models": ["model1", "model2"],
    "source_quality": "high|medium|low",
    "extracted_parameters": {{"param": value}} or null,
    "example_code": "code snippet" or null
  }}
]

Only extract concrete, verifiable practices. Be specific about which models they apply to."""

            response = await processor._process_lmstudio(prompt)
            
            # Parse response (handle markdown-wrapped JSON)
            try:
                practices = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                import re
                json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', response, re.DOTALL)
                if not json_match:
                    # Try without code block markers
                    json_match = re.search(r'\[.*\]', response, re.DOTALL)
                
                if json_match:
                    try:
                        practices = json.loads(json_match.group(1) if '```' in response else json_match.group())
                    except:
                        logger.error("Failed to parse practices from LLM")
                        return []
                else:
                    logger.error("No JSON array found in LLM response")
                    return []
            
            if isinstance(practices, dict) and "practices" in practices:
                practices = practices["practices"]
            
            # Ensure applicable_models includes entities.models_mentioned
            for practice in practices:
                if not practice.get("applicable_models"):
                    practice["applicable_models"] = entities.models_mentioned or ["general"]
                    
            return practices
                
        finally:
            await processor.close()
    
    async def scrape_reddit_browser(self, page: Page, subreddit: str, max_posts: int = 10) -> List[ProcessedContent]:
        """Scrape Reddit using browser and process with LLM."""
        logger.info(f"Scraping r/{subreddit} with browser")
        
        url = f"https://old.reddit.com/r/{subreddit}/top/?t=week"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(self.scrape_delay)
        
        processed = []
        
        # Get post links
        post_links = await page.evaluate(f'''
            Array.from(document.querySelectorAll('.thing.link')).slice(0, {max_posts}).map(post => ({{
                title: post.querySelector('a.title')?.innerText || '',
                url: post.querySelector('.comments')?.href || '',
                score: post.querySelector('.score.unvoted')?.innerText || '0'
            }})).filter(p => p.url)
        ''')
        
        for i, post in enumerate(post_links):
            if i >= max_posts:
                break
                
            try:
                # Navigate to post
                post_page = await page.context.new_page()
                await post_page.goto(post['url'], wait_until='domcontentloaded')
                await asyncio.sleep(1)
                
                # Extract content
                content_data = await post_page.evaluate('''
                    (() => {
                        const title = document.querySelector('.top-matter .title')?.innerText || '';
                        const postText = document.querySelector('.usertext-body .md')?.innerText || '';
                        const comments = Array.from(document.querySelectorAll('.comment:not(.deleted) .usertext-body .md'))
                            .slice(0, 5)
                            .map(c => c.innerText)
                            .filter(t => t.length > 50);
                        
                        return {
                            title,
                            postText,
                            comments,
                            fullContent: title + '\\n\\n' + postText + '\\n\\n' + comments.join('\\n\\n')
                        };
                    })()
                ''')
                
                await post_page.close()
                
                # Process with LLM - Step 1: Entity extraction
                logger.info(f"Extracting entities from: {content_data['title'][:60]}...")
                entities = await self.extract_entities_with_llm(content_data['fullContent'], f"reddit:{subreddit}")
                
                if entities.is_ai_related:
                    # Step 2: Extract best practices
                    logger.info(f"AI content found (score: {entities.relevance_score}). Extracting practices...")
                    practices = await self.extract_best_practices_with_llm(content_data['fullContent'], entities)
                    
                    processed.append(ProcessedContent(
                        original_text=content_data['fullContent'],
                        entities=entities,
                        best_practices=practices,
                        source_url=post['url'],
                        source_type=f"reddit:{subreddit}",
                        timestamp=datetime.now().isoformat()
                    ))
                    
                    logger.info(f"Extracted {len(practices)} practices from post")
                else:
                    logger.debug(f"Skipping non-AI content: {content_data['title'][:60]}")
                    
            except Exception as e:
                logger.error(f"Error processing post: {e}")
            
            await asyncio.sleep(self.scrape_delay)
        
        return processed
    
    async def scrape_hackernews_browser(self, page: Page, max_posts: int = 10) -> List[ProcessedContent]:
        """Scrape HackerNews for AI content."""
        logger.info("Scraping HackerNews with browser")
        
        # Search for AI content
        search_url = "https://hn.algolia.com/?query=LLM%20OR%20GPT%20OR%20Claude%20OR%20prompt&sort=byPopularity&dateRange=pastWeek"
        await page.goto(search_url, wait_until='networkidle')
        await asyncio.sleep(self.scrape_delay)
        
        processed = []
        
        # Get stories
        stories = await page.evaluate(f'''
            Array.from(document.querySelectorAll('.Story')).slice(0, {max_posts}).map(story => ({{
                title: story.querySelector('.Story_title a')?.innerText || '',
                url: story.querySelector('.Story_comment a')?.href || '',
                points: story.querySelector('.Story_points')?.innerText || '0'
            }})).filter(s => s.url)
        ''')
        
        for story in stories[:max_posts]:
            try:
                # Get discussion content
                discussion_page = await page.context.new_page()
                await discussion_page.goto(story['url'], wait_until='domcontentloaded')
                await asyncio.sleep(1)
                
                # Extract discussion
                content_data = await discussion_page.evaluate('''
                    (() => {
                        const title = document.querySelector('.titleline')?.innerText || '';
                        const comments = Array.from(document.querySelectorAll('.comment'))
                            .slice(0, 10)
                            .map(c => c.innerText)
                            .filter(t => t.length > 100);
                        
                        return {
                            title,
                            fullContent: title + '\\n\\n' + comments.join('\\n\\n')
                        };
                    })()
                ''')
                
                await discussion_page.close()
                
                # Process with LLM
                entities = await self.extract_entities_with_llm(content_data['fullContent'], "hackernews")
                
                if entities.is_ai_related and entities.relevance_score > 0.4:
                    practices = await self.extract_best_practices_with_llm(content_data['fullContent'], entities)
                    
                    processed.append(ProcessedContent(
                        original_text=content_data['fullContent'],
                        entities=entities,
                        best_practices=practices,
                        source_url=story['url'],
                        source_type="hackernews",
                        timestamp=datetime.now().isoformat()
                    ))
                    
                    logger.info(f"Processed HN story: {story['title'][:60]}...")
                    
            except Exception as e:
                logger.error(f"Error processing HN story: {e}")
            
            await asyncio.sleep(self.scrape_delay)
        
        return processed
    
    async def save_to_model_directories(self):
        """Save processed content to appropriate model directories."""
        models_dir = Path("models")
        
        # Group practices by model
        model_practices = {}
        
        for content in self.processed_content:
            for practice in content.best_practices:
                models = practice.get("applicable_models", ["general"])
                for model in models:
                    if model not in model_practices:
                        model_practices[model] = {
                            "prompting": [],
                            "parameters": [],
                            "pitfalls": [],
                            "tips": []
                        }
                    
                    practice_data = {
                        "content": practice["content"],
                        "confidence": practice.get("confidence", 0.5),
                        "source": content.source_type,
                        "timestamp": content.timestamp,
                        "theme": content.entities.theme
                    }
                    
                    practice_type = practice.get("practice_type", "tip")
                    if practice_type in model_practices[model]:
                        model_practices[model][practice_type].append(practice_data)
        
        # Save to files
        for model_name, practices in model_practices.items():
            # Skip generic category names
            if model_name.lower() in ['text-to-image models', 'vision models', 'all models', 'llms']:
                continue
                
            # Determine category based on model name
            category = "text"  # default
            
            # Image models
            if any(img in model_name.lower() for img in ['stable-diffusion', 'midjourney', 'dalle', 'flux', 'sdxl', 'imagen', 'playground']):
                category = "image"
            # Video models  
            elif any(vid in model_name.lower() for vid in ['runway', 'pika', 'stable-video', 'sora', 'gen-']):
                category = "video"
            # Audio models
            elif any(aud in model_name.lower() for aud in ['whisper', 'bark', 'elevenlabs', 'tortoise', 'musicgen']):
                category = "audio"
            # Multimodal models
            elif any(multi in model_name.lower() for multi in ['vision', 'clip', 'blip', 'llava', 'gpt-4v', 'gemini-vision', 'minigpt']):
                category = "multimodal"
            
            model_dir = models_dir / category / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            # Update or create files
            timestamp = datetime.now().isoformat()
            
            # Prompting guide
            if practices["prompting"]:
                prompting_file = model_dir / "prompting.md"
                content = f"# {model_name.title()} Prompting Guide\n\n"
                content += f"*Last updated: {timestamp}*\n\n"
                
                for p in practices["prompting"]:
                    content += f"## {p['content']}\n"
                    content += f"- Theme: {p['theme']}\n"
                    content += f"- Confidence: {p['confidence']}\n"
                    content += f"- Source: {p['source']}\n\n"
                
                prompting_file.write_text(content)
            
            # Parameters
            if practices["parameters"]:
                params_file = model_dir / "parameters.json"
                params_data = []
                
                for p in practices["parameters"]:
                    # Extract parameter name and value from content
                    params_data.append({
                        "name": "parameter",
                        "description": p["content"],
                        "confidence": p["confidence"],
                        "source": p["source"]
                    })
                
                with open(params_file, 'w') as f:
                    json.dump(params_data, f, indent=2)
            
            # Save metadata
            metadata_file = model_dir / "metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump({
                    "model_id": model_name,
                    "last_updated": timestamp,
                    "sources_count": len(set(p["source"] for plist in practices.values() for p in plist)),
                    "themes": list(set(p["theme"] for plist in practices.values() for p in plist)),
                    "total_practices": sum(len(plist) for plist in practices.values())
                }, f, indent=2)
            
            logger.info(f"Saved {sum(len(plist) for plist in practices.values())} practices for {model_name}")
    
    async def scrape_github_browser(self, page: Page, repo_path: str) -> List[ProcessedContent]:
        """Scrape GitHub repository for AI best practices."""
        logger.info(f"Scraping GitHub repo: {repo_path}")
        
        # Common AI best practices repositories
        if "/" not in repo_path:
            # Default to some well-known repos
            repo_path = f"dair-ai/{repo_path}"
        
        url = f"https://github.com/{repo_path}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(self.scrape_delay)
        
        processed = []
        
        # Look for README and documentation files
        readme_content = await page.evaluate('''
            (() => {
                const readme = document.querySelector('.markdown-body');
                return readme ? readme.innerText : '';
            })()
        ''')
        
        if readme_content:
            # Process README
            entities = await self.extract_entities_with_llm(readme_content[:3000], f"github:{repo_path}")
            
            if entities.is_ai_related and entities.relevance_score > 0.3:
                practices = await self.extract_best_practices_with_llm(readme_content[:3000], entities)
                
                processed.append(ProcessedContent(
                    original_text=readme_content[:3000],
                    entities=entities,
                    best_practices=practices,
                    source_url=url,
                    source_type=f"github:{repo_path}",
                    timestamp=datetime.now().isoformat()
                ))
                
                logger.info(f"Processed GitHub README: {entities.summary[:60]}...")
        
        return processed
    
    async def scrape_sources(self, sources: List[str] = None, max_posts_per_source: int = 10):
        """Main entry point for scraping multiple sources."""
        if sources is None:
            sources = ["reddit:LocalLLaMA", "reddit:OpenAI", "hackernews"]
        
        await self.initialize_browser()
        
        try:
            page = await self.context.new_page()
            
            for source in sources:
                if source.startswith("reddit:"):
                    subreddit = source.split(":", 1)[1]
                    content = await self.scrape_reddit_browser(page, subreddit, max_posts_per_source)
                    self.processed_content.extend(content)
                    
                elif source == "hackernews":
                    content = await self.scrape_hackernews_browser(page, max_posts_per_source)
                    self.processed_content.extend(content)
                    
                elif source.startswith("github:"):
                    repo = source.split(":", 1)[1]
                    content = await self.scrape_github_browser(page, repo)
                    self.processed_content.extend(content)
                
                logger.info(f"Completed scraping {source}")
            
            # Save all processed content
            await self.save_to_model_directories()
            
            # Summary
            total_practices = sum(len(c.best_practices) for c in self.processed_content)
            models_found = set()
            for c in self.processed_content:
                models_found.update(c.entities.models_mentioned)
            
            logger.info(f"Scraping complete! Processed {len(self.processed_content)} posts")
            logger.info(f"Total practices extracted: {total_practices}")
            logger.info(f"Models found: {sorted(models_found)}")
            
            # Save summary
            summary = {
                "timestamp": datetime.now().isoformat(),
                "sources": sources,
                "posts_processed": len(self.processed_content),
                "total_practices": total_practices,
                "models_found": sorted(list(models_found)),
                "themes": list(set(c.entities.theme for c in self.processed_content if c.entities.theme)),
                "average_relevance": sum(c.entities.relevance_score for c in self.processed_content) / len(self.processed_content) if self.processed_content else 0
            }
            
            with open("intelligent_scraper_summary.json", "w") as f:
                json.dump(summary, f, indent=2)
                
        finally:
            await self.close_browser()


# Test function
async def test_intelligent_scraper():
    """Test the intelligent scraper."""
    scraper = IntelligentBrowserScraper()
    await scraper.scrape_sources(
        sources=["reddit:LocalLLaMA", "hackernews"],
        max_posts_per_source=5
    )


if __name__ == "__main__":
    asyncio.run(test_intelligent_scraper())