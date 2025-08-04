#!/usr/bin/env python3
"""
Initialize the SOTA Practices pipeline.

This script:
1. Creates necessary directories
2. Initializes the database
3. Creates example model structures
4. Validates configuration
"""

import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import settings
from src.core.database import engine, Base
from src.core.logging import setup_logging, get_logger
from src.services.data_service import DataService
from src.core.database import SessionLocal

# Setup logging
setup_logging()
logger = get_logger(__name__)


def create_directories() -> List[Path]:
    """Create necessary directories."""
    directories = [
        settings.models_dir,
        settings.models_dir / "text",
        settings.models_dir / "image",
        settings.models_dir / "video",
        settings.models_dir / "audio",
        settings.models_dir / "multimodal",
        Path("logs"),
        Path("data"),
    ]
    
    created = []
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
            logger.info(f"Created directory: {directory}")
    
    return created


def validate_configuration() -> Tuple[bool, List[str]]:
    """Validate configuration and return status with warnings."""
    warnings = []
    
    # Check optional credentials
    if not settings.reddit_client_id:
        warnings.append("Reddit credentials not configured - Reddit scraper will be skipped")
    
    if not settings.discord_bot_token:
        warnings.append("Discord token not configured - Discord scraper will be skipped")
    
    if not settings.github_token:
        warnings.append("GitHub token not configured - API rate limits will apply")
    
    # Check LLM configuration
    if settings.llm_processing_enabled:
        if settings.llm_provider == "openrouter" and not settings.openrouter_api_key:
            warnings.append("OpenRouter API key not configured - LLM processing disabled")
        elif settings.llm_provider == "local":
            warnings.append(f"Using local LLM at {settings.local_llm_url}")
    
    # Check database
    if settings.database_url.startswith("sqlite"):
        warnings.append("Using SQLite database - consider PostgreSQL for production")
    
    return True, warnings


def initialize_database():
    """Initialize database tables."""
    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Initialize source status for known sources
        db = SessionLocal()
        data_service = DataService(db)
        
        # Add known sources (simplified for now)
        sources = [
            ("r/LocalLLaMA", "reddit", "high"),
            ("r/StableDiffusion", "reddit", "high"),
            ("OpenAI Forum", "forum", "medium"),
            ("Hugging Face Hub", "github", "high"),
        ]
        
        # We'll skip actual source initialization for now
        # as it requires the full async setup
        
        db.close()
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def create_example_models():
    """Create example model structures."""
    examples = [
        ("text", "gpt-4", "GPT-4"),
        ("image", "stable-diffusion", "Stable Diffusion"),
        ("video", "wan2.2", "Wan2.2"),
    ]
    
    for category, model_id, display_name in examples:
        model_dir = settings.models_dir / category / model_id
        if model_dir.exists():
            logger.info(f"Model {category}/{model_id} already exists")
            continue
        
        model_dir.mkdir(parents=True, exist_ok=True)
        
        # Create basic structure
        (model_dir / "examples").mkdir(exist_ok=True)
        
        # Create placeholder files
        files = {
            "prompting.md": f"# {display_name} Prompting Guide\n\nThis guide will be populated by the scraping pipeline.",
            "parameters.json": "[]",
            "pitfalls.md": f"# Common Pitfalls for {display_name}\n\nThis will be populated by the scraping pipeline.",
            "examples/prompts.json": "[]",
            "metadata.json": f'{{\n  "model_id": "{model_id}",\n  "display_name": "{display_name}",\n  "version": "0.0.1",\n  "confidence_score": 0.1,\n  "sources_count": 0\n}}',
        }
        
        for filename, content in files.items():
            filepath = model_dir / filename
            filepath.parent.mkdir(exist_ok=True)
            filepath.write_text(content)
        
        logger.info(f"Created example model: {category}/{model_id}")


def main():
    """Run initialization."""
    print("🚀 Initializing SOTA Practices Pipeline\n")
    
    # Create directories
    print("📁 Creating directories...")
    created_dirs = create_directories()
    if created_dirs:
        print(f"   Created {len(created_dirs)} directories")
    else:
        print("   All directories already exist")
    
    # Validate configuration
    print("\n🔍 Validating configuration...")
    is_valid, warnings = validate_configuration()
    if warnings:
        print("   ⚠️  Warnings:")
        for warning in warnings:
            print(f"      - {warning}")
    else:
        print("   ✅ Configuration valid")
    
    # Initialize database
    print("\n🗄️  Initializing database...")
    try:
        initialize_database()
        print("   ✅ Database initialized")
    except Exception as e:
        print(f"   ❌ Database initialization failed: {e}")
        return 1
    
    # Create example models
    print("\n📝 Creating example models...")
    create_example_models()
    print("   ✅ Example models created")
    
    print("\n✨ Initialization complete!")
    print("\nNext steps:")
    print("1. Configure credentials in .env file for scrapers you want to use")
    print("2. Run scrapers: python -m src.scrapers.run reddit --limit 10")
    print("3. Start API server: uvicorn src.api.server:app --reload")
    print("4. Or use MCP server: python mcp/server.py")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())