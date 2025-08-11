#!/usr/bin/env python3
"""
Validate sources.yaml file for correctness and completeness.

This helps contributors ensure their additions are properly formatted.
"""

import sys
import yaml
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import urlparse

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


class SourceValidator:
    """Validates sources.yaml structure and content."""
    
    VALID_PRIORITIES = {"high", "medium", "low", "critical", "ultra"}
    VALID_SOURCE_TYPES = {"reddit", "forums", "github", "apis", "rss_feeds", "news_aggregators"}
    REQUIRED_FIELDS = {"name", "url", "priority"}
    OPTIONAL_FIELDS = {
        "models", "description", "requires_auth", "channels", 
        "categories", "keywords", "paths", "playlist", "type",
        "focus", "license", "update_frequency", "raw_url", "api",
        "endpoints", "rate_limit", "auth", "sdk", "example_endpoint",
        "specific_datasets", "invite", "size", "note", "format",
        "tags_to_track"
    }
    
    def __init__(self, sources_file: Path):
        self.sources_file = sources_file
        self.errors = []
        self.warnings = []
        self.stats = {
            "total_sources": 0,
            "by_type": {},
            "by_priority": {"high": 0, "medium": 0, "low": 0, "critical": 0, "ultra": 0},
            "duplicates": []
        }
    
    def validate(self) -> bool:
        """Run all validation checks."""
        print("🔍 Validating sources.yaml...\n")
        
        # Load file
        try:
            with open(self.sources_file) as f:
                sources_data = yaml.safe_load(f)
        except Exception as e:
            self.errors.append(f"Failed to load YAML: {e}")
            return False
        
        if not isinstance(sources_data, dict):
            self.errors.append("Root must be a dictionary")
            return False
        
        # Check each source type
        seen_urls = set()
        
        for source_type, source_config in sources_data.items():
            # Skip configuration sections
            if source_type in ["scraping_config", "content_filters"]:
                continue
                
            if source_type not in self.VALID_SOURCE_TYPES:
                self.warnings.append(f"Unknown source type: {source_type}")
            
            # Handle new structure where each source type has a sources list
            if isinstance(source_config, dict) and "sources" in source_config:
                sources = source_config["sources"]
                if not isinstance(sources, list):
                    self.errors.append(f"{source_type}: 'sources' must be a list")
                    continue
            elif isinstance(source_config, list):
                sources = source_config
            else:
                self.errors.append(f"{source_type}: Invalid structure")
                continue
            
            self.stats["by_type"][source_type] = len(sources)
            
            for idx, source in enumerate(sources):
                self._validate_source(source_type, idx, source, seen_urls)
        
        return len(self.errors) == 0
    
    def _validate_source(self, source_type: str, idx: int, source: Dict, seen_urls: Set[str]):
        """Validate individual source entry."""
        self.stats["total_sources"] += 1
        source_id = f"{source_type}[{idx}]"
        
        # Check required fields
        for field in self.REQUIRED_FIELDS:
            if field not in source:
                self.errors.append(f"{source_id}: Missing required field '{field}'")
        
        # Check field types
        if "name" in source and not isinstance(source["name"], str):
            self.errors.append(f"{source_id}: 'name' must be a string")
        
        if "url" in source:
            if not isinstance(source["url"], str):
                self.errors.append(f"{source_id}: 'url' must be a string")
            else:
                # Validate URL
                try:
                    result = urlparse(source["url"])
                    if not all([result.scheme, result.netloc]):
                        self.errors.append(f"{source_id}: Invalid URL format")
                except:
                    self.errors.append(f"{source_id}: Invalid URL")
                
                # Check duplicates
                if source["url"] in seen_urls:
                    self.stats["duplicates"].append(source["url"])
                    self.errors.append(f"{source_id}: Duplicate URL")
                seen_urls.add(source["url"])
        
        # Check priority
        if "priority" in source:
            if source["priority"] not in self.VALID_PRIORITIES:
                self.errors.append(
                    f"{source_id}: Invalid priority '{source['priority']}'. "
                    f"Must be one of: {self.VALID_PRIORITIES}"
                )
            else:
                self.stats["by_priority"][source["priority"]] += 1
        
        # Check models
        if "models" in source:
            if not isinstance(source["models"], list):
                self.errors.append(f"{source_id}: 'models' must be a list")
            elif not source["models"]:
                self.warnings.append(f"{source_id}: Empty models list")
        
        # Check unknown fields
        all_fields = self.REQUIRED_FIELDS | self.OPTIONAL_FIELDS
        unknown_fields = set(source.keys()) - all_fields
        if unknown_fields:
            self.warnings.append(
                f"{source_id}: Unknown fields: {unknown_fields}. "
                "These will be ignored."
            )
        
        # Type-specific validation
        self._validate_source_type_specific(source_type, source_id, source)
    
    def _validate_source_type_specific(self, source_type: str, source_id: str, source: Dict):
        """Validate source-type specific requirements."""
        if source_type == "discord" and source.get("requires_auth") != True:
            self.warnings.append(
                f"{source_id}: Discord sources usually require auth. "
                "Add 'requires_auth: true' if bot token is needed."
            )
        
        if source_type == "rss" and "type" in source:
            self.warnings.append(
                f"{source_id}: 'type' field not needed for RSS sources"
            )
        
        if source_type == "github" and "paths" in source:
            if not isinstance(source["paths"], list):
                self.errors.append(f"{source_id}: 'paths' must be a list")
    
    def print_report(self):
        """Print validation report."""
        print("\n" + "="*50)
        print("VALIDATION REPORT")
        print("="*50)
        
        # Statistics
        print("\n📊 Statistics:")
        print(f"   Total sources: {self.stats['total_sources']}")
        print("\n   By type:")
        for source_type, count in sorted(self.stats["by_type"].items()):
            print(f"      {source_type}: {count}")
        print("\n   By priority:")
        for priority, count in self.stats["by_priority"].items():
            print(f"      {priority}: {count}")
        
        # Results
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.stats["duplicates"]:
            print(f"\n🔁 Duplicate URLs found:")
            for url in self.stats["duplicates"]:
                print(f"   • {url}")
        
        # Summary
        print("\n" + "-"*50)
        if self.errors:
            print("❌ Validation FAILED - Please fix errors above")
        elif self.warnings:
            print("⚠️  Validation PASSED with warnings")
        else:
            print("✅ Validation PASSED - All good!")
    
    def suggest_improvements(self):
        """Suggest improvements for the sources."""
        print("\n💡 Suggestions:")
        
        # Check for missing popular sources
        popular_missing = self._check_missing_popular_sources()
        if popular_missing:
            print("\n   Popular sources you might want to add:")
            for source in popular_missing:
                print(f"      • {source}")
        
        # Check balance
        if self.stats["by_priority"]["high"] > self.stats["total_sources"] * 0.5:
            print("\n   ⚠️  Over 50% of sources are high priority. Consider balancing.")
        
        # Model coverage
        print("\n   Consider adding sources for these models:")
        print("      • Gemini (Google)")
        print("      • Mixtral")
        print("      • Phi-3")
    
    def _check_missing_popular_sources(self) -> List[str]:
        """Check for popular sources that might be missing."""
        popular_sources = [
            "r/LocalLLaMA",
            "r/singularity", 
            "r/MachineLearning",
            "r/artificial",
            "Hugging Face Forums",
            "OpenAI Community",
            "Anthropic Discord"
        ]
        
        # This is simplified - in reality we'd check against loaded sources
        return popular_sources[:3]  # Return top 3 as examples


def main():
    """Run source validation."""
    sources_file = Path("src/scrapers/sources.yaml")
    
    if not sources_file.exists():
        print(f"❌ File not found: {sources_file}")
        print("Make sure you're running from the repository root.")
        return 1
    
    validator = SourceValidator(sources_file)
    is_valid = validator.validate()
    validator.print_report()
    
    if is_valid:
        validator.suggest_improvements()
    
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())