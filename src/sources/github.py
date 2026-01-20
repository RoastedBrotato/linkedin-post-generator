"""
GitHub trending repositories scraper.

Fetches trending repositories from GitHub, focusing on AI/ML projects.
"""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.sources import TrendSource
from src.logger import logger
from config.settings import get_settings

settings = get_settings()


class GitHubTrendingSource(TrendSource):
    """GitHub trending repositories source"""

    BASE_URL = "https://github.com/trending"

    # Languages to focus on for AI/ML
    AI_LANGUAGES = ["python", "jupyter-notebook", "r", "julia", "c++"]

    # Keywords for AI/tech relevance
    AI_KEYWORDS = [
        "ai", "artificial intelligence", "machine learning", "ml", "deep learning",
        "neural network", "llm", "gpt", "chatgpt", "openai", "anthropic", "claude",
        "transformer", "nlp", "computer vision", "robotics", "autonomous",
        "tensorflow", "pytorch", "hugging face", "langchain", "vector database",
        "embedding", "fine-tuning", "rag", "prompt engineering", "agent",
        "diffusion", "stable diffusion", "midjourney", "dall-e", "generative",
        "reinforcement learning", "supervised learning", "unsupervised learning",
        "gan", "vae", "bert", "clip", "stable-diffusion", "diffusers"
    ]

    TECH_KEYWORDS = [
        "programming", "software", "developer", "code", "github", "api",
        "cloud", "aws", "azure", "gcp", "kubernetes", "docker", "devops",
        "react", "vue", "angular", "python", "javascript", "rust", "go",
        "database", "postgresql", "mongodb", "redis", "microservices",
        "blockchain", "web3", "crypto", "framework", "library", "tool"
    ]

    def __init__(self):
        """Initialize GitHub trending source"""
        super().__init__(source_name="GitHub Trending")
        self.max_items = settings.trends.github_max_items
        self.min_stars_today = settings.trends.github_min_stars_today

    def fetch_trends(self, limit: int = None, timeframe: str = "daily") -> List[Dict[str, Any]]:
        """
        Fetch trending repositories from GitHub.

        Args:
            limit: Maximum number of trends to return
            timeframe: "daily", "weekly", or "monthly"

        Returns:
            List of trend dictionaries
        """
        if limit is None:
            limit = self.max_items

        all_trends = []

        # Fetch from overall trending
        trends = self._fetch_trending_page(None, timeframe)
        all_trends.extend(trends)

        # Also fetch from AI-focused languages
        for language in self.AI_LANGUAGES[:2]:  # Limit to avoid rate limiting
            trends = self._fetch_trending_page(language, timeframe)
            all_trends.extend(trends)

        # Remove duplicates (same repo URL)
        seen_urls = set()
        unique_trends = []
        for trend in all_trends:
            url = trend.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                if self.is_relevant(trend):
                    unique_trends.append(trend)

        # Sort by stars today (higher = more trending)
        unique_trends.sort(key=lambda x: x.get("score", 0), reverse=True)

        logger.info(f"Found {len(unique_trends[:limit])} relevant trending repos from GitHub")
        return unique_trends[:limit]

    def _fetch_trending_page(self, language: Optional[str], timeframe: str) -> List[Dict[str, Any]]:
        """
        Fetch and parse GitHub trending page for a specific language.

        Args:
            language: Programming language (e.g., "python") or None for all languages
            timeframe: "daily", "weekly", or "monthly"

        Returns:
            List of trend dictionaries
        """
        try:
            # Build URL
            url = self.BASE_URL
            params = {}
            if language:
                url = f"{self.BASE_URL}/{language}"
            if timeframe:
                params["since"] = timeframe

            logger.debug(f"Fetching GitHub trending: {url} (timeframe: {timeframe})")

            # Fetch page
            headers = {
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
            }
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            # Parse HTML
            soup = BeautifulSoup(response.text, "html.parser")

            trends = []
            repo_articles = soup.find_all("article", class_="Box-row")

            for article in repo_articles:
                trend = self._parse_repo_article(article, language)
                if trend:
                    trends.append(trend)

            logger.debug(f"Parsed {len(trends)} repos from GitHub trending ({language or 'all languages'})")
            return trends

        except Exception as e:
            logger.error(f"Error fetching GitHub trending ({language}): {e}")
            return []

    def _parse_repo_article(self, article: Any, language: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse a single repository article from the trending page"""
        try:
            # Get repo name and URL
            h2 = article.find("h2", class_="h3")
            if not h2:
                return None

            link = h2.find("a")
            if not link:
                return None

            repo_path = link.get("href", "").strip()
            if not repo_path:
                return None

            repo_url = f"https://github.com{repo_path}"
            repo_name = repo_path.strip("/")

            # Get description
            description_elem = article.find("p", class_="col-9")
            description = ""
            if description_elem:
                description = description_elem.get_text(strip=True)

            # Get language
            lang_elem = article.find("span", itemprop="programmingLanguage")
            detected_language = language or (lang_elem.get_text(strip=True) if lang_elem else "")

            # Get stars today
            stars_today = 0
            star_spans = article.find_all("span", class_="d-inline-block")
            for span in star_spans:
                text = span.get_text(strip=True)
                if "stars today" in text.lower() or "stars this week" in text.lower():
                    # Extract number
                    try:
                        stars_text = text.split()[0].replace(",", "")
                        stars_today = int(stars_text)
                    except (ValueError, IndexError):
                        pass

            # Get total stars
            total_stars = 0
            star_link = article.find("a", href=lambda x: x and "/stargazers" in x)
            if star_link:
                try:
                    stars_text = star_link.get_text(strip=True).replace(",", "")
                    total_stars = int(stars_text)
                except (ValueError, AttributeError):
                    pass

            # Skip if below minimum stars threshold
            if stars_today < self.min_stars_today:
                return None

            return {
                "title": repo_name,
                "description": description,
                "url": repo_url,
                "score": stars_today,  # Use stars today as the score
                "published_at": datetime.now(),  # Trending page doesn't show exact date
                "category": "tech",  # Will be refined by relevance check
                "metadata": {
                    "language": detected_language,
                    "total_stars": total_stars,
                    "stars_today": stars_today,
                    "repo_name": repo_name,
                }
            }

        except Exception as e:
            logger.debug(f"Failed to parse repo article: {e}")
            return None

    def is_relevant(self, trend: Dict[str, Any]) -> bool:
        """
        Check if repository is relevant to AI/tech.

        Uses keyword matching on title and description.
        """
        text = f"{trend.get('title', '')} {trend.get('description', '')}".lower()

        # Check language - Python, Jupyter notebooks are likely AI-related
        language = trend.get("metadata", {}).get("language", "").lower()
        if language in ["python", "jupyter notebook", "r", "julia"]:
            # Check for AI keywords
            for keyword in self.AI_KEYWORDS:
                if keyword.lower() in text:
                    trend["category"] = "ai"
                    return True

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
        Calculate relevance score (0.0 to 1.0) based on keywords and popularity.

        Higher scores for:
        - AI-related content
        - Higher stars today
        - AI-focused programming languages
        """
        text = f"{trend.get('title', '')} {trend.get('description', '')}".lower()
        score = 0.0

        # AI keyword boost (0.3 per keyword, max 0.6)
        ai_matches = sum(1 for kw in self.AI_KEYWORDS if kw.lower() in text)
        score += min(ai_matches * 0.3, 0.6)

        # Tech keyword boost (0.1 per keyword, max 0.3)
        tech_matches = sum(1 for kw in self.TECH_KEYWORDS if kw.lower() in text)
        score += min(tech_matches * 0.1, 0.3)

        # Stars today boost (trending indicator)
        stars_today = trend.get("metadata", {}).get("stars_today", 0)
        score += min(stars_today / 500.0, 0.2)  # Max 0.2

        # Language boost
        language = trend.get("metadata", {}).get("language", "").lower()
        if language in ["python", "jupyter notebook"]:
            score += 0.1

        # Total stars boost (popularity/quality indicator)
        total_stars = trend.get("metadata", {}).get("total_stars", 0)
        score += min(total_stars / 10000.0, 0.1)  # Max 0.1

        return min(score, 1.0)  # Cap at 1.0
