from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class ModelCategory(str, Enum):
    """Categories of AI models."""
    
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    MULTIMODAL = "multimodal"


class SourceType(str, Enum):
    """Types of sources for best practices."""
    
    REDDIT = "reddit"
    DISCORD = "discord"
    FORUM = "forum"
    GITHUB = "github"
    TWITTER = "twitter"
    MANUAL = "manual"


class Parameter(BaseModel):
    """Model parameter recommendation."""
    
    name: str = Field(..., description="Parameter name")
    type: str = Field(..., description="Parameter type (float, int, str, etc.)")
    default: Any = Field(..., description="Default value")
    recommended: Any = Field(..., description="Recommended value")
    range: Optional[Dict[str, Any]] = Field(None, description="Valid range (min/max)")
    description: str = Field(..., description="Parameter description")
    impact: str = Field(..., description="Impact on output")


class PromptExample(BaseModel):
    """Example prompt with explanation."""
    
    prompt: str = Field(..., description="Example prompt text")
    explanation: str = Field(..., description="Why this prompt works")
    output_preview: Optional[str] = Field(None, description="Expected output preview")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")


class Pitfall(BaseModel):
    """Common mistake or pitfall."""
    
    title: str = Field(..., description="Pitfall title")
    description: str = Field(..., description="Detailed description")
    example: Optional[str] = Field(None, description="Example of the mistake")
    solution: str = Field(..., description="How to avoid or fix")
    severity: str = Field(..., description="Impact severity (low/medium/high)")


class Source(BaseModel):
    """Source of information."""
    
    type: SourceType = Field(..., description="Source type")
    url: Optional[str] = Field(None, description="Source URL")
    author: Optional[str] = Field(None, description="Author name")
    date: datetime = Field(..., description="Date of information")
    credibility_score: float = Field(..., ge=0, le=1, description="Credibility score")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class ModelBestPractices(BaseModel):
    """Complete best practices for a model."""
    
    model_config = {"protected_namespaces": ()}
    
    model_id: str = Field(..., description="Unique model identifier")
    model_name: str = Field(..., description="Human-readable model name")
    category: ModelCategory = Field(..., description="Model category")
    version: str = Field(..., description="Model version")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last update time")
    
    # Prompting
    prompt_structure: str = Field(..., description="Recommended prompt structure")
    prompt_examples: List[PromptExample] = Field(
        default_factory=list, description="Example prompts"
    )
    prompt_tips: List[str] = Field(
        default_factory=list, description="Quick prompting tips"
    )
    
    # Parameters
    parameters: List[Parameter] = Field(
        default_factory=list, description="Parameter recommendations"
    )
    
    # Pitfalls
    pitfalls: List[Pitfall] = Field(
        default_factory=list, description="Common pitfalls"
    )
    
    # Metadata
    sources: List[Source] = Field(
        default_factory=list, description="Information sources"
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for search"
    )
    related_models: List[str] = Field(
        default_factory=list, description="Related model IDs"
    )
    
    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: str) -> str:
        """Ensure model_id follows naming convention."""
        if not v.replace("-", "").replace("_", "").replace(".", "").isalnum():
            raise ValueError("model_id must be alphanumeric with -_.allowed")
        return v.lower()


class ScrapedPost(BaseModel):
    """A scraped post from a source."""
    
    source_type: SourceType = Field(..., description="Source type")
    post_id: str = Field(..., description="Unique post ID from source")
    url: str = Field(..., description="Post URL")
    title: Optional[str] = Field(None, description="Post title")
    content: str = Field(..., description="Post content")
    author: str = Field(..., description="Author name")
    created_at: datetime = Field(..., description="Post creation time")
    score: int = Field(default=0, description="Post score/upvotes")
    relevance_score: float = Field(..., ge=0, le=1, description="Relevance to AI practices")
    extracted_practices: Dict[str, Any] = Field(
        default_factory=dict, description="Extracted best practices"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class ModelMetadata(BaseModel):
    """Metadata for a model's best practices."""
    
    model_config = {"protected_namespaces": ()}
    
    model_id: str = Field(..., description="Model ID")
    version: str = Field(..., description="Practices version")
    last_updated: datetime = Field(..., description="Last update time")
    update_frequency_hours: int = Field(default=24, description="Update frequency")
    sources_count: int = Field(default=0, description="Number of sources")
    confidence_score: float = Field(..., ge=0, le=1, description="Overall confidence")
    change_log: List[Dict[str, Any]] = Field(
        default_factory=list, description="Change history"
    )