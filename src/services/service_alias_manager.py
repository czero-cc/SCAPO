"""
Service Alias Manager - Handles service name variations and normalization
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
import logging

logger = logging.getLogger(__name__)


class ServiceAliasManager:
    """Manages service name aliases and variations"""
    
    # Common variations we need to handle
    VARIATION_PATTERNS = [
        # Spacing variations
        ('elevenlabs', ['eleven labs', 'elevenlabs', 'eleven-labs', 'ElevenLabs', 'Eleven Labs']),
        ('heygen', ['heygen', 'hey gen', 'hey-gen', 'HeyGen', 'Hey Gen']),
        ('stablediffusion', ['stable diffusion', 'stablediffusion', 'stable-diffusion', 'StableDiffusion']),
        ('midjourney', ['midjourney', 'mid journey', 'mid-journey', 'MidJourney', 'Mid Journey']),
        ('characterai', ['character.ai', 'character ai', 'characterai', 'character-ai', 'Character.AI']),
        ('githubcopilot', ['github copilot', 'githubcopilot', 'github-copilot', 'copilot', 'Copilot']),
        ('openai', ['openai', 'open ai', 'open-ai', 'OpenAI', 'Open AI']),
        ('anthropic', ['anthropic', 'claude', 'Claude', 'Anthropic']),
        ('huggingface', ['huggingface', 'hugging face', 'hugging-face', 'HuggingFace', 'HF']),
        ('scaleai', ['scale ai', 'scaleai', 'scale-ai', 'Scale AI', 'Scale.AI']),
        ('replicastudios', ['replica studios', 'replicastudios', 'replica-studios', 'Replica Studios']),
        ('playht', ['play.ht', 'playht', 'play-ht', 'Play.ht', 'PlayHT']),
        ('wellsaidlabs', ['wellsaid', 'wellsaid labs', 'wellsaidlabs', 'WellSaid Labs', 'WellSaid']),
        ('deepbrain', ['deepbrain', 'deep brain', 'deep-brain', 'DeepBrain', 'Deep Brain AI']),
        ('synthesia', ['synthesia', 'Synthesia']),
        ('did', ['d-id', 'did', 'D-ID', 'D-id']),
        ('runway', ['runway', 'runway ml', 'runwayml', 'Runway', 'RunwayML']),
        ('pika', ['pika', 'pika labs', 'pikalabs', 'Pika', 'Pika Labs']),
        ('leonardo', ['leonardo', 'leonardo ai', 'leonardoai', 'Leonardo', 'Leonardo.AI']),
        ('ideogram', ['ideogram', 'ideogram ai', 'ideogramai', 'Ideogram', 'Ideogram.AI']),
        ('cursor', ['cursor', 'cursor ai', 'cursorai', 'Cursor', 'Cursor AI']),
        ('codeium', ['codeium', 'Codeium']),
        ('luma', ['luma', 'luma ai', 'lumaai', 'luma labs', 'lumalabs', 'Luma', 'Luma Labs']),
        ('kaiber', ['kaiber', 'kaiber ai', 'kaiberai', 'Kaiber', 'Kaiber.AI']),
        ('genmo', ['genmo', 'genmo ai', 'genmoai', 'Genmo', 'Genmo.AI']),
        ('haiper', ['haiper', 'haiper ai', 'haiperai', 'Haiper', 'Haiper.AI']),
        ('moonvalley', ['moonvalley', 'moon valley', 'moon-valley', 'MoonValley', 'Moon Valley']),
        ('neuralframes', ['neural frames', 'neuralframes', 'neural-frames', 'Neural Frames']),
        ('immersity', ['immersity', 'immersity ai', 'immersityai', 'Immersity', 'Immersity.AI']),
        ('leiapix', ['leiapix', 'leia pix', 'leia-pix', 'LeiaPix', 'Leia Pix']),
        ('depthlab', ['depthlab', 'depth lab', 'depth-lab', 'DepthLab', 'Depth Lab']),
    ]
    
    def __init__(self, services_path: Path = Path("data/cache/services.json")):
        self.services_path = services_path
        self.services = {}
        self.aliases = {}  # Maps any variation to canonical name
        self.reverse_aliases = {}  # Maps canonical to all variations
        self.load_services()
        self.build_alias_maps()
    
    def load_services(self):
        """Load services from JSON"""
        if self.services_path.exists():
            with open(self.services_path, 'r') as f:
                data = json.load(f)
                self.services = data.get('services', {})
    
    def build_alias_maps(self):
        """Build comprehensive alias mappings"""
        # First, add known variations
        for canonical, variations in self.VARIATION_PATTERNS:
            self.reverse_aliases[canonical] = set(variations)
            for variation in variations:
                self.aliases[variation.lower()] = canonical
                self.aliases[self.normalize_name(variation)] = canonical
        
        # Then add variations from services.json
        for service_key, service_data in self.services.items():
            display_name = service_data.get('display_name', '')
            
            # Find if this matches any known pattern
            matched_canonical = None
            for canonical, variations in self.VARIATION_PATTERNS:
                if any(self.normalize_name(display_name) == self.normalize_name(v) for v in variations):
                    matched_canonical = canonical
                    break
            
            if matched_canonical:
                # Add this service key as an alias
                self.aliases[service_key] = matched_canonical
                self.aliases[display_name.lower()] = matched_canonical
                if matched_canonical in self.reverse_aliases:
                    self.reverse_aliases[matched_canonical].add(display_name)
            else:
                # New service not in our patterns
                canonical = service_key
                self.aliases[service_key] = canonical
                self.aliases[display_name.lower()] = canonical
                self.aliases[self.normalize_name(display_name)] = canonical
                self.reverse_aliases[canonical] = {service_key, display_name, display_name.lower()}
    
    def normalize_name(self, name: str) -> str:
        """Normalize a service name for matching"""
        # Remove special characters and normalize spacing
        normalized = name.lower()
        normalized = re.sub(r'[^a-z0-9]+', '', normalized)
        return normalized
    
    def get_canonical_name(self, name: str) -> Optional[str]:
        """Get the canonical name for any variation"""
        name_lower = name.lower()
        
        # Try exact match first
        if name_lower in self.aliases:
            return self.aliases[name_lower]
        
        # Try normalized match
        normalized = self.normalize_name(name)
        if normalized in self.aliases:
            return self.aliases[normalized]
        
        # Try partial matching for common services
        for canonical, variations in self.VARIATION_PATTERNS:
            for variation in variations:
                if name_lower in variation.lower() or variation.lower() in name_lower:
                    return canonical
        
        return None
    
    def get_display_name(self, canonical_or_alias: str) -> str:
        """Get the display name for a service"""
        canonical = self.get_canonical_name(canonical_or_alias)
        if not canonical:
            canonical = canonical_or_alias
        
        # Look for the service in our data
        for service_key, service_data in self.services.items():
            if self.get_canonical_name(service_key) == canonical:
                return service_data.get('display_name', canonical_or_alias)
        
        # Fallback to the canonical name with proper casing
        for pattern_canonical, variations in self.VARIATION_PATTERNS:
            if pattern_canonical == canonical and variations:
                # Return the first variation (usually the properly cased one)
                return variations[0]
        
        return canonical_or_alias
    
    def get_all_variations(self, name: str) -> Set[str]:
        """Get all known variations of a service name"""
        canonical = self.get_canonical_name(name)
        if not canonical:
            return {name}
        
        return self.reverse_aliases.get(canonical, {name})
    
    def find_service_in_text(self, text: str) -> List[str]:
        """Find all service mentions in a text"""
        found_services = set()
        text_lower = text.lower()
        
        for canonical, variations in self.VARIATION_PATTERNS:
            for variation in variations:
                if variation.lower() in text_lower:
                    found_services.add(canonical)
                    break
        
        return list(found_services)
    
    def match_service(self, query: str) -> Optional[Dict]:
        """Match a query to a service and return its data"""
        canonical = self.get_canonical_name(query)
        if not canonical:
            return None
        
        # Find the service data
        for service_key, service_data in self.services.items():
            if self.get_canonical_name(service_key) == canonical:
                return {
                    'canonical': canonical,
                    'display_name': service_data.get('display_name', query),
                    'category': service_data.get('category', 'general'),
                    'service_key': service_key,
                    'all_variations': list(self.get_all_variations(query))
                }
        
        # If not in services.json, still return what we know
        return {
            'canonical': canonical,
            'display_name': self.get_display_name(canonical),
            'category': 'general',
            'service_key': canonical,
            'all_variations': list(self.get_all_variations(query))
        }


def test_alias_manager():
    """Test the alias manager"""
    manager = ServiceAliasManager()
    
    test_cases = [
        "Eleven Labs",
        "elevenlabs", 
        "eleven-labs",
        "HeyGen",
        "hey gen",
        "GitHub Copilot",
        "copilot",
        "character.ai",
        "Character AI",
        "midjourney",
        "Mid Journey",
        "RunwayML",
        "runway"
    ]
    
    print("Testing service name matching:")
    for test in test_cases:
        result = manager.match_service(test)
        if result:
            print(f"  '{test}' -> {result['display_name']} (canonical: {result['canonical']})")
        else:
            print(f"  '{test}' -> No match found")
    
    print("\nTesting text extraction:")
    sample_text = "I use Eleven Labs for voice and HeyGen for video. GitHub Copilot helps with coding."
    found = manager.find_service_in_text(sample_text)
    print(f"  Found services: {found}")
    
    print("\nTesting variations:")
    for service in ["elevenlabs", "githubcopilot"]:
        variations = manager.get_all_variations(service)
        print(f"  Variations of '{service}': {variations}")


if __name__ == "__main__":
    test_alias_manager()