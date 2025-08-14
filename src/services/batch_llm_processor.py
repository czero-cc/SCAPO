"""
Batch LLM Processor - Efficiently processes multiple posts in single LLM calls
with careful context window management
"""
import json
import asyncio
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import tiktoken
import logging
import os

logger = logging.getLogger(__name__)


class BatchLLMProcessor:
    """Processes multiple posts in a single LLM call with context window awareness"""
    
    # Default context limit if we can't determine from API or env
    DEFAULT_CONTEXT_LIMIT = 4096  # Conservative default
    
    # Reserved tokens for system prompt and response
    RESERVED_TOKENS = {
        'system_prompt': 500,    # Tokens for instructions
        'response_buffer': 1000,  # Tokens for model response (reduced)
        'safety_margin': 200      # Additional safety buffer (reduced)
    }
    
    def __init__(self, model_name: str = "gpt-3.5-turbo"):
        self.model_name = model_name
        self.encoder = self._get_encoder(model_name)
        
        # Try to get context from OpenRouter API or environment variables
        self.context_limit = self._get_dynamic_context_limit(model_name)
        if not self.context_limit:
            # For local models, check environment variable
            from src.core.config import settings
            if settings.llm_provider == "local" and settings.local_llm_max_context:
                self.context_limit = settings.local_llm_max_context
                logger.info(f"Using LOCAL_LLM_MAX_CONTEXT: {self.context_limit}")
            else:
                # Fall back to conservative default
                self.context_limit = self.DEFAULT_CONTEXT_LIMIT
                logger.warning(f"Using default context limit: {self.context_limit}. Set LOCAL_LLM_MAX_CONTEXT for better performance.")
        
        self.usable_tokens = self._calculate_usable_tokens()
        
        logger.info(f"Initialized BatchLLMProcessor for {model_name}")
        logger.info(f"Context limit: {self.context_limit}, Usable tokens: {self.usable_tokens}")
        logger.info("NOTE: Quality filtering (LLM_QUALITY_THRESHOLD) is NOT applied in batch processing - mixed quality content expected")
    
    def _get_dynamic_context_limit(self, model_name: str) -> Optional[int]:
        """Try to get context limit from OpenRouter API"""
        try:
            # Try to get API key from settings or environment
            from src.core.config import Settings
            settings = Settings()
            api_key = settings.openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
            
            if api_key:
                from src.services.openrouter_context import OpenRouterContextManager
                manager = OpenRouterContextManager(api_key=api_key)
                # Load from cache first
                manager.load_cache()
                context = manager.get_context_length(model_name)
                if context:
                    logger.info(f"Got context limit from OpenRouter: {context}")
                    return context
        except Exception as e:
            logger.debug(f"Could not get context from OpenRouter: {e}")
        return None
    
    def _get_encoder(self, model_name: str):
        """Get appropriate tokenizer for the model"""
        try:
            # Try to get model-specific encoder
            if 'gpt-4' in model_name.lower():
                return tiktoken.encoding_for_model('gpt-4')
            elif 'gpt-3.5' in model_name.lower():
                return tiktoken.encoding_for_model('gpt-3.5-turbo')
            else:
                # Default to cl100k_base for most modern models
                return tiktoken.get_encoding('cl100k_base')
        except Exception as e:
            logger.warning(f"Could not get specific encoder for {model_name}: {e}")
            return tiktoken.get_encoding('cl100k_base')
    
    
    def _calculate_usable_tokens(self) -> int:
        """Calculate tokens available for actual content"""
        reserved_total = sum(self.RESERVED_TOKENS.values())
        usable = self.context_limit - reserved_total
        
        # Ensure we have reasonable space
        if usable < 1000:
            logger.warning(f"Very limited context space: {usable} tokens")
            return max(1000, usable)  # Minimum 1000 tokens for content
        
        return usable
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text"""
        try:
            return len(self.encoder.encode(text))
        except Exception as e:
            logger.warning(f"Token counting failed, using approximation: {e}")
            # Fallback: approximate 1 token per 4 characters
            return len(text) // 4
    
    def create_batch_prompt(self, posts: List[Dict], service_name: str) -> str:
        """Create prompt for batch processing multiple posts"""
        # Simplify posts to just title and content
        simplified_posts = []
        for p in posts:
            simplified_posts.append({
                "title": p.get("title", ""),
                "content": p.get("content", "")[:500],  # Limit content length
                "id": p.get("id", "")
            })
        
        return f"""Extract SPECIFIC, ACTIONABLE tips about {service_name} from these Reddit posts. 

CRITICAL RULES:
1. ONLY extract information DIRECTLY RELATED to {service_name}
2. IGNORE any content about unrelated topics (e.g., 3D printing, cooking, gaming, etc.)
3. IGNORE generic advice like "be respectful" or "read the docs"
4. Each extracted item MUST mention {service_name} or be clearly about it
5. Include the FULL context - don't truncate mid-sentence

Posts:
{json.dumps(simplified_posts, indent=2)}

Look for SPECIFIC mentions about {service_name}:
- Exact pricing, tiers, limits (e.g., "$10/month", "300 requests/day", "10k character limit")
- Hidden features or workarounds (e.g., "use API v2 for unlimited", "add this flag to bypass limit")
- Specific parameter values (e.g., "set temperature=0.7", "use model='gpt-4-turbo'")
- Bugs and their fixes (e.g., "crashes when X>100", "use version 2.3.1 to avoid bug")
- Specific file names, configs, or settings (e.g., "edit config.json", "add to .env file")
- Alternative access methods (e.g., "use Azure credits", "third-party API is cheaper")
- Exact error messages and solutions

EXTRACTION GUIDELINES:
- Include valuable info even if phrasing is informal or broken
- Preserve the complete thought/tip - don't cut off mid-sentence
- Focus on SPECIFIC details (numbers, settings, commands) about {service_name}
- Settings must be returned as 'key=value' strings, NOT as dictionaries

Return JSON with ONLY {service_name}-specific information:
{{
  "service": "{service_name}",
  "problems": ["{service_name}-specific technical problems with details"],
  "tips": ["{service_name}-specific actionable tips with concrete details"],
  "cost_info": ["{service_name}-specific pricing, limits, or credit information"],
  "settings": ["{service_name} settings as 'key=value' strings, NOT dictionaries"]
}}

If you find NO specific technical information about {service_name}, return empty lists.
Generic tips or unrelated content (3D printing, cooking, etc.) MUST BE IGNORED."""
    
    def batch_posts_by_tokens(self, posts: List[Dict], service_name: str) -> List[List[Dict]]:
        """
        Batch posts to fit within context window
        Returns list of post batches that fit within token limits
        """
        batches = []
        current_batch = []
        current_tokens = 0
        
        # Calculate base prompt tokens (without posts)
        base_prompt = self.create_batch_prompt([], service_name)
        base_tokens = self.count_tokens(base_prompt)
        
        logger.info(f"Base prompt tokens: {base_tokens}")
        
        for post in posts:
            # Serialize post to estimate tokens
            post_json = json.dumps(post, indent=2)
            post_tokens = self.count_tokens(post_json)
            
            # Check if adding this post would exceed limit
            projected_tokens = base_tokens + current_tokens + post_tokens
            
            if projected_tokens > self.usable_tokens:
                # Save current batch if it has posts
                if current_batch:
                    batches.append(current_batch)
                    logger.info(f"Created batch with {len(current_batch)} posts, ~{current_tokens} tokens")
                
                # Start new batch
                current_batch = [post]
                current_tokens = post_tokens
                
                # Check if single post is too large
                if post_tokens > self.usable_tokens - base_tokens:
                    logger.warning(f"Single post exceeds token limit ({post_tokens} tokens), truncating")
                    # Truncate post content
                    if 'content' in post:
                        max_content_tokens = (self.usable_tokens - base_tokens - 500) * 4  # Convert to chars
                        post['content'] = post['content'][:max_content_tokens] + "...[truncated]"
                    current_tokens = self.count_tokens(json.dumps(post))
            else:
                # Add to current batch
                current_batch.append(post)
                current_tokens += post_tokens
        
        # Add final batch
        if current_batch:
            batches.append(current_batch)
            logger.info(f"Created final batch with {len(current_batch)} posts, ~{current_tokens} tokens")
        
        logger.info(f"Created {len(batches)} batches from {len(posts)} posts")
        return batches
    
    def estimate_batch_size(self, sample_post: Dict) -> int:
        """
        Estimate optimal batch size based on sample post
        Returns estimated number of posts that can fit in one batch
        """
        # Get base prompt size
        base_prompt = self.create_batch_prompt([], "sample_service")
        base_tokens = self.count_tokens(base_prompt)
        
        # Get sample post size
        post_json = json.dumps(sample_post, indent=2)
        post_tokens = self.count_tokens(post_json)
        
        # Calculate how many posts can fit
        available_tokens = self.usable_tokens - base_tokens
        estimated_posts = available_tokens // post_tokens
        
        # Apply safety factor
        safe_estimate = int(estimated_posts * 0.8)  # 80% to be safe
        
        logger.info(f"Estimated batch size: {safe_estimate} posts")
        logger.info(f"  Base prompt: {base_tokens} tokens")
        logger.info(f"  Sample post: {post_tokens} tokens")
        logger.info(f"  Available: {available_tokens} tokens")
        
        return max(1, safe_estimate)  # At least 1 post per batch
    
    async def process_batch(self, posts: List[Dict], service_name: str, llm_processor) -> Dict:
        """
        Process a batch of posts with the LLM
        Returns extracted problems, solutions, and optimizations
        """
        # Create prompt
        prompt = self.create_batch_prompt(posts, service_name)
        
        # Check token count
        prompt_tokens = self.count_tokens(prompt)
        logger.info(f"Processing batch of {len(posts)} posts ({prompt_tokens} tokens) for {service_name}")
        
        if prompt_tokens > self.context_limit:
            logger.error(f"Batch exceeds context limit! {prompt_tokens} > {self.context_limit}")
            # Try to recover by splitting batch
            if len(posts) > 1:
                mid = len(posts) // 2
                logger.info(f"Splitting batch into two parts: {mid} and {len(posts) - mid} posts")
                result1 = await self.process_batch(posts[:mid], service_name, llm_processor)
                result2 = await self.process_batch(posts[mid:], service_name, llm_processor)
                # Merge results
                return self.merge_results([result1, result2])
            else:
                logger.error("Cannot split single post, truncating")
                # Truncate the single post
                if 'content' in posts[0]:
                    posts[0]['content'] = posts[0]['content'][:1000] + "...[truncated]"
                prompt = self.create_batch_prompt(posts, service_name)
        
        try:
            # Process with LLM
            response = await llm_processor.process_raw_prompt(prompt)
            
            # Check if response is empty
            if not response or response.strip() == "":
                logger.error(f"Empty response from LLM for {service_name}")
                return {
                    "service": service_name,
                    "problems": [],
                    "tips": [],
                    "cost_info": [],
                    "settings": [],
                    "error": "Empty response from LLM",
                    "batch_size": len(posts)
                }
            
            # Parse response
            result = json.loads(response)
            
            # Clean settings - ensure they are strings not dicts
            if 'settings' in result:
                clean_settings = []
                for setting in result['settings']:
                    if isinstance(setting, dict):
                        # Convert dict to string format
                        for key, value in setting.items():
                            clean_settings.append(f"{key} = {value}")
                    elif isinstance(setting, str):
                        clean_settings.append(setting)
                result['settings'] = clean_settings
            
            # Add metadata
            result['batch_size'] = len(posts)
            result['timestamp'] = datetime.now().isoformat()
            result['token_count'] = prompt_tokens
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            logger.error(f"Raw response: {response[:500]}...")
            return {
                "service": service_name,
                "problems": [],
                "optimizations": [],
                "parameters": [],
                "error": str(e),
                "batch_size": len(posts)
            }
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            return {
                "service": service_name,
                "problems": [],
                "optimizations": [],
                "parameters": [],
                "error": str(e),
                "batch_size": len(posts)
            }
    
    def merge_results(self, results: List[Dict]) -> Dict:
        """Merge multiple batch results into one"""
        merged = {
            "service": results[0].get("service", "unknown"),
            "problems": [],
            "tips": [],
            "cost_info": [],
            "settings": [],
            "batch_count": len(results),
            "total_posts": sum(r.get("batch_size", 0) for r in results)
        }
        
        for result in results:
            merged["problems"].extend(result.get("problems", []))
            merged["tips"].extend(result.get("tips", []))
            merged["cost_info"].extend(result.get("cost_info", []))
            merged["settings"].extend(result.get("settings", []))
        
        # Lightweight deduplication - only for simple strings
        # Using case-insensitive comparison to catch more duplicates
        def dedupe_list(items):
            """Deduplicate while preserving order and handling edge cases"""
            if not items:
                return []
            seen = set()
            deduped = []
            for item in items:
                # Only dedupe strings, keep other types as-is
                if isinstance(item, str):
                    # Use lowercase for comparison but keep original case
                    item_lower = item.lower().strip()
                    if item_lower not in seen:
                        seen.add(item_lower)
                        deduped.append(item)
                else:
                    # Non-strings pass through (shouldn't happen but safety first)
                    deduped.append(item)
            return deduped
        
        # Apply deduplication
        merged["problems"] = dedupe_list(merged["problems"])
        merged["tips"] = dedupe_list(merged["tips"])
        merged["cost_info"] = dedupe_list(merged["cost_info"])
        merged["settings"] = dedupe_list(merged["settings"])
        
        logger.debug(f"Deduplication: problems {len(results[0].get('problems', []))}→{len(merged['problems'])}, "
                    f"tips {len(results[0].get('tips', []))}→{len(merged['tips'])}")
        
        return merged
    
    def _deduplicate_problems(self, problems: List[Dict]) -> List[Dict]:
        """Deduplicate problems by problem text"""
        seen = {}
        for problem in problems:
            key = problem.get("problem", "").lower()
            if key not in seen:
                seen[key] = problem
            else:
                # Merge post_ids
                existing_ids = seen[key].get("post_ids", [])
                new_ids = problem.get("post_ids", [])
                seen[key]["post_ids"] = list(set(existing_ids + new_ids))
                # Merge solutions
                existing_solutions = seen[key].get("solutions", [])
                new_solutions = problem.get("solutions", [])
                seen[key]["solutions"] = list(set(existing_solutions + new_solutions))
        
        return list(seen.values())
    
    def _deduplicate_optimizations(self, optimizations: List[Dict]) -> List[Dict]:
        """Deduplicate optimizations by tip text"""
        seen = {}
        for opt in optimizations:
            key = opt.get("tip", "").lower()
            if key not in seen:
                seen[key] = opt
            else:
                # Merge post_ids
                existing_ids = seen[key].get("post_ids", [])
                new_ids = opt.get("post_ids", [])
                seen[key]["post_ids"] = list(set(existing_ids + new_ids))
        
        return list(seen.values())
    
    def _deduplicate_parameters(self, parameters: List[Dict]) -> List[Dict]:
        """Deduplicate parameters by parameter name"""
        seen = {}
        for param in parameters:
            key = param.get("parameter", "").lower()
            if key not in seen:
                seen[key] = param
            else:
                # Merge post_ids
                existing_ids = seen[key].get("post_ids", [])
                new_ids = param.get("post_ids", [])
                seen[key]["post_ids"] = list(set(existing_ids + new_ids))
        
        return list(seen.values())


async def test_batch_processor():
    """Test the batch processor with sample data"""
    processor = BatchLLMProcessor("gpt-3.5-turbo")
    
    # Sample posts
    sample_posts = [
        {
            "id": "post1",
            "title": "HeyGen burned through my credits",
            "content": "I uploaded a 5 minute video and it cost me $50 in credits! The lip sync quality wasn't even that good.",
            "score": 45
        },
        {
            "id": "post2",
            "title": "Found a way to reduce HeyGen costs",
            "content": "If you batch process videos and use 720p instead of 1080p, you can save about 40% on credits.",
            "score": 123
        }
    ]
    
    # Test token counting
    for post in sample_posts:
        tokens = processor.count_tokens(json.dumps(post))
        print(f"Post {post['id']}: {tokens} tokens")
    
    # Test batching
    batches = processor.batch_posts_by_tokens(sample_posts * 20, "HeyGen")
    print(f"\nCreated {len(batches)} batches:")
    for i, batch in enumerate(batches):
        print(f"  Batch {i+1}: {len(batch)} posts")
    
    # Test batch size estimation
    estimated_size = processor.estimate_batch_size(sample_posts[0])
    print(f"\nEstimated batch size: {estimated_size} posts per batch")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_batch_processor())