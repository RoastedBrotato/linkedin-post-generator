"""
Reddit API integration for tech and AI discussions.

Fetches top posts from relevant subreddits like r/MachineLearning, r/artificial, etc.
"""

import praw
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.sources import TrendSource
from src.logger import logger
from config.settings import get_settings

settings = get_settings()


class RedditSource(TrendSource):
    """Reddit trend source"""

    # Default subreddits for AI/tech trends
    DEFAULT_SUBREDDITS = [
        "MachineLearning",
        "artificial",
        "LocalLLaMA",
        "OpenAI",
        "ChatGPT",
        "ArtificialIntelligence",
        "StableDiffusion",
        "programming",
        "Python",
        "javascript",
        "webdev",
        "technology",
        "tech",
        "startups",
        "SaaS",
    ]

    # Keywords for AI/tech relevance
    AI_KEYWORDS = [
        "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
        "neural network", "llm", "gpt", "chatgpt", "openai", "anthropic", "claude",
        "transformer", "nlp", "computer vision", "robotics", "autonomous",
        "tensorflow", "pytorch", "hugging face", "langchain", "vector database",
        "embedding", "fine-tuning", "rag", "prompt engineering", "agent",
        "diffusion", "stable diffusion", "midjourney", "dall-e", "generative"
    ]

    TECH_KEYWORDS = [
        "programming", "software", "developer", "code", "github", "api",
        "cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops",
        "react", "vue", "angular", "python", "javascript", "rust", "go",
        "database", "postgresql", "mongodb", "redis", "microservices",
        "blockchain", "web3", "startup", "tech", "saas"
    ]

    def __init__(self, subreddits: Optional[List[str]] = None, read_only: bool = True):
        """
        Initialize Reddit source.

        Args:
            subreddits: List of subreddit names to fetch from. Uses defaults if not provided.
            read_only: If True, uses Reddit in read-only mode (no authentication needed)
        """
        super().__init__(source_name="Reddit")
        self.subreddits = subreddits or self.DEFAULT_SUBREDDITS
        self.read_only = read_only
        self.min_score = settings.trends.reddit_min_score
        self.max_items_per_subreddit = settings.trends.reddit_max_items_per_subreddit

        # Initialize Reddit client
        try:
            if read_only:
                # Read-only mode doesn't require credentials
                self.reddit = praw.Reddit(
                    client_id="read_only_client",
                    client_secret=None,
                    user_agent="linkedin-post-generator/1.0 (by /u/your_username)"
                )
            else:
                # Authenticated mode (requires credentials in .env)
                self.reddit = praw.Reddit(
                    client_id=settings.trends.reddit_client_id,
                    client_secret=settings.trends.reddit_client_secret,
                    user_agent=settings.trends.reddit_user_agent
                )

            logger.info(f"Initialized Reddit source with {len(self.subreddits)} subreddits")
        except Exception as e:
            logger.error(f"Failed to initialize Reddit client: {e}")
            self.reddit = None

    def fetch_trends(self, limit: int = None) -> List[Dict[str, Any]]:
        """
        Fetch trends from configured subreddits.

        Args:
            limit: Maximum number of trends to return (total across all subreddits)

        Returns:
            List of trend dictionaries
        """
        if self.reddit is None:
            logger.error("Reddit client not initialized")
            return []

        if limit is None:
            limit = len(self.subreddits) * self.max_items_per_subreddit

        all_trends = []

        for subreddit_name in self.subreddits:
            try:
                logger.info(f"Fetching from r/{subreddit_name}...")

                subreddit = self.reddit.subreddit(subreddit_name)

                # Fetch hot posts from the subreddit
                for submission in subreddit.hot(limit=self.max_items_per_subreddit):
                    # Skip stickied posts (announcements, etc.)
                    if submission.stickied:
                        continue

                    # Check minimum score
                    if submission.score < self.min_score:
                        continue

                    trend = self._submission_to_trend(submission, subreddit_name)
                    if trend and self.is_relevant(trend):
                        all_trends.append(trend)
                        logger.debug(f"Added relevant post: {trend['title']}")

                logger.info(f"Found {len([t for t in all_trends if t.get('metadata', {}).get('subreddit') == subreddit_name])} relevant posts from r/{subreddit_name}")

            except Exception as e:
                logger.error(f"Error fetching from r/{subreddit_name}: {e}")
                continue

        # Sort by score (upvotes) and limit
        all_trends.sort(key=lambda x: x.get("score", 0), reverse=True)
        logger.info(f"Total relevant trends from Reddit: {len(all_trends[:limit])}")

        return all_trends[:limit]

    def _submission_to_trend(self, submission: Any, subreddit_name: str) -> Optional[Dict[str, Any]]:
        """Convert Reddit submission to trend format"""
        try:
            # Get title
            title = submission.title.strip()
            if not title:
                return None

            # Get description (selftext for text posts, or empty for link posts)
            description = ""
            if submission.selftext:
                description = submission.selftext
            elif submission.is_self is False:
                # Link post - use title as description
                description = title

            # Get URL (use permalink for self posts, external URL for link posts)
            if submission.is_self:
                url = f"https://reddit.com{submission.permalink}"
            else:
                url = submission.url or f"https://reddit.com{submission.permalink}"

            # Convert timestamp to datetime
            published_at = datetime.fromtimestamp(submission.created_utc)

            # Get flair if available
            flair = submission.link_flair_text or ""

            return {
                "title": title,
                "description": description,
                "url": url,
                "score": submission.score,
                "published_at": published_at,
                "category": "tech",  # Will be refined by relevance check
                "metadata": {
                    "subreddit": subreddit_name,
                    "author": str(submission.author) if submission.author else "[deleted]",
                    "num_comments": submission.num_comments,
                    "upvote_ratio": submission.upvote_ratio,
                    "flair": flair,
                    "reddit_id": submission.id,
                }
            }

        except Exception as e:
            logger.debug(f"Failed to parse submission: {e}")
            return None

    def is_relevant(self, trend: Dict[str, Any]) -> bool:
        """
        Check if trend is relevant to AI/tech.

        Uses keyword matching on title and description.
        """
        text = f"{trend.get('title', '')} {trend.get('description', '')}".lower()

        # Check subreddit - AI-focused subreddits are automatically relevant
        subreddit = trend.get("metadata", {}).get("subreddit", "")
        ai_subreddits = ["MachineLearning", "artificial", "LocalLLaMA", "OpenAI", "ChatGPT", "ArtificialIntelligence", "StableDiffusion"]
        if subreddit in ai_subreddits:
            trend["category"] = "ai"
            return True

        # Check for AI keywords
        for keyword in self.AI_KEYWORDS:
            if keyword.lower() in text:
                trend["category"] = "ai"
                return True

        # Check for tech keywords
        for keyword in self.TECH_KEYWORDS:
            if keyword.lower() in text:
                trend["category"] = "tech"
                return True

        # Check flair
        flair = trend.get("metadata", {}).get("flair", "").lower()
        if any(kw in flair for kw in self.AI_KEYWORDS):
            trend["category"] = "ai"
            return True
        if any(kw in flair for kw in self.TECH_KEYWORDS):
            trend["category"] = "tech"
            return True

        return False

    def calculate_relevance_score(self, trend: Dict[str, Any]) -> float:
        """
        Calculate relevance score (0.0 to 1.0) based on keywords and engagement.

        Higher scores for:
        - AI-related content
        - Higher engagement (score, comments, upvote ratio)
        - AI-focused subreddits
        """
        text = f"{trend.get('title', '')} {trend.get('description', '')}".lower()
        score = 0.0

        # AI keyword boost (0.3 per keyword, max 0.6)
        ai_matches = sum(1 for kw in self.AI_KEYWORDS if kw.lower() in text)
        score += min(ai_matches * 0.3, 0.6)

        # Tech keyword boost (0.1 per keyword, max 0.3)
        tech_matches = sum(1 for kw in self.TECH_KEYWORDS if kw.lower() in text)
        score += min(tech_matches * 0.1, 0.3)

        # Engagement boost based on Reddit score (normalized)
        reddit_score = trend.get("score", 0)
        score += min(reddit_score / 1000.0, 0.15)  # Max 0.15 for high score

        # Comments boost (discussion indicator)
        num_comments = trend.get("metadata", {}).get("num_comments", 0)
        score += min(num_comments / 200.0, 0.1)  # Max 0.1

        # Upvote ratio boost (quality indicator)
        upvote_ratio = trend.get("metadata", {}).get("upvote_ratio", 0)
        score += upvote_ratio * 0.1  # Max 0.1

        # Subreddit reputation boost
        subreddit = trend.get("metadata", {}).get("subreddit", "")
        quality_subreddits = ["MachineLearning", "artificial", "OpenAI", "programming"]
        if subreddit in quality_subreddits:
            score += 0.05

        return min(score, 1.0)  # Cap at 1.0
