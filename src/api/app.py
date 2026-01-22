"""
FastAPI app scaffolding for the web UI.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.database import get_db
from src.api.query_runner import enqueue_query_run
from src.llm import LLMClient
from src.linkedin_api import LinkedInAPI
from src.logger import logger

_POST_EXECUTOR = ThreadPoolExecutor(max_workers=2)

app = FastAPI(title="LinkedIn Post Generator API")

raw_origins = os.getenv("WEB_UI_ORIGINS", "")
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

# Allow common local dev origins if not explicitly configured.
if not allowed_origins:
    allowed_origins = [
        "http://localhost:4321",
        "http://127.0.0.1:4321",
        "http://localhost:4322",
        "http://127.0.0.1:4322",
        "http://localhost:3000",
    ]
    # Accept any localhost port in dev to avoid CORS mismatches.
    allowed_origin_regex = r"https?://(localhost|127\.0\.0\.1)(:\\d+)?"
else:
    allowed_origin_regex = None

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRunCreate(BaseModel):
    """Payload for creating a query run."""
    keywords: str = Field(default="", max_length=2000)
    phrases: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)
    options: Dict[str, Any] = Field(default_factory=dict)


class QueryRunResponse(BaseModel):
    """Response for creating or fetching a query run."""
    id: int
    status: str
    keywords_raw: str
    phrases: List[str]
    sources: List[str]
    options: Dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


def _parse_query_run(row: Dict[str, Any]) -> QueryRunResponse:
    """Convert DB row to API response payload."""
    return QueryRunResponse(
        id=row["id"],
        status=row["status"],
        keywords_raw=row["keywords_raw"],
        phrases=json.loads(row.get("phrases_raw") or "[]"),
        sources=json.loads(row.get("sources_json") or "[]"),
        options=json.loads(row.get("options_json") or "{}"),
        created_at=str(row["created_at"]),
        completed_at=str(row["completed_at"]) if row.get("completed_at") else None,
        error_message=row.get("error_message"),
    )


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    """Simple health endpoint."""
    return {"status": "ok"}


@app.get("/api/sources")
def list_sources() -> Dict[str, Any]:
    """List available sources and their options."""
    return {
        "sources": [
            {
                "id": "hackernews",
                "name": "Hacker News",
                "options": {
                    "min_score": {"type": "int", "default": 100},
                    "max_items": {"type": "int", "default": 30},
                },
            },
            {
                "id": "rss",
                "name": "RSS Feeds",
                "options": {
                    "feeds": {"type": "list", "default": []},
                    "max_items_per_feed": {"type": "int", "default": 10},
                },
            },
            {
                "id": "github",
                "name": "GitHub Trending",
                "options": {
                    "timeframe": {"type": "enum", "default": "daily"},
                    "max_items": {"type": "int", "default": 30},
                    "min_stars_today": {"type": "int", "default": 25},
                },
            },
        ]
    }


@app.post("/api/query-runs", response_model=QueryRunResponse)
def create_query_run(payload: QueryRunCreate) -> QueryRunResponse:
    """Create a query run (execution handled later)."""
    db = get_db()
    run_id = db.create_query_run(
        keywords_raw=payload.keywords,
        phrases_raw=json.dumps(payload.phrases),
        sources_json=json.dumps(payload.sources),
        options_json=json.dumps(payload.options),
        status="queued",
    )
    row = db.get_query_run(run_id)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create query run.")
    enqueue_query_run(run_id)
    return _parse_query_run(row)


@app.get("/api/query-runs/{query_run_id}", response_model=QueryRunResponse)
def get_query_run(query_run_id: int) -> QueryRunResponse:
    """Fetch a query run by ID."""
    db = get_db()
    row = db.get_query_run(query_run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Query run not found.")
    return _parse_query_run(row)


@app.get("/api/query-runs/{query_run_id}/results")
def get_query_run_results(query_run_id: int) -> Dict[str, Any]:
    """Fetch query run results."""
    db = get_db()
    row = db.get_query_run(query_run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Query run not found.")
    results = db.get_query_run_results(query_run_id)
    parsed_results = []
    for result in results:
        result["matched_terms"] = json.loads(result.get("matched_terms_json") or "[]")
        result["match_fields"] = json.loads(result.get("match_fields_json") or "{}")
        parsed_results.append(result)
    return {"query_run_id": query_run_id, "results": parsed_results}


@app.get("/api/query-runs")
def list_query_runs(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    """List recent query runs."""
    db = get_db()
    rows = db.list_query_runs(limit=limit, offset=offset)
    return {"results": [_parse_query_run(row) for row in rows]}


# ============================================
# Post Management Endpoints
# ============================================

class PostCreate(BaseModel):
    """Payload for creating a post from a trend."""
    trend_id: int = Field(..., description="Trend ID to generate post from")


class PostUpdate(BaseModel):
    """Payload for updating a post."""
    content: str = Field(..., min_length=1, max_length=5000)
    hashtags: Optional[str] = None


class PostResponse(BaseModel):
    """Response for post operations."""
    id: int
    content: str
    hashtags: Optional[str] = None
    status: str
    trend_id: int
    trend_title: Optional[str] = None
    trend_url: Optional[str] = None
    created_at: str
    published_at: Optional[str] = None
    platform_post_id: Optional[str] = None
    post_url: Optional[str] = None


def _parse_post(row: Dict[str, Any]) -> PostResponse:
    """Convert DB row to post API response."""
    return PostResponse(
        id=row["id"],
        content=row["content"],
        hashtags=row.get("hashtags"),
        status=row["status"],
        trend_id=row["trend_id"],
        trend_title=row.get("trend_title"),
        trend_url=row.get("trend_url"),
        created_at=str(row["created_at"]),
        published_at=str(row["published_at"]) if row.get("published_at") else None,
        platform_post_id=row.get("platform_post_id"),
        post_url=row.get("post_url"),
    )


@app.post("/api/posts", response_model=PostResponse)
def create_post(payload: PostCreate) -> PostResponse:
    """Generate a post from a trend."""
    db = get_db()

    # Get the trend
    trend = db.get_trend_by_id(payload.trend_id)
    if not trend:
        raise HTTPException(status_code=404, detail="Trend not found")

    # Generate post using LLM
    try:
        llm = LLMClient()
        logger.info(f"Generating post for trend: {trend['title']}")

        # Prepare trend dict with required fields
        trend_dict = {
            "title": trend["title"],
            "description": trend.get("description", ""),
            "url": trend.get("source_url", ""),
            "source_name": trend.get("source_name", ""),
            "category": trend.get("category", ""),
            "relevance_score": trend.get("relevance_score", 0.0),
        }

        result = llm.generate_post(trend=trend_dict)

        # Create post in database
        post_id = db.create_post_from_dict(
            content=result["content"],
            hashtags=" ".join(result.get("hashtags", [])),
            trend_id=payload.trend_id,
            status="pending"
        )

        row = db.get_post_with_trend(post_id)
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create post")

        return _parse_post(row)

    except Exception as e:
        logger.error(f"Failed to generate post: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate post: {str(e)}")


@app.get("/api/posts", response_model=List[PostResponse])
def list_posts(status: Optional[str] = None, limit: int = 50) -> List[PostResponse]:
    """List posts, optionally filtered by status."""
    db = get_db()
    posts = db.list_posts(status=status, limit=limit)
    return [_parse_post(post) for post in posts]


@app.get("/api/posts/{post_id}", response_model=PostResponse)
def get_post(post_id: int) -> PostResponse:
    """Get a single post by ID."""
    db = get_db()
    post = db.get_post_with_trend(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _parse_post(post)


@app.put("/api/posts/{post_id}", response_model=PostResponse)
def update_post(post_id: int, payload: PostUpdate) -> PostResponse:
    """Update a post's content and hashtags."""
    db = get_db()

    # Check if post exists
    post = db.get_post_with_trend(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Don't allow editing published posts
    if post["status"] == "published":
        raise HTTPException(status_code=400, detail="Cannot edit published posts")

    # Update the post
    db.update_post(
        post_id=post_id,
        content=payload.content,
        hashtags=payload.hashtags,
        updated_at=datetime.utcnow()
    )

    updated_post = db.get_post_with_trend(post_id)
    if not updated_post:
        raise HTTPException(status_code=500, detail="Failed to update post")

    return _parse_post(updated_post)


@app.post("/api/posts/{post_id}/approve", response_model=PostResponse)
def approve_post(post_id: int) -> PostResponse:
    """Approve a post for publishing."""
    db = get_db()

    post = db.get_post_with_trend(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post["status"] == "published":
        raise HTTPException(status_code=400, detail="Post is already published")

    db.update_post_status(post_id, "approved")

    updated_post = db.get_post_with_trend(post_id)
    return _parse_post(updated_post)


@app.post("/api/posts/{post_id}/publish")
def publish_post(post_id: int) -> Dict[str, Any]:
    """Publish a post to LinkedIn."""
    db = get_db()

    post = db.get_post_with_trend(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post["status"] == "published":
        raise HTTPException(status_code=400, detail="Post is already published")

    # Publish to LinkedIn
    try:
        api = LinkedInAPI(db=db)

        # Ensure token is valid
        if not api.ensure_valid_token():
            raise HTTPException(
                status_code=401,
                detail="LinkedIn authentication required. Please run OAuth flow."
            )

        # Prepare post content (combine content and hashtags)
        post_text = post["content"]
        if post.get("hashtags"):
            post_text += f"\n\n{post['hashtags']}"

        # Publish the post
        result = api.publish_post(text=post_text, post_id=post_id)

        if result:
            return {
                "success": True,
                "post_id": post_id,
                "platform_post_id": result.get("linkedin_post_id"),
                "post_url": result.get("post_url"),
                "message": "Post published successfully!"
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to publish post")

    except Exception as e:
        logger.error(f"Failed to publish post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to publish: {str(e)}")
