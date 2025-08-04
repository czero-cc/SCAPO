#!/usr/bin/env python3
"""
Validate model directory structure and files for correctness.

This helps contributors ensure their model additions follow the correct format.
"""

import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Set, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


class ModelValidator:
    """Validates model directory structure and content."""
    
    REQUIRED_FILES = {
        "prompting.md": "Prompting best practices",
        "parameters.json": "Recommended parameter settings",
        "metadata.json": "Model metadata and version info"
    }
    
    OPTIONAL_FILES = {
        "pitfalls.md": "Common mistakes and solutions",
        "examples/": "Directory with example prompts"
    }
    
    VALID_CATEGORIES = {
        "text": "Text generation models (GPT, Claude, Llama)",
        "image": "Image generation models (DALL-E, Midjourney, SD)",
        "video": "Video generation models (Runway, Pika)",
        "audio": "Audio generation models (Whisper, ElevenLabs)",
        "multimodal": "Multimodal models (GPT-4V, CLIP)"
    }
    
    def __init__(self, models_dir: Path = None):
        self.models_dir = models_dir or Path("models")
        self.errors = []
        self.warnings = []
        self.stats = {
            "total_models": 0,
            "by_category": {},
            "missing_files": {},
            "empty_files": [],
            "invalid_json": [],
            "outdated_models": []
        }
    
    def validate_all(self) -> bool:
        """Validate all models in the repository."""
        print("🔍 Validating all models...\n")
        
        if not self.models_dir.exists():
            self.errors.append(f"Models directory not found: {self.models_dir}")
            return False
        
        # Check each category
        for category_dir in self.models_dir.iterdir():
            if not category_dir.is_dir():
                continue
                
            category = category_dir.name
            if category not in self.VALID_CATEGORIES:
                self.warnings.append(f"Unknown category: {category}")
            
            self.stats["by_category"][category] = 0
            
            # Check each model in category
            for model_dir in category_dir.iterdir():
                if not model_dir.is_dir():
                    continue
                    
                self.stats["total_models"] += 1
                self.stats["by_category"][category] += 1
                self._validate_model(category, model_dir)
        
        return len(self.errors) == 0
    
    def validate_specific(self, model_path: str) -> bool:
        """Validate a specific model by path (e.g., 'text/gpt-4')."""
        print(f"🔍 Validating model: {model_path}\n")
        
        parts = model_path.split('/')
        if len(parts) != 2:
            self.errors.append(f"Invalid model path format. Use: category/model-name")
            return False
        
        category, model_name = parts
        model_dir = self.models_dir / category / model_name
        
        if not model_dir.exists():
            self.errors.append(f"Model directory not found: {model_dir}")
            return False
        
        self.stats["total_models"] = 1
        self.stats["by_category"][category] = 1
        self._validate_model(category, model_dir)
        
        return len(self.errors) == 0
    
    def _validate_model(self, category: str, model_dir: Path):
        """Validate individual model directory."""
        model_id = f"{category}/{model_dir.name}"
        logger.info(f"Validating {model_id}")
        
        # Check required files
        for file_name, description in self.REQUIRED_FILES.items():
            file_path = model_dir / file_name
            if not file_path.exists():
                self.errors.append(f"{model_id}: Missing required file '{file_name}' ({description})")
                if file_name not in self.stats["missing_files"]:
                    self.stats["missing_files"][file_name] = []
                self.stats["missing_files"][file_name].append(model_id)
            else:
                self._validate_file_content(model_id, file_path)
        
        # Check optional files
        for file_name, description in self.OPTIONAL_FILES.items():
            file_path = model_dir / file_name
            if file_name.endswith('/'):
                # Directory check
                if file_path.exists() and not file_path.is_dir():
                    self.errors.append(f"{model_id}: '{file_name}' should be a directory")
            else:
                # File check
                if file_path.exists():
                    self._validate_file_content(model_id, file_path)
        
        # Validate examples directory if present
        examples_dir = model_dir / "examples"
        if examples_dir.exists():
            self._validate_examples_dir(model_id, examples_dir)
        
        # Check for unexpected files
        expected_files = set(self.REQUIRED_FILES.keys()) | set(self.OPTIONAL_FILES.keys())
        expected_files.add("examples")  # Directory name without /
        
        for item in model_dir.iterdir():
            if item.name not in expected_files and not item.name.startswith('.'):
                self.warnings.append(f"{model_id}: Unexpected file '{item.name}'")
    
    def _validate_file_content(self, model_id: str, file_path: Path):
        """Validate specific file content."""
        # Check if file is empty
        if file_path.stat().st_size == 0:
            self.errors.append(f"{model_id}: File '{file_path.name}' is empty")
            self.stats["empty_files"].append(f"{model_id}/{file_path.name}")
            return
        
        # Validate JSON files
        if file_path.suffix == '.json':
            try:
                with open(file_path) as f:
                    data = json.load(f)
                
                # Specific validation based on file name
                if file_path.name == 'parameters.json':
                    self._validate_parameters_json(model_id, data)
                elif file_path.name == 'metadata.json':
                    self._validate_metadata_json(model_id, data)
                    
            except json.JSONDecodeError as e:
                self.errors.append(f"{model_id}: Invalid JSON in '{file_path.name}': {e}")
                self.stats["invalid_json"].append(f"{model_id}/{file_path.name}")
        
        # Validate Markdown files
        elif file_path.suffix == '.md':
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for minimal content
            if len(content.strip()) < 100:
                self.warnings.append(
                    f"{model_id}: '{file_path.name}' seems too short ({len(content)} chars). "
                    "Consider adding more detail."
                )
            
            # Check for required sections in prompting.md
            if file_path.name == 'prompting.md':
                self._validate_prompting_md(model_id, content)
    
    def _validate_parameters_json(self, model_id: str, data: Dict):
        """Validate parameters.json structure."""
        # Check for common parameter fields
        common_params = {
            "temperature", "max_tokens", "top_p", "frequency_penalty",
            "presence_penalty", "stop_sequences"
        }
        
        if not isinstance(data, dict):
            self.errors.append(f"{model_id}: parameters.json must be a dictionary")
            return
        
        # Check if at least some common parameters are present
        found_params = set(data.keys()) & common_params
        if not found_params and len(data) == 0:
            self.warnings.append(
                f"{model_id}: parameters.json is empty. Consider adding recommended parameters."
            )
        
        # Validate parameter types
        for param, value in data.items():
            if param == "temperature" and not isinstance(value, (int, float)):
                self.errors.append(f"{model_id}: temperature must be a number")
            elif param == "max_tokens" and not isinstance(value, int):
                self.errors.append(f"{model_id}: max_tokens must be an integer")
            elif param == "stop_sequences" and not isinstance(value, list):
                self.errors.append(f"{model_id}: stop_sequences must be a list")
    
    def _validate_metadata_json(self, model_id: str, data: Dict):
        """Validate metadata.json structure."""
        required_fields = {"version", "last_updated", "sources"}
        
        if not isinstance(data, dict):
            self.errors.append(f"{model_id}: metadata.json must be a dictionary")
            return
        
        # Check required fields
        missing = required_fields - set(data.keys())
        if missing:
            self.errors.append(
                f"{model_id}: metadata.json missing required fields: {missing}"
            )
        
        # Validate field types
        if "version" in data and not isinstance(data["version"], str):
            self.errors.append(f"{model_id}: version must be a string")
        
        if "last_updated" in data:
            try:
                # Try parsing the date
                date = datetime.fromisoformat(data["last_updated"].replace('Z', '+00:00'))
                # Check if outdated (>6 months)
                if (datetime.now() - date.replace(tzinfo=None)).days > 180:
                    self.stats["outdated_models"].append(model_id)
                    self.warnings.append(
                        f"{model_id}: Model practices last updated {data['last_updated']} "
                        "(>6 months ago)"
                    )
            except:
                self.errors.append(
                    f"{model_id}: last_updated must be ISO format (YYYY-MM-DD)"
                )
        
        if "sources" in data and not isinstance(data["sources"], list):
            self.errors.append(f"{model_id}: sources must be a list")
    
    def _validate_prompting_md(self, model_id: str, content: str):
        """Validate prompting.md content."""
        # Check for key sections
        expected_sections = [
            "## Overview",
            "## Basic Structure",
            "## Best Practices",
            "## Examples"
        ]
        
        missing_sections = []
        for section in expected_sections:
            if section not in content:
                missing_sections.append(section)
        
        if missing_sections:
            self.warnings.append(
                f"{model_id}: prompting.md missing sections: {', '.join(missing_sections)}"
            )
        
        # Check for code blocks
        if "```" not in content:
            self.warnings.append(
                f"{model_id}: prompting.md has no code examples. Consider adding prompt examples."
            )
    
    def _validate_examples_dir(self, model_id: str, examples_dir: Path):
        """Validate examples directory content."""
        example_files = list(examples_dir.glob("*.json"))
        
        if not example_files:
            self.warnings.append(
                f"{model_id}: examples/ directory is empty. Consider adding example prompts."
            )
            return
        
        # Validate each example file
        for example_file in example_files:
            try:
                with open(example_file) as f:
                    examples = json.load(f)
                
                if not isinstance(examples, list):
                    self.errors.append(
                        f"{model_id}: {example_file.name} must contain a list of examples"
                    )
                elif len(examples) == 0:
                    self.warnings.append(
                        f"{model_id}: {example_file.name} is empty"
                    )
                else:
                    # Validate example structure
                    for idx, example in enumerate(examples):
                        if not isinstance(example, dict):
                            self.errors.append(
                                f"{model_id}: Example {idx} in {example_file.name} must be a dict"
                            )
                        elif "prompt" not in example:
                            self.errors.append(
                                f"{model_id}: Example {idx} in {example_file.name} missing 'prompt'"
                            )
                            
            except json.JSONDecodeError as e:
                self.errors.append(
                    f"{model_id}: Invalid JSON in examples/{example_file.name}: {e}"
                )
    
    def print_report(self):
        """Print validation report."""
        print("\n" + "="*60)
        print("MODEL VALIDATION REPORT")
        print("="*60)
        
        # Statistics
        print("\n📊 Statistics:")
        print(f"   Total models validated: {self.stats['total_models']}")
        
        if self.stats["by_category"]:
            print("\n   Models by category:")
            for category, count in sorted(self.stats["by_category"].items()):
                desc = self.VALID_CATEGORIES.get(category, "Unknown")
                print(f"      {category}: {count} ({desc})")
        
        # File issues
        if self.stats["missing_files"]:
            print("\n📁 Missing files summary:")
            for file_name, models in self.stats["missing_files"].items():
                print(f"   {file_name}: {len(models)} models")
        
        # Results
        if self.errors:
            print(f"\n❌ Errors ({len(self.errors)}):")
            for error in self.errors:
                print(f"   • {error}")
        
        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"   • {warning}")
        
        if self.stats["outdated_models"]:
            print(f"\n⏰ Outdated models (need update):")
            for model in self.stats["outdated_models"]:
                print(f"   • {model}")
        
        # Summary
        print("\n" + "-"*60)
        if self.errors:
            print("❌ Validation FAILED - Please fix errors above")
        elif self.warnings:
            print("⚠️  Validation PASSED with warnings")
        else:
            print("✅ Validation PASSED - All models properly structured!")
    
    def suggest_fixes(self):
        """Suggest fixes for common issues."""
        if not self.errors and not self.warnings:
            return
            
        print("\n💡 Quick Fixes:")
        
        # Missing files
        if self.stats["missing_files"]:
            print("\n   For missing files, create them with:")
            if "prompting.md" in self.stats["missing_files"]:
                print("   • prompting.md: Add sections Overview, Basic Structure, Best Practices, Examples")
            if "parameters.json" in self.stats["missing_files"]:
                print("   • parameters.json: Add temperature, max_tokens, top_p recommendations")
            if "metadata.json" in self.stats["missing_files"]:
                print("   • metadata.json: Add version, last_updated, sources fields")
        
        # Empty files
        if self.stats["empty_files"]:
            print("\n   For empty files:")
            print("   • Copy from similar models as a starting point")
            print("   • Check CONTRIBUTING.md for templates")
        
        # Invalid JSON
        if self.stats["invalid_json"]:
            print("\n   For invalid JSON:")
            print("   • Validate with: python -m json.tool <file>")
            print("   • Common issues: trailing commas, unquoted keys")
        
        print("\n   Run with --fix to attempt automatic fixes (coming soon!)")


def main():
    """Run model validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate model documentation")
    parser.add_argument(
        "model",
        nargs="?",
        help="Specific model to validate (e.g., text/gpt-4)"
    )
    parser.add_argument(
        "--models-dir",
        type=Path,
        default=Path("models"),
        help="Models directory path"
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Attempt to fix common issues (not implemented yet)"
    )
    
    args = parser.parse_args()
    
    # Ensure we're in the right directory
    if not args.models_dir.exists():
        # Try from repository root
        root_models = Path.cwd() / "models"
        if root_models.exists():
            args.models_dir = root_models
        else:
            print(f"❌ Models directory not found: {args.models_dir}")
            print("Make sure you're running from the repository root.")
            return 1
    
    validator = ModelValidator(args.models_dir)
    
    # Run validation
    if args.model:
        is_valid = validator.validate_specific(args.model)
    else:
        is_valid = validator.validate_all()
    
    # Print report
    validator.print_report()
    
    if not is_valid or validator.warnings:
        validator.suggest_fixes()
    
    return 0 if is_valid else 1


if __name__ == "__main__":
    sys.exit(main())