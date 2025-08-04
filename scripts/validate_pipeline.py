#!/usr/bin/env python3
"""
Validate the SOTA Practices pipeline configuration and setup.

This script checks:
1. Environment configuration
2. Directory structure
3. Database connectivity
4. Scraper credentials
5. Model file integrity
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings
from src.core.database import engine, SessionLocal
from src.core.logging import setup_logging, get_logger
from sqlalchemy import text

# Setup logging
setup_logging()
logger = get_logger(__name__)


class PipelineValidator:
    """Validates pipeline configuration and setup."""
    
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.successes = []
    
    def check_environment(self) -> bool:
        """Check environment configuration."""
        print("🔍 Checking environment configuration...")
        
        # Check required settings
        required = {
            "database_url": settings.database_url,
            "api_key": settings.api_key,
            "secret_key": settings.secret_key,
        }
        
        for name, value in required.items():
            if not value or value.startswith("dev_"):
                self.warnings.append(f"{name} is using default value - update for production")
            else:
                self.successes.append(f"{name} is configured")
        
        # Check optional credentials
        optional_creds = {
            "Reddit": (settings.reddit_client_id, settings.reddit_client_secret),
            "Discord": (settings.discord_bot_token,),
            "GitHub": (settings.github_token,),
            "OpenRouter": (settings.openrouter_api_key,) if settings.llm_provider == "openrouter" else (True,),
        }
        
        for service, creds in optional_creds.items():
            if all(creds):
                self.successes.append(f"{service} credentials configured")
            else:
                self.warnings.append(f"{service} credentials not configured - {service} scraper will be skipped")
        
        return True
    
    def check_directories(self) -> bool:
        """Check directory structure."""
        print("\n📁 Checking directory structure...")
        
        required_dirs = [
            settings.models_dir,
            settings.models_dir / "text",
            settings.models_dir / "image",
            settings.models_dir / "video",
            settings.models_dir / "audio",
            settings.models_dir / "multimodal",
            Path("logs"),
            Path("data"),
        ]
        
        for directory in required_dirs:
            if directory.exists():
                self.successes.append(f"Directory exists: {directory}")
            else:
                self.issues.append(f"Missing directory: {directory}")
        
        return len(self.issues) == 0
    
    def check_database(self) -> bool:
        """Check database connectivity and tables."""
        print("\n🗄️  Checking database...")
        
        try:
            # Test connection
            db = SessionLocal()
            db.execute(text("SELECT 1"))
            db.close()
            self.successes.append("Database connection successful")
            
            # Check tables
            from src.core.database import Base
            from sqlalchemy import inspect
            
            inspector = inspect(engine)
            existing_tables = inspector.get_table_names()
            
            expected_tables = [
                "scraped_posts",
                "practice_updates",
                "scraper_runs",
                "model_practices",
                "source_status",
            ]
            
            for table in expected_tables:
                if table in existing_tables:
                    self.successes.append(f"Table exists: {table}")
                else:
                    self.issues.append(f"Missing table: {table}")
            
            return True
            
        except Exception as e:
            self.issues.append(f"Database error: {str(e)}")
            return False
    
    def check_model_files(self) -> bool:
        """Check model file integrity."""
        print("\n📝 Checking model files...")
        
        models_found = 0
        
        for category_dir in settings.models_dir.iterdir():
            if not category_dir.is_dir():
                continue
            
            for model_dir in category_dir.iterdir():
                if not model_dir.is_dir():
                    continue
                
                models_found += 1
                model_id = f"{category_dir.name}/{model_dir.name}"
                
                # Check required files
                required_files = [
                    ("metadata.json", self._validate_json),
                    ("parameters.json", self._validate_json),
                    ("prompting.md", self._validate_text),
                    ("examples/prompts.json", self._validate_json),
                ]
                
                model_valid = True
                for filename, validator in required_files:
                    filepath = model_dir / filename
                    if filepath.exists():
                        if validator(filepath):
                            # File exists and is valid
                            pass
                        else:
                            self.warnings.append(f"{model_id}: Invalid {filename}")
                            model_valid = False
                    else:
                        self.warnings.append(f"{model_id}: Missing {filename}")
                        model_valid = False
                
                if model_valid:
                    self.successes.append(f"Model valid: {model_id}")
        
        if models_found == 0:
            self.warnings.append("No models found - run scrapers to populate")
        
        return True
    
    def _validate_json(self, filepath: Path) -> bool:
        """Validate JSON file."""
        try:
            with open(filepath) as f:
                json.load(f)
            return True
        except:
            return False
    
    def _validate_text(self, filepath: Path) -> bool:
        """Validate text file."""
        try:
            content = filepath.read_text()
            return len(content) > 0
        except:
            return False
    
    def check_redis(self) -> bool:
        """Check Redis connectivity."""
        print("\n🔴 Checking Redis...")
        
        try:
            import redis
            r = redis.from_url(settings.redis_url)
            r.ping()
            self.successes.append("Redis connection successful")
            return True
        except Exception as e:
            self.warnings.append(f"Redis not available: {str(e)} - caching disabled")
            return False
    
    def run_validation(self) -> int:
        """Run all validation checks."""
        print("🚀 Validating SOTA Practices Pipeline\n")
        
        # Run checks
        self.check_environment()
        self.check_directories()
        self.check_database()
        self.check_model_files()
        self.check_redis()
        
        # Print results
        print("\n" + "="*50)
        print("VALIDATION RESULTS")
        print("="*50)
        
        if self.successes:
            print("\n✅ SUCCESSES:")
            for success in self.successes:
                print(f"   ✓ {success}")
        
        if self.warnings:
            print("\n⚠️  WARNINGS:")
            for warning in self.warnings:
                print(f"   ! {warning}")
        
        if self.issues:
            print("\n❌ ISSUES:")
            for issue in self.issues:
                print(f"   ✗ {issue}")
        
        # Summary
        print("\n" + "-"*50)
        total_checks = len(self.successes) + len(self.warnings) + len(self.issues)
        print(f"Total checks: {total_checks}")
        print(f"Successes: {len(self.successes)}")
        print(f"Warnings: {len(self.warnings)}")
        print(f"Issues: {len(self.issues)}")
        
        if self.issues:
            print("\n❌ Pipeline validation FAILED")
            print("Please fix the issues above before running the pipeline.")
            return 1
        elif self.warnings:
            print("\n⚠️  Pipeline validation PASSED with warnings")
            print("The pipeline will work but some features may be limited.")
            return 0
        else:
            print("\n✅ Pipeline validation PASSED")
            print("All systems ready!")
            return 0


def main():
    """Run validation."""
    validator = PipelineValidator()
    return validator.run_validation()


if __name__ == "__main__":
    sys.exit(main())