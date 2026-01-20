"""
Main trend fetching and aggregation module.

Fetches trends from multiple sources (Hacker News, RSS, Reddit, GitHub)
and aggregates them into a unified list.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from src.logger import logger
from config.settings import get_settings
from src.database import Database
from src.sources.hackernews import HackerNewsSource
from src.sources.rss_feeds import RSSFeedSource
from src.sources.reddit import RedditSource
from src.sources.github import GitHubTrendingSource

settings = get_settings()


class TrendFetcher:
    """Main trend fetcher that aggregates from multiple sources"""

    def __init__(self, db: Optional[Database] = None):
        """
        Initialize trend fetcher.

        Args:
            db: Optional Database instance for storing trends
        """
        self.db = db
        self.sources = []

        # Initialize enabled sources
        if settings.trends.hackernews_enabled:
            self.sources.append(HackerNewsSource())
            logger.info("Enabled Hacker News source")

        if settings.trends.rss_enabled:
            self.sources.append(RSSFeedSource())
            logger.info("Enabled RSS feeds source")

        if settings.trends.reddit_enabled:
            self.sources.append(RedditSource(read_only=True))
            logger.info("Enabled Reddit source")

        if settings.trends.github_enabled:
            self.sources.append(GitHubTrendingSource())
            logger.info("Enabled GitHub trending source")

        logger.info(f"Initialized TrendFetcher with {len(self.sources)} sources")

    def fetch_all_trends(self, save_to_db: bool = True) -> List[Dict[str, Any]]:
        """
        Fetch trends from all enabled sources.

        Args:
            save_to_db: If True, save trends to database

        Returns:
            List of all fetched trends
        """
        logger.info("Starting trend fetch from all sources...")
        all_trends = []

        for source in self.sources:
            try:
                logger.info(f"Fetching from {source.source_name}...")
                trends = source.fetch_trends()

                # Calculate relevance scores for each trend
                for trend in trends:
                    if hasattr(source, 'calculate_relevance_score'):
                        relevance_score = source.calculate_relevance_score(trend)
                        trend['relevance_score'] = relevance_score
                    else:
                        trend['relevance_score'] = 0.5  # Default score

                all_trends.extend(trends)
                logger.info(f"Fetched {len(trends)} trends from {source.source_name}")

            except Exception as e:
                logger.error(f"Error fetching from {source.source_name}: {e}")
                continue

        logger.info(f"Total trends fetched: {len(all_trends)}")

        # Deduplicate trends
        deduplicated = self._deduplicate_trends(all_trends)
        logger.info(f"After deduplication: {len(deduplicated)} unique trends")

        # Filter by minimum relevance
        filtered = self._filter_by_relevance(deduplicated)
        logger.info(f"After relevance filtering: {len(filtered)} relevant trends")

        # Sort by relevance score
        filtered.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        # Save to database if enabled
        if save_to_db and self.db:
            self._save_trends_to_db(filtered)

        return filtered

    def _deduplicate_trends(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate trends based on URL and title similarity.

        Args:
            trends: List of trend dictionaries

        Returns:
            Deduplicated list of trends
        """
        seen_urls = set()
        seen_titles = set()
        unique_trends = []

        for trend in trends:
            url = trend.get('url', '')
            title = trend.get('title', '').lower().strip()

            # Skip if we've seen this URL
            if url and url in seen_urls:
                logger.debug(f"Duplicate URL found: {url}")
                continue

            # Skip if we've seen very similar title (exact match)
            if title and title in seen_titles:
                logger.debug(f"Duplicate title found: {title}")
                continue

            # Add to unique trends
            unique_trends.append(trend)
            if url:
                seen_urls.add(url)
            if title:
                seen_titles.add(title)

        return unique_trends

    def _filter_by_relevance(self, trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Filter trends by minimum relevance score.

        Args:
            trends: List of trend dictionaries

        Returns:
            Filtered list of trends
        """
        min_relevance = settings.post_generation.min_trend_relevance
        filtered = [
            trend for trend in trends
            if trend.get('relevance_score', 0) >= min_relevance
        ]

        logger.debug(f"Filtered {len(trends) - len(filtered)} trends below relevance threshold {min_relevance}")
        return filtered

    def _save_trends_to_db(self, trends: List[Dict[str, Any]]) -> None:
        """
        Save trends to database.

        Args:
            trends: List of trend dictionaries to save
        """
        if not self.db:
            logger.warning("Database not initialized, skipping trend storage")
            return

        saved_count = 0
        for trend in trends:
            try:
                # Check if trend already exists (by URL)
                existing = self.db.get_trends(url=trend.get('url'))
                if existing:
                    logger.debug(f"Trend already in database: {trend.get('title')}")
                    continue

                # Save new trend
                trend_data = {
                    'title': trend.get('title', ''),
                    'description': trend.get('description', ''),
                    'source_url': trend.get('url', ''),
                    'source_name': trend.get('metadata', {}).get('feed_name') or
                                   trend.get('metadata', {}).get('subreddit') or
                                   'unknown',
                    'fetched_at': datetime.now().isoformat(),
                    'relevance_score': trend.get('relevance_score', 0),
                    'category': trend.get('category', 'tech'),
                    'metadata': str(trend.get('metadata', {})),
                }

                self.db.create_trend(**trend_data)
                saved_count += 1
                logger.debug(f"Saved trend to DB: {trend.get('title')}")

            except Exception as e:
                logger.error(f"Error saving trend to DB: {e}")
                continue

        logger.info(f"Saved {saved_count} new trends to database")

    def get_top_trends(self, limit: int = 10, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get top trends, optionally filtered by category.

        Args:
            limit: Maximum number of trends to return
            category: Optional category filter ('ai', 'tech', etc.)

        Returns:
            List of top trends
        """
        if not self.db:
            logger.warning("Database not initialized, cannot retrieve trends")
            return []

        # Get all recent trends from database
        trends = self.db.get_trends(limit=limit * 2)  # Get more than needed for filtering

        if category:
            trends = [t for t in trends if t.get('category') == category]

        # Sort by relevance score
        trends.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)

        return trends[:limit]

    def analyze_trend(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single trend and add enrichment data.

        Args:
            trend: Trend dictionary

        Returns:
            Enriched trend dictionary
        """
        # Add analysis metadata
        analysis = {
            'word_count': len(trend.get('description', '').split()),
            'has_url': bool(trend.get('url')),
            'category': trend.get('category', 'unknown'),
            'relevance_score': trend.get('relevance_score', 0),
            'source': trend.get('metadata', {}).get('feed_name') or
                     trend.get('metadata', {}).get('subreddit') or
                     'unknown',
        }

        trend['analysis'] = analysis
        return trend
