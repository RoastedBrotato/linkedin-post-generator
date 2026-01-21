"""Tests for post generation pipeline."""

from pathlib import Path

import pytest

from src.database import Database
from src.post_generator import PostGenerator
from src.validators import normalize_hashtags, validate_post_components


class FakeLLMClient:
    """Deterministic LLM stub for tests."""

    def __init__(self, response):
        self.response = response

    def generate_post(self, trend, system_prompt=None, max_retries=3):
        return self.response

    def health_check(self):
        return True


def test_validate_post_components_success():
    content = "A" * 250 + "\n\nSource: https://example.com"
    hashtags = ["#AI", "#Tech"]
    errors = validate_post_components(
        content=content,
        hashtags=hashtags,
        source_url="https://example.com",
        min_length=200,
        max_length=3000,
        max_hashtags=5,
        include_citations=True,
    )
    assert errors == []


def test_normalize_hashtags():
    tags = ["AI", "#Tech", "ai", "  #AI  "]
    normalized = normalize_hashtags(tags, max_hashtags=3)
    assert normalized == ["#AI", "#Tech"]


def test_generate_post_saves_to_db(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    llm = FakeLLMClient(
        {
            "content": "B" * 240,
            "hashtags": ["#AI", "#Trends"],
            "source_url": "https://example.com/article",
            "confidence": "High",
        }
    )
    generator = PostGenerator(db=db, llm=llm)
    trend = {
        "title": "Test Trend",
        "description": "Interesting development in AI.",
        "url": "https://example.com/article",
        "category": "ai",
        "relevance_score": 0.9,
        "metadata": {"feed_name": "Test Feed"},
    }

    result = generator.generate_post_for_trend(trend, save_to_db=True)
    assert result is not None
    assert "post_id" in result

    saved = db.get_post(result["post_id"])
    assert saved is not None
    assert "Source: https://example.com/article" in saved["content"]

    sources = db.get_sources_for_post(result["post_id"])
    assert len(sources) == 1
    assert sources[0]["source_url"] == "https://example.com/article"


def test_generate_post_validation_failure(tmp_path: Path):
    db = Database(tmp_path / "test.db")
    llm = FakeLLMClient(
        {
            "content": "Too short",
            "hashtags": ["#AI"],
            "source_url": "https://example.com/article",
            "confidence": "Low",
        }
    )
    generator = PostGenerator(db=db, llm=llm)
    trend = {
        "title": "Tiny Trend",
        "description": "Short content",
        "url": "https://example.com/article",
        "category": "ai",
        "relevance_score": 0.8,
        "metadata": {"feed_name": "Test Feed"},
    }

    result = generator.generate_post_for_trend(trend, save_to_db=True)
    assert result is None
