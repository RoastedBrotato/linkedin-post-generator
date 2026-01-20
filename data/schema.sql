-- LinkedIn Post Generator Database Schema
-- SQLite Database
-- Generated: 2026-01-20

-- ============================================
-- TRENDS TABLE
-- Stores fetched AI/tech trends from various sources
-- ============================================
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

-- ============================================
-- POSTS TABLE
-- Stores generated LinkedIn posts
-- ============================================
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trend_id INTEGER NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, approved, rejected, published
    generated_at TIMESTAMP NOT NULL,
    reviewed_at TIMESTAMP,
    published_at TIMESTAMP,
    linkedin_post_url TEXT,
    reviewer_notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (trend_id) REFERENCES trends(id) ON DELETE CASCADE
);

-- ============================================
-- SOURCES TABLE
-- Stores source citations for posts
-- ============================================
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    post_id INTEGER NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT NOT NULL,
    citation_text TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES posts(id) ON DELETE CASCADE
);

-- ============================================
-- PUBLISHING HISTORY TABLE
-- Tracks published posts and engagement metrics
-- ============================================
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

-- ============================================
-- INDEXES
-- For improved query performance
-- ============================================
CREATE INDEX IF NOT EXISTS idx_trends_category ON trends(category);
CREATE INDEX IF NOT EXISTS idx_trends_fetched_at ON trends(fetched_at);
CREATE INDEX IF NOT EXISTS idx_trends_relevance_score ON trends(relevance_score);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_posts_trend_id ON posts(trend_id);
CREATE INDEX IF NOT EXISTS idx_posts_generated_at ON posts(generated_at);
CREATE INDEX IF NOT EXISTS idx_sources_post_id ON sources(post_id);
CREATE INDEX IF NOT EXISTS idx_publishing_history_post_id ON publishing_history(post_id);
