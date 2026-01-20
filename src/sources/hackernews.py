"""
Hacker News API integration.

Fetches top stories from Hacker News and filters for AI/tech relevance.
"""

import requests
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.sources import TrendSource
from src.logger import logger
from config.settings import get_settings

settings = get_settings()


class HackerNewsSource(TrendSource):
    """Hacker News trend source"""

    BASE_URL = "https://hacker-news.firebaseio.com/v0"

    # Keywords for AI/tech relevance
    AI_KEYWORDS = [
        "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
        "neural network", "llm", "gpt", "chatgpt", "openai", "anthropic", "claude",
        "transformer", "nlp", "computer vision", "robotics", "autonomous",
        "tensorflow", "pytorch", "hugging face", "langchain", "vector database",
        "embedding", "fine-tuning", "rag", "prompt engineering", "agent"
    ]

    TECH_KEYWORDS = [
        "programming", "software", "developer", "code", "github", "api",
        "cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops",
        "react", "vue", "angular", "python", "javascript", "rust", "go",
        "database", "postgresql", "mongodb", "redis", "microservices",
        "security", "blockchain", "web3", "startup", "tech", "saas"
    ]

    def __init__(self):
        super().__init__(source_name="Hacker News")
        self.min_score = settings.trends.hackernews_min_score
        self.max_items = settings.trends.hackernews_max_items

    def fetch_trends(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch top stories from Hacker News.

        Args:
            limit: Maximum number of stories to return (overrides config)

        Returns:
            List of trend dictionaries
        """
        if limit is None:
            limit = self.max_items

        try:
            logger.info(f"Fetching top stories from {self.source_name}...")

            # Get top story IDs
            response = requests.get(
                f"{self.BASE_URL}/topstories.json",
                timeout=10
            )
            response.raise_for_status()
            story_ids = response.json()[:100]  # Get top 100 IDs

            logger.debug(f"Retrieved {len(story_ids)} story IDs")

            # Fetch individual stories
            trends = []
            for story_id in story_ids:
                if len(trends) >= limit:
                    break

                story = self._fetch_story(story_id)
                if story and self._meets_criteria(story):
                    trend = self._story_to_trend(story)
                    if self.is_relevant(trend):
                        trends.append(trend)
                        logger.debug(f"Added relevant story: {trend['title']}")

            logger.info(f"Found {len(trends)} relevant trends from {self.source_name}")
            return trends

        except requests.RequestException as e:
            logger.error(f"Error fetching from {self.source_name}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in {self.source_name}: {e}")
            return []

    def _fetch_story(self, story_id: int) -> Optional[Dict[str, Any]]:
        """Fetch individual story details"""
        try:
            response = requests.get(
                f"{self.BASE_URL}/item/{story_id}.json",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.debug(f"Failed to fetch story {story_id}: {e}")
            return None

    def _meets_criteria(self, story: Dict[str, Any]) -> bool:
        """Check if story meets basic criteria"""
        # Must be a story (not comment, poll, etc.)
        if story.get("type") != "story":
            return False

        # Must have minimum score
        score = story.get("score", 0)
        if score < self.min_score:
            return False

        # Must have a title
        if not story.get("title"):
            return False

        # Must not be deleted or dead
        if story.get("deleted") or story.get("dead"):
            return False

        return True

    def _story_to_trend(self, story: Dict[str, Any]) -> Dict[str, Any]:
        """Convert HN story to trend format"""
        # Get URL - use HN discussion URL if no external URL
        url = story.get("url")
        if not url:
            url = f"https://news.ycombinator.com/item?id={story['id']}"

        # Get description from text field or empty
        description = story.get("text", "")
        if not description:
            # If no description, use title as description
            description = story.get("title", "")

        # Convert Unix timestamp to datetime
        published_at = datetime.fromtimestamp(story.get("time", 0))

        return {
            "title": story.get("title", ""),
            "description": description,
            "url": url,
            "score": story.get("score", 0),
            "published_at": published_at,
            "category": "tech",  # Will be refined by relevance scoring
            "metadata": {
                "hn_id": story.get("id"),
                "by": story.get("by"),
                "descendants": story.get("descendants", 0)  # comment count
            }
        }

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

        return False

    def calculate_relevance_score(self, trend: Dict[str, Any]) -> float:
        """
        Calculate relevance score (0.0 to 1.0) based on keywords and engagement.

        Higher scores for:
        - AI-related content
        - Higher engagement (score, comments)
        - Recent posts
        """
        text = f"{trend.get('title', '')} {trend.get('description', '')}".lower()
        score = 0.0

        # AI keyword boost (0.3 per keyword, max 0.6)
        ai_matches = sum(1 for kw in self.AI_KEYWORDS if kw.lower() in text)
        score += min(ai_matches * 0.3, 0.6)

        # Tech keyword boost (0.1 per keyword, max 0.3)
        tech_matches = sum(1 for kw in self.TECH_KEYWORDS if kw.lower() in text)
        score += min(tech_matches * 0.1, 0.3)

        # Engagement boost based on HN score (normalized)
        hn_score = trend.get("score", 0)
        score += min(hn_score / 1000.0, 0.2)  # Max 0.2 for high engagement

        # Comments boost
        comments = trend.get("metadata", {}).get("descendants", 0)
        score += min(comments / 500.0, 0.1)  # Max 0.1 for discussion

        return min(score, 1.0)  # Cap at 1.0
