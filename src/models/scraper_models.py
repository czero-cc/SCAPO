"""Database models for scraper data persistence."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON,
    ForeignKey, Boolean, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship

from src.core.database import Base


class ScrapedPostDB(Base):
    """Database model for scraped posts."""
    
    __tablename__ = "scraped_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    post_id = Column(String(255), nullable=False)  # External ID
    url = Column(String(1000), nullable=False)
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    score = Column(Integer, default=0)
    relevance_score = Column(Float, default=0.0)
    
    # JSON fields for flexibility
    extracted_practices = Column(JSON, default={})
    metadata = Column(JSON, default={})
    
    # Processing status
    processed = Column(Boolean, default=False, index=True)
    processing_error = Column(Text, nullable=True)
    
    # Relationships
    practice_updates = relationship("PracticeUpdateDB", back_populates="post")
    
    # Unique constraint on source_type + post_id
    __table_args__ = (
        UniqueConstraint('source_type', 'post_id', name='_source_post_uc'),
        Index('idx_relevance_date', 'relevance_score', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ScrapedPost({self.source_type}:{self.post_id} - {self.title[:50]})>"


class PracticeUpdateDB(Base):
    """Database model for practice updates."""
    
    __tablename__ = "practice_updates"
    
    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("scraped_posts.id"), nullable=False)
    model_id = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    update_type = Column(String(50), nullable=False)  # prompt, parameter, tip, pitfall
    
    # Update details
    content = Column(Text, nullable=False)
    confidence = Column(Float, default=0.5)
    source_url = Column(String(1000))
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    applied = Column(Boolean, default=False, index=True)
    applied_at = Column(DateTime, nullable=True)
    
    # Deduplication hash
    content_hash = Column(String(64), nullable=False, index=True)
    
    # Relationships
    post = relationship("ScrapedPostDB", back_populates="practice_updates")
    
    __table_args__ = (
        Index('idx_model_update', 'model_id', 'update_type', 'applied'),
    )
    
    def __repr__(self):
        return f"<PracticeUpdate({self.model_id}:{self.update_type})>"


class ScraperRunDB(Base):
    """Database model for scraper runs."""
    
    __tablename__ = "scraper_runs"
    
    id = Column(Integer, primary_key=True, index=True)
    scraper_name = Column(String(50), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False)  # running, success, failed
    
    # Metrics
    posts_scraped = Column(Integer, default=0)
    practices_extracted = Column(Integer, default=0)
    models_updated = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    error_count = Column(Integer, default=0)
    
    # Configuration used
    target = Column(String(255), nullable=True)
    limit = Column(Integer, nullable=True)
    time_filter = Column(String(50), nullable=True)
    
    __table_args__ = (
        Index('idx_scraper_status_date', 'scraper_name', 'status', 'started_at'),
    )
    
    def __repr__(self):
        return f"<ScraperRun({self.scraper_name} at {self.started_at})>"


class ModelPracticeDB(Base):
    """Database model for consolidated model practices."""
    
    __tablename__ = "model_practices"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(100), nullable=False, unique=True, index=True)
    category = Column(String(50), nullable=False)
    
    # Version tracking
    version = Column(String(20), default="1.0.0")
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Practice counts
    prompt_count = Column(Integer, default=0)
    parameter_count = Column(Integer, default=0)
    tip_count = Column(Integer, default=0)
    pitfall_count = Column(Integer, default=0)
    
    # Quality metrics
    confidence_score = Column(Float, default=0.0)
    source_count = Column(Integer, default=0)
    
    # File paths (relative to models_dir)
    prompting_file = Column(String(500), nullable=True)
    parameters_file = Column(String(500), nullable=True)
    pitfalls_file = Column(String(500), nullable=True)
    
    # Metadata
    metadata = Column(JSON, default={})
    
    def __repr__(self):
        return f"<ModelPractice({self.model_id})>"


class SourceStatusDB(Base):
    """Database model for tracking source status."""
    
    __tablename__ = "source_status"
    
    id = Column(Integer, primary_key=True, index=True)
    source_name = Column(String(100), nullable=False, unique=True, index=True)
    source_type = Column(String(50), nullable=False)
    
    # Status tracking
    last_scraped = Column(DateTime, nullable=True)
    last_success = Column(DateTime, nullable=True)
    consecutive_failures = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Metrics
    total_posts = Column(Integer, default=0)
    total_practices = Column(Integer, default=0)
    avg_relevance_score = Column(Float, default=0.0)
    
    # Configuration
    priority = Column(String(20), default="medium")
    scrape_interval_hours = Column(Integer, default=24)
    
    def __repr__(self):
        return f"<SourceStatus({self.source_name})>"