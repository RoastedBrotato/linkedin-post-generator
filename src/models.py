"""
Data models for the LinkedIn Post Generator application.

These models define the structure of data stored in the database.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, HttpUrl


class PostStatus(str, Enum):
    """Status of a generated post"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"


class TrendCategory(str, Enum):
    """Categories for trends"""
    AI = "ai"
    MACHINE_LEARNING = "machine_learning"
    DEEP_LEARNING = "deep_learning"
    NLP = "nlp"
    COMPUTER_VISION = "computer_vision"
    ROBOTICS = "robotics"
    GENERAL_TECH = "general_tech"
    CLOUD = "cloud"
    DEVOPS = "devops"
    OTHER = "other"


class Trend(BaseModel):
    """Model for a technology/AI trend"""
    id: Optional[int] = None
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    source_url: str
    source_name: str = Field(..., max_length=100)
    category: TrendCategory = TrendCategory.OTHER
    relevance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    fetched_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class Post(BaseModel):
    """Model for a generated LinkedIn post"""
    id: Optional[int] = None
    trend_id: int
    content: str = Field(..., min_length=1, max_length=3000)
    status: PostStatus = PostStatus.PENDING
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    linkedin_post_url: Optional[str] = None
    reviewer_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class Source(BaseModel):
    """Model for source citations in posts"""
    id: Optional[int] = None
    post_id: int
    source_name: str = Field(..., max_length=200)
    source_url: str
    citation_text: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PublishingHistory(BaseModel):
    """Model for tracking publishing history and engagement"""
    id: Optional[int] = None
    post_id: int
    platform: str = Field(default="linkedin", max_length=50)
    published_at: datetime = Field(default_factory=datetime.utcnow)
    post_url: Optional[str] = None
    likes_count: int = Field(default=0, ge=0)
    comments_count: int = Field(default=0, ge=0)
    shares_count: int = Field(default=0, ge=0)
    impressions_count: int = Field(default=0, ge=0)
    last_metrics_update: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
