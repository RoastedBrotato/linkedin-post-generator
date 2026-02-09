"""
FastAPI app scaffolding for the web UI.
"""

import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from src.database import get_db
from src.api.query_runner import enqueue_query_run
from src.llm import LLMClient
from src.linkedin_api import LinkedInAPI
from src.linkedin_engagement import LinkedInEngagementClient
from src.logger import logger
from src.scheduler import get_scheduler, start_scheduler, stop_scheduler
from src.post_templates import get_all_format_options

try:
    from PIL import Image
except ImportError:
    Image = None

_POST_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_ENGAGE_EXECUTOR = ThreadPoolExecutor(max_workers=1)

app = FastAPI(title="LinkedIn Post Generator API")

# Start scheduler on startup
@app.on_event("startup")
async def startup_event():
    """Start the post scheduler when API starts"""
    try:
        start_scheduler()
        logger.info("Post scheduler started")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the scheduler when API shuts down"""
    try:
        stop_scheduler()
        logger.info("Post scheduler stopped")
    except Exception as e:
        logger.error(f"Failed to stop scheduler: {e}")

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


class EngagementRunCreate(BaseModel):
    """Payload for creating an engagement run."""
    keywords: List[str] = Field(default_factory=list)
    influencers: List[str] = Field(default_factory=list)
    max_targets: int = Field(default=3, ge=1, le=10)


class EngagementRunResponse(BaseModel):
    id: int
    status: str
    sources: Dict[str, Any]
    options: Dict[str, Any]
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class EngagementTargetResponse(BaseModel):
    id: int
    run_id: int
    post_url: str
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    post_text: Optional[str] = None
    source: Optional[str] = None
    status: str
    scraped_at: str
    created_at: str


class EngagementCommentResponse(BaseModel):
    id: int
    target_id: int
    content: str
    status: str
    generated_at: str
    approved_at: Optional[str] = None
    posted_at: Optional[str] = None
    post_url: Optional[str] = None
    author_name: Optional[str] = None
    author_url: Optional[str] = None
    post_text: Optional[str] = None
    error_message: Optional[str] = None


class EngagementCommentUpdate(BaseModel):
    content: Optional[str] = None
    status: Optional[str] = None


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


def _parse_engagement_run(row: Dict[str, Any]) -> EngagementRunResponse:
    return EngagementRunResponse(
        id=row["id"],
        status=row["status"],
        sources=json.loads(row.get("sources_json") or "{}"),
        options=json.loads(row.get("options_json") or "{}"),
        created_at=str(row["created_at"]),
        completed_at=str(row["completed_at"]) if row.get("completed_at") else None,
        error_message=row.get("error_message"),
    )


def _parse_engagement_target(row: Dict[str, Any]) -> EngagementTargetResponse:
    return EngagementTargetResponse(
        id=row["id"],
        run_id=row["run_id"],
        post_url=row["post_url"],
        author_name=row.get("author_name"),
        author_url=row.get("author_url"),
        post_text=row.get("post_text"),
        source=row.get("source"),
        status=row["status"],
        scraped_at=str(row["scraped_at"]),
        created_at=str(row["created_at"]),
    )


def _parse_engagement_comment(row: Dict[str, Any]) -> EngagementCommentResponse:
    return EngagementCommentResponse(
        id=row["id"],
        target_id=row["target_id"],
        content=row["content"],
        status=row["status"],
        generated_at=str(row["generated_at"]),
        approved_at=str(row["approved_at"]) if row.get("approved_at") else None,
        posted_at=str(row["posted_at"]) if row.get("posted_at") else None,
        post_url=row.get("post_url"),
        author_name=row.get("author_name"),
        author_url=row.get("author_url"),
        post_text=row.get("post_text"),
        error_message=row.get("error_message"),
    )


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    """Simple health endpoint."""
    return {"status": "ok"}


@app.get("/api/images/{filename}")
def get_image(filename: str):
    """Serve uploaded images."""
    image_path = os.path.join("data", "images", filename)

    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")

    # Security check: ensure the path is within the images directory
    abs_image_path = os.path.abspath(image_path)
    abs_images_dir = os.path.abspath(os.path.join("data", "images"))

    if not abs_image_path.startswith(abs_images_dir):
        raise HTTPException(status_code=403, detail="Access denied")

    return FileResponse(image_path)


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


@app.get("/api/post-formats")
def list_post_formats() -> Dict[str, Any]:
    """List available post formats/templates."""
    return {
        "formats": get_all_format_options()
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
    post_format: str = Field(default="standard", description="Post format/template to use")


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

        result = llm.generate_post(trend=trend_dict, post_format=payload.post_format)
        if not result:
            raise HTTPException(
                status_code=502,
                detail="LLM failed to generate a post. Check LLM logs/health and try again."
            )

        # Create post in database
        post_id = db.create_post_from_dict(
            content=result["content"],
            hashtags=" ".join(result.get("hashtags", [])),
            trend_id=payload.trend_id,
            status="pending",
            post_format=payload.post_format
        )

        row = db.get_post_with_trend(post_id)
        if not row:
            raise HTTPException(status_code=500, detail="Failed to create post")

        return _parse_post(row)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate post: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate post: {str(e)}")


@app.get("/api/posts", response_model=List[PostResponse])
def list_posts(status: Optional[str] = None, limit: int = 50) -> List[PostResponse]:
    """List posts, optionally filtered by status."""
    db = get_db()
    posts = db.list_posts(status=status, limit=limit)
    return [_parse_post(post) for post in posts]


def _run_engagement(run_id: int, payload: EngagementRunCreate) -> None:
    db = get_db()
    try:
        db.update_engagement_run(run_id, status="running")
        client = LinkedInEngagementClient()

        targets = client.fetch_targets(
            keywords=payload.keywords,
            influencers=payload.influencers,
            limit=payload.max_targets,
        )

        for target in targets:
            target_id = db.create_engagement_target(
                run_id=run_id,
                post_url=target.post_url,
                author_name=target.author_name,
                author_url=target.author_url,
                post_text=target.post_text,
                source=target.source,
                status="pending",
            )

            comment = client.generate_comment(target.post_text or "")
            if comment:
                db.create_engagement_comment(
                    target_id=target_id,
                    content=comment,
                    status="draft",
                )
            else:
                db.update_engagement_target(target_id, status="skipped")

        db.update_engagement_run(run_id, status="complete", completed_at=datetime.utcnow())
    except Exception as exc:
        logger.error(f"Engagement run failed: {exc}")
        db.update_engagement_run(
            run_id,
            status="failed",
            error_message=str(exc),
            completed_at=datetime.utcnow(),
        )


@app.post("/api/engagement/runs", response_model=EngagementRunResponse)
def create_engagement_run(payload: EngagementRunCreate) -> EngagementRunResponse:
    """Start an engagement run to scrape trending posts and draft comments."""
    from config.settings import get_settings

    settings = get_settings().engagement
    if not settings.enabled:
        raise HTTPException(
            status_code=400,
            detail="Engagement is disabled. Set ENGAGE_ENABLED=true and configure cookies.",
        )

    keywords = payload.keywords or settings.keywords
    influencers = payload.influencers or settings.influencers

    if not keywords and not influencers:
        raise HTTPException(
            status_code=400,
            detail="Provide keywords or influencers to search for engagement targets.",
        )

    run_id = get_db().create_engagement_run(
        sources_json=json.dumps({"keywords": keywords, "influencers": influencers}),
        options_json=json.dumps({"max_targets": payload.max_targets}),
        status="queued",
    )

    _ENGAGE_EXECUTOR.submit(
        _run_engagement,
        run_id,
        EngagementRunCreate(
            keywords=keywords,
            influencers=influencers,
            max_targets=payload.max_targets,
        ),
    )

    row = get_db().get_engagement_run(run_id)
    if not row:
        raise HTTPException(status_code=500, detail="Failed to create engagement run.")
    return _parse_engagement_run(row)


@app.get("/api/engagement/runs/{run_id}", response_model=EngagementRunResponse)
def get_engagement_run(run_id: int) -> EngagementRunResponse:
    row = get_db().get_engagement_run(run_id)
    if not row:
        raise HTTPException(status_code=404, detail="Engagement run not found")
    return _parse_engagement_run(row)


@app.get("/api/engagement/targets", response_model=List[EngagementTargetResponse])
def list_engagement_targets(status: Optional[str] = None, limit: int = 50) -> List[EngagementTargetResponse]:
    rows = get_db().list_engagement_targets(status=status, limit=limit)
    return [_parse_engagement_target(row) for row in rows]


@app.get("/api/engagement/comments", response_model=List[EngagementCommentResponse])
def list_engagement_comments(status: Optional[str] = None, limit: int = 50) -> List[EngagementCommentResponse]:
    rows = get_db().list_engagement_comments(status=status, limit=limit)
    return [_parse_engagement_comment(row) for row in rows]


@app.patch("/api/engagement/comments/{comment_id}", response_model=EngagementCommentResponse)
def update_engagement_comment(comment_id: int, payload: EngagementCommentUpdate) -> EngagementCommentResponse:
    db = get_db()
    row = db.get_engagement_comment(comment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Engagement comment not found")

    updates: Dict[str, Any] = {}
    if payload.content is not None:
        updates["content"] = payload.content.strip()
    if payload.status is not None:
        updates["status"] = payload.status
        if payload.status == "approved":
            updates["approved_at"] = datetime.utcnow()
        if payload.status == "rejected":
            updates["approved_at"] = None

    if updates:
        db.update_engagement_comment(comment_id, **updates)

    updated = db.get_engagement_comment(comment_id)
    return _parse_engagement_comment(updated)


@app.post("/api/engagement/comments/{comment_id}/post", response_model=EngagementCommentResponse)
def post_engagement_comment(comment_id: int) -> EngagementCommentResponse:
    db = get_db()
    row = db.get_engagement_comment(comment_id)
    if not row:
        raise HTTPException(status_code=404, detail="Engagement comment not found")

    if row["status"] != "approved":
        raise HTTPException(status_code=400, detail="Comment must be approved before posting")

    client = LinkedInEngagementClient()
    try:
        client.post_comment(row["post_url"], row["content"])
        db.update_engagement_comment(
            comment_id,
            status="posted",
            posted_at=datetime.utcnow(),
            error_message=None,
        )
        db.update_engagement_target(row["target_id"], status="commented")
    except Exception as exc:
        db.update_engagement_comment(comment_id, error_message=str(exc))
        raise HTTPException(status_code=500, detail=f"Failed to post comment: {str(exc)}")

    updated = db.get_engagement_comment(comment_id)
    return _parse_engagement_comment(updated)


class BatchPostCreate(BaseModel):
    """Payload for batch post generation."""
    trend_ids: List[int] = Field(..., description="List of trend IDs to generate posts from")
    post_formats: Optional[List[str]] = Field(default=None, description="List of post formats (optional, one per trend)")
    default_format: str = Field(default="standard", description="Default format if formats list not provided")


@app.post("/api/posts/batch")
def create_batch_posts(payload: BatchPostCreate) -> Dict[str, Any]:
    """Generate multiple posts at once from trends."""
    db = get_db()
    llm = LLMClient()

    if not payload.trend_ids:
        raise HTTPException(status_code=400, detail="No trend IDs provided")

    # If formats provided, validate length matches trends
    formats = payload.post_formats
    if formats and len(formats) != len(payload.trend_ids):
        raise HTTPException(
            status_code=400,
            detail=f"Number of formats ({len(formats)}) must match number of trends ({len(payload.trend_ids)})"
        )

    results = {
        "success": [],
        "failed": [],
        "total": len(payload.trend_ids)
    }

    for idx, trend_id in enumerate(payload.trend_ids):
        try:
            # Get the trend
            trend = db.get_trend_by_id(trend_id)
            if not trend:
                results["failed"].append({
                    "trend_id": trend_id,
                    "error": "Trend not found"
                })
                continue

            # Determine post format
            post_format = formats[idx] if formats else payload.default_format

            logger.info(f"Generating {post_format} post for trend: {trend['title']}")

            # Prepare trend dict
            trend_dict = {
                "title": trend["title"],
                "description": trend.get("description", ""),
                "url": trend.get("source_url", ""),
                "source_name": trend.get("source_name", ""),
                "category": trend.get("category", ""),
                "relevance_score": trend.get("relevance_score", 0.0),
            }

            # Generate post
            result = llm.generate_post(trend=trend_dict, post_format=post_format)

            if not result:
                results["failed"].append({
                    "trend_id": trend_id,
                    "error": "Failed to generate post"
                })
                continue

            # Create post in database
            post_id = db.create_post_from_dict(
                content=result["content"],
                hashtags=" ".join(result.get("hashtags", [])),
                trend_id=trend_id,
                status="pending",
                post_format=post_format
            )

            results["success"].append({
                "trend_id": trend_id,
                "post_id": post_id,
                "post_format": post_format,
                "title": trend["title"]
            })

        except Exception as e:
            logger.error(f"Failed to generate post for trend {trend_id}: {e}")
            results["failed"].append({
                "trend_id": trend_id,
                "error": str(e)
            })

    return {
        "results": results,
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "total_count": results["total"]
    }


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


class BulkApproveRequest(BaseModel):
    """Request to approve multiple posts"""
    post_ids: List[int] = Field(..., description="List of post IDs to approve")


@app.post("/api/posts/bulk-approve")
def bulk_approve_posts(request: BulkApproveRequest) -> Dict[str, Any]:
    """Approve multiple posts at once."""
    db = get_db()

    results = {
        "success": [],
        "failed": [],
        "total": len(request.post_ids)
    }

    for post_id in request.post_ids:
        try:
            post = db.get_post_with_trend(post_id)
            if not post:
                results["failed"].append({
                    "post_id": post_id,
                    "error": "Post not found"
                })
                continue

            if post["status"] == "published":
                results["failed"].append({
                    "post_id": post_id,
                    "error": "Post is already published"
                })
                continue

            db.update_post_status(post_id, "approved")
            results["success"].append(post_id)

        except Exception as e:
            logger.error(f"Failed to approve post {post_id}: {e}")
            results["failed"].append({
                "post_id": post_id,
                "error": str(e)
            })

    return {
        "results": results,
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "total_count": results["total"]
    }


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


@app.post("/api/posts/{post_id}/upload-image")
def upload_post_image(post_id: int, file: UploadFile = File(...)) -> Dict[str, Any]:
    """Upload an image to attach to a post."""
    db = get_db()

    # Verify post exists
    post = db.get_post_with_trend(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Validate file type
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_types)}"
        )

    # Read file content
    try:
        file_content = file.file.read()
        file_size = len(file_content)

        # Validate file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {max_size / 1024 / 1024}MB"
            )

        # Validate it's a valid image and get dimensions
        if Image:
            try:
                from io import BytesIO
                img = Image.open(BytesIO(file_content))
                width, height = img.size
                img.close()
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid image file: {str(e)}")
        else:
            width, height = None, None

        # Create images directory if it doesn't exist
        images_dir = os.path.join("data", "images")
        os.makedirs(images_dir, exist_ok=True)

        # Generate unique filename
        import hashlib
        file_hash = hashlib.md5(file_content).hexdigest()
        file_ext = os.path.splitext(file.filename)[1] or ".jpg"
        filename = f"{post_id}_{file_hash}{file_ext}"
        file_path = os.path.join(images_dir, filename)

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        # Update post with image path
        with db.get_connection() as conn:
            conn.execute("""
                UPDATE posts
                SET image_path = ?,
                    updated_at = ?
                WHERE id = ?
            """, (file_path, datetime.utcnow(), post_id))

            # Insert into post_images table
            conn.execute("""
                INSERT INTO post_images
                (post_id, image_path, width, height, file_size, mime_type)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (post_id, file_path, width, height, file_size, file.content_type))

        logger.info(f"Image uploaded for post {post_id}: {file_path}")

        return {
            "success": True,
            "post_id": post_id,
            "image_path": file_path,
            "filename": filename,
            "size": file_size,
            "dimensions": {"width": width, "height": height} if width and height else None
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to upload image for post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to upload image: {str(e)}")
    finally:
        file.file.close()


@app.delete("/api/posts/{post_id}/image")
def delete_post_image(post_id: int) -> Dict[str, Any]:
    """Delete the image attached to a post."""
    db = get_db()

    # Verify post exists
    post = db.get_post_with_trend(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    image_path = post.get("image_path")
    if not image_path:
        raise HTTPException(status_code=404, detail="Post has no image attached")

    try:
        # Delete physical file
        if os.path.exists(image_path):
            os.remove(image_path)
            logger.info(f"Deleted image file: {image_path}")

        # Update database
        with db.get_connection() as conn:
            conn.execute("""
                UPDATE posts
                SET image_path = NULL,
                    image_url = NULL,
                    updated_at = ?
                WHERE id = ?
            """, (datetime.utcnow(), post_id))

            # Delete from post_images table
            conn.execute("""
                DELETE FROM post_images
                WHERE post_id = ? AND image_path = ?
            """, (post_id, image_path))

        return {
            "success": True,
            "post_id": post_id,
            "message": "Image deleted successfully"
        }

    except Exception as e:
        logger.error(f"Failed to delete image for post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete image: {str(e)}")


# ============================================
# Post Scheduling Endpoints
# ============================================

class SchedulePostRequest(BaseModel):
    """Request to schedule a post"""
    scheduled_time: str = Field(..., description="ISO format datetime (e.g., 2026-01-25T14:30:00)")


@app.post("/api/posts/{post_id}/schedule")
def schedule_post(post_id: int, request: SchedulePostRequest) -> Dict[str, Any]:
    """Schedule a post for future publishing"""
    try:
        # Parse the scheduled time
        scheduled_time = datetime.fromisoformat(request.scheduled_time)

        # Verify post exists and is approved
        db = get_db()
        post = db.get_post_with_trend(post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if post["status"] != "approved":
            raise HTTPException(
                status_code=400,
                detail=f"Post must be approved before scheduling (current status: {post['status']})"
            )

        # Schedule the post
        scheduler = get_scheduler()
        success = scheduler.schedule_post(post_id, scheduled_time)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to schedule post")

        return {
            "success": True,
            "post_id": post_id,
            "scheduled_for": scheduled_time.isoformat(),
            "message": "Post scheduled successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid datetime format: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to schedule post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to schedule: {str(e)}")


@app.delete("/api/posts/{post_id}/schedule")
def unschedule_post(post_id: int) -> Dict[str, Any]:
    """Cancel a scheduled post"""
    try:
        scheduler = get_scheduler()
        success = scheduler.unschedule_post(post_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to unschedule post")

        return {
            "success": True,
            "post_id": post_id,
            "message": "Post unscheduled successfully"
        }

    except Exception as e:
        logger.error(f"Failed to unschedule post {post_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to unschedule: {str(e)}")


@app.get("/api/scheduled-posts")
def get_scheduled_posts(days_ahead: int = 30) -> Dict[str, Any]:
    """Get all scheduled posts"""
    try:
        scheduler = get_scheduler()
        posts = scheduler.get_scheduled_posts(days_ahead=days_ahead)

        return {
            "scheduled_posts": posts,
            "count": len(posts)
        }

    except Exception as e:
        logger.error(f"Failed to get scheduled posts: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get scheduled posts: {str(e)}")


class BulkScheduleRequest(BaseModel):
    """Request to schedule multiple posts"""
    post_ids: List[int] = Field(..., description="List of post IDs to schedule")
    scheduled_times: List[str] = Field(..., description="List of ISO format datetimes for each post")


@app.post("/api/posts/bulk-schedule")
def bulk_schedule_posts(request: BulkScheduleRequest) -> Dict[str, Any]:
    """Schedule multiple posts at once."""
    if len(request.post_ids) != len(request.scheduled_times):
        raise HTTPException(
            status_code=400,
            detail=f"Number of post_ids ({len(request.post_ids)}) must match number of scheduled_times ({len(request.scheduled_times)})"
        )

    db = get_db()
    scheduler = get_scheduler()

    results = {
        "success": [],
        "failed": [],
        "total": len(request.post_ids)
    }

    for post_id, scheduled_time_str in zip(request.post_ids, request.scheduled_times):
        try:
            # Parse scheduled time
            scheduled_time = datetime.fromisoformat(scheduled_time_str)

            # Verify post exists and is approved
            post = db.get_post_with_trend(post_id)
            if not post:
                results["failed"].append({
                    "post_id": post_id,
                    "error": "Post not found"
                })
                continue

            if post["status"] != "approved":
                results["failed"].append({
                    "post_id": post_id,
                    "error": f"Post must be approved before scheduling (current status: {post['status']})"
                })
                continue

            # Schedule the post
            success = scheduler.schedule_post(post_id, scheduled_time)

            if not success:
                results["failed"].append({
                    "post_id": post_id,
                    "error": "Failed to schedule post"
                })
                continue

            results["success"].append({
                "post_id": post_id,
                "scheduled_for": scheduled_time.isoformat()
            })

        except ValueError as e:
            results["failed"].append({
                "post_id": post_id,
                "error": f"Invalid datetime format: {str(e)}"
            })
        except Exception as e:
            logger.error(f"Failed to schedule post {post_id}: {e}")
            results["failed"].append({
                "post_id": post_id,
                "error": str(e)
            })

    return {
        "results": results,
        "success_count": len(results["success"]),
        "failed_count": len(results["failed"]),
        "total_count": results["total"]
    }
