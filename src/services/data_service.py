"""Data service for persisting and retrieving scraper data."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
import hashlib

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.logging import get_logger
from src.core.models import ScrapedPost
from src.models.scraper_models import (
    ScrapedPostDB,
    PracticeUpdateDB,
    ScraperRunDB,
    ModelPracticeDB,
    SourceStatusDB,
)

logger = get_logger(__name__)


class DataService:
    """Service for managing scraper data persistence."""
    
    def __init__(self, db: Session = None):
        self.db = db or next(get_db())
    
    async def save_scraped_posts(
        self,
        posts: List[ScrapedPost],
        scraper_run_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Save scraped posts to database."""
        stats = {
            "saved": 0,
            "duplicates": 0,
            "errors": 0,
        }
        
        for post in posts:
            try:
                # Check if post already exists
                existing = self.db.query(ScrapedPostDB).filter(
                    and_(
                        ScrapedPostDB.source_type == post.source_type.value,
                        ScrapedPostDB.post_id == post.post_id
                    )
                ).first()
                
                if existing:
                    # Update if newer or higher relevance
                    if post.relevance_score > existing.relevance_score:
                        existing.relevance_score = post.relevance_score
                        existing.extracted_practices = post.extracted_practices
                        existing.scraped_at = datetime.utcnow()
                        self.db.commit()
                        logger.debug(f"Updated existing post {post.post_id}")
                    stats["duplicates"] += 1
                else:
                    # Create new post
                    db_post = ScrapedPostDB(
                        source_type=post.source_type.value,
                        post_id=post.post_id,
                        url=post.url,
                        title=post.title,
                        content=post.content,
                        author=post.author,
                        created_at=post.created_at,
                        score=post.score,
                        relevance_score=post.relevance_score,
                        extracted_practices=post.extracted_practices,
                        metadata=post.metadata,
                    )
                    self.db.add(db_post)
                    self.db.commit()
                    stats["saved"] += 1
                    
            except Exception as e:
                logger.error(f"Error saving post {post.post_id}: {e}")
                stats["errors"] += 1
                self.db.rollback()
        
        return stats
    
    async def create_scraper_run(
        self,
        scraper_name: str,
        target: Optional[str] = None,
        limit: Optional[int] = None,
        time_filter: Optional[str] = None
    ) -> ScraperRunDB:
        """Create a new scraper run record."""
        run = ScraperRunDB(
            scraper_name=scraper_name,
            status="running",
            target=target,
            limit=limit,
            time_filter=time_filter,
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run
    
    async def update_scraper_run(
        self,
        run_id: int,
        status: str,
        posts_scraped: int = 0,
        practices_extracted: int = 0,
        models_updated: int = 0,
        error_message: Optional[str] = None
    ) -> None:
        """Update scraper run with results."""
        run = self.db.query(ScraperRunDB).filter(ScraperRunDB.id == run_id).first()
        if run:
            run.status = status
            run.completed_at = datetime.utcnow()
            run.posts_scraped = posts_scraped
            run.practices_extracted = practices_extracted
            run.models_updated = models_updated
            if error_message:
                run.error_message = error_message
                run.error_count += 1
            self.db.commit()
    
    async def save_practice_updates(
        self,
        updates: List[Dict[str, Any]],
        post_id: int,
        model_id: str,
        category: str
    ) -> int:
        """Save practice updates from a post."""
        saved_count = 0
        
        for update in updates:
            # Generate content hash for deduplication
            content_hash = self._generate_content_hash(update["content"])
            
            # Check if already exists
            existing = self.db.query(PracticeUpdateDB).filter(
                and_(
                    PracticeUpdateDB.model_id == model_id,
                    PracticeUpdateDB.content_hash == content_hash
                )
            ).first()
            
            if not existing:
                practice_update = PracticeUpdateDB(
                    post_id=post_id,
                    model_id=model_id,
                    category=category,
                    update_type=update["type"],
                    content=update["content"],
                    confidence=update.get("confidence", 0.5),
                    source_url=update.get("source_url"),
                    content_hash=content_hash,
                )
                self.db.add(practice_update)
                saved_count += 1
        
        self.db.commit()
        return saved_count
    
    async def get_unprocessed_posts(
        self,
        limit: int = 100,
        min_relevance: float = 0.5
    ) -> List[ScrapedPostDB]:
        """Get posts that haven't been processed yet."""
        posts = self.db.query(ScrapedPostDB).filter(
            and_(
                ScrapedPostDB.processed == False,
                ScrapedPostDB.relevance_score >= min_relevance
            )
        ).order_by(
            ScrapedPostDB.relevance_score.desc(),
            ScrapedPostDB.created_at.desc()
        ).limit(limit).all()
        
        return posts
    
    async def mark_post_processed(
        self,
        post_id: int,
        error: Optional[str] = None
    ) -> None:
        """Mark a post as processed."""
        post = self.db.query(ScrapedPostDB).filter(
            ScrapedPostDB.id == post_id
        ).first()
        
        if post:
            post.processed = True
            if error:
                post.processing_error = error
            self.db.commit()
    
    async def get_pending_practice_updates(
        self,
        model_id: str,
        limit: int = 100
    ) -> List[PracticeUpdateDB]:
        """Get pending practice updates for a model."""
        updates = self.db.query(PracticeUpdateDB).filter(
            and_(
                PracticeUpdateDB.model_id == model_id,
                PracticeUpdateDB.applied == False
            )
        ).order_by(
            PracticeUpdateDB.confidence.desc(),
            PracticeUpdateDB.created_at.desc()
        ).limit(limit).all()
        
        return updates
    
    async def mark_updates_applied(
        self,
        update_ids: List[int]
    ) -> None:
        """Mark practice updates as applied."""
        self.db.query(PracticeUpdateDB).filter(
            PracticeUpdateDB.id.in_(update_ids)
        ).update(
            {
                "applied": True,
                "applied_at": datetime.utcnow()
            },
            synchronize_session=False
        )
        self.db.commit()
    
    async def update_source_status(
        self,
        source_name: str,
        source_type: str,
        success: bool,
        posts_count: int = 0,
        practices_count: int = 0,
        avg_relevance: float = 0.0
    ) -> None:
        """Update source scraping status."""
        status = self.db.query(SourceStatusDB).filter(
            SourceStatusDB.source_name == source_name
        ).first()
        
        if not status:
            status = SourceStatusDB(
                source_name=source_name,
                source_type=source_type,
            )
            self.db.add(status)
        
        status.last_scraped = datetime.utcnow()
        
        if success:
            status.last_success = datetime.utcnow()
            status.consecutive_failures = 0
            status.total_posts += posts_count
            status.total_practices += practices_count
            
            # Update average relevance
            if posts_count > 0:
                old_total = status.total_posts - posts_count
                status.avg_relevance_score = (
                    (status.avg_relevance_score * old_total + avg_relevance * posts_count) /
                    status.total_posts
                )
        else:
            status.consecutive_failures += 1
            
            # Disable source after too many failures
            if status.consecutive_failures >= 5:
                status.is_active = False
                logger.warning(f"Disabling source {source_name} after 5 consecutive failures")
        
        self.db.commit()
    
    async def get_active_sources(
        self,
        min_interval_hours: int = 6
    ) -> List[SourceStatusDB]:
        """Get sources that are due for scraping."""
        cutoff_time = datetime.utcnow() - timedelta(hours=min_interval_hours)
        
        sources = self.db.query(SourceStatusDB).filter(
            and_(
                SourceStatusDB.is_active == True,
                or_(
                    SourceStatusDB.last_scraped == None,
                    SourceStatusDB.last_scraped < cutoff_time
                )
            )
        ).order_by(
            SourceStatusDB.priority.desc(),
            SourceStatusDB.last_scraped.asc()
        ).all()
        
        return sources
    
    async def update_model_practice_stats(
        self,
        model_id: str,
        category: str,
        updates: Dict[str, int]
    ) -> None:
        """Update model practice statistics."""
        practice = self.db.query(ModelPracticeDB).filter(
            ModelPracticeDB.model_id == model_id
        ).first()
        
        if not practice:
            practice = ModelPracticeDB(
                model_id=model_id,
                category=category,
            )
            self.db.add(practice)
        
        # Update counts
        practice.prompt_count += updates.get("prompts", 0)
        practice.parameter_count += updates.get("parameters", 0)
        practice.tip_count += updates.get("tips", 0)
        practice.pitfall_count += updates.get("pitfalls", 0)
        practice.last_updated = datetime.utcnow()
        
        # Update source count
        practice.source_count = self.db.query(
            func.count(func.distinct(PracticeUpdateDB.source_url))
        ).filter(
            PracticeUpdateDB.model_id == model_id
        ).scalar() or 0
        
        # Calculate confidence score
        practice.confidence_score = self._calculate_confidence_score(practice)
        
        self.db.commit()
    
    async def get_scraper_metrics(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """Get scraper performance metrics."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        # Get run statistics
        runs = self.db.query(
            ScraperRunDB.scraper_name,
            func.count(ScraperRunDB.id).label("runs"),
            func.sum(ScraperRunDB.posts_scraped).label("total_posts"),
            func.sum(ScraperRunDB.practices_extracted).label("total_practices"),
            func.avg(
                func.extract('epoch', ScraperRunDB.completed_at - ScraperRunDB.started_at)
            ).label("avg_duration"),
            func.sum(func.case([(ScraperRunDB.status == "failed", 1)], else_=0)).label("failures"),
        ).filter(
            ScraperRunDB.started_at >= cutoff
        ).group_by(
            ScraperRunDB.scraper_name
        ).all()
        
        # Get post statistics
        post_stats = self.db.query(
            ScrapedPostDB.source_type,
            func.count(ScrapedPostDB.id).label("count"),
            func.avg(ScrapedPostDB.relevance_score).label("avg_relevance"),
        ).filter(
            ScrapedPostDB.scraped_at >= cutoff
        ).group_by(
            ScrapedPostDB.source_type
        ).all()
        
        # Get update statistics
        update_stats = self.db.query(
            PracticeUpdateDB.model_id,
            func.count(PracticeUpdateDB.id).label("updates"),
            func.sum(func.case([(PracticeUpdateDB.applied == True, 1)], else_=0)).label("applied"),
        ).filter(
            PracticeUpdateDB.created_at >= cutoff
        ).group_by(
            PracticeUpdateDB.model_id
        ).all()
        
        return {
            "period_hours": hours,
            "scraper_runs": [
                {
                    "scraper": run.scraper_name,
                    "runs": run.runs,
                    "total_posts": run.total_posts or 0,
                    "total_practices": run.total_practices or 0,
                    "avg_duration_seconds": run.avg_duration or 0,
                    "failure_rate": (run.failures or 0) / run.runs if run.runs > 0 else 0,
                }
                for run in runs
            ],
            "post_stats": [
                {
                    "source": stat.source_type,
                    "count": stat.count,
                    "avg_relevance": stat.avg_relevance or 0,
                }
                for stat in post_stats
            ],
            "update_stats": [
                {
                    "model": stat.model_id,
                    "updates": stat.updates,
                    "applied": stat.applied or 0,
                    "pending": stat.updates - (stat.applied or 0),
                }
                for stat in update_stats
            ],
        }
    
    def _generate_content_hash(self, content: str) -> str:
        """Generate hash for content deduplication."""
        normalized = content.lower().strip()
        normalized = " ".join(normalized.split())
        return hashlib.sha256(normalized.encode()).hexdigest()
    
    def _calculate_confidence_score(self, practice: ModelPracticeDB) -> float:
        """Calculate confidence score for model practices."""
        score = 0.0
        
        # Based on content quantity
        if practice.prompt_count > 10:
            score += 0.2
        if practice.parameter_count > 5:
            score += 0.2
        if practice.tip_count > 20:
            score += 0.2
        if practice.pitfall_count > 10:
            score += 0.2
        
        # Based on source diversity
        if practice.source_count >= 5:
            score += 0.2
        elif practice.source_count >= 3:
            score += 0.1
        
        return min(score, 1.0)