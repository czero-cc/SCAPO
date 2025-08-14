"""
Model Entry Generator - Creates structured documentation in the models folder
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
import logging
from src.services.update_manager import UpdateManager

logger = logging.getLogger(__name__)


class ModelEntryGenerator:
    """Generates structured model documentation from extracted tips"""
    
    def __init__(self, models_root: Path = Path("models")):
        self.models_root = models_root
        self.ensure_directory_structure()
        self.update_manager = UpdateManager(models_root)
    
    def ensure_directory_structure(self):
        """Ensure the models root directory exists"""
        # Only create the root models directory
        # Category directories will be created as needed when models are saved
        self.models_root.mkdir(parents=True, exist_ok=True)
    
    def categorize_service(self, service_name: str) -> str:
        """Get category from services.json using ServiceAliasManager"""
        from src.services.service_alias_manager import ServiceAliasManager
        
        # Use alias manager for better matching
        alias_manager = ServiceAliasManager()
        service_match = alias_manager.match_service(service_name)
        
        if service_match:
            return service_match.get('category', 'general')
        
        # Default to general if not found
        return 'general'
    
    def normalize_service_name(self, service_name: str) -> str:
        """Normalize service name for file/folder naming"""
        # Remove special characters and spaces
        normalized = service_name.lower()
        normalized = normalized.replace(' ', '-')
        normalized = ''.join(c for c in normalized if c.isalnum() or c == '-')
        return normalized
    
    def generate_prompting_md(self, service_name: str, tips: List[str], settings: List[str]) -> str:
        """Generate prompting.md content - focused on HOW to use the service effectively"""
        content = f"# {service_name} Prompting Guide\n\n"
        content += f"*Last updated: {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        
        # Don't filter tips - include all extracted tips like the current pipeline does
        # The LLM already filtered for relevance during extraction
        if tips:
            content += "## Tips & Techniques\n\n"
            for tip in tips:
                content += f"- {tip}\n"
            content += "\n"
        
        if settings:
            content += "## Recommended Settings\n\n"
            for setting in settings:
                content += f"- {setting}\n"
            content += "\n"
        
        # Only add if we have actual content
        if not (tips or settings):
            content += "*No specific prompting tips available yet. Check back for updates.*\n\n"
        
        content += "## Sources\n\n"
        content += "- Reddit community discussions\n"
        content += "- User-reported experiences\n"
        
        return content
    
    def generate_parameters_json(self, service_name: str, settings: List[str], cost_info: List[str]) -> Dict:
        """Generate parameters.json content"""
        parameters = {
            "service": service_name,
            "last_updated": datetime.now().isoformat(),
            "recommended_settings": {},
            "cost_optimization": {},
            "sources": ["Reddit community", "User reports"]
        }
        
        # Parse settings into structured format
        for setting in settings:
            if "break" in setting.lower() and "tag" in setting.lower():
                parameters["recommended_settings"]["speech_pauses"] = {
                    "description": setting,
                    "value": "<break time=\"1.5s\" />"
                }
            elif "speech rate" in setting.lower() or "slower" in setting.lower():
                parameters["recommended_settings"]["speech_rate"] = {
                    "description": setting,
                    "value": "slower_preferred"
                }
            else:
                # Generic setting
                key = f"setting_{len(parameters['recommended_settings'])}"
                parameters["recommended_settings"][key] = {
                    "description": setting
                }
        
        # Add cost information
        for cost in cost_info:
            if "$" in cost:
                parameters["cost_optimization"]["pricing"] = cost
            elif "unlimited" in cost.lower():
                parameters["cost_optimization"]["unlimited_option"] = cost
            else:
                parameters["cost_optimization"][f"tip_{len(parameters['cost_optimization'])}"] = cost
        
        return parameters
    
    def generate_pitfalls_md(self, service_name: str, problems: List[str], cost_info: List[str]) -> str:
        """Generate pitfalls.md content - focused on what to AVOID"""
        content = f"# {service_name} - Common Pitfalls & Issues\n\n"
        content += f"*Last updated: {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        
        # Categorize problems
        technical_issues = []
        policy_issues = []
        cost_issues = []
        
        for problem in problems:
            problem_lower = problem.lower()
            if any(keyword in problem_lower for keyword in ['api', 'stutter', 'error', 'bug', 'crash', 'slow']):
                technical_issues.append(problem)
            elif any(keyword in problem_lower for keyword in ['policy', 'account', 'ban', 'disable', 'misuse', 'trial']):
                policy_issues.append(problem)
            elif any(keyword in problem_lower for keyword in ['credit', 'cost', 'expensive', 'limit']):
                cost_issues.append(problem)
        
        # Add cost info to cost issues if relevant
        for info in cost_info:
            if 'limit' in info.lower() or 'character' in info.lower():
                cost_issues.append(info)
        
        if technical_issues:
            content += "## Technical Issues\n\n"
            for issue in technical_issues:
                content += f"### ⚠️ {issue}\n"
                # Add specific solutions
                if "stutter" in issue.lower():
                    content += "**Fix**: Keep speech rate adjustments under 5%. Record slower initially rather than slowing down in post.\n\n"
                elif "api key" in issue.lower():
                    content += "**Fix**: Store API keys in environment variables or use a secrets manager.\n\n"
                else:
                    content += "\n"
        
        if policy_issues:
            content += "## Policy & Account Issues\n\n"
            for issue in policy_issues:
                content += f"### ⚠️ {issue}\n"
                if "trial" in issue.lower() or "account" in issue.lower():
                    content += "**Note**: Be aware of terms of service regarding account creation.\n\n"
                else:
                    content += "\n"
        
        if cost_issues:
            content += "## Cost & Limits\n\n"
            for issue in cost_issues:
                content += f"### 💰 {issue}\n\n"
        
        if not (technical_issues or policy_issues or cost_issues):
            content += "*No major issues reported yet. This may indicate limited community data.*\n\n"
        
        return content
    
    def generate_cost_optimization_md(self, service_name: str, cost_info: List[str], tips: List[str]) -> str:
        """Generate cost_optimization.md - focused on saving money"""
        content = f"# {service_name} - Cost Optimization Guide\n\n"
        content += f"*Last updated: {datetime.now().strftime('%Y-%m-%d')}*\n\n"
        
        # Include all cost info without filtering - LLM already filtered
        if cost_info:
            content += "## Cost & Pricing Information\n\n"
            for info in cost_info:
                content += f"- {info}\n"
            content += "\n"
        
        # Include money-saving tips from the tips list
        money_tips = [tip for tip in tips if any(
            keyword in tip.lower() for keyword in 
            ['save', 'cheap', 'free', 'cost', 'price', 'credit', 'limit', 'tier', 'plan']
        )]
        
        if money_tips:
            content += "## Money-Saving Tips\n\n"
            for tip in money_tips:
                content += f"- {tip}\n"
            content += "\n"
        
        if not (cost_info or money_tips):
            content += "*No cost optimization information available yet.*\n\n"
        
        return content
    
    def generate_metadata_json(self, service_name: str, extraction_data: Dict) -> Dict:
        """Generate metadata.json"""
        return {
            "service": service_name,
            "category": self.categorize_service(service_name),
            "last_updated": datetime.now().isoformat(),
            "extraction_timestamp": extraction_data.get('timestamp', datetime.now().isoformat()),
            "data_sources": ["Reddit API", "Community discussions"],
            "posts_analyzed": extraction_data.get('batch_size', 0),
            "confidence": "medium",  # Could be calculated based on number of corroborating posts
            "version": "1.0.0"
        }
    
    def create_model_entry(self, extraction: Dict) -> bool:
        """Create a complete model entry from extraction data"""
        try:
            service_name = extraction.get('service', 'unknown')
            if service_name == 'unknown':
                logger.warning("Skipping entry with unknown service name")
                return False
            
            # Get data
            tips = extraction.get('tips', [])
            problems = extraction.get('problems', [])
            settings = extraction.get('settings', [])
            cost_info = extraction.get('cost_info', [])
            
            # Skip if no useful data
            if not any([tips, problems, settings, cost_info]):
                logger.info(f"No useful data for {service_name}, skipping")
                return False
            
            # Determine category and create directory
            category = self.categorize_service(service_name)
            normalized_name = self.normalize_service_name(service_name)
            model_dir = self.models_root / category / normalized_name
            model_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Creating model entry for {service_name} in {category}/{normalized_name}")
            
            # Generate and save files
            files_created = []
            
            # prompting.md - focus on usage tips and settings
            if tips or settings:
                prompting_content = self.generate_prompting_md(service_name, tips, settings)
                with open(model_dir / "prompting.md", 'w', encoding='utf-8') as f:
                    f.write(prompting_content)
                files_created.append("prompting.md")
            
            # parameters.json
            if settings or cost_info:
                parameters = self.generate_parameters_json(service_name, settings, cost_info)
                with open(model_dir / "parameters.json", 'w', encoding='utf-8') as f:
                    json.dump(parameters, f, indent=2)
                files_created.append("parameters.json")
            
            # pitfalls.md - include problems and relevant cost issues
            if problems or any('limit' in c.lower() for c in cost_info):
                pitfalls_content = self.generate_pitfalls_md(service_name, problems, cost_info)
                with open(model_dir / "pitfalls.md", 'w', encoding='utf-8') as f:
                    f.write(pitfalls_content)
                files_created.append("pitfalls.md")
            
            # cost_optimization.md - money-saving tips
            if cost_info or any('free' in t.lower() or 'unlimited' in t.lower() for t in tips):
                cost_content = self.generate_cost_optimization_md(service_name, cost_info, tips)
                with open(model_dir / "cost_optimization.md", 'w', encoding='utf-8') as f:
                    f.write(cost_content)
                files_created.append("cost_optimization.md")
            
            # metadata.json
            metadata = self.generate_metadata_json(service_name, extraction)
            with open(model_dir / "metadata.json", 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2)
            files_created.append("metadata.json")
            
            logger.info(f"Created {len(files_created)} files for {service_name}: {', '.join(files_created)}")
            
            # Record the update
            self.update_manager.record_update(
                service_name, 
                {
                    'tips': tips,
                    'problems': problems,
                    'cost_info': cost_info,
                    'settings': settings
                },
                {'files_created': len(files_created)}
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create model entry for {extraction.get('service', 'unknown')}: {e}")
            return False
    
    def process_extraction_results(self, results_file: Path) -> int:
        """Process extraction results and generate model entries"""
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            results = data.get('results', [])
            entries_created = 0
            
            # Merge results by service
            merged_by_service = {}
            for result in results:
                service = result.get('service')
                if not service:
                    continue
                
                if service not in merged_by_service:
                    merged_by_service[service] = {
                        'service': service,
                        'tips': [],
                        'problems': [],
                        'settings': [],
                        'cost_info': [],
                        'batch_size': 0,
                        'timestamp': result.get('timestamp')
                    }
                
                # Merge data
                merged_by_service[service]['tips'].extend(result.get('tips', []))
                merged_by_service[service]['problems'].extend(result.get('problems', []))
                merged_by_service[service]['settings'].extend(result.get('settings', []))
                merged_by_service[service]['cost_info'].extend(result.get('cost_info', []))
                merged_by_service[service]['batch_size'] += result.get('batch_size', 0)
            
            # Deduplicate and normalize
            for service, data in merged_by_service.items():
                # Simple string lists can use set
                data['tips'] = list(set(data['tips']))
                data['problems'] = list(set(data['problems']))
                data['cost_info'] = list(set(data['cost_info']))
                
                # Settings might contain dicts from local LLMs, need special handling
                normalized_settings = []
                seen_settings = set()
                for setting in data['settings']:
                    if isinstance(setting, dict):
                        # Convert dict to string representation
                        for key, value in setting.items():
                            setting_str = f"{key} = {value}"
                            if setting_str not in seen_settings:
                                normalized_settings.append(setting_str)
                                seen_settings.add(setting_str)
                    elif isinstance(setting, str):
                        if setting not in seen_settings:
                            normalized_settings.append(setting)
                            seen_settings.add(setting)
                data['settings'] = normalized_settings
            
            # Create entries
            for service, extraction in merged_by_service.items():
                if self.create_model_entry(extraction):
                    entries_created += 1
            
            logger.info(f"Created {entries_created} model entries from {len(results)} extraction results")
            return entries_created
            
        except Exception as e:
            logger.error(f"Failed to process extraction results: {e}")
            return 0


def test_generator():
    """Test the model entry generator"""
    generator = ModelEntryGenerator()
    
    # Test with sample extraction
    sample_extraction = {
        "service": "Eleven Labs",
        "problems": ["Slowing down speech more than 5% causes tiny stutters"],
        "tips": [
            "Use <break time=\"1.5s\" /> tag to create pauses in speech",
            "Use slower speech rates as it's easier to speed up in post-processing"
        ],
        "cost_info": ["$10 a month or $96 a year"],
        "settings": ["Keep speech rate slower rather than faster"],
        "batch_size": 5,
        "timestamp": datetime.now().isoformat()
    }
    
    # Create entry
    success = generator.create_model_entry(sample_extraction)
    print(f"Created entry: {success}")
    
    # Check created files
    model_dir = Path("models/audio/eleven-labs")
    if model_dir.exists():
        print(f"\nCreated files in {model_dir}:")
        for file in model_dir.iterdir():
            print(f"  - {file.name}")


if __name__ == "__main__":
    test_generator()