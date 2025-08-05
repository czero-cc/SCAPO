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

            # Use the structured process_content method instead of raw prompt
            processed_practices = await processor.process_content(content[:3000], f"reddit post about {entities.theme}")
            
            # Convert ProcessedPractice objects to the expected format
            practices = []
            for practice in processed_practices:
                # Map model_name to applicable_models array
                applicable_models = [practice.model_name] if practice.model_name else []
                
                # Try to match any mentioned models from entities
                if entities.models_mentioned and not applicable_models:
                    # If no specific model in practice, use first mentioned model
                    applicable_models = entities.models_mentioned[:1]
                
                practices.append({
                    "practice_type": practice.practice_type,
                    "content": practice.content,
                    "confidence": practice.confidence,
                    "applicable_models": applicable_models,
                    "source_quality": "high" if practice.confidence > 0.8 else ("medium" if practice.confidence > 0.5 else "low"),
                    "extracted_parameters": None,  # Could extract from content if needed
                    "example_code": None  # Could extract from content if needed
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
                        source_url=self.normalize_reddit_url(post['url']),
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
        """Save processed content to appropriate model directories WITHOUT overwriting existing content."""
        models_dir = Path("models")
        
        # Group practices by model
        model_practices = {}
        
        # Use quality threshold from settings
        quality_threshold = settings.llm_quality_threshold
        
        # Progress tracking
        total_practices = sum(len(content.best_practices) for content in self.processed_content)
        evaluated_count = 0
        start_time = datetime.now()
        
        logger.info(f"Starting quality evaluation for {total_practices} practices...")
        if quality_threshold > 0:
            logger.info(f"Quality threshold: {quality_threshold} (practices below this score will be filtered)")
            if settings.llm_provider == "local":
                logger.info("Using local LLM - this may take several minutes. Consider:")
                logger.info("  • Using a faster model (still, 7B+ recommended)")
                logger.info("  • Switching to OpenRouter for faster processing")
                logger.info("  • Lowering LLM_QUALITY_THRESHOLD in .env to speed up")
        
        for content in self.processed_content:
            for practice in content.best_practices:
                models = practice.get("applicable_models", ["general"])
                
                # Skip if all models are generic
                non_generic_models = [m for m in models if m.lower() not in ["general", "unknown", "ai", "llm"]]
                if not non_generic_models:
                    logger.debug("Skipping practice with only generic models")
                    continue
                
                # Progress update
                evaluated_count += 1
                if evaluated_count % 5 == 0 or evaluated_count == 1:
                    elapsed = (datetime.now() - start_time).total_seconds()
                    rate = evaluated_count / elapsed if elapsed > 0 else 0
                    remaining = (total_practices - evaluated_count) / rate if rate > 0 else 0
                    logger.info(
                        f"Progress: {evaluated_count}/{total_practices} practices evaluated "
                        f"({evaluated_count/total_practices*100:.1f}%) - "
                        f"Est. time remaining: {remaining/60:.1f} minutes"
                    )
                
                # Evaluate practice quality once for the first non-generic model
                first_model = non_generic_models[0]
                evaluated_practice = await self.evaluate_practice_quality(
                    practice.copy(),  # Don't modify original
                    first_model,
                    content.original_text[:1000]  # Provide context
                )
                
                # Check quality threshold
                quality_score = evaluated_practice.get('quality_score', 0.0)
                if quality_score < quality_threshold:
                    logger.info(
                        f"Filtered out low-quality practice: "
                        f"score={quality_score:.2f}, models={models}, "
                        f"reason={evaluated_practice.get('quality_evaluation', {}).get('reason', 'N/A')}"
                    )
                    continue
                
                logger.info(f"Keeping high-quality practice: score={quality_score:.2f}, models={models}")
                
                # Now add this practice to all applicable models
                for model in models:
                    # Sanitize model name
                    clean_model = sanitize_model_name(model)
                    if not clean_model:
                        logger.warning(f"Skipping invalid model name: {model}")
                        continue
                    
                    if clean_model not in model_practices:
                        model_practices[clean_model] = {
                            "prompting": [],
                            "parameters": [],
                            "pitfalls": [],
                            "tips": []
                        }
                    
                    practice_data = {
                        "content": evaluated_practice.get("content", practice["content"]),  # Use improved content if available
                        "confidence": evaluated_practice.get("confidence", practice.get("confidence", 0.5)),
                        "quality_score": quality_score,
                        "source": content.source_type,
                        "source_url": content.source_url,
                        "timestamp": content.timestamp,
                        "theme": content.entities.theme,
                        "extracted_parameters": practice.get("extracted_parameters"),
                        "example_code": practice.get("example_code")
                    }
                    
                    # Map singular practice types to plural storage keys
                    practice_type = practice.get("practice_type", "tip")
                    type_mapping = {
                        "prompting": "prompting",
                        "parameter": "parameters",
                        "pitfall": "pitfalls",
                        "tip": "tips"
                    }
                    storage_key = type_mapping.get(practice_type, "tips")
                    
                    model_practices[clean_model][storage_key].append(practice_data)
        
        # Save to files
        for model_name, practices in model_practices.items():
            # Skip if no practices
            total_practices = sum(len(plist) for plist in practices.values())
            if total_practices == 0:
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
            
            timestamp = datetime.now().isoformat()
            
            # Update prompting guide with deduplication
            if practices["prompting"]:
                prompting_file = model_dir / "prompting.md"
                
                # Parse existing practices from the file
                existing_practices = []
                if prompting_file.exists():
                    existing_content = prompting_file.read_text()
                    # Extract practice headings (lines starting with ##)
                    import re
                    practice_pattern = r'^##\s+(.+)$'
                    for match in re.finditer(practice_pattern, existing_content, re.MULTILINE):
                        practice_text = match.group(1).strip()
                        # Skip section headers like "Practices Added..."
                        if not practice_text.startswith("Practices Added"):
                            existing_practices.append(practice_text.lower())
                
                # Build new content, checking for duplicates
                practices_to_add = []
                for p in practices["prompting"]:
                    normalized_content = p['content'].lower().strip()
                    
                    # Check for duplicates
                    is_duplicate = False
                    for existing in existing_practices:
                        # Calculate similarity
                        new_words = set(normalized_content.split())
                        existing_words = set(existing.split())
                        
                        if new_words and existing_words:
                            common_words = new_words.intersection(existing_words)
                            similarity = len(common_words) / min(len(new_words), len(existing_words))
                            
                            if similarity > 0.8:  # 80% similarity threshold
                                is_duplicate = True
                                logger.info(f"Skipping duplicate prompting practice: {p['content'][:50]}...")
                                break
                    
                    if not is_duplicate:
                        practices_to_add.append(p)
                        existing_practices.append(normalized_content)
                
                # Only write if we have new practices to add
                if practices_to_add:
                    # If file doesn't exist, create with header
                    if not prompting_file.exists():
                        existing_content = f"# {model_name} Prompting Guide\n\n*Last updated: {timestamp}*\n"
                    else:
                        # Update the last updated timestamp
                        existing_content = re.sub(
                            r'\*Last updated: .+\*', 
                            f'*Last updated: {timestamp}*', 
                            existing_content
                        )
                    
                    # Add new practices
                    new_content = "\n"
                    for p in practices_to_add:
                        new_content += f"\n## {p['content']}\n"
                        new_content += f"- **Quality Score**: {p.get('quality_score', 'N/A')}\n"
                        new_content += f"- **Confidence**: {p['confidence']}\n"
                        new_content += f"- **Source**: [{p['source']}]({p.get('source_url', '#')})\n"
                        new_content += f"- **Theme**: {p['theme']}\n"
                        if p.get('example_code'):
                            new_content += f"\n```\n{p['example_code']}\n```\n"
                        new_content += "\n"
                    
                    # Write combined content
                    if existing_content and not existing_content.endswith('\n'):
                        existing_content += '\n'
                    prompting_file.write_text(existing_content + new_content)
                    logger.info(f"Added {len(practices_to_add)} new prompting practices for {model_name}")
            
            # Merge parameters (don't overwrite)
            if practices["parameters"]:
                params_file = model_dir / "parameters.json"
                
                # Load existing parameters
                existing_params = []
                if params_file.exists():
                    with open(params_file, 'r') as f:
                        existing_params = json.load(f)
                
                # Create a set of existing parameter descriptions for deduplication
                existing_descriptions = {param["description"].lower().strip() for param in existing_params}
                
                # Add new parameters
                for p in practices["parameters"]:
                    normalized_desc = p["content"].lower().strip()
                    
                    # Check for duplicates
                    is_duplicate = False
                    for existing_desc in existing_descriptions:
                        # Calculate similarity
                        new_words = set(normalized_desc.split())
                        existing_words = set(existing_desc.split())
                        
                        if new_words and existing_words:
                            common_words = new_words.intersection(existing_words)
                            similarity = len(common_words) / min(len(new_words), len(existing_words))
                            
                            if similarity > 0.8:  # 80% similarity threshold
                                is_duplicate = True
                                logger.info(f"Skipping duplicate parameter: {p['content'][:50]}...")
                                break
                    
                    if not is_duplicate:
                        # Filter extracted parameters to only include this model's data
                        extracted_params = p.get("extracted_parameters", {})
                        if extracted_params is None:
                            extracted_params = {}
                        filtered_params = {}
                        
                        # Check if parameters contain model-specific data
                        for param_name, param_value in extracted_params.items():
                            if isinstance(param_value, dict):
                                # If it's a dict with model names as keys, extract only this model's data
                                if model_name in param_value:
                                    filtered_params[param_name] = param_value[model_name]
                                elif clean_model in param_value:
                                    filtered_params[param_name] = param_value[clean_model]
                                # If neither exact match, skip this parameter for this model
                            else:
                                # If it's not a dict, include it as-is
                                filtered_params[param_name] = param_value
                        
                        # Only add parameter entry if we have relevant data
                        if filtered_params or not extracted_params:  # Include if no params or if we found relevant params
                            param_entry = {
                                "description": p["content"],
                                "confidence": p["confidence"],
                                "source": p["source"],
                                "timestamp": p["timestamp"],
                                "extracted_values": filtered_params
                            }
                            existing_params.append(param_entry)
                            existing_descriptions.add(normalized_desc)
                            logger.info(f"Added new parameter for {model_name}: {p['content'][:50]}...")
                
                # Save merged parameters
                with open(params_file, 'w') as f:
                    json.dump(existing_params, f, indent=2)
            
            # Update pitfalls with deduplication
            if practices["pitfalls"]:
                pitfalls_file = model_dir / "pitfalls.md"
                
                # Parse existing pitfalls from the file
                existing_pitfalls = []
                if pitfalls_file.exists():
                    existing_content = pitfalls_file.read_text()
                    # Extract pitfall headings (lines starting with ## or ###)
                    import re
                    pitfall_pattern = r'^###?\s+(.+)$'
                    for match in re.finditer(pitfall_pattern, existing_content, re.MULTILINE):
                        pitfall_text = match.group(1).strip()
                        # Skip section headers like "Pitfalls Added..."
                        if not pitfall_text.startswith("Pitfalls Added"):
                            existing_pitfalls.append(pitfall_text.lower())
                
                # Build new content, checking for duplicates
                pitfalls_to_add = []
                for p in practices["pitfalls"]:
                    normalized_content = p['content'].lower().strip()
                    
                    # Check for duplicates
                    is_duplicate = False
                    for existing in existing_pitfalls:
                        # Calculate similarity
                        new_words = set(normalized_content.split())
                        existing_words = set(existing.split())
                        
                        if new_words and existing_words:
                            common_words = new_words.intersection(existing_words)
                            similarity = len(common_words) / min(len(new_words), len(existing_words))
                            
                            if similarity > 0.8:  # 80% similarity threshold
                                is_duplicate = True
                                logger.info(f"Skipping duplicate pitfall: {p['content'][:50]}...")
                                break
                    
                    if not is_duplicate:
                        pitfalls_to_add.append(p)
                        existing_pitfalls.append(normalized_content)
                
                # Only write if we have new pitfalls to add
                if pitfalls_to_add:
                    # If file doesn't exist, create with header
                    if not pitfalls_file.exists():
                        existing_content = f"# {model_name} Common Pitfalls\n\n*Last updated: {timestamp}*\n"
                    else:
                        # Update the last updated timestamp
                        existing_content = re.sub(
                            r'\*Last updated: .+\*', 
                            f'*Last updated: {timestamp}*', 
                            existing_content
                        )
                    
                    # Add new pitfalls
                    new_content = "\n"
                    for p in pitfalls_to_add:
                        new_content += f"\n## {p['content']}\n"
                        new_content += f"- **Confidence**: {p['confidence']}\n"
                        new_content += f"- **Source**: [{p['source']}]({p.get('source_url', '#')})\n"
                        if p.get('example_code'):
                            new_content += f"\n```\n{p['example_code']}\n```\n"
                        new_content += "\n"
                    
                    # Write combined content
                    if existing_content and not existing_content.endswith('\n'):
                        existing_content += '\n'
                    pitfalls_file.write_text(existing_content + new_content)
                    logger.info(f"Added {len(pitfalls_to_add)} new pitfalls for {model_name}")
            
            # Save tips to examples directory
            if practices["tips"]:
                examples_dir = model_dir / "examples"
                examples_dir.mkdir(exist_ok=True)
                
                tips_file = examples_dir / "tips.json"
                
                # Load existing tips
                existing_tips = []
                if tips_file.exists():
                    with open(tips_file, 'r') as f:
                        existing_tips = json.load(f)
                
                # Create a set of existing tip contents for deduplication
                # Normalize content for comparison (lowercase, strip whitespace)
                existing_contents = {tip["tip"].lower().strip() for tip in existing_tips}
                
                # Add new tips, avoiding duplicates
                for p in practices["tips"]:
                    normalized_content = p["content"].lower().strip()
                    
                    # Check for similar content (not just exact match)
                    is_duplicate = False
                    for existing_content in existing_contents:
                        # Calculate similarity (simple approach: check if 80% of words match)
                        new_words = set(normalized_content.split())
                        existing_words = set(existing_content.split())
                        
                        if new_words and existing_words:
                            common_words = new_words.intersection(existing_words)
                            similarity = len(common_words) / min(len(new_words), len(existing_words))
                            
                            if similarity > 0.8:  # 80% similarity threshold
                                is_duplicate = True
                                logger.info(f"Skipping duplicate tip: {p['content'][:50]}...")
                                break
                    
                    if not is_duplicate:
                        new_tip = {
                            "tip": p["content"],
                            "confidence": p["confidence"],
                            "source": p["source"],
                            "timestamp": p["timestamp"],
                            "example": p.get("example_code")
                        }
                        existing_tips.append(new_tip)
                        existing_contents.add(normalized_content)
                        logger.info(f"Added new tip for {model_name}: {p['content'][:50]}...")
                
                # Save merged tips
                with open(tips_file, 'w') as f:
                    json.dump(existing_tips, f, indent=2)
            
            # Update metadata without overwriting
            metadata_file = model_dir / "metadata.json"
            metadata = {}
            if metadata_file.exists():
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
            
            # Update metadata
            if "model_id" not in metadata:
                metadata["model_id"] = model_name
            metadata["last_updated"] = timestamp
            metadata["total_practices"] = metadata.get("total_practices", 0) + total_practices
            
            # Add sources
            if "sources" not in metadata:
                metadata["sources"] = []
            
            for content in self.processed_content:
                if content.source_url and content.source_url not in metadata["sources"]:
                    metadata["sources"].append(content.source_url)
            
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Saved {total_practices} practices for {model_name}")
        
        # Final summary
        if quality_threshold > 0:
            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"Quality evaluation complete! Took {total_time/60:.1f} minutes")
            logger.info(f"Evaluated {evaluated_count} practices, saved to {len(model_practices)} models")
    
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