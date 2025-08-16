"""
Service Discovery Pipeline - Discovers AI services from various sources
"""
import json
import re
import asyncio
import aiohttp
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class ServiceDiscoverySource(ABC):
    """Abstract base class for service discovery sources"""
    
    @abstractmethod
    async def discover_services(self) -> List[Dict]:
        """
        Discover services from this source
        Returns list of service dicts with: name, category, url, description
        """
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Return the name of this source"""
        pass


class GitHubAwesomeListSource(ServiceDiscoverySource):
    """Discovers services from GitHub Awesome lists"""
    
    def __init__(self):
        self.awesome_lists = [
            {
                'url': 'https://raw.githubusercontent.com/steven2358/awesome-generative-ai/main/README.md',
                'name': 'awesome-generative-ai'
            },
            {
                'url': 'https://raw.githubusercontent.com/mahseema/awesome-ai-tools/main/README.md',
                'name': 'awesome-ai-tools'
            },
            {
                'url': 'https://raw.githubusercontent.com/filipecalegario/awesome-generative-ai/main/README.md',
                'name': 'filipecalegario-awesome-generative-ai'
            },
            {
                'url': 'https://raw.githubusercontent.com/aishwaryanr/awesome-generative-ai-guide/main/README.md',
                'name': 'awesome-generative-ai-guide'
            },
            {
                'url': 'https://raw.githubusercontent.com/eudk/awesome-ai-tools/main/README.md',
                'name': 'eudk-awesome-ai-tools'
            }
        ]
    
    def get_source_name(self) -> str:
        return "github_awesome"
    
    async def discover_services(self) -> List[Dict]:
        """Parse GitHub Awesome lists for AI services"""
        services = []
        
        async with aiohttp.ClientSession() as session:
            for awesome_list in self.awesome_lists:
                try:
                    services.extend(await self._parse_awesome_list(session, awesome_list))
                except Exception as e:
                    logger.error(f"Failed to parse {awesome_list['name']}: {e}")
        
        return services
    
    async def _parse_awesome_list(self, session: aiohttp.ClientSession, list_info: Dict) -> List[Dict]:
        """Parse a single awesome list"""
        services = []
        
        async with session.get(list_info['url']) as response:
            if response.status != 200:
                logger.warning(f"Failed to fetch {list_info['name']}: {response.status}")
                return services
            
            content = await response.text()
            
            # Parse markdown for service entries
            # Common patterns in awesome lists:
            # - [ServiceName](url) - Description
            # - **ServiceName** - Description
            
            # Pattern 1: Links with descriptions
            link_pattern = r'\[([^\]]+)\]\(([^)]+)\)\s*[-–—:]\s*([^\n]+)'
            matches = re.findall(link_pattern, content)
            
            for name, url, description in matches:
                # Filter for actual services (not documentation/articles)
                if self._is_likely_service(name, url, description):
                    services.append({
                        'name': self._clean_service_name(name),
                        'url': url,
                        'description': description.strip(),
                        'category': self._infer_category(name, description),
                        'source': list_info['name'],
                        'discovered': datetime.now().isoformat()
                    })
            
            # Pattern 2: Bold entries
            bold_pattern = r'\*\*([^*]+)\*\*\s*[-–—:]\s*([^\n]+)'
            matches = re.findall(bold_pattern, content)
            
            for name, description in matches:
                if self._is_likely_service(name, '', description):
                    services.append({
                        'name': self._clean_service_name(name),
                        'url': '',
                        'description': description.strip(),
                        'category': self._infer_category(name, description),
                        'source': list_info['name'],
                        'discovered': datetime.now().isoformat()
                    })
        
        logger.info(f"Found {len(services)} services in {list_info['name']}")
        return services
    
    def _is_likely_service(self, name: str, url: str, description: str) -> bool:
        """Determine if entry is likely an AI service vs documentation/article"""
        # Skip common non-service entries and article-like titles
        skip_keywords = ['tutorial', 'guide', 'paper', 'book', 'course', 'awesome', 'list', 
                        'collection', 'article', 'news', 'blog', 'post', 'story', 'report',
                        'analysis', 'review', 'opinion', 'party', 'craze', 'trend', 'revolution',
                        'gold rush', 'heralds', 'announcement', 'release', 'sparks', 'transform']
        name_lower = name.lower()
        description_lower = description.lower()
        
        # Skip if name sounds like an article title (too many words, contains sentence-like structure)
        if len(name.split()) > 5:  # Service names are typically short
            return False
            
        if any(keyword in name_lower for keyword in skip_keywords):
            return False
            
        # Skip descriptions that sound like article summaries
        article_indicators = ['article', 'op-ed', 'announcement', 'examination of', 'summarizing',
                             'comprehensive look', 'explores', 'discusses', 'argues']
        if any(indicator in description_lower for indicator in article_indicators):
            return False
        
        # Check URL patterns that indicate actual services
        if url:
            # Skip news/article URLs
            if any(domain in url.lower() for domain in ['/blog/', '/news/', '/article/', 
                                                         'medium.com', 'arxiv.org', 'youtube.com']):
                return False
                
            service_domains = ['.ai', '.io', 'api.', 'app.', 'platform.', 'cloud.', 
                             'huggingface.co', 'openai.com', 'anthropic.com', 'cohere.com',
                             'replicate.com', 'stability.ai', 'github.com/.*api', 'github.com/.*sdk']
            if any(domain in url.lower() for domain in service_domains):
                return True
        
        # Look for service indicators (more specific now)
        service_indicators = ['api access', 'platform for', 'sdk', 'model api', 'inference', 
                             'endpoint', 'deployment', 'hosted', 'cloud service', 'playground',
                             'provides access to', 'api for']
        combined = (name + ' ' + description).lower()
        
        # Require at least one strong indicator
        strong_indicators = ['api', 'sdk', 'platform', 'model api', 'inference service', 
                            'provides access to', 'api for']
        has_strong = any(indicator in combined for indicator in strong_indicators)
        
        # If name looks like a product name (single word or two words max)
        is_product_name = len(name.split()) <= 2
        
        return has_strong and is_product_name
    
    def _clean_service_name(self, name: str) -> str:
        """Clean and normalize service name"""
        # Remove emojis, special characters
        name = re.sub(r'[^\w\s\-.]', '', name)
        # Remove extra whitespace
        name = ' '.join(name.split())
        return name.strip()
    
    def _infer_category(self, name: str, description: str) -> str:
        """Infer service category from name and description"""
        name_lower = name.lower()
        desc_lower = description.lower()
        combined = (name + ' ' + description).lower()
        
        # Priority-based categorization with weighted keywords
        # Check for most specific categories first
        
        # Video - very specific keywords
        video_strong = ['video', 'animation', 'motion graphics', 'movie', 'film', 'footage']
        video_names = ['synthesia', 'heygen', 'runway', 'pika', 'pictory', 'fliki', 
                      'invideo', 'luma', 'kaiber', 'genmo', 'hour one', 'deepbrain',
                      'colossyan', 'elai', 'steve.ai', 'rephrase', 'd-id']
        if any(kw in name_lower for kw in video_names):
            return 'video'
        if any(kw in combined for kw in video_strong):
            return 'video'
        
        # Audio - specific audio keywords
        audio_strong = ['audio', 'voice', 'speech', 'music', 'sound', 'tts', 'text-to-speech',
                       'voice synthesis', 'voice clone', 'podcast', 'transcription']
        audio_names = ['elevenlabs', 'eleven labs', 'murf', 'play.ht', 'wellsaid', 
                      'resemble', 'descript', 'overdub', 'respeecher', 'sonantic']
        if any(kw in name_lower for kw in audio_names):
            return 'audio'
        if any(kw in combined for kw in audio_strong):
            return 'audio'
        
        # Image - specific image keywords
        image_strong = ['image', 'picture', 'photo', 'art', 'drawing', 'illustration',
                       'graphic', 'visual', 'paint', 'design', 'artwork']
        image_names = ['dall-e', 'midjourney', 'stable diffusion', 'leonardo', 'ideogram',
                      'dreamstudio', 'nightcafe', 'artbreeder', 'deep dream']
        if any(kw in name_lower for kw in image_names):
            return 'image'
        if any(kw in combined for kw in image_strong):
            return 'image'
        
        # Code - programming specific
        code_strong = ['code', 'programming', 'developer', 'ide', 'compiler', 'debugger',
                      'repository', 'github', 'coding assistant']
        code_names = ['copilot', 'codeium', 'cursor', 'tabnine', 'codex', 'replit']
        if any(kw in name_lower for kw in code_names):
            return 'code'
        if any(kw in combined for kw in code_strong):
            return 'code'
        
        # Multimodal - handles multiple modalities
        multimodal_keywords = ['multimodal', 'vision', 'multi-modal', 'image and text',
                              'vision language', 'vlm', 'visual language']
        if any(kw in combined for kw in multimodal_keywords):
            return 'multimodal'
        
        # Text/LLM - language models and text generation
        # Check this AFTER more specific categories to avoid false positives
        text_strong = ['llm', 'language model', 'chatbot', 'chat assistant', 'gpt', 
                      'claude', 'writing assistant', 'text generation', 'conversation']
        text_names = ['openai', 'anthropic', 'claude', 'gpt', 'mistral', 'llama',
                     'gemini', 'palm', 'character.ai', 'replika']
        # Exclude if it's clearly about text-to-X conversion
        if not any(pattern in combined for pattern in ['text-to-video', 'text-to-image', 
                                                       'text-to-speech', 'text-to-audio']):
            if any(kw in name_lower for kw in text_names):
                return 'text'
            if any(kw in combined for kw in text_strong):
                return 'text'
        
        return 'general'


class HuggingFaceModelsSource(ServiceDiscoverySource):
    """Discovers popular models from Hugging Face"""
    
    def get_source_name(self) -> str:
        return "huggingface"
    
    async def discover_services(self) -> List[Dict]:
        """Fetch popular models from Hugging Face API"""
        # TODO: Implement HF API integration
        # For now, return empty list
        return []


class ServiceRegistry:
    """Manages discovered services with deduplication"""
    
    def __init__(self, registry_path: Path = Path("data/cache/services.json")):
        self.registry_path = registry_path
        self.services = {}
        self.aliases = {}  # Maps variations to canonical names
        self.load()
    
    def load(self):
        """Load existing registry from file"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r') as f:
                data = json.load(f)
                self.services = data.get('services', {})
                self.aliases = data.get('aliases', {})
    
    def save(self):
        """Save registry to file"""
        # Ensure directory exists
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'services': self.services,
            'aliases': self.aliases,
            'last_updated': datetime.now().isoformat()
        }
        with open(self.registry_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def add_service(self, service_data: Dict) -> str:
        """
        Add a service to the registry with deduplication
        Returns the canonical name used
        """
        name = service_data['name']
        canonical = self._get_canonical_name(name)
        
        if canonical not in self.services:
            # New service
            self.services[canonical] = {
                'canonical_name': canonical,
                'display_name': name,
                'aliases': [canonical, name.lower()],
                'category': service_data.get('category', 'general'),
                'description': service_data.get('description', ''),
                'url': service_data.get('url', ''),
                'sources': [service_data.get('source', 'unknown')],
                'first_seen': service_data.get('discovered', datetime.now().isoformat()),
                'last_seen': datetime.now().isoformat()
            }
            
            # Add aliases
            self.aliases[name.lower()] = canonical
            self.aliases[canonical] = canonical
        else:
            # Update existing service
            existing = self.services[canonical]
            
            # Add new aliases
            if name.lower() not in existing['aliases']:
                existing['aliases'].append(name.lower())
                self.aliases[name.lower()] = canonical
            
            # Add source if new
            source = service_data.get('source', 'unknown')
            if source not in existing['sources']:
                existing['sources'].append(source)
            
            # Update last seen
            existing['last_seen'] = datetime.now().isoformat()
            
            # Update description if better
            if len(service_data.get('description', '')) > len(existing['description']):
                existing['description'] = service_data['description']
        
        return canonical
    
    def _get_canonical_name(self, name: str) -> str:
        """Get canonical name for a service"""
        name_lower = name.lower()
        
        # Check if already mapped
        if name_lower in self.aliases:
            return self.aliases[name_lower]
        
        # Create canonical form
        # Remove common suffixes
        canonical = re.sub(r'\s*(ai|api|platform|tool|app|\.ai|\.io|\.com)$', '', name_lower)
        canonical = re.sub(r'[^a-z0-9]', '', canonical)
        
        return canonical
    
    def get_all_services(self) -> Dict:
        """Get all registered services"""
        return self.services
    
    def get_service_names_by_category(self, category: Optional[str] = None) -> List[str]:
        """Get list of service names, optionally filtered by category"""
        if category:
            return [
                service['display_name'] 
                for service in self.services.values() 
                if service['category'] == category
            ]
        return [service['display_name'] for service in self.services.values()]


class ServiceDiscoveryPipeline:
    """Main pipeline for discovering AI services"""
    
    def __init__(self):
        self.sources = []
        self.registry = ServiceRegistry()
    
    def add_source(self, source: ServiceDiscoverySource):
        """Add a discovery source to the pipeline"""
        self.sources.append(source)
    
    async def run(self):
        """Run the discovery pipeline"""
        logger.info("Starting service discovery pipeline")
        
        all_services = []
        
        # Gather services from all sources
        for source in self.sources:
            logger.info(f"Discovering services from {source.get_source_name()}")
            try:
                services = await source.discover_services()
                all_services.extend(services)
            except Exception as e:
                logger.error(f"Failed to discover from {source.get_source_name()}: {e}")
        
        # Add to registry (handles deduplication)
        logger.info(f"Processing {len(all_services)} discovered services")
        
        for service in all_services:
            canonical = self.registry.add_service(service)
            logger.debug(f"Added/updated service: {canonical}")
        
        # Save registry
        self.registry.save()
        
        # Print summary
        total = len(self.registry.get_all_services())
        by_category = {}
        for service in self.registry.services.values():
            cat = service['category']
            by_category[cat] = by_category.get(cat, 0) + 1
        
        logger.info(f"Discovery complete! Total services: {total}")
        for cat, count in sorted(by_category.items()):
            logger.info(f"  {cat}: {count}")
        
        return self.registry


async def main():
    """Run the service discovery pipeline"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.core.logging import setup_logging
    
    setup_logging()
    
    # Create pipeline
    pipeline = ServiceDiscoveryPipeline()
    
    # Add sources
    pipeline.add_source(GitHubAwesomeListSource())
    # pipeline.add_source(HuggingFaceModelsSource())  # Future
    
    # Run discovery
    registry = await pipeline.run()
    
    # Print some examples
    print("\nExample services discovered:")
    for i, (name, service) in enumerate(registry.get_all_services().items()):
        if i >= 10:
            break
        print(f"  - {service['display_name']} ({service['category']}): {service['description'][:50]}...")


if __name__ == "__main__":
    asyncio.run(main())