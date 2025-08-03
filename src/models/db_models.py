from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from src.core.database import Base


class ModelPractice(Base):
    """Database model for AI model best practices."""
    
    __tablename__ = "model_practices"
    
    id = Column(Integer, primary_key=True, index=True)
    model_id = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    model_name = Column(String(200), nullable=False)
    version = Column(String(20), nullable=False, default="1.0.0")
    
    # Content
    prompt_structure = Column(Text, nullable=True)
    prompt_tips = Column(JSON, nullable=True, default=list)
    parameters = Column(JSON, nullable=True, default=list)
    pitfalls = Column(JSON, nullable=True, default=list)
    
    # Metadata
    tags = Column(JSON, nullable=True, default=list)
    related_models = Column(JSON, nullable=True, default=list)
    confidence_score = Column(Float, nullable=False, default=0.5)
    sources_count = Column(Integer, nullable=False, default=0)
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scraped_at = Column(DateTime, nullable=True)
    
    # Relationships
    examples = relationship("PromptExample", back_populates="model_practice", cascade="all, delete-orphan")
    sources = relationship("PracticeSource", back_populates="model_practice", cascade="all, delete-orphan")
    scrape_history = relationship("ScrapeHistory", back_populates="model_practice", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint("model_id", "category", name="uq_model_category"),
        Index("idx_model_category", "model_id", "category"),
        Index("idx_updated_at", "updated_at"),
    )


class PromptExample(Base):
    """Database model for prompt examples."""
    
    __tablename__ = "prompt_examples"
    
    id = Column(Integer, primary_key=True, index=True)
    model_practice_id = Column(Integer, ForeignKey("model_practices.id"), nullable=False)
    
    prompt = Column(Text, nullable=False)
    explanation = Column(Text, nullable=False)
    output_preview = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True, default=list)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    model_practice = relationship("ModelPractice", back_populates="examples")


class PracticeSource(Base):
    """Database model for practice sources."""
    
    __tablename__ = "practice_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    model_practice_id = Column(Integer, ForeignKey("model_practices.id"), nullable=False)
    
    source_type = Column(String(50), nullable=False)
    url = Column(String(500), nullable=True)
    author = Column(String(200), nullable=True)
    date = Column(DateTime, nullable=False)
    credibility_score = Column(Float, nullable=False, default=0.5)
    metadata = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    model_practice = relationship("ModelPractice", back_populates="sources")


class ScrapedPost(Base):
    """Database model for scraped posts."""
    
    __tablename__ = "scraped_posts"
    
    id = Column(Integer, primary_key=True, index=True)
    source_type = Column(String(50), nullable=False, index=True)
    post_id = Column(String(100), nullable=False, index=True)
    url = Column(String(500), nullable=False)
    
    title = Column(String(500), nullable=True)
    content = Column(Text, nullable=False)
    author = Column(String(200), nullable=False)
    score = Column(Integer, nullable=False, default=0)
    
    relevance_score = Column(Float, nullable=False, default=0.0)
    extracted_practices = Column(JSON, nullable=True, default=dict)
    metadata = Column(JSON, nullable=True, default=dict)
    
    created_at = Column(DateTime, nullable=False)
    scraped_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed = Column(Boolean, nullable=False, default=False, index=True)
    
    __table_args__ = (
        UniqueConstraint("source_type", "post_id", name="uq_source_post"),
        Index("idx_source_relevance", "source_type", "relevance_score"),
        Index("idx_scraped_processed", "scraped_at", "processed"),
    )


class ScrapeHistory(Base):
    """Database model for scraping history."""
    
    __tablename__ = "scrape_history"
    
    id = Column(Integer, primary_key=True, index=True)
    model_practice_id = Column(Integer, ForeignKey("model_practices.id"), nullable=True)
    
    source_type = Column(String(50), nullable=False, index=True)
    target = Column(String(200), nullable=True)
    status = Column(String(50), nullable=False)
    
    posts_scraped = Column(Integer, nullable=False, default=0)
    practices_extracted = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    
    started_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Relationships
    model_practice = relationship("ModelPractice", back_populates="scrape_history")
    
    __table_args__ = (
        Index("idx_scrape_source_date", "source_type", "started_at"),
    )


class UserQuery(Base):
    """Database model for tracking user queries."""
    
    __tablename__ = "user_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    query_type = Column(String(50), nullable=False, index=True)
    model_id = Column(String(100), nullable=True, index=True)
    category = Column(String(50), nullable=True)
    query_params = Column(JSON, nullable=True, default=dict)
    
    response_time_ms = Column(Float, nullable=True)
    status_code = Column(Integer, nullable=False)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_query_model_date", "model_id", "created_at"),
    )