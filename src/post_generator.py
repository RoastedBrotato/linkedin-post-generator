"""
Post generation pipeline for LinkedIn posts from trend data.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from config.settings import get_settings
from src.database import Database
from src.llm import LLMClient
from src.logger import logger
from src.models import Post, Source, Trend, TrendCategory
from src.validators import normalize_hashtags, validate_post_components
from src.image_generator import ImageGenerator


class PostGenerator:
    """Generate and store LinkedIn posts from trends."""

    def __init__(
        self,
        db: Optional[Database] = None,
        llm: Optional[LLMClient] = None,
        image_generator: Optional[ImageGenerator] = None,
    ) -> None:
        self.settings = get_settings()
        self.db = db
        self.llm = llm or LLMClient()
        self.image_generator = image_generator or ImageGenerator()

    def generate_post_for_trend(
        self,
        trend: Dict[str, Any],
        save_to_db: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Generate a post for a single trend."""
        result = self.llm.generate_post(trend)
        if not result:
            logger.error("LLM returned no result.")
            return None

        source_url = (
            result.get("source_url")
            or trend.get("url")
            or trend.get("source_url")
            or ""
        ).strip()
        hashtags = normalize_hashtags(result.get("hashtags", []))
        content = self._build_post_content(result.get("content", ""), hashtags, source_url)

        errors = validate_post_components(
            content=content,
            hashtags=hashtags,
            source_url=source_url,
        )
        if errors:
            logger.warning(f"Post validation failed: {errors}")
            return None

        # Generate image for the post
        image_path = None
        try:
            logger.info("Generating image for LinkedIn post...")
            image_path = self.image_generator.generate_image_from_post(
                post_content=content,
                trend_title=trend.get("title")
            )
            if image_path:
                logger.info(f"Image generated successfully: {image_path}")
            else:
                logger.warning("Image generation returned no path, continuing without image")
        except Exception as e:
            logger.warning(f"Image generation failed: {e}. Continuing without image.")

        post_record = {
            "content": content,
            "hashtags": hashtags,
            "source_url": source_url,
            "confidence": result.get("confidence", "Medium"),
            "trend_title": trend.get("title"),
            "trend_category": trend.get("category"),
            "image_path": image_path,
        }

        if save_to_db and self.db:
            trend_id = self._ensure_trend_in_db(trend)
            if trend_id is None:
                logger.error("Unable to persist trend for post.")
                return None

            post_id = self._save_post(trend_id, content, image_path)
            if post_id is None:
                return None

            self._save_source(post_id, trend, source_url)
            post_record["post_id"] = post_id

        return post_record

    def generate_posts_batch(
        self,
        trends: List[Dict[str, Any]],
        limit: Optional[int] = None,
        save_to_db: bool = True,
    ) -> List[Dict[str, Any]]:
        """Generate posts for a list of trends."""
        results = []
        for trend in trends[: limit or len(trends)]:
            post = self.generate_post_for_trend(trend, save_to_db=save_to_db)
            if post:
                results.append(post)
        return results

    def _build_post_content(self, content: str, hashtags: List[str], source_url: str) -> str:
        """Build final post content with citations and hashtags."""
        body = (content or "").strip()
        parts = [body] if body else []

        if self.settings.post_generation.include_citations and source_url:
            citation_line = f"Source: {source_url}"
            if citation_line not in body:
                parts.append(citation_line)

        if hashtags:
            parts.append(" ".join(hashtags))

        return "\n\n".join(parts).strip()

    def _ensure_trend_in_db(self, trend: Dict[str, Any]) -> Optional[int]:
        """Ensure the trend exists in the database and return its ID."""
        if not self.db:
            return None

        existing_id = trend.get("id")
        if existing_id:
            return int(existing_id)

        source_url = trend.get("url") or trend.get("source_url") or ""
        source_name = self._extract_source_name(trend)
        category = self._normalize_category(trend.get("category"))

        try:
            trend_model = Trend(
                title=trend.get("title", "Untitled Trend"),
                description=trend.get("description", "No description provided."),
                source_url=source_url,
                source_name=source_name,
                category=category,
                relevance_score=trend.get("relevance_score", 0.0),
                fetched_at=trend.get("fetched_at") or datetime.utcnow(),
            )
            return self.db.create_trend(trend_model)
        except Exception as exc:
            logger.error(f"Failed to save trend: {exc}")
            return None

    def _save_post(self, trend_id: int, content: str, image_path: Optional[str] = None) -> Optional[int]:
        """Persist the post in the database."""
        if not self.db:
            return None

        try:
            post = Post(trend_id=trend_id, content=content, image_path=image_path)
            post_id = self.db.create_post(post)

            # Update with image_path if provided (since create_post may not handle it)
            if post_id and image_path:
                self.db.update_post(post_id, image_path=image_path)

            return post_id
        except Exception as exc:
            logger.error(f"Failed to save post: {exc}")
            return None

    def _save_source(self, post_id: int, trend: Dict[str, Any], source_url: str) -> None:
        """Persist the source citation in the database."""
        if not self.db or not source_url:
            return

        source_name = self._extract_source_name(trend)
        try:
            source = Source(
                post_id=post_id,
                source_name=source_name,
                source_url=source_url,
            )
            self.db.create_source(source)
        except Exception as exc:
            logger.warning(f"Failed to save source citation: {exc}")

    def _extract_source_name(self, trend: Dict[str, Any]) -> str:
        metadata = trend.get("metadata", {}) or {}
        return (
            trend.get("source_name")
            or metadata.get("feed_name")
            or (f"r/{metadata.get('subreddit')}" if metadata.get("subreddit") else None)
            or metadata.get("repo_name")
            or "Unknown Source"
        )

    def _normalize_category(self, category_value: Any) -> TrendCategory:
        try:
            if isinstance(category_value, TrendCategory):
                return category_value
            if isinstance(category_value, str) and category_value:
                return TrendCategory(category_value)
        except Exception:
            pass
        return TrendCategory.OTHER
