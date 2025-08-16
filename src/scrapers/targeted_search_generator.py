"""
Targeted Search Query Generator - Creates specific searches for discovered services
"""
import json
from pathlib import Path
from typing import List, Dict, Set
import logging
from datetime import datetime
import sys
sys.path.append(str(Path(__file__).parent.parent))
from src.services.service_alias_manager import ServiceAliasManager

logger = logging.getLogger(__name__)


class TargetedSearchGenerator:
    """Generates targeted search queries for specific AI services"""
    
    def __init__(self, services_path: Path = Path("data/cache/services.json")):
        self.services_path = services_path
        self.services = {}
        self.alias_manager = ServiceAliasManager(services_path)
        self.load_services()
        
        # More specific search patterns to find actionable tips
        self.problem_patterns = {
            'cost': [
                '"{service}" price per month',
                '"{service}" credits cost',
                '"{service}" tier pricing',
                '"{service}" free limit'
            ],
            'optimization': [
                '"{service}" config settings',
                '"{service}" parameters temperature',
                '"{service}" system prompt',
                '"{service}" model selection'
            ],
            'technical': [
                '"{service}" API key',
                '"{service}" rate limit daily',
                '"{service}" context window',
                '"{service}" max tokens'
            ],
            'workarounds': [
                '"{service}" bypass limit',
                '"{service}" unlimited hack',
                '"{service}" Azure credits',
                '"{service}" alternative API'
            ],
            'bugs': [
                '"{service}" bug fix',
                '"{service}" not working',
                '"{service}" error message',
                '"{service}" crashes when'
            ]
        }
        
        # High-priority services for focused extraction (manually curated)
        self.priority_services = {
            'heygen', 'synthesia', 'elevenlabs', 'eleven labs', 'runway', 'leonardo',
            'midjourney', 'd-id', 'pika', 'luma', 'replika', 'character.ai',
            'spatialos', 'unity cloud', 'soul machines', 'murf', 'play.ht',
            'ideogram', 'github copilot', 'cursor', 'codeium', 'scale ai',
            'glambase', 'wav2lip', 'rephrase.ai', 'hour one', 'deepbrain',
            'synthetically', 'colossyan', 'elai', 'steve.ai', 'pictory',
            'invideo', 'fliki', 'wellsaid', 'resemble', 'descript',
            'overdub', 'respeecher', 'sonantic', 'replica studios',
            'kaiber', 'genmo', 'lumalabs', 'haiper', 'moonvalley',
            'neural frames', 'immersity', 'leiapix', 'depthlab'
        }
    
    def load_services(self):
        """Load discovered services from JSON"""
        if self.services_path.exists():
            with open(self.services_path, 'r') as f:
                data = json.load(f)
                self.services = data.get('services', {})
    
    def generate_queries_for_service(self, service_name: str, max_queries: int = 10, use_all_patterns: bool = False) -> List[Dict]:
        """Generate queries for a specific service
        
        Args:
            service_name: The service to generate queries for
            max_queries: Maximum number of queries to generate
            use_all_patterns: If True, use ALL patterns (20 total), not just first from each category
        """
        queries = []
        
        # Try to get service info from alias manager
        service_info = self.alias_manager.match_service(service_name)
        if service_info:
            service_category = service_info['category']
            service_key = service_info['service_key']
        else:
            service_category = 'general'
            service_key = service_name.lower().replace(' ', '-')
        
        # If category is 'general', try to determine it from known keywords
        if service_category == 'general':
            service_name_lower = service_name.lower()
            if any(keyword in service_name_lower for keyword in ['midjourney', 'dall-e', 'stable diffusion', 'leonardo', 'ideogram']):
                service_category = 'image'
            elif any(keyword in service_name_lower for keyword in ['runway', 'pika', 'luma', 'kaiber', 'genmo', 'haiper']):
                service_category = 'video'
            elif any(keyword in service_name_lower for keyword in ['elevenlabs', 'eleven labs', 'murf', 'play.ht', 'wellsaid', 'descript']):
                service_category = 'audio'
            elif any(keyword in service_name_lower for keyword in ['gpt', 'claude', 'llama', 'gemini', 'mistral']):
                service_category = 'text'
            elif any(keyword in service_name_lower for keyword in ['copilot', 'cursor', 'codeium', 'tabnine']):
                service_category = 'code'
        
        if use_all_patterns:
            # Use ALL patterns from each category
            for pattern_type, pattern_list in self.problem_patterns.items():
                for pattern in pattern_list:
                    query_text = pattern.replace('{service}', service_name)
                    query_url = f'https://old.reddit.com/search?q={query_text.replace(" ", "+").replace('"', "%22")}'
                    
                    query = {
                        'service': service_name,
                        'service_key': service_key,
                        'category': service_category,
                        'query': query_text,
                        'query_url': query_url,
                        'pattern': query_text,
                        'pattern_type': pattern_type,
                        'priority': 'custom',
                        'generated': datetime.now().isoformat()
                    }
                    queries.append(query)
                    
                    if len(queries) >= max_queries:
                        return queries[:max_queries]
        else:
            # Original behavior: use first pattern from each type
            patterns_to_use = list(self.problem_patterns.keys())
            queries_per_pattern = max(1, max_queries // len(patterns_to_use))
            
            for pattern_type in patterns_to_use[:max_queries]:
                pattern_list = self.problem_patterns[pattern_type]
                # Use first pattern from each type
                if pattern_list:
                    pattern = pattern_list[0]
                    query_text = pattern.replace('{service}', service_name)
                    query_url = f'https://old.reddit.com/search?q={query_text.replace(" ", "+").replace('"', "%22")}'
                    
                    query = {
                        'service': service_name,
                        'service_key': service_key,
                        'category': service_category,
                        'query': query_text,
                        'query_url': query_url,
                        'pattern': query_text,
                        'pattern_type': pattern_type,
                        'priority': 'custom',
                        'generated': datetime.now().isoformat()
                    }
                    queries.append(query)
        
        return queries[:max_queries]
    
    def generate_queries(self, max_queries: int = 100, category_filter: str = None, use_all_patterns: bool = False) -> List[Dict]:
        """
        Generate targeted search queries for discovered services
        Returns list of query dicts with: service, query_url, pattern_type, priority
        
        Args:
            max_queries: Maximum number of queries to generate
            category_filter: Filter services by category
            use_all_patterns: If True, use ALL patterns (20 total), not just first from each category
        """
        queries = []
        
        # Filter services by category if specified
        filtered_services = self.services
        if category_filter:
            filtered_services = {
                k: v for k, v in self.services.items() 
                if v['category'] == category_filter
            }
            if not filtered_services:
                logger.warning(f"No services found for category: {category_filter}")
                return []
        
        # Prioritize high-value services
        prioritized_services = []
        
        # First, add known priority services that were discovered
        for service_key, service_data in filtered_services.items():
            display_name = service_data['display_name'].lower()
            if any(priority in display_name for priority in self.priority_services):
                prioritized_services.append((service_data, 'ultra'))
        
        # Then add video/audio services (typically expensive)
        for service_key, service_data in filtered_services.items():
            if service_data['category'] in ['video', 'audio'] and service_data not in [s[0] for s in prioritized_services]:
                prioritized_services.append((service_data, 'critical'))
        
        # Then add image generation services
        for service_key, service_data in filtered_services.items():
            if service_data['category'] == 'image' and service_data not in [s[0] for s in prioritized_services]:
                prioritized_services.append((service_data, 'high'))
        
        # Add remaining services if needed
        if len(prioritized_services) == 0:
            # If no prioritized services, add all filtered services
            for service_key, service_data in filtered_services.items():
                prioritized_services.append((service_data, 'medium'))
        
        # If we still have room and want more services, add non-priority ones
        # This ensures we use all available services when max_queries allows
        if len(prioritized_services) < len(filtered_services):
            for service_key, service_data in filtered_services.items():
                if service_data not in [s[0] for s in prioritized_services]:
                    prioritized_services.append((service_data, 'normal'))
        
        # Calculate services to process
        if use_all_patterns:
            # When using all patterns, we generate 20 queries per service
            services_to_process = min(len(prioritized_services), max(1, max_queries // 20))
        else:
            # Original behavior: 5 queries per service (one from each category)
            services_to_process = min(len(prioritized_services), max(1, max_queries // 5))
        
        # Generate queries for prioritized services
        for service_data, priority in prioritized_services[:services_to_process]:
            service_name = service_data['display_name']
            
            # Generate queries for each pattern type
            for pattern_type, patterns in self.problem_patterns.items():
                # Use all patterns or just first one based on flag
                patterns_to_use = patterns if use_all_patterns else patterns[:1]
                
                for pattern in patterns_to_use:
                    query = pattern.replace('{service}', service_name)
                    query_url = f'https://old.reddit.com/search?q={query.replace(" ", "+").replace('"', "%22")}'
                    
                    queries.append({
                        'service': service_name,
                        'service_key': service_data['canonical_name'],
                        'category': service_data['category'],
                        'query': query,
                        'query_url': query_url,
                        'pattern_type': pattern_type,
                        'priority': priority,
                        'generated': datetime.now().isoformat()
                    })
                    
                    if len(queries) >= max_queries:
                        break
                if len(queries) >= max_queries:
                    break
            if len(queries) >= max_queries:
                break
        
        logger.info(f"Generated {len(queries)} targeted search queries (max_queries={max_queries})")
        
        # Group by service for summary
        by_service = {}
        for q in queries:
            service = q['service']
            if service not in by_service:
                by_service[service] = []
            by_service[service].append(q['pattern_type'])
        
        logger.info(f"Queries cover {len(by_service)} services")
        for service, patterns in list(by_service.items())[:5]:
            logger.info(f"  {service}: {', '.join(set(patterns))}")
        
        return queries
    
    def save_queries(self, queries: List[Dict], output_path: Path = Path("data/intermediate/targeted_searches.json")):
        """Save generated queries to JSON"""
        data = {
            'total_queries': len(queries),
            'generated': datetime.now().isoformat(),
            'queries': queries,
            'summary': self._generate_summary(queries)
        }
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(queries)} queries to {output_path}")
    
    def _generate_summary(self, queries: List[Dict]) -> Dict:
        """Generate summary statistics for queries"""
        summary = {
            'by_priority': {},
            'by_category': {},
            'by_pattern': {},
            'services_covered': set()
        }
        
        for q in queries:
            # By priority
            priority = q['priority']
            summary['by_priority'][priority] = summary['by_priority'].get(priority, 0) + 1
            
            # By category
            category = q['category']
            summary['by_category'][category] = summary['by_category'].get(category, 0) + 1
            
            # By pattern type
            pattern = q['pattern_type']
            summary['by_pattern'][pattern] = summary['by_pattern'].get(pattern, 0) + 1
            
            # Services
            summary['services_covered'].add(q['service'])
        
        summary['services_covered'] = list(summary['services_covered'])
        summary['total_services'] = len(summary['services_covered'])
        
        return summary


async def main():
    """Generate targeted searches for discovered services"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.core.logging import setup_logging
    
    setup_logging()
    
    # Generate queries
    generator = TargetedSearchGenerator()
    queries = generator.generate_queries(max_queries=100)
    
    # Save to file
    generator.save_queries(queries)
    
    # Print examples
    print("\nExample targeted searches generated:")
    for i, query in enumerate(queries[:10]):
        print(f"{i+1}. {query['service']} ({query['pattern_type']}): {query['query'][:80]}...")
        print(f"   Priority: {query['priority']}, Category: {query['category']}")
    
    print(f"\nTotal: {len(queries)} queries for {len(set(q['service'] for q in queries))} services")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())