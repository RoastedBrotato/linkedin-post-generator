"""
Data models for the LinkedIn Post Generator application.

These models define the structure of data stored in the database.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
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
    image_path: Optional[str] = None
    image_url: Optional[str] = None
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


class QueryRun(BaseModel):
    """Model for tracking a query run from the web UI"""
    id: Optional[int] = None
    keywords_raw: str = Field(default="", max_length=2000)
    phrases: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="queued", max_length=20)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class QueryRunTrend(BaseModel):
    """Model for a trend included in a query run"""
    id: Optional[int] = None
    query_run_id: int
    trend_id: int
    match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_terms: List[str] = Field(default_factory=list)
    match_fields: Dict[str, str] = Field(default_factory=dict)
    rank: int = Field(default=0, ge=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EngagementRunStatus(str, Enum):
    """Status of an engagement run"""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class EngagementTargetStatus(str, Enum):
    """Status of a scraped LinkedIn post target"""
    PENDING = "pending"
    COMMENTED = "commented"
    SKIPPED = "skipped"


class EngagementCommentStatus(str, Enum):
    """Status of a generated comment"""
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    POSTED = "posted"


class EngagementRun(BaseModel):
    """Model for engagement run tracking"""
    id: Optional[int] = None
    status: EngagementRunStatus = EngagementRunStatus.QUEUED
    sources: Dict[str, Any] = Field(default_factory=dict)
    options: Dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class EngagementTarget(BaseModel):
    """Model for a LinkedIn post selected for engagement"""
    id: Optional[int] = None
    run_id: int
    post_url: str
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    post_text: Optional[str] = None
    source: Optional[str] = None
    status: EngagementTargetStatus = EngagementTargetStatus.PENDING
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class EngagementComment(BaseModel):
    """Model for a generated engagement comment"""
    id: Optional[int] = None
    target_id: int
    content: str = Field(..., min_length=1, max_length=400)
    status: EngagementCommentStatus = EngagementCommentStatus.DRAFT
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    posted_at: Optional[datetime] = None
    linkedin_comment_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
