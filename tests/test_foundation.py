"""
Tests for Phase 1 foundation components.

Tests database, configuration, and logging infrastructure.
"""

import pytest
from datetime import datetime
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import Database, get_db
from src.models import Trend, Post, Source, PostStatus, TrendCategory
from config.settings import get_settings


class TestConfiguration:
    """Test configuration system"""

    def test_settings_load(self):
        """Test that settings load correctly"""
        settings = get_settings()
        assert settings is not None
        assert settings.environment in ["development", "production"]

    def test_llm_config(self):
        """Test LLM configuration"""
        settings = get_settings()
        assert settings.llm.provider in ["ollama", "openai", "vllm", "lmstudio"]
        assert 0.0 <= settings.llm.temperature <= 2.0
        assert settings.llm.max_tokens >= 100

    def test_storage_config(self):
        """Test storage configuration"""
        settings = get_settings()
        assert settings.storage.database_path is not None
        assert isinstance(settings.storage.database_path, Path)


class TestDatabase:
    """Test database operations"""

    @pytest.fixture
    def db(self, tmp_path):
        """Create a temporary test database"""
        db_path = tmp_path / "test.db"
        return Database(db_path)

    def test_database_initialization(self, db):
        """Test that database initializes correctly"""
        stats = db.get_stats()
        assert stats["total_trends"] == 0
        assert stats["total_posts"] == 0

    def test_create_trend(self, db):
        """Test creating a trend"""
        trend = Trend(
            title="Test AI Breakthrough",
            description="A revolutionary AI model was released",
            source_url="https://example.com/article",
            source_name="Tech News",
            category=TrendCategory.AI,
            relevance_score=0.9,
        )

        trend_id = db.create_trend(trend)
        assert trend_id > 0

        # Retrieve the trend
        retrieved = db.get_trend(trend_id)
        assert retrieved is not None
        assert retrieved["title"] == "Test AI Breakthrough"
        assert retrieved["category"] == "ai"

    def test_create_post(self, db):
        """Test creating a post"""
        # First create a trend
        trend = Trend(
            title="Test Trend",
            description="Test description",
            source_url="https://example.com",
            source_name="Test Source",
        )
        trend_id = db.create_trend(trend)

        # Create a post
        post = Post(
            trend_id=trend_id,
            content="This is a test LinkedIn post about AI trends.",
            status=PostStatus.PENDING,
        )

        post_id = db.create_post(post)
        assert post_id > 0

        # Retrieve the post
        retrieved = db.get_post(post_id)
        assert retrieved is not None
        assert retrieved["content"] == post.content
        assert retrieved["status"] == "pending"

    def test_post_workflow(self, db):
        """Test complete post workflow: create -> approve -> publish"""
        # Create trend and post
        trend = Trend(
            title="Workflow Test",
            description="Testing workflow",
            source_url="https://example.com",
            source_name="Test",
        )
        trend_id = db.create_trend(trend)

        post = Post(trend_id=trend_id, content="Test post content")
        post_id = db.create_post(post)

        # Approve the post
        success = db.approve_post(post_id, notes="Looks good!")
        assert success is True

        retrieved = db.get_post(post_id)
        assert retrieved["status"] == "approved"
        assert retrieved["reviewer_notes"] == "Looks good!"

        # Publish the post
        success = db.mark_post_published(
            post_id, linkedin_url="https://linkedin.com/post/123"
        )
        assert success is True

        retrieved = db.get_post(post_id)
        assert retrieved["status"] == "published"
        assert retrieved["linkedin_post_url"] == "https://linkedin.com/post/123"

    def test_create_source(self, db):
        """Test creating source citations"""
        # Create trend and post
        trend = Trend(
            title="Source Test",
            description="Testing sources",
            source_url="https://example.com",
            source_name="Test",
        )
        trend_id = db.create_trend(trend)

        post = Post(trend_id=trend_id, content="Post with sources")
        post_id = db.create_post(post)

        # Add sources
        source = Source(
            post_id=post_id,
            source_name="TechCrunch",
            source_url="https://techcrunch.com/article",
            citation_text="According to TechCrunch...",
        )
        source_id = db.create_source(source)
        assert source_id > 0

        # Retrieve sources
        sources = db.get_sources_for_post(post_id)
        assert len(sources) == 1
        assert sources[0]["source_name"] == "TechCrunch"

    def test_get_posts_by_status(self, db):
        """Test filtering posts by status"""
        # Create trends and posts with different statuses
        trend = Trend(
            title="Status Test",
            description="Testing statuses",
            source_url="https://example.com",
            source_name="Test",
        )
        trend_id = db.create_trend(trend)

        # Create pending post
        post1 = Post(trend_id=trend_id, content="Pending post", status=PostStatus.PENDING)
        post1_id = db.create_post(post1)

        # Create and approve second post
        post2 = Post(trend_id=trend_id, content="Approved post", status=PostStatus.PENDING)
        post2_id = db.create_post(post2)
        db.approve_post(post2_id)

        # Get pending posts
        pending = db.get_posts(status=PostStatus.PENDING)
        assert len(pending) == 1
        assert pending[0]["id"] == post1_id

        # Get approved posts
        approved = db.get_posts(status=PostStatus.APPROVED)
        assert len(approved) == 1
        assert approved[0]["id"] == post2_id

    def test_database_stats(self, db):
        """Test database statistics"""
        # Create some data
        trend = Trend(
            title="Stats Test",
            description="Testing stats",
            source_url="https://example.com",
            source_name="Test",
        )
        trend_id = db.create_trend(trend)

        for i in range(5):
            post = Post(trend_id=trend_id, content=f"Post {i}")
            db.create_post(post)

        # Approve 2 posts
        posts = db.get_posts()
        db.approve_post(posts[0]["id"])
        db.approve_post(posts[1]["id"])

        # Publish 1 post
        db.mark_post_published(posts[0]["id"])

        # Check stats
        stats = db.get_stats()
        assert stats["total_trends"] == 1
        assert stats["total_posts"] == 5
        assert stats["pending_posts"] == 3
        assert stats["approved_posts"] == 1
        assert stats["published_posts"] == 1


class TestModels:
    """Test Pydantic models"""

    def test_trend_model(self):
        """Test Trend model validation"""
        trend = Trend(
            title="Test Trend",
            description="Test description",
            source_url="https://example.com",
            source_name="Test Source",
            category=TrendCategory.MACHINE_LEARNING,
            relevance_score=0.85,
        )

        assert trend.title == "Test Trend"
        assert trend.category == TrendCategory.MACHINE_LEARNING
        assert 0.0 <= trend.relevance_score <= 1.0

    def test_post_model(self):
        """Test Post model validation"""
        post = Post(
            trend_id=1,
            content="This is a test post",
            status=PostStatus.PENDING,
        )

        assert post.trend_id == 1
        assert post.status == PostStatus.PENDING
        assert post.content == "This is a test post"

    def test_post_status_enum(self):
        """Test PostStatus enum"""
        assert PostStatus.PENDING == "pending"
        assert PostStatus.APPROVED == "approved"
        assert PostStatus.REJECTED == "rejected"
        assert PostStatus.PUBLISHED == "published"

    def test_trend_category_enum(self):
        """Test TrendCategory enum"""
        assert TrendCategory.AI == "ai"
        assert TrendCategory.MACHINE_LEARNING == "machine_learning"
        assert TrendCategory.NLP == "nlp"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
