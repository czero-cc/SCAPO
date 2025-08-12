"""Intelligent browser-based scraper with LLM entity extraction."""

import asyncio
import json
import re
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



def sanitize_model_name(model_name: str) -> str:
    """Clean up model names to be valid directory names."""
    # Remove parenthetical references
    model_name = re.sub(r'\s*\(.*?\)\s*', '', model_name)
    
    # Remove version numbers that aren't part of the model name
    if 'release' in model_name.lower():
        return None  # Skip generic release references
    
    # Clean up the name
    model_name = model_name.strip()
    
    # Remove invalid characters for directory names
    model_name = re.sub(r'[<>:"/\\|?*]', '', model_name)
    
    # Normalize common variations
    if model_name.lower() == 'llama':
        model_name = 'llama-3'  # Default to latest version
    
    return model_name if model_name else None

class IntelligentBrowserScraper(BrowserBaseScraper):
    """Smart scraper that uses LLM for entity extraction and content processing."""
    
    def __init__(self):
        super().__init__(SourceType.FORUM, headless=True)
        self.processed_content: List[ProcessedContent] = []
        self.scrape_delay = settings.scraping_delay_seconds  # Use config value for polite delay
        self._llm_processor = None  # Cache the processor instance
        
    async def fetch_posts(self, subreddit: Optional[str] = None, limit: int = 100, time_filter: str = "week") -> List[ScrapedPost]:
        """Required abstract method - handled by scrape_sources instead."""
        return []
    
    def extract_best_practices(self, posts: List[ScrapedPost]) -> Dict[str, Any]:
        """Required abstract method - handled by LLM processing instead."""
        return {}
    
    def _get_llm_processor(self, max_chars: Optional[int] = None):
        """Get or create a cached LLM processor instance."""
        if self._llm_processor is None:
            if settings.llm_provider == "openrouter":
                self._llm_processor = LLMProcessorFactory.create_processor(
                    provider="openrouter",
                    api_key=settings.openrouter_api_key,
                    model=settings.openrouter_model,
                    max_chars=max_chars or settings.llm_max_chars
                )
            else:
                self._llm_processor = LLMProcessorFactory.create_processor(
                    provider="local",
                    base_url=settings.local_llm_url,
                    model=settings.local_llm_model,
                    max_chars=max_chars or settings.llm_max_chars
                )
        return self._llm_processor
        
    async def extract_entities_with_llm(self, content: str, source: str) -> ExtractedEntities:
        """Use LLM to extract entities from content."""
        # Use cached processor
        processor = self._get_llm_processor()
        
        try:
            # Create extraction prompt with explicit JSON instructions
            prompt = f"""Analyze this {source} content and extract key entities.

Content:
{content[:2000]}

You MUST respond with ONLY a valid JSON object. No explanations before or after.

Return this exact JSON structure:
{{
    "models_mentioned": ["exact model names as mentioned in the text, including version numbers"],
    "theme": "main theme: prompting|fine-tuning|deployment|benchmarks|tools|general",
    "techniques": ["specific techniques mentioned in the text"],
    "parameters": {{"parameter_name": "value as mentioned"}},
    "is_ai_related": true/false,
    "relevance_score": 0.0-1.0 (how relevant to AI/ML best practices),
    "summary": "one sentence summary of the content"
}}

IMPORTANT: Start your response with {{ and end with }}. No other text allowed."""

            # Get LLM response using the unified interface with better JSON handling
            system_prompt = "You are a JSON generator. Output ONLY valid JSON. Start with { or [ and end with } or ]. No explanations, no text before or after the JSON."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
            
            # Use internal method directly for more control
            response = await processor._make_completion(
                messages=messages,
                temperature=0.1,  # Lower temperature for more consistent JSON
                max_tokens=1000,
            )
            
            # Parse response (handle various formats)
            data = None
            try:
                # Try direct parsing first
                data = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown code block
                import re
                json_patterns = [
                    r'```(?:json)?\s*(\{.*?\})\s*```',  # Markdown code block
                    r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # Nested JSON
                    r'\{.*?\}'  # Simple JSON
                ]
                
                for pattern in json_patterns:
                    match = re.search(pattern, response, re.DOTALL)
                    if match:
                        try:
                            json_str = match.group(1) if '```' in pattern else match.group()
                            data = json.loads(json_str)
                            break
                        except:
                            continue
                
                if not data:
                    logger.error(f"No valid JSON found in LLM response. Raw response: {response[:200]}...")
                    # Return a default entity indicating potential AI content for manual review
                    return ExtractedEntities(
                        is_ai_related=True,  # Assume it might be AI related
                        relevance_score=0.3,  # Low confidence
                        summary="Could not parse LLM response"
                    )
            
            return ExtractedEntities(
                models_mentioned=data.get("models_mentioned", []),
                theme=data.get("theme", "general"),
                techniques=data.get("techniques", []),
                parameters=data.get("parameters", {}),
                is_ai_related=data.get("is_ai_related", False),
                relevance_score=float(data.get("relevance_score", 0.0)),
                summary=data.get("summary", "")
            )
                
        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            return ExtractedEntities()
    
    async def extract_best_practices_with_llm(self, content: str, entities: ExtractedEntities) -> List[Dict[str, Any]]:
        """Extract best practices using LLM, guided by entities."""
        if not entities.is_ai_related or entities.relevance_score < 0.3:
            return []
            
        # Use cached processor
        processor = self._get_llm_processor()
        
        try:
            # Use entities to create focused prompt
            models_context = f"Models discussed: {', '.join(entities.models_mentioned)}" if entities.models_mentioned else ""
            theme_context = f"Theme: {entities.theme}"
            
            prompt = f"""Extract SPECIFIC tips, settings, and techniques from this AI discussion.
{models_context}
{theme_context}

Content:
{content[:3000]}

Look for ANY of these:
1. SPECIFIC SETTINGS: "temperature 0.7", "top_p 0.95", "steps 50", "cfg 7"
2. TECHNIQUES: "use system prompt", "chain of thought", "few-shot examples"
3. PROBLEMS & SOLUTIONS: "slow" -> "use streaming", "expensive" -> "batch requests"
4. PARAMETERS: API limits, token counts, rate limits, pricing tiers
5. TIPS: keyboard shortcuts, hidden features, workarounds, optimizations

Return a JSON array. ONLY include SPECIFIC, ACTIONABLE information:
[
  {{
    "model_or_service": "GPT-4|Claude|Midjourney|ElevenLabs|etc",
    "tip": "the specific tip or technique",
    "details": "exact settings, parameters, or steps",
    "type": "parameter|technique|optimization|workaround",
    "benefit": "faster|cheaper|better quality|etc"
  }}
]

Return EMPTY array [] if no specific tips found. Skip ALL generic advice like "be clear" or "experiment"."""

            # Use our new problem-solution extraction prompt
            response = await processor.process_raw_prompt(prompt)
            
            # Parse the response
            try:
                extracted_items = json.loads(response)
                if not isinstance(extracted_items, list):
                    extracted_items = []
            except json.JSONDecodeError:
                # Try to extract JSON from response
                import re
                json_match = re.search(r'\[.*?\]', response, re.DOTALL)
                if json_match:
                    try:
                        extracted_items = json.loads(json_match.group())
                    except:
                        extracted_items = []
                else:
                    extracted_items = []
            
            # Convert to new pipeline format (tips, problems, settings, cost_info)
            practices = []
            for item in extracted_items:
                # Create a practice in the legacy format for compatibility
                if item.get("tip"):
                    # New format from updated prompt
                    model_or_service = item.get("model_or_service", "unknown")
                    practice = {
                        "practice_type": item.get("type", "technique"),
                        "content": item.get("tip"),
                        "details": item.get("details", ""),
                        "benefit": item.get("benefit", ""),
                        "applicable_models": [model_or_service] if model_or_service != "unknown" else entities.models_mentioned[:1] if entities.models_mentioned else ["general"],
                        "confidence": 0.7  # Default confidence for extracted tips
                    }
                    practices.append(practice)
                elif item.get("problem") and item.get("solution"):
                    # Old problem-solution format (fallback)
                    practices.append({
                        "practice_type": item.get("practice_type", "cost_optimization"),
                        "problem": item.get("problem"),
                        "solution": item.get("solution"),
                        "service_name": item.get("service_name"),
                        "savings_or_improvement": item.get("savings_or_improvement"),
                        "specific_settings": item.get("specific_settings"),
                        "content": f"Problem: {item.get('problem')}\nSolution: {item.get('solution')}",
                        "confidence": item.get("confidence", 0.5),
                        "applicable_models": [item.get("service_name")] if item.get("service_name") else entities.models_mentioned[:1] if entities.models_mentioned else ["general"]
                    })
                else:
                    # Fallback to traditional format
                    practices.append({
                        "practice_type": "tip",
                        "content": item.get("content", str(item)),
                        "confidence": item.get("confidence", 0.5),
                        "applicable_models": entities.models_mentioned[:1] if entities.models_mentioned else ["general"]
                    })
            
            # Ensure applicable_models includes entities.models_mentioned
            for practice in practices:
                if not practice.get("applicable_models"):
                    practice["applicable_models"] = entities.models_mentioned or ["general"]
                    
            return practices
                
        except Exception as e:
            logger.error(f"Failed to extract entities: {e}")
            return ExtractedEntities()
    
    def normalize_reddit_url(self, url: str) -> str:
        """Convert old.reddit.com URLs to standard reddit.com URLs."""
        if 'old.reddit.com' in url:
            return url.replace('old.reddit.com', 'reddit.com')
        return url
    
    async def evaluate_practice_quality(self, practice: Dict[str, Any], model_name: str, content_context: str) -> Dict[str, Any]:
        """Use LLM to evaluate if a practice is actually useful and specific to the model."""
        # Use cached processor
        processor = self._get_llm_processor(max_chars=2000)
        
        try:
            prompt = f"""Evaluate if this practice is actually useful, specific, and relevant to {model_name}.

Practice to evaluate:
- Type: {practice.get('practice_type', 'unknown')}
- Content: {practice.get('content', '')}
- Claims to apply to: {', '.join(practice.get('applicable_models', []))}

Context (original discussion):
{content_context[:500]}...

Evaluate based on:
1. Is this practice SPECIFIC to {model_name} or just generic AI advice?
2. Does it provide ACTIONABLE guidance (not just observations)?
3. Is it ACCURATE based on what you know about {model_name}?
4. Does the original context actually discuss {model_name} specifically?

You MUST respond with ONLY this JSON structure. No explanations:
{{
  "is_relevant": true/false,
  "is_specific": true/false,
  "is_actionable": true/false,
  "quality_score": 0.0-1.0,
  "reason": "brief explanation",
  "improved_content": "rewritten practice if needed, or null"
}}

IMPORTANT: Start with {{ and end with }}. Be strict - only high-quality, model-specific practices should pass."""

            response = await processor.process_raw_prompt(prompt)
            
            # Parse response
            try:
                evaluation = json.loads(response)
            except json.JSONDecodeError:
                # Try to extract JSON from markdown
                import re
                json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response, re.DOTALL)
                if not json_match:
                    json_match = re.search(r'\{.*\}', response, re.DOTALL)
                
                if json_match:
                    evaluation = json.loads(json_match.group(1) if '```' in response else json_match.group())
                else:
                    # Default to rejecting if can't parse
                    evaluation = {
                        "is_relevant": False,
                        "is_specific": False,
                        "is_actionable": False,
                        "quality_score": 0.0,
                        "reason": "Failed to parse evaluation"
                    }
            
            # Update practice with quality info
            practice['quality_score'] = evaluation.get('quality_score', 0.0)
            practice['quality_evaluation'] = evaluation
            
            # Use improved content if provided
            if evaluation.get('improved_content'):
                practice['content'] = evaluation['improved_content']
            
            return practice
            
        except Exception as e:
            logger.error(f"Quality evaluation failed: {e}")
            # Default to original practice with low quality score
            practice['quality_score'] = 0.3
            practice['quality_evaluation'] = {
                "is_relevant": False,
                "reason": f"Evaluation failed: {str(e)}"
            }
            return practice
        finally:
            # Don't close the processor - we're reusing it
            pass
    
    async def scrape_reddit_browser(self, page: Page, source_name: str, max_posts: int = 10) -> List[ProcessedContent]:
        """Scrape Reddit using browser and process with LLM."""
        logger.info(f"Scraping {source_name} with browser")
        
        # Get the actual URL from sources.yaml
        from src.scrapers.source_manager import SourceManager
        source_manager = SourceManager()
        reddit_sources = source_manager.get_reddit_sources()
        
        # Find the source by name
        source_config = None
        for source in reddit_sources:
            if source.get('name', '').replace('r/', '') == source_name:
                source_config = source
                break
        
        if not source_config:
            logger.error(f"Source {source_name} not found in sources.yaml")
            return []
            
        url = source_config.get('url', '')
        if not url:
            logger.error(f"No URL found for source {source_name}")
            return []
            
        # Convert to old.reddit.com for better scraping
        if 'reddit.com' in url and 'old.reddit.com' not in url:
            if 'www.reddit.com' in url:
                url = url.replace('www.reddit.com', 'old.reddit.com')
            else:
                url = url.replace('reddit.com', 'old.reddit.com')
            
        logger.info(f"Navigating to: {url}")
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(self.scrape_delay)
        
        processed = []
        
        # Get post links - handle both subreddit pages and search results
        post_links = await page.evaluate('''
            (maxPosts) => {
                // Try both regular subreddit selectors and search result selectors
                let posts = Array.from(document.querySelectorAll('.thing.link'));
                let isSearchPage = false;
                
                if (posts.length === 0) {
                    // Try search result selectors
                    posts = Array.from(document.querySelectorAll('.search-result-link'));
                    isSearchPage = true;
                }
                
                return posts.slice(0, maxPosts).map(post => {
                    if (isSearchPage) {
                        // Search result page structure
                        const header = post.querySelector('.search-result-header');
                        const titleLink = header?.querySelector('a.search-title') || header?.querySelector('a');
                        const commentsLink = header?.querySelector('a.search-comments');
                        
                        return {
                            title: titleLink?.innerText || '',
                            url: commentsLink?.href || titleLink?.href || '',
                            score: post.querySelector('.search-score')?.innerText || '0'
                        };
                    } else {
                        // Regular subreddit page structure
                        return {
                            title: post.querySelector('a.title')?.innerText || '',
                            url: post.querySelector('.comments')?.href || '',
                            score: post.querySelector('.score.unvoted')?.innerText || '0'
                        };
                    }
                }).filter(p => p.url && p.title);
            }
        ''', max_posts)
        
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
                entities = await self.extract_entities_with_llm(content_data['fullContent'], f"reddit:{source_name}")
                
                if entities.is_ai_related:
                    # Step 2: Extract best practices
                    logger.info(f"AI content found (score: {entities.relevance_score}). Extracting practices...")
                    practices = await self.extract_best_practices_with_llm(content_data['fullContent'], entities)
                    
                    processed.append(ProcessedContent(
                        original_text=content_data['fullContent'],
                        entities=entities,
                        best_practices=practices,
                        source_url=self.normalize_reddit_url(post['url']),
                        source_type=f"reddit:{source_name}",
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
        """Save processed content using the ModelEntryGenerator for consistency with new pipeline."""
        from src.services.model_entry_generator import ModelEntryGenerator
        
        generator = ModelEntryGenerator()
        
        # Group practices by model/service
        model_data = {}
        
        # Use quality threshold from settings
        quality_threshold = settings.llm_quality_threshold
        
        # Progress tracking
        total_practices = sum(len(content.best_practices) for content in self.processed_content)
        evaluated_count = 0
        saved_count = 0
        start_time = datetime.now()
        
        logger.info(f"Processing {total_practices} practices from {len(self.processed_content)} posts...")
        if quality_threshold > 0:
            logger.info(f"Quality threshold: {quality_threshold}")
        
        # Process all content and group by model/service
        for content in self.processed_content:
            for practice in content.best_practices:
                models = practice.get("applicable_models", ["general"])
                
                # Skip if all models are generic
                non_generic_models = [m for m in models if m.lower() not in ["general", "unknown", "ai", "llm"]]
                if not non_generic_models:
                    continue
                
                evaluated_count += 1
                
                # Simple quality check - skip if confidence too low
                confidence = practice.get('confidence', 0.5)
                if confidence < quality_threshold:
                    logger.debug(f"Skipping low confidence practice: {confidence}")
                    continue
                
                # Add to each applicable model/service
                for model in non_generic_models:
                    clean_model = sanitize_model_name(model)
                    if not clean_model:
                        continue
                    
                    # Initialize model data if needed
                    if clean_model not in model_data:
                        model_data[clean_model] = {
                            "service": clean_model,
                            "tips": [],
                            "problems": [],
                            "settings": [],
                            "cost_info": []
                        }
                    
                    # Convert practice to new format
                    if practice.get("tip"):  # New format from updated prompt
                        model_data[clean_model]["tips"].append(
                            f"{practice.get('tip')} - {practice.get('details', '')}"
                        )
                        if practice.get("details") and any(k in practice.get("details", "").lower() for k in ["parameter", "setting", "config"]):
                            model_data[clean_model]["settings"].append(practice.get("details"))
                    elif practice.get("problem") and practice.get("solution"):
                        # Problem-solution format
                        model_data[clean_model]["problems"].append(
                            f"Problem: {practice.get('problem')}\nSolution: {practice.get('solution')}"
                        )
                        if practice.get("savings_or_improvement"):
                            model_data[clean_model]["cost_info"].append(practice.get("savings_or_improvement"))
                    else:
                        # Generic practice - add as tip
                        content_text = practice.get("content", "")
                        if content_text:
                            model_data[clean_model]["tips"].append(content_text)
                    
                    saved_count += 1
        
        # Save using ModelEntryGenerator for consistency
        models_created = 0
        for model_name, extraction_data in model_data.items():
            # Skip if no data
            if not any([extraction_data.get('tips'), extraction_data.get('problems'), 
                       extraction_data.get('settings'), extraction_data.get('cost_info')]):
                continue
            
            # Use ModelEntryGenerator to create the model entry
            try:
                success = generator.create_model_entry(extraction_data)
                if success:
                    models_created += 1
                    logger.info(f"Created model entry for {model_name}")
                else:
                    logger.warning(f"Failed to create model entry for {model_name}")
            except Exception as e:
                logger.error(f"Error creating model entry for {model_name}: {e}")
        
        # Final summary
        logger.info(f"Legacy scraping complete: {evaluated_count} practices processed, {models_created} models created")
    

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
            
            # Save summary in data directory
            summary_file = Path("data") / "intelligent_scraper_summary.json"
            summary_file.parent.mkdir(parents=True, exist_ok=True)
            with open(summary_file, "w") as f:
                json.dump(summary, f, indent=2)
                
        finally:
            await self.close_browser()

    async def scrape_url(self, url: str, max_posts: int = 10) -> List[Dict]:
        """Scrape a single URL and return posts as dicts."""
        posts = []
        
        # For Reddit, use JSON API instead of browser scraping
        if 'reddit.com' in url:
            import aiohttp
            import urllib.parse
            
            # Extract search query from URL
            parsed = urllib.parse.urlparse(url)
            params = urllib.parse.parse_qs(parsed.query)
            query = params.get('q', [''])[0]
            
            if query:
                # Use Reddit JSON API
                json_url = f'https://www.reddit.com/search.json?q={urllib.parse.quote(query)}&limit={max_posts}'
                
                async with aiohttp.ClientSession() as session:
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    async with session.get(json_url, headers=headers) as response:
                        if response.status == 200:
                            data = await response.json()
                            
                            # Extract posts from JSON
                            if 'data' in data and 'children' in data['data']:
                                for child in data['data']['children'][:max_posts]:
                                    post_data = child['data']
                                    posts.append({
                                        'id': post_data.get('id', ''),
                                        'title': post_data.get('title', ''),
                                        'content': post_data.get('selftext', '')[:500],
                                        'url': f"https://reddit.com{post_data.get('permalink', '')}",
                                        'score': post_data.get('score', 0),
                                        'subreddit': post_data.get('subreddit', ''),
                                        'num_comments': post_data.get('num_comments', 0)
                                    })
            
            return posts
        
        # For non-Reddit URLs, use browser scraping
        if not self.browser:
            from playwright.async_api import async_playwright
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
        
        page = await self.browser.new_page()
        try:
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await asyncio.sleep(2)
            
            # Extract posts based on URL type
            posts = []
            if False:  # Disabled old Reddit scraping code
                # Convert to old.reddit.com for easier scraping
                if 'old.reddit.com' not in url:
                    url = url.replace('www.reddit.com', 'old.reddit.com').replace('reddit.com', 'old.reddit.com')
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    await asyncio.sleep(2)
                
                # Extract posts directly from Reddit search pages using old Reddit structure
                post_data = await page.evaluate('''() => {
                    const posts = [];
                    
                    // Old Reddit uses .thing.link for posts
                    let postElements = document.querySelectorAll('.thing.link');
                    
                    // If no posts found, try search result specific selectors
                    if (postElements.length === 0) {
                        postElements = document.querySelectorAll('.search-result-link');
                    }
                    
                    postElements.forEach((post, idx) => {
                        if (idx >= ''' + str(max_posts) + ''') return;
                        
                        // Extract title
                        let title = '';
                        const titleEl = post.querySelector('h3, [data-testid="post-title"], a.title, .title');
                        if (titleEl) title = titleEl.innerText || titleEl.textContent;
                        
                        // Extract content/selftext
                        let content = '';
                        const contentEl = post.querySelector('[data-testid="post-content"], .selftext, .md');
                        if (contentEl) content = contentEl.innerText || contentEl.textContent;
                        
                        // Extract score
                        let score = 0;
                        const scoreEl = post.querySelector('.score, [score]');
                        if (scoreEl) {
                            const scoreText = scoreEl.innerText || scoreEl.getAttribute('score') || '0';
                            score = parseInt(scoreText.replace(/[^0-9-]/g, '')) || 0;
                        }
                        
                        // Extract URL
                        let postUrl = '';
                        const linkEl = post.querySelector('a[href*="/comments/"], [data-testid="post-title"] a');
                        if (linkEl) {
                            postUrl = linkEl.href;
                            if (postUrl.startsWith('/')) postUrl = 'https://www.reddit.com' + postUrl;
                        }
                        
                        posts.push({
                            id: 'post_' + idx,
                            title: title || 'No title',
                            content: content || title || '',
                            url: postUrl || window.location.href,
                            score: score
                        });
                    });
                    
                    return posts;
                }''')
                
                posts = post_data if post_data else []
            else:
                # Generic extraction for other sites
                # Try to find post-like elements
                elements = await page.query_selector_all('article, .post, .item, .entry, .result')
                for elem in elements[:max_posts]:
                    try:
                        title = await elem.query_selector('h2, h3, .title')
                        title_text = await title.inner_text() if title else ''
                        content = await elem.inner_text()
                        posts.append({
                            'id': f'post_{len(posts)}',
                            'title': title_text,
                            'content': content[:500],
                            'url': url,
                            'score': 0
                        })
                    except:
                        continue
            
            return posts
        finally:
            await page.close()
    
    async def scrape(self, url: str, max_posts: int = 10) -> List[Dict]:
        """Alias for scrape_url for compatibility."""
        return await self.scrape_url(url, max_posts)
    
    async def close(self):
        """Close browser and save all extracted data."""
        await self.save_to_model_directories()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()


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