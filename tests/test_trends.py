"""
Tests for trend fetching and processing.

Tests the trend sources and aggregation logic.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
from src.trends import TrendFetcher
from src.sources.hackernews import HackerNewsSource
from src.sources.rss_feeds import RSSFeedSource
from src.sources.reddit import RedditSource
from src.sources.github import GitHubTrendingSource


class TestHackerNewsSource:
    """Test Hacker News trend source"""

    def test_init(self):
        """Test HN source initialization"""
        source = HackerNewsSource()
        assert source.source_name == "Hacker News"
        assert source.BASE_URL == "https://hacker-news.firebaseio.com/v0"

    def test_is_relevant_ai_keyword(self):
        """Test relevance detection with AI keywords"""
        source = HackerNewsSource()

        trend = {
            "title": "New GPT-4 model released",
            "description": "OpenAI announces GPT-4",
            "category": "tech"
        }

        assert source.is_relevant(trend) is True
        assert trend["category"] == "ai"

    def test_is_relevant_tech_keyword(self):
        """Test relevance detection with tech keywords"""
        source = HackerNewsSource()

        trend = {
            "title": "New Python framework released",
            "description": "Framework for web development",
            "category": "tech"
        }

        assert source.is_relevant(trend) is True
        assert trend["category"] == "tech"

    def test_is_not_relevant(self):
        """Test irrelevant content detection"""
        source = HackerNewsSource()

        trend = {
            "title": "Best pizza restaurants in NYC",
            "description": "A guide to pizza",
            "category": "tech"
        }

        assert source.is_relevant(trend) is False

    def test_calculate_relevance_score_ai(self):
        """Test relevance score calculation for AI content"""
        source = HackerNewsSource()

        trend = {
            "title": "Machine learning breakthrough in NLP",
            "description": "New transformer model for AI",
            "score": 500,
            "metadata": {"descendants": 100}
        }

        score = source.calculate_relevance_score(trend)2026-01-19
        assert 0 <= score <= 1.0
        assert score > 0.5  # Should have high score due to AI keywords


class TestRSSFeedSource:
    """Test RSS feed source"""

    def test_init(self):
        """Test RSS source initialization"""
        source = RSSFeedSource()
        assert source.source_name == "RSS Feeds"
        assert len(source.feeds) > 0

    def test_init_custom_feeds(self):
        """Test RSS source with custom feeds"""
        custom_feeds = {"Test Feed": "https://example.com/feed"}
        source = RSSFeedSource(feeds=custom_feeds)
        assert source.feeds == custom_feeds

    def test_is_relevant_ai_content(self):
        """Test relevance detection for AI content in RSS"""
        source = RSSFeedSource()

        trend = {
            "title": "Deep learning advances in computer vision",
            "description": "New CNN architecture",
            "category": "tech"
        }

        assert source.is_relevant(trend) is True
        assert trend["category"] == "ai"

    def test_entry_to_trend_minimal(self):
        """Test RSS entry parsing with minimal data"""
        source = RSSFeedSource()

        # Mock RSS entry with spec to handle hasattr checks
        entry = MagicMock()
        entry.get = MagicMock(side_effect=lambda key, default=None: {
            "title": "Test Article",
            "link": "https://example.com/article"
        }.get(key, default))
        entry.title = "Test Article"
        entry.link = "https://example.com/article"
        entry.summary = "Test description"
        entry.published_parsed = None
        entry.updated_parsed = None
        entry.tags = []

        trend = source._entry_to_trend(entry, "Test Feed")

        assert trend is not None
        assert trend["title"] == "Test Article"
        assert trend["url"] == "https://example.com/article"
        assert trend["metadata"]["feed_name"] == "Test Feed"


class TestRedditSource:
    """Test Reddit source"""

    def test_init_read_only(self):
        """Test Reddit source initialization in read-only mode"""
        source = RedditSource(read_only=True)
        assert source.source_name == "Reddit"
        assert len(source.subreddits) > 0

    def test_is_relevant_ai_subreddit(self):
        """Test relevance for AI-focused subreddits"""
        source = RedditSource(read_only=True)

        trend = {
            "title": "Any post from MachineLearning",
            "description": "Doesn't matter",
            "metadata": {"subreddit": "MachineLearning"}
        }

        assert source.is_relevant(trend) is True
        assert trend["category"] == "ai"

    def test_is_relevant_ai_keywords(self):
        """Test relevance detection with AI keywords"""
        source = RedditSource(read_only=True)

        trend = {
            "title": "New LLM training technique",
            "description": "Improving AI models",
            "metadata": {"subreddit": "programming"}
        }

        assert source.is_relevant(trend) is True
        assert trend["category"] == "ai"

    def test_calculate_relevance_score(self):
        """Test relevance score calculation for Reddit"""
        source = RedditSource(read_only=True)

        trend = {
            "title": "ChatGPT and machine learning",
            "description": "AI advancements",
            "score": 500,
            "metadata": {
                "subreddit": "MachineLearning",
                "num_comments": 100,
                "upvote_ratio": 0.95
            }
        }

        score = source.calculate_relevance_score(trend)
        assert 0 <= score <= 1.0
        assert score > 0.5  # High score due to AI keywords and engagement


class TestGitHubTrendingSource:
    """Test GitHub trending source"""

    def test_init(self):
        """Test GitHub source initialization"""
        source = GitHubTrendingSource()
        assert source.source_name == "GitHub Trending"
        assert source.BASE_URL == "https://github.com/trending"

    def test_is_relevant_ai_repo(self):
        """Test relevance detection for AI repositories"""
        source = GitHubTrendingSource()

        trend = {
            "title": "username/awesome-llm",
            "description": "Collection of LLM resources and tools",
            "metadata": {"language": "Python"}
        }

        assert source.is_relevant(trend) is True
        assert trend["category"] == "ai"

    def test_is_relevant_tech_repo(self):
        """Test relevance detection for tech repositories"""
        source = GitHubTrendingSource()

        trend = {
            "title": "username/react-framework",
            "description": "Modern React framework for web apps",
            "metadata": {"language": "JavaScript"}
        }

        assert source.is_relevant(trend) is True
        assert trend["category"] == "tech"

    def test_calculate_relevance_score(self):
        """Test relevance score calculation for GitHub"""
        source = GitHubTrendingSource()

        trend = {
            "title": "username/pytorch-lightning",
            "description": "Deep learning framework for PyTorch",
            "metadata": {
                "language": "Python",
                "stars_today": 250,
                "total_stars": 15000
            }
        }

        score = source.calculate_relevance_score(trend)
        assert 0 <= score <= 1.0
        assert score > 0.5  # High score due to AI keywords and popularity


class TestTrendFetcher:
    """Test main TrendFetcher class"""

    def test_init(self):
        """Test TrendFetcher initialization"""
        fetcher = TrendFetcher()
        assert len(fetcher.sources) > 0

    def test_deduplicate_trends_by_url(self):
        """Test deduplication by URL"""
        fetcher = TrendFetcher()

        trends = [
            {"title": "Article 1", "url": "https://example.com/1"},
            {"title": "Article 2", "url": "https://example.com/1"},  # Duplicate URL
            {"title": "Article 3", "url": "https://example.com/2"},
        ]

        deduplicated = fetcher._deduplicate_trends(trends)
        assert len(deduplicated) == 2
        assert deduplicated[0]["title"] == "Article 1"
        assert deduplicated[1]["title"] == "Article 3"

    def test_deduplicate_trends_by_title(self):
        """Test deduplication by title"""
        fetcher = TrendFetcher()

        trends = [
            {"title": "Same Title", "url": "https://example.com/1"},
            {"title": "Same Title", "url": "https://example.com/2"},  # Duplicate title
            {"title": "Different Title", "url": "https://example.com/3"},
        ]

        deduplicated = fetcher._deduplicate_trends(trends)
        assert len(deduplicated) == 2

    def test_filter_by_relevance(self):
        """Test filtering by relevance score"""
        fetcher = TrendFetcher()

        trends = [
            {"title": "High relevance", "relevance_score": 0.8},
            {"title": "Low relevance", "relevance_score": 0.3},
            {"title": "Medium relevance", "relevance_score": 0.6},
        ]

        filtered = fetcher._filter_by_relevance(trends)
        # Default min_relevance is 0.5, so should keep 2 trends
        assert len(filtered) == 2
        assert all(t["relevance_score"] >= 0.5 for t in filtered)

    def test_analyze_trend(self):
        """Test trend analysis"""
        fetcher = TrendFetcher()

        trend = {
            "title": "Test Trend",
            "description": "This is a test description with some words",
            "url": "https://example.com/test",
            "category": "ai",
            "relevance_score": 0.75,
            "metadata": {"feed_name": "TechCrunch"}
        }

        analyzed = fetcher.analyze_trend(trend)

        assert "analysis" in analyzed
        assert analyzed["analysis"]["word_count"] > 0
        assert analyzed["analysis"]["has_url"] is True
        assert analyzed["analysis"]["category"] == "ai"
        assert analyzed["analysis"]["source"] == "TechCrunch"

    @patch('src.trends.HackerNewsSource')
    @patch('src.trends.RSSFeedSource')
    @patch('src.trends.RedditSource')
    @patch('src.trends.GitHubTrendingSource')
    def test_fetch_all_trends_integration(self, mock_github, mock_reddit, mock_rss, mock_hn):
        """Test fetching trends from all sources"""
        # Mock each source to return sample trends
        mock_hn_instance = Mock()
        mock_hn_instance.source_name = "Hacker News"
        mock_hn_instance.fetch_trends.return_value = [
            {
                "title": "HN Trend 1",
                "description": "AI news",
                "url": "https://hn.com/1",
                "score": 100,
                "published_at": datetime.now(),
                "category": "ai",
                "metadata": {}
            }
        ]
        mock_hn_instance.calculate_relevance_score.return_value = 0.8
        mock_hn.return_value = mock_hn_instance

        mock_rss_instance = Mock()
        mock_rss_instance.source_name = "RSS Feeds"
        mock_rss_instance.fetch_trends.return_value = [
            {
                "title": "RSS Trend 1",
                "description": "Tech news",
                "url": "https://rss.com/1",
                "score": 0,
                "published_at": datetime.now(),
                "category": "tech",
                "metadata": {"feed_name": "TechCrunch"}
            }
        ]
        mock_rss_instance.calculate_relevance_score.return_value = 0.7
        mock_rss.return_value = mock_rss_instance

        mock_reddit_instance = Mock()
        mock_reddit_instance.source_name = "Reddit"
        mock_reddit_instance.fetch_trends.return_value = []
        mock_reddit.return_value = mock_reddit_instance

        mock_github_instance = Mock()
        mock_github_instance.source_name = "GitHub Trending"
        mock_github_instance.fetch_trends.return_value = []
        mock_github.return_value = mock_github_instance

        # Create fetcher and fetch trends
        fetcher = TrendFetcher()
        trends = fetcher.fetch_all_trends(save_to_db=False)

        # Should have trends from HN and RSS
        assert len(trends) >= 2
        assert any(t["title"] == "HN Trend 1" for t in trends)
        assert any(t["title"] == "RSS Trend 1" for t in trends)

        # Check relevance scores were added
        for trend in trends:
            assert "relevance_score" in trend
            assert 0 <= trend["relevance_score"] <= 1.0
