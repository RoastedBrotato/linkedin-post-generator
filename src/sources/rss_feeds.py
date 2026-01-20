"""
RSS feed integration for tech and AI news sources.

Supports multiple RSS feeds including TechCrunch, VentureBeat, and AI-focused blogs.
"""

import feedparser
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.sources import TrendSource
from src.logger import logger
from config.settings import get_settings

settings = get_settings()


class RSSFeedSource(TrendSource):
    """RSS feed trend source"""

    # Default RSS feeds for tech and AI news
    DEFAULT_FEEDS = {
        "TechCrunch": "https://techcrunch.com/feed/",
        "VentureBeat": "https://venturebeat.com/feed/",
        "The Verge": "https://www.theverge.com/rss/index.xml",
        "Ars Technica": "https://feeds.arstechnica.com/arstechnica/index",
        "MIT Technology Review": "https://www.technologyreview.com/feed/",
        "Towards Data Science": "https://towardsdatascience.com/feed",
        "Machine Learning Mastery": "https://machinelearningmastery.com/feed/",
        "OpenAI Blog": "https://openai.com/blog/rss.xml",
        "DeepMind Blog": "https://deepmind.google/blog/rss.xml",
        "AI News": "https://artificialintelligence-news.com/feed/",
    }

    # Keywords for AI/tech relevance
    AI_KEYWORDS = [
        "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
        "neural network", "llm", "gpt", "chatgpt", "openai", "anthropic", "claude",
        "transformer", "nlp", "natural language", "computer vision", "robotics",
        "autonomous", "tensorflow", "pytorch", "hugging face", "langchain",
        "vector database", "embedding", "fine-tuning", "rag", "prompt engineering",
        "agent", "multimodal", "generative", "diffusion", "stable diffusion",
        "midjourney", "dall-e", "reinforcement learning", "supervised learning"
    ]

    TECH_KEYWORDS = [
        "programming", "software", "developer", "code", "github", "api",
        "cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops",
        "react", "vue", "angular", "python", "javascript", "rust", "go", "java",
        "database", "postgresql", "mongodb", "redis", "microservices", "backend",
        "frontend", "fullstack", "cybersecurity", "blockchain", "web3", "crypto",
        "startup", "tech", "saas", "venture capital", "vc", "funding", "ipo"
    ]

    def __init__(self, feeds: Optional[Dict[str, str]] = None):
        """
        Initialize RSS feed source.

        Args:
            feeds: Optional dict of {feed_name: feed_url}. Uses defaults if not provided.
        """
        super().__init__(source_name="RSS Feeds")
        self.feeds = feeds or self.DEFAULT_FEEDS
        self.max_items_per_feed = settings.trends.rss_max_items_per_feed
        logger.info(f"Initialized RSS source with {len(self.feeds)} feeds")

    def fetch_trends(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch trends from all configured RSS feeds.

        Args:
            limit: Maximum number of trends to return (total across all feeds)

        Returns:
            List of trend dictionaries
        """
        if limit is None:
            limit = len(self.feeds) * self.max_items_per_feed

        all_trends = []

        for feed_name, feed_url in self.feeds.items():
            logger.info(f"Fetching from {feed_name}...")

            try:
                feed = feedparser.parse(feed_url)

                # Check for errors
                if feed.get("bozo"):
                    logger.warning(f"Parse error for {feed_name}: {feed.get('bozo_exception')}")

                # Process entries
                for entry in feed.entries[:self.max_items_per_feed]:
                    trend = self._entry_to_trend(entry, feed_name)
                    if trend and self.is_relevant(trend):
                        all_trends.append(trend)
                        logger.debug(f"Added relevant article: {trend['title']}")

                logger.info(f"Found {len([t for t in all_trends if t.get('metadata', {}).get('feed_name') == feed_name])} relevant items from {feed_name}")

            except Exception as e:
                logger.error(f"Error fetching from {feed_name}: {e}")
                continue

        # Sort by published date (most recent first) and limit
        all_trends.sort(key=lambda x: x.get("published_at", datetime.min), reverse=True)
        logger.info(f"Total relevant trends from RSS feeds: {len(all_trends[:limit])}")

        return all_trends[:limit]

    def _entry_to_trend(self, entry: Any, feed_name: str) -> Optional[Dict[str, Any]]:
        """Convert RSS entry to trend format"""
        try:
            # Get title
            title = entry.get("title", "").strip()
            if not title:
                return None

            # Get description/summary
            description = ""
            if hasattr(entry, "summary"):
                description = entry.summary
            elif hasattr(entry, "description"):
                description = entry.description
            elif hasattr(entry, "content"):
                # Some feeds use content instead
                if isinstance(entry.content, list) and len(entry.content) > 0:
                    description = entry.content[0].get("value", "")

            # Get URL
            url = entry.get("link", "")
            if not url:
                return None

            # Parse published date
            published_at = datetime.now()  # Default to now
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    published_at = datetime(*entry.published_parsed[:6])
                except Exception:
                    pass
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                try:
                    published_at = datetime(*entry.updated_parsed[:6])
                except Exception:
                    pass

            # Extract tags/categories if available
            tags = []
            if hasattr(entry, "tags"):
                tags = [tag.get("term", "") for tag in entry.tags]

            return {
                "title": title,
                "description": description,
                "url": url,
                "score": 0,  # RSS doesn't have scores, will be set by relevance
                "published_at": published_at,
                "category": "tech",  # Will be refined by relevance check
                "metadata": {
                    "feed_name": feed_name,
                    "tags": tags,
                    "author": entry.get("author", ""),
                }
            }

        except Exception as e:
            logger.debug(f"Failed to parse entry: {e}")
            return None

    def is_relevant(self, trend: Dict[str, Any]) -> bool:
        """
        Check if trend is relevant to AI/tech.

        Uses keyword matching on title and description.
        """
        text = f"{trend.get('title', '')} {trend.get('description', '')}".lower()

        # Check for AI keywords (high relevance)
        for keyword in self.AI_KEYWORDS:
            if keyword.lower() in text:
                trend["category"] = "ai"
                return True

        # Check for tech keywords (medium relevance)
        for keyword in self.TECH_KEYWORDS:
            if keyword.lower() in text:
                trend["category"] = "tech"
                return True

        # Also check tags if available
        tags = trend.get("metadata", {}).get("tags", [])
        for tag in tags:
            tag_lower = tag.lower()
            if any(kw in tag_lower for kw in self.AI_KEYWORDS):
                trend["category"] = "ai"
                return True
            if any(kw in tag_lower for kw in self.TECH_KEYWORDS):
                trend["category"] = "tech"
                return True

        return False

    def calculate_relevance_score(self, trend: Dict[str, Any]) -> float:
        """
        Calculate relevance score (0.0 to 1.0) based on keywords and recency.

        Higher scores for:
        - AI-related content
        - Recent posts
        - Reputable sources
        """
        text = f"{trend.get('title', '')} {trend.get('description', '')}".lower()
        score = 0.0

        # AI keyword boost (0.3 per keyword, max 0.6)
        ai_matches = sum(1 for kw in self.AI_KEYWORDS if kw.lower() in text)
        score += min(ai_matches * 0.3, 0.6)

        # Tech keyword boost (0.1 per keyword, max 0.3)
        tech_matches = sum(1 for kw in self.TECH_KEYWORDS if kw.lower() in text)
        score += min(tech_matches * 0.1, 0.3)

        # Recency boost (newer = higher score, max 0.2)
        published_at = trend.get("published_at")
        if published_at:
            hours_old = (datetime.now() - published_at).total_seconds() / 3600
            recency_score = max(0, 1 - (hours_old / 168))  # 168 hours = 1 week
            score += recency_score * 0.2

        # Source reputation boost (0.1 for known quality sources)
        feed_name = trend.get("metadata", {}).get("feed_name", "")
        quality_sources = ["TechCrunch", "MIT Technology Review", "OpenAI Blog", "DeepMind Blog"]
        if feed_name in quality_sources:
            score += 0.1

        return min(score, 1.0)  # Cap at 1.0
