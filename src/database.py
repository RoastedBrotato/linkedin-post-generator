"""
Database management for the LinkedIn Post Generator.

Handles SQLite database initialization, connections, and CRUD operations.
"""

import json
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

-- Query runs (for web UI history and filtering)
CREATE TABLE IF NOT EXISTS query_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keywords_raw TEXT NOT NULL,
    phrases_raw TEXT NOT NULL,
    sources_json TEXT NOT NULL,
    options_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- Query run results (join to trends)
CREATE TABLE IF NOT EXISTS query_run_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query_run_id INTEGER NOT NULL,
    trend_id INTEGER NOT NULL,
    match_score REAL NOT NULL DEFAULT 0.0,
    matched_terms_json TEXT NOT NULL,
    match_fields_json TEXT NOT NULL,
    rank INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (query_run_id) REFERENCES query_runs(id) ON DELETE CASCADE,
    FOREIGN KEY (trend_id) REFERENCES trends(id) ON DELETE CASCADE
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
CREATE INDEX IF NOT EXISTS idx_query_runs_status ON query_runs(status);
CREATE INDEX IF NOT EXISTS idx_query_runs_created_at ON query_runs(created_at);
CREATE INDEX IF NOT EXISTS idx_query_run_trends_query_run_id ON query_run_trends(query_run_id);
CREATE INDEX IF NOT EXISTS idx_query_run_trends_match_score ON query_run_trends(match_score);
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
            self._run_migrations(conn)

    def _run_migrations(self, conn):
        """Run database migrations"""
        cursor = conn.cursor()

        # Check if hashtags column exists
        cursor.execute("PRAGMA table_info(posts)")
        columns = [row[1] for row in cursor.fetchall()]

        if "hashtags" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN hashtags TEXT")

        if "platform_post_id" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN platform_post_id TEXT")

        if "post_url" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN post_url TEXT")

        # Add scheduling fields
        if "scheduled_for" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN scheduled_for TIMESTAMP")

        if "is_scheduled" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN is_scheduled INTEGER DEFAULT 0")

        # Add image fields
        if "image_path" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN image_path TEXT")

        if "image_url" not in columns:
            cursor.execute("ALTER TABLE posts ADD COLUMN image_url TEXT")

        # Create post_images table if it doesn't exist
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS post_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                image_path TEXT NOT NULL,
                image_url TEXT,
                uploaded_to_linkedin INTEGER DEFAULT 0,
                linkedin_asset_id TEXT,
                width INTEGER,
                height INTEGER,
                file_size INTEGER,
                mime_type TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
            )
        """)

        conn.commit()

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

    def get_trend_by_url(self, source_url: str) -> Optional[Dict[str, Any]]:
        """Get a trend by source URL"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM trends WHERE source_url = ?", (source_url,)
            )
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

    # ==================== QUERY RUNS CRUD ====================

    def create_query_run(
        self,
        keywords_raw: str,
        phrases_raw: str,
        sources_json: str,
        options_json: str,
        status: str = "queued",
    ) -> int:
        """Create a new query run record"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO query_runs (
                    keywords_raw, phrases_raw, sources_json, options_json,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    keywords_raw,
                    phrases_raw,
                    sources_json,
                    options_json,
                    status,
                    datetime.utcnow(),
                ),
            )
            return cursor.lastrowid

    def get_query_run(self, query_run_id: int) -> Optional[Dict[str, Any]]:
        """Get a query run by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM query_runs WHERE id = ?", (query_run_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_query_runs(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """List query runs (most recent first)"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT * FROM query_runs
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    def update_query_run(self, query_run_id: int, **kwargs) -> bool:
        """Update a query run record"""
        if "options_json" in kwargs and isinstance(kwargs["options_json"], dict):
            kwargs["options_json"] = json.dumps(kwargs["options_json"])
        if "sources_json" in kwargs and isinstance(kwargs["sources_json"], list):
            kwargs["sources_json"] = json.dumps(kwargs["sources_json"])
        if "phrases_raw" in kwargs and isinstance(kwargs["phrases_raw"], list):
            kwargs["phrases_raw"] = json.dumps(kwargs["phrases_raw"])

        set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
        values = list(kwargs.values()) + [query_run_id]

        with self.get_connection() as conn:
            cursor = conn.execute(
                f"UPDATE query_runs SET {set_clause} WHERE id = ?", values
            )
            return cursor.rowcount > 0

    def add_query_run_trend(
        self,
        query_run_id: int,
        trend_id: int,
        match_score: float,
        matched_terms_json: str,
        match_fields_json: str,
        rank: int,
    ) -> int:
        """Create a query run trend result record"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO query_run_trends (
                    query_run_id, trend_id, match_score, matched_terms_json,
                    match_fields_json, rank, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    query_run_id,
                    trend_id,
                    match_score,
                    matched_terms_json,
                    match_fields_json,
                    rank,
                    datetime.utcnow(),
                ),
            )
            return cursor.lastrowid

    def get_query_run_results(
        self,
        query_run_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get query run results joined with trend data"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    qrt.id as query_run_trend_id,
                    qrt.match_score,
                    qrt.matched_terms_json,
                    qrt.match_fields_json,
                    qrt.rank,
                    t.*
                FROM query_run_trends qrt
                JOIN trends t ON t.id = qrt.trend_id
                WHERE qrt.query_run_id = ?
                ORDER BY qrt.rank ASC
                LIMIT ? OFFSET ?
                """,
                (query_run_id, limit, offset),
            )
            return [dict(row) for row in cursor.fetchall()]

    # ==================== HELPER METHODS FOR WEB API ====================

    def get_trend_by_id(self, trend_id: int) -> Optional[Dict[str, Any]]:
        """Get a trend by ID (alias for get_trend)"""
        return self.get_trend(trend_id)

    def get_post_with_trend(self, post_id: int) -> Optional[Dict[str, Any]]:
        """Get a post with its associated trend data"""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    p.*,
                    t.title as trend_title,
                    t.description as trend_description,
                    t.source_url as trend_url,
                    t.source_name as trend_source
                FROM posts p
                JOIN trends t ON t.id = p.trend_id
                WHERE p.id = ?
                """,
                (post_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_posts(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List posts, optionally filtered by status"""
        with self.get_connection() as conn:
            if status:
                cursor = conn.execute(
                    """
                    SELECT
                        p.*,
                        t.title as trend_title,
                        t.source_url as trend_url
                    FROM posts p
                    JOIN trends t ON t.id = p.trend_id
                    WHERE p.status = ?
                    ORDER BY p.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (status, limit, offset),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT
                        p.*,
                        t.title as trend_title,
                        t.source_url as trend_url
                    FROM posts p
                    JOIN trends t ON t.id = p.trend_id
                    ORDER BY p.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset),
                )
            return [dict(row) for row in cursor.fetchall()]

    def update_post_status(self, post_id: int, status: str) -> bool:
        """Update post status"""
        return self.update_post(post_id, status=status, updated_at=datetime.utcnow())

    def create_post_from_dict(
        self,
        content: str,
        trend_id: int,
        status: str = "pending",
        hashtags: Optional[str] = None
    ) -> int:
        """Helper to create post from dict (for API)"""
        from src.models import Post
        post = Post(
            trend_id=trend_id,
            content=content,
            status=status,
            generated_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        post_id = self.create_post(post)

        # Update with hashtags if provided
        if hashtags:
            self.update_post(post_id, hashtags=hashtags)

        return post_id

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
