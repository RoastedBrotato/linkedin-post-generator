"""
Validation helpers for generated LinkedIn posts.
"""

from typing import List, Optional

from config.settings import get_settings


def validate_post_components(
    content: str,
    hashtags: List[str],
    source_url: str,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    max_hashtags: Optional[int] = None,
    include_citations: Optional[bool] = None,
) -> List[str]:
    """Validate post content, hashtags, and citations."""
    settings = get_settings()
    errors: List[str] = []

    content = (content or "").strip()
    if not content:
        errors.append("Post content is empty.")
        return errors

    min_len = min_length if min_length is not None else settings.post_generation.min_length
    max_len = max_length if max_length is not None else settings.post_generation.max_length
    max_tags = max_hashtags if max_hashtags is not None else settings.post_generation.max_hashtags
    require_citations = (
        include_citations
        if include_citations is not None
        else settings.post_generation.include_citations
    )

    if len(content) < min_len:
        errors.append(f"Post content is too short ({len(content)} < {min_len}).")

    if len(content) > max_len:
        errors.append(f"Post content is too long ({len(content)} > {max_len}).")

    if max_tags is not None and len(hashtags) > max_tags:
        errors.append(
            f"Too many hashtags ({len(hashtags)} > {max_tags})."
        )

    for tag in hashtags:
        if not tag.startswith("#"):
            errors.append(f"Invalid hashtag format: {tag}")

    if require_citations:
        if not source_url:
            errors.append("Missing source URL for citation.")
        elif source_url not in content:
            errors.append("Source URL not included in post content.")

    return errors


def normalize_hashtags(hashtags: List[str], max_hashtags: Optional[int] = None) -> List[str]:
    """Normalize and deduplicate hashtags."""
    settings = get_settings()
    max_tags = max_hashtags if max_hashtags is not None else settings.post_generation.max_hashtags

    cleaned = []
    seen = set()
    for tag in hashtags:
        tag = tag.strip()
        if not tag:
            continue
        if not tag.startswith("#"):
            tag = f"#{tag}"
        if tag.lower() in seen:
            continue
        seen.add(tag.lower())
        cleaned.append(tag)

    if max_tags is not None:
        cleaned = cleaned[:max_tags]

    return cleaned
