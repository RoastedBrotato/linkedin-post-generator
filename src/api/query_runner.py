"""
Query run execution and matching logic for the web UI.
"""

from __future__ import annotations

import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config.settings import get_settings
from src.database import get_db
from src.logger import logger
from src.models import Trend, TrendCategory
from src.sources.github import GitHubTrendingSource
from src.sources.hackernews import HackerNewsSource
from src.sources.rss_feeds import RSSFeedSource

_EXECUTOR = ThreadPoolExecutor(max_workers=2)

_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "for",
    "to", "of", "in", "on", "with", "at", "by", "from", "as", "is",
}

_SOURCE_IDS = {"hackernews", "rss", "github"}


def enqueue_query_run(query_run_id: int) -> None:
    """Submit a query run to the background executor."""
    _EXECUTOR.submit(_execute_query_run, query_run_id)


def _execute_query_run(query_run_id: int) -> None:
    db = get_db()
    run = db.get_query_run(query_run_id)
    if not run:
        logger.error(f"Query run {query_run_id} not found.")
        return

    db.update_query_run(query_run_id, status="running")

    try:
        keywords_raw = run.get("keywords_raw", "") or ""
        phrases_input = json.loads(run.get("phrases_raw") or "[]")
        sources_input = json.loads(run.get("sources_json") or "[]")
        options = json.loads(run.get("options_json") or "{}")

        keywords, phrases = _parse_keywords_phrases(keywords_raw, phrases_input)
        sources = _normalize_sources(sources_input)

        trends = _fetch_trends(sources, options)
        matched = _match_trends(trends, keywords, phrases)

        _persist_results(query_run_id, matched)

        db.update_query_run(
            query_run_id,
            status="complete",
            completed_at=datetime.utcnow(),
        )
    except Exception as exc:
        logger.error(f"Query run {query_run_id} failed: {exc}")
        db.update_query_run(
            query_run_id,
            status="failed",
            error_message=str(exc),
            completed_at=datetime.utcnow(),
        )


def _parse_keywords_phrases(
    keywords_raw: str,
    phrases_input: Iterable[str],
) -> Tuple[List[str], List[str]]:
    extracted_phrases = re.findall(r"\"([^\"]+)\"", keywords_raw)
    keywords_clean = re.sub(r"\"[^\"]+\"", " ", keywords_raw)

    phrases = list(phrases_input) + extracted_phrases
    phrases = [re.sub(r"\s+", " ", p.strip().lower()) for p in phrases if p.strip()]
    phrases = list(dict.fromkeys(phrases))

    keywords = []
    for token in re.split(r"\s+", keywords_clean.strip().lower()):
        if not token or token in _STOPWORDS:
            continue
        keywords.append(token)

    keywords = list(dict.fromkeys(keywords))
    return keywords, phrases


def _normalize_sources(sources_input: Iterable[str]) -> List[str]:
    sources = [s for s in sources_input if s in _SOURCE_IDS]
    return sources or sorted(_SOURCE_IDS)


def _fetch_trends(
    sources: Iterable[str],
    options: Dict[str, Any],
) -> List[Dict[str, Any]]:
    settings = get_settings()
    all_trends: List[Dict[str, Any]] = []

    if "hackernews" in sources:
        hn_options = options.get("hackernews", {})
        source = HackerNewsSource()
        if "min_score" in hn_options:
            source.min_score = hn_options["min_score"]
        limit = hn_options.get("max_items") or source.max_items
        trends = source.fetch_trends(limit=limit)
        _apply_relevance_scores(source, trends)
        _tag_source(trends, "Hacker News")
        all_trends.extend(trends)

    if "rss" in sources:
        rss_options = options.get("rss", {})
        feeds = rss_options.get("feeds")
        if isinstance(feeds, list):
            feeds = {url: url for url in feeds}
        source = RSSFeedSource(feeds=feeds)
        if "max_items_per_feed" in rss_options:
            source.max_items_per_feed = rss_options["max_items_per_feed"]
        limit = rss_options.get("max_items") or (len(source.feeds) * source.max_items_per_feed)
        trends = source.fetch_trends(limit=limit)
        _apply_relevance_scores(source, trends)
        _tag_source(trends, "RSS Feeds")
        all_trends.extend(trends)

    if "github" in sources:
        gh_options = options.get("github", {})
        source = GitHubTrendingSource()
        if "min_stars_today" in gh_options:
            source.min_stars_today = gh_options["min_stars_today"]
        if "max_items" in gh_options:
            source.max_items = gh_options["max_items"]
        timeframe = gh_options.get("timeframe", "daily")
        trends = source.fetch_trends(limit=source.max_items, timeframe=timeframe)
        _apply_relevance_scores(source, trends)
        _tag_source(trends, "GitHub Trending")
        all_trends.extend(trends)

    deduped = _deduplicate_trends(all_trends)
    min_relevance = settings.post_generation.min_trend_relevance
    filtered = [t for t in deduped if t.get("relevance_score", 0) >= min_relevance]
    return filtered


def _apply_relevance_scores(source: Any, trends: List[Dict[str, Any]]) -> None:
    for trend in trends:
        if hasattr(source, "calculate_relevance_score"):
            trend["relevance_score"] = source.calculate_relevance_score(trend)
        else:
            trend["relevance_score"] = trend.get("relevance_score", 0.5)


def _tag_source(trends: List[Dict[str, Any]], source_name: str) -> None:
    for trend in trends:
        trend.setdefault("source_name", source_name)
        trend.setdefault("fetched_at", datetime.utcnow())


def _deduplicate_trends(trends: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen_urls = set()
    seen_titles = set()
    unique_trends = []

    for trend in trends:
        url = trend.get("url", "") or trend.get("source_url", "")
        title = (trend.get("title") or "").strip().lower()

        if url and url in seen_urls:
            continue
        if title and title in seen_titles:
            continue

        unique_trends.append(trend)
        if url:
            seen_urls.add(url)
        if title:
            seen_titles.add(title)

    return unique_trends


def _match_trends(
    trends: Iterable[Dict[str, Any]],
    keywords: List[str],
    phrases: List[str],
) -> List[Dict[str, Any]]:
    # If no keywords or phrases provided, return all trends sorted by relevance
    if not keywords and not phrases:
        all_trends = list(trends)
        for trend in all_trends:
            trend["match_score"] = trend.get("relevance_score", 0)
            trend["matched_terms"] = []
            trend["match_fields"] = {}
        all_trends.sort(key=lambda t: t.get("relevance_score", 0), reverse=True)
        return all_trends

    matched = []
    for trend in trends:
        match_terms, match_fields = _match_terms(trend, keywords, phrases)
        if not match_terms:
            continue
        match_score = _calculate_match_score(trend, match_terms, keywords, phrases)
        trend["match_score"] = match_score
        trend["matched_terms"] = match_terms
        trend["match_fields"] = match_fields
        matched.append(trend)

    matched.sort(
        key=lambda t: (t.get("match_score", 0), t.get("relevance_score", 0)),
        reverse=True,
    )
    return matched


def _match_terms(
    trend: Dict[str, Any],
    keywords: List[str],
    phrases: List[str],
) -> Tuple[List[str], Dict[str, str]]:
    title = (trend.get("title") or "").lower()
    description = (trend.get("description") or "").lower()

    matched_terms: List[str] = []
    match_fields: Dict[str, str] = {}

    def record_match(term: str, in_title: bool, in_desc: bool) -> None:
        if in_title and in_desc:
            match_fields[term] = "both"
        elif in_title:
            match_fields[term] = "title"
        elif in_desc:
            match_fields[term] = "description"
        matched_terms.append(term)

    for phrase in phrases:
        in_title = phrase in title
        in_desc = phrase in description
        if in_title or in_desc:
            record_match(phrase, in_title, in_desc)

    for keyword in keywords:
        if _is_plain_word(keyword):
            pattern = re.compile(rf"\\b{re.escape(keyword)}\\b")
            in_title = bool(pattern.search(title))
            in_desc = bool(pattern.search(description))
        else:
            in_title = keyword in title
            in_desc = keyword in description
        if in_title or in_desc:
            record_match(keyword, in_title, in_desc)

    return matched_terms, match_fields


def _calculate_match_score(
    trend: Dict[str, Any],
    matched_terms: List[str],
    keywords: List[str],
    phrases: List[str],
) -> float:
    base = float(trend.get("relevance_score") or 0.0)
    matched_phrases = [t for t in matched_terms if t in phrases]
    matched_keywords = [t for t in matched_terms if t in keywords]

    phrase_bonus = min(len(matched_phrases) * 0.2, 0.6)
    keyword_bonus = min(len(matched_keywords) * 0.05, 0.2)
    recency_bonus = 0.0

    published_at = trend.get("published_at")
    if isinstance(published_at, str):
        published_at = _parse_datetime(published_at)
    if isinstance(published_at, datetime):
        if datetime.utcnow() - published_at <= timedelta(hours=48):
            recency_bonus = 0.1

    score = min(base + phrase_bonus + keyword_bonus + recency_bonus, 1.0)
    return round(score, 4)


def _parse_datetime(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def _is_plain_word(term: str) -> bool:
    return bool(re.fullmatch(r"[a-z0-9]+", term))


def _persist_results(query_run_id: int, trends: List[Dict[str, Any]]) -> None:
    db = get_db()
    rank = 1
    for trend in trends:
        trend_id = _ensure_trend(trend)
        if not trend_id:
            continue

        db.add_query_run_trend(
            query_run_id=query_run_id,
            trend_id=trend_id,
            match_score=trend.get("match_score", 0.0),
            matched_terms_json=json.dumps(trend.get("matched_terms", [])),
            match_fields_json=json.dumps(trend.get("match_fields", {})),
            rank=rank,
        )
        rank += 1


def _ensure_trend(trend: Dict[str, Any]) -> int | None:
    db = get_db()
    source_url = trend.get("url") or trend.get("source_url") or ""
    if source_url:
        existing = db.get_trend_by_url(source_url)
        if existing:
            return int(existing["id"])

    category = _normalize_category(trend.get("category"))
    source_name = trend.get("source_name") or _extract_source_name(trend)

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
        return db.create_trend(trend_model)
    except Exception as exc:
        logger.error(f"Failed to save trend: {exc}")
        return None


def _normalize_category(category_value: Any) -> TrendCategory:
    if isinstance(category_value, TrendCategory):
        return category_value
    if isinstance(category_value, str):
        normalized = category_value.strip().lower()
        if normalized == "tech":
            return TrendCategory.GENERAL_TECH
        try:
            return TrendCategory(normalized)
        except Exception:
            return TrendCategory.OTHER
    return TrendCategory.OTHER


def _extract_source_name(trend: Dict[str, Any]) -> str:
    metadata = trend.get("metadata", {}) or {}
    return (
        trend.get("source_name")
        or metadata.get("feed_name")
        or metadata.get("repo_name")
        or "Unknown Source"
    )
