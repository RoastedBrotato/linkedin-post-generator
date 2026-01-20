"""
Database management for the LinkedIn Post Generator.

Handles SQLite database initialization, connections, and CRUD operations.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any

from src.models import Trend, Post, Source, PublishingHistory, PostStatus, TrendCategory


# Database file location
DB_PATH = Path(__file__).parent.parent / "data" / "database.db"


# SQL Schema
SCHEMA_SQL = """
-- Trends table
CREATE TABLE IF NOT EXISTS trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_name TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'other',
    relevance_score REAL NOT NULL DEFAULT 0.0,
    fetched_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trend_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    generated_at TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP,
    published_at TIMESTAMP,
    linkedin_post_url TEXT,
    reviewer_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trend_id) REFERENCES trends(id) ON DELETE CASCADE
);

-- Sources table (for citations in posts)
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    citation_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- Publishing history table
CREATE TABLE IF NOT EXISTS publishing_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    platform TEXT NOT NULL DEFAULT 'linkedin',
    published_at TIMESTAMP NOT NULL,
    post_url TEXT,
    likes_count INTEGER DEFAULT 0,
    comments_count INTEGER DEFAULT 0,
    shares_count INTEGER DEFAULT 0,
    impressions_count INTEGER DEFAULT 0,
    last_metrics_update TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- Indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_trends_category ON trends(category);
CREATE INDEX IF NOT EXISTS idx_trends_fetched_at ON trends(fetched_at);
CREATE INDEX IF NOT EXISTS idx_trends_relevance_score ON trends(relevance_score);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_trend_id ON posts(trend_id);
CREATE INDEX IF NOT EXISTS idx_posts_generated_at ON posts(generated_at);
CREATE INDEX IF NOT EXISTS idx_sources_post_id ON sources(post_id);
CREATE INDEX IF NOT EXISTS idx_publishing_history_post_id ON publishing_history(post_id);
"""


class Database:
    """Database manager for the application"""

    def __init__(self, db_path: Path = DB_PATH):
        """Initialize database connection"""
        self.db_path = db_path
        self._ensure_db_directory()
        self.init_db()

    def _ensure_db_directory(self):
        """Ensure the data directory exists"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def init_db(self):
        """Initialize database with schema"""
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)

    # ==================== TRENDS CRUD ====================

    def create_trend(self, trend: Trend) -> int:
        """Create a new trend record"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO trends (
                    title, description, source_url, source_name, category,
                    relevance_score, fetched_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trend.title,
                    trend.description,
                    trend.source_url,
                    trend.source_name,
                    trend.category,
                    trend.relevance_score,
                    trend.fetched_at,
                    trend.created_at,
                    trend.updated_at,
                ),
            )
            return cursor.lastrowid

    def get_trend(self, trend_id: int) -> Optional[Dict[str, Any]]:
        """Get a trend by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM trends WHERE id = ?", (trend_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_trends(
        self,
        category: Optional[TrendCategory] = None,
        min_relevance: float = 0.0,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get trends with optional filtering"""
        query = "SELECT * FROM trends WHERE relevance_score >= ?"
        params = [min_relevance]

        if category:
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY fetched_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_trend(self, trend_id: int, **kwargs) -> bool:
        """Update a trend record"""
        kwargs["updated_at"] = datetime.utcnow()

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [trend_id]

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE trends SET {set_clause} WHERE id = ?", values
            )
            return cursor.rowcount > 0

    # ==================== POSTS CRUD ====================

    def create_post(self, post: Post) -> int:
        """Create a new post record"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO posts (
                    trend_id, content, status, generated_at, reviewed_at,
                    published_at, linkedin_post_url, reviewer_notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    post.trend_id,
                    post.content,
                    post.status,
                    post.generated_at,
                    post.reviewed_at,
                    post.published_at,
                    post.linkedin_post_url,
                    post.reviewer_notes,
                    post.created_at,
                    post.updated_at,
                ),
            )
            return cursor.lastrowid

    def get_post(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Get a post by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_posts(
        self,
        status: Optional[PostStatus] = None,
        trend_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get posts with optional filtering"""
        query = "SELECT * FROM posts WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)

        if trend_id:
            query += " AND trend_id = ?"
            params.append(trend_id)

        query += " ORDER BY generated_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        with self.get_connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def update_post(self, post_id: int, **kwargs) -> bool:
        """Update a post record"""
        kwargs["updated_at"] = datetime.utcnow()

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [post_id]

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE posts SET {set_clause} WHERE id = ?", values
            )
            return cursor.rowcount > 0

    def approve_post(self, post_id: int, notes: Optional[str] = None) -> bool:
        """Approve a post for publishing"""
        return self.update_post(
            post_id,
            status=PostStatus.APPROVED,
            reviewed_at=datetime.utcnow(),
            reviewer_notes=notes,
        )

    def reject_post(self, post_id: int, notes: Optional[str] = None) -> bool:
        """Reject a post"""
        return self.update_post(
            post_id,
            status=PostStatus.REJECTED,
            reviewed_at=datetime.utcnow(),
            reviewer_notes=notes,
        )

    def mark_post_published(
        self, post_id: int, linkedin_url: Optional[str] = None
    ) -> bool:
        """Mark a post as published"""
        return self.update_post(
            post_id,
            status=PostStatus.PUBLISHED,
            published_at=datetime.utcnow(),
            linkedin_post_url=linkedin_url,
        )

    # ==================== SOURCES CRUD ====================

    def create_source(self, source: Source) -> int:
        """Create a new source citation"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO sources (
                    post_id, source_name, source_url, citation_text, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    source.post_id,
                    source.source_name,
                    source.source_url,
                    source.citation_text,
                    source.created_at,
                ),
            )
            return cursor.lastrowid

    def get_sources_for_post(self, post_id: int) -> List[Dict[str, Any]]:
        """Get all sources for a specific post"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM sources WHERE post_id = ?", (post_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # ==================== PUBLISHING HISTORY CRUD ====================

    def create_publishing_record(self, history: PublishingHistory) -> int:
        """Create a new publishing history record"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO publishing_history (
                    post_id, platform, published_at, post_url,
                    likes_count, comments_count, shares_count, impressions_count,
                    last_metrics_update, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    history.post_id,
                    history.platform,
                    history.published_at,
                    history.post_url,
                    history.likes_count,
                    history.comments_count,
                    history.shares_count,
                    history.impressions_count,
                    history.last_metrics_update,
                    history.created_at,
                    history.updated_at,
                ),
            )
            return cursor.lastrowid

    def get_publishing_history(self, post_id: int) -> List[Dict[str, Any]]:
        """Get publishing history for a post"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM publishing_history WHERE post_id = ?", (post_id,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_engagement_metrics(
        self,
        history_id: int,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        impressions: int = 0,
    ) -> bool:
        """Update engagement metrics for a published post"""
        return self.update_publishing_record(
            history_id,
            likes_count=likes,
            comments_count=comments,
            shares_count=shares,
            impressions_count=impressions,
            last_metrics_update=datetime.utcnow(),
        )

    def update_publishing_record(self, history_id: int, **kwargs) -> bool:
        """Update a publishing history record"""
        kwargs["updated_at"] = datetime.utcnow()

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [history_id]

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE publishing_history SET {set_clause} WHERE id = ?", values
            )
            return cursor.rowcount > 0

    # ==================== UTILITY METHODS ====================

    def get_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        with self.get_connection() as conn:
            stats = {}

            cursor = conn.execute("SELECT COUNT(*) as count FROM trends")
            stats["total_trends"] = cursor.fetchone()["count"]

            cursor = conn.execute("SELECT COUNT(*) as count FROM posts")
            stats["total_posts"] = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM posts WHERE status = 'pending'"
            )
            stats["pending_posts"] = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM posts WHERE status = 'approved'"
            )
            stats["approved_posts"] = cursor.fetchone()["count"]

            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM posts WHERE status = 'published'"
            )
            stats["published_posts"] = cursor.fetchone()["count"]

            return stats

    def cleanup_old_trends(self, days: int = 30) -> int:
        """Delete trends older than specified days"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM trends
                WHERE fetched_at < datetime('now', '-' || ? || ' days')
                """,
                (days,),
            )
            return cursor.rowcount


# Singleton instance
_db_instance = None


def get_db() -> Database:
    """Get or create database singleton instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = Database()
    return _db_instance
