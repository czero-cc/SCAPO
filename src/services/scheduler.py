"""Scheduler service for automated scraping."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import signal
import sys

from celery import Celery
from celery.schedules import crontab

from src.core.config import settings
from src.core.logging import get_logger
from src.services.scraper_service import ScraperService
from src.services.data_service import DataService
from src.core.database import SessionLocal

logger = get_logger(__name__)

# Initialize Celery
celery_app = Celery(
    "sota_practices",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit at 55 minutes
)


# Celery Beat Schedule
celery_app.conf.beat_schedule = {
    # High priority sources - every 6 hours
    "scrape-high-priority": {
        "task": "src.services.scheduler.scrape_high_priority",
        "schedule": crontab(hour="*/6"),
    },
    # Medium priority sources - twice daily
    "scrape-medium-priority": {
        "task": "src.services.scheduler.scrape_medium_priority",
        "schedule": crontab(hour="6,18"),
    },
    # Low priority sources - once daily
    "scrape-low-priority": {
        "task": "src.services.scheduler.scrape_low_priority",
        "schedule": crontab(hour="3"),
    },
    # Process unprocessed posts - every 2 hours
    "process-pending-posts": {
        "task": "src.services.scheduler.process_pending_posts",
        "schedule": crontab(minute="0", hour="*/2"),
    },
    # Update model practices - daily at 5 AM
    "update-model-practices": {
        "task": "src.services.scheduler.update_model_practices",
        "schedule": crontab(hour="5", minute="0"),
    },
    # Clean old data - weekly
    "clean-old-data": {
        "task": "src.services.scheduler.clean_old_data",
        "schedule": crontab(day_of_week="0", hour="4"),
    },
}


@celery_app.task(bind=True, max_retries=3)
def scrape_high_priority(self):
    """Scrape high priority sources."""
    return asyncio.run(_scrape_by_priority("high", limit=200))


@celery_app.task(bind=True, max_retries=3)
def scrape_medium_priority(self):
    """Scrape medium priority sources."""
    return asyncio.run(_scrape_by_priority("medium", limit=100))


@celery_app.task(bind=True, max_retries=3)
def scrape_low_priority(self):
    """Scrape low priority sources."""
    return asyncio.run(_scrape_by_priority("low", limit=50))


@celery_app.task(bind=True, max_retries=2)
def process_pending_posts(self):
    """Process posts that haven't been analyzed yet."""
    return asyncio.run(_process_pending_posts())


@celery_app.task(bind=True)
def update_model_practices(self):
    """Update model practice files from database."""
    return asyncio.run(_update_model_practices())


@celery_app.task(bind=True)
def clean_old_data(self):
    """Clean old scraped data."""
    return asyncio.run(_clean_old_data())


async def _scrape_by_priority(priority: str, limit: int) -> Dict[str, Any]:
    """Scrape sources by priority level."""
    logger.info(f"Starting {priority} priority scraping")
    
    db = SessionLocal()
    data_service = DataService(db)
    scraper_service = ScraperService()
    
    results = {
        "priority": priority,
        "started_at": datetime.utcnow().isoformat(),
        "sources_scraped": 0,
        "total_posts": 0,
        "total_practices": 0,
        "errors": [],
    }
    
    try:
        # Get active sources for this priority
        sources = await data_service.get_active_sources()
        priority_sources = [s for s in sources if s.priority == priority]
        
        logger.info(f"Found {len(priority_sources)} {priority} priority sources to scrape")
        
        for source in priority_sources:
            try:
                # Map source to scraper
                scraper_name = _map_source_to_scraper(source.source_name, source.source_type)
                
                if not scraper_name:
                    logger.warning(f"No scraper mapped for source {source.source_name}")
                    continue
                
                # Create scraper run
                run = await data_service.create_scraper_run(
                    scraper_name=scraper_name,
                    limit=limit,
                    time_filter="week" if priority == "high" else "month"
                )
                
                # Run scraper
                result = await scraper_service.run_scraper(
                    source=scraper_name,
                    target=source.source_name if scraper_name == "reddit" else None,
                    limit=limit,
                )
                
                if result["status"] == "success":
                    results["sources_scraped"] += 1
                    results["total_posts"] += result.get("posts_scraped", 0)
                    results["total_practices"] += result.get("practices_extracted", 0)
                    
                    # Update source status
                    await data_service.update_source_status(
                        source_name=source.source_name,
                        source_type=source.source_type,
                        success=True,
                        posts_count=result.get("posts_scraped", 0),
                        practices_count=result.get("practices_extracted", 0),
                    )
                    
                    # Update scraper run
                    await data_service.update_scraper_run(
                        run_id=run.id,
                        status="success",
                        posts_scraped=result.get("posts_scraped", 0),
                        practices_extracted=result.get("practices_extracted", 0),
                        models_updated=result.get("practice_update", {}).get("models_updated", 0),
                    )
                else:
                    error_msg = result.get("error", "Unknown error")
                    results["errors"].append(f"{source.source_name}: {error_msg}")
                    
                    # Update source status
                    await data_service.update_source_status(
                        source_name=source.source_name,
                        source_type=source.source_type,
                        success=False,
                    )
                    
                    # Update scraper run
                    await data_service.update_scraper_run(
                        run_id=run.id,
                        status="failed",
                        error_message=error_msg,
                    )
                
            except Exception as e:
                logger.error(f"Error scraping source {source.source_name}: {e}")
                results["errors"].append(f"{source.source_name}: {str(e)}")
        
        results["completed_at"] = datetime.utcnow().isoformat()
        logger.info(
            f"Completed {priority} priority scraping",
            sources=results["sources_scraped"],
            posts=results["total_posts"],
            practices=results["total_practices"],
        )
        
    except Exception as e:
        logger.error(f"Error in priority scraping: {e}")
        results["errors"].append(f"General error: {str(e)}")
    finally:
        db.close()
    
    return results


async def _process_pending_posts() -> Dict[str, Any]:
    """Process unprocessed posts through LLM."""
    logger.info("Starting pending post processing")
    
    db = SessionLocal()
    data_service = DataService(db)
    
    results = {
        "processed": 0,
        "errors": 0,
        "practices_extracted": 0,
    }
    
    try:
        # Get unprocessed posts
        posts = await data_service.get_unprocessed_posts(limit=50)
        logger.info(f"Found {len(posts)} unprocessed posts")
        
        if not posts:
            return results
        
        # Process through LLM if enabled
        if settings.llm_processing_enabled:
            from src.services.llm_processor import process_scraped_content
            
            for post in posts:
                try:
                    # Process content
                    content = {
                        "post": f"Title: {post.title}\n\nContent: {post.content}"
                    }
                    
                    processed = await process_scraped_content(
                        content,
                        provider=settings.llm_provider,
                        max_chars=settings.llm_max_chars,
                    )
                    
                    # Save extracted practices
                    for practices in processed.values():
                        for practice in practices:
                            # Convert to update format
                            update = {
                                "type": practice.practice_type,
                                "content": practice.content,
                                "confidence": practice.confidence,
                                "source_url": post.url,
                            }
                            
                            # Determine model
                            models = practice.applicable_models or ["general"]
                            for model in models:
                                await data_service.save_practice_updates(
                                    updates=[update],
                                    post_id=post.id,
                                    model_id=model,
                                    category="text",  # Simplified
                                )
                            
                            results["practices_extracted"] += 1
                    
                    # Mark as processed
                    await data_service.mark_post_processed(post.id)
                    results["processed"] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing post {post.id}: {e}")
                    await data_service.mark_post_processed(post.id, error=str(e))
                    results["errors"] += 1
        else:
            # Just mark as processed if LLM is disabled
            for post in posts:
                await data_service.mark_post_processed(post.id)
                results["processed"] += 1
        
        logger.info(
            f"Completed post processing",
            processed=results["processed"],
            practices=results["practices_extracted"],
        )
        
    except Exception as e:
        logger.error(f"Error in post processing: {e}")
    finally:
        db.close()
    
    return results


async def _update_model_practices() -> Dict[str, Any]:
    """Update model practice files from database."""
    logger.info("Starting model practice updates")
    
    db = SessionLocal()
    data_service = DataService(db)
    
    results = {
        "models_updated": 0,
        "practices_applied": 0,
        "errors": [],
    }
    
    try:
        # Get models with pending updates
        from sqlalchemy import select, func
        from src.models.scraper_models import PracticeUpdateDB
        
        models_with_updates = db.query(
            PracticeUpdateDB.model_id,
            func.count(PracticeUpdateDB.id).label("update_count")
        ).filter(
            PracticeUpdateDB.applied == False
        ).group_by(
            PracticeUpdateDB.model_id
        ).all()
        
        logger.info(f"Found {len(models_with_updates)} models with pending updates")
        
        from src.services.practice_updater import PracticeUpdater
        updater = PracticeUpdater()
        
        for model_id, update_count in models_with_updates:
            try:
                # Get pending updates
                updates = await data_service.get_pending_practice_updates(model_id)
                
                if not updates:
                    continue
                
                # Group by type
                grouped_updates = {}
                for update in updates:
                    if update.update_type not in grouped_updates:
                        grouped_updates[update.update_type] = []
                    grouped_updates[update.update_type].append(update)
                
                # Apply updates
                applied_ids = []
                for update_type, type_updates in grouped_updates.items():
                    # Apply top N updates per type
                    for update in type_updates[:10]:  # Limit per batch
                        applied_ids.append(update.id)
                        results["practices_applied"] += 1
                
                # Mark as applied
                if applied_ids:
                    await data_service.mark_updates_applied(applied_ids)
                    results["models_updated"] += 1
                    
                    # Update model statistics
                    await data_service.update_model_practice_stats(
                        model_id=model_id,
                        category="text",  # Simplified
                        updates={
                            update_type: len(updates)
                            for update_type, updates in grouped_updates.items()
                        }
                    )
                
            except Exception as e:
                logger.error(f"Error updating model {model_id}: {e}")
                results["errors"].append(f"{model_id}: {str(e)}")
        
        logger.info(
            f"Completed model practice updates",
            models=results["models_updated"],
            practices=results["practices_applied"],
        )
        
    except Exception as e:
        logger.error(f"Error in model updates: {e}")
        results["errors"].append(f"General error: {str(e)}")
    finally:
        db.close()
    
    return results


async def _clean_old_data() -> Dict[str, Any]:
    """Clean old scraped data."""
    logger.info("Starting data cleanup")
    
    db = SessionLocal()
    
    results = {
        "posts_deleted": 0,
        "runs_deleted": 0,
    }
    
    try:
        # Delete old low-relevance posts (> 90 days)
        cutoff = datetime.utcnow() - timedelta(days=90)
        
        from src.models.scraper_models import ScrapedPostDB, ScraperRunDB
        
        old_posts = db.query(ScrapedPostDB).filter(
            ScrapedPostDB.created_at < cutoff,
            ScrapedPostDB.relevance_score < 0.3,
            ScrapedPostDB.processed == True,
        ).delete(synchronize_session=False)
        
        results["posts_deleted"] = old_posts
        
        # Delete old scraper runs (> 30 days)
        run_cutoff = datetime.utcnow() - timedelta(days=30)
        old_runs = db.query(ScraperRunDB).filter(
            ScraperRunDB.started_at < run_cutoff
        ).delete(synchronize_session=False)
        
        results["runs_deleted"] = old_runs
        
        db.commit()
        
        logger.info(
            f"Completed data cleanup",
            posts=results["posts_deleted"],
            runs=results["runs_deleted"],
        )
        
    except Exception as e:
        logger.error(f"Error in data cleanup: {e}")
        db.rollback()
    finally:
        db.close()
    
    return results


def _map_source_to_scraper(source_name: str, source_type: str) -> Optional[str]:
    """Map source name to scraper name."""
    source_lower = source_name.lower()
    
    # Reddit sources
    if source_type == "reddit" or any(r in source_lower for r in ["r/", "reddit"]):
        return "reddit"
    
    # GitHub sources
    if source_type == "github" or "github" in source_lower:
        return "github"
    
    # Forum sources
    if source_type == "forum" or any(f in source_lower for f in ["forum", "community", "discuss"]):
        # Use enhanced scraper for known JS-heavy forums
        if any(js in source_lower for js in ["openai", "huggingface"]):
            return "forum_enhanced"
        return "forum"
    
    # HackerNews
    if "hacker" in source_lower or "hn" in source_lower:
        return "hackernews"
    
    # RSS feeds
    if source_type == "rss" or any(r in source_lower for r in ["rss", "feed", "blog"]):
        return "rss"
    
    # Discord
    if source_type == "discord" or "discord" in source_lower:
        return "discord"
    
    return None


class SchedulerManager:
    """Manager for the scheduler service."""
    
    def __init__(self):
        self.worker_process = None
        self.beat_process = None
        
    def start(self):
        """Start Celery worker and beat scheduler."""
        logger.info("Starting scheduler services")
        
        # Start worker
        import subprocess
        
        self.worker_process = subprocess.Popen([
            sys.executable, "-m", "celery",
            "-A", "src.services.scheduler", "worker",
            "--loglevel=info",
            "--concurrency=2",
        ])
        
        # Start beat
        self.beat_process = subprocess.Popen([
            sys.executable, "-m", "celery",
            "-A", "src.services.scheduler", "beat",
            "--loglevel=info",
        ])
        
        logger.info("Scheduler services started")
        
    def stop(self):
        """Stop scheduler services."""
        logger.info("Stopping scheduler services")
        
        if self.worker_process:
            self.worker_process.terminate()
            self.worker_process.wait()
            
        if self.beat_process:
            self.beat_process.terminate()
            self.beat_process.wait()
            
        logger.info("Scheduler services stopped")


# For running as standalone script
if __name__ == "__main__":
    manager = SchedulerManager()
    
    def signal_handler(signum, frame):
        logger.info("Received shutdown signal")
        manager.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        manager.start()
        # Keep running
        signal.pause()
    except KeyboardInterrupt:
        manager.stop()