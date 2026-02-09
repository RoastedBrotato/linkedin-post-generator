"""
Application configuration using Pydantic for validation.

Loads settings from environment variables with sensible defaults.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, validator, HttpUrl
from dotenv import load_dotenv

# Load environment variables
load_dotenv(override=True)

# Base directory
BASE_DIR = Path(__file__).parent.parent


class LLMConfig(BaseModel):
    """LLM (Large Language Model) configuration"""

    provider: str = Field(
        default="ollama", description="LLM provider: ollama, openai, vllm, lmstudio"
    )
    api_url: str = Field(
        default="http://localhost:11434", description="LLM API endpoint URL"
    )
    model: str = Field(default="llama2", description="Model name to use")
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Sampling temperature"
    )
    max_tokens: int = Field(
        default=1000, ge=100, le=4000, description="Maximum tokens in response"
    )
    timeout: int = Field(default=120, ge=10, description="Request timeout in seconds")

    # OpenAI specific (fallback)
    openai_api_key: Optional[str] = Field(
        default=None, description="OpenAI API key (if using OpenAI)"
    )
    openai_model: str = Field(
        default="gpt-4", description="OpenAI model name (fallback)"
    )

    class Config:
        env_prefix = "LLM_"


class LinkedInConfig(BaseModel):
    """LinkedIn API configuration"""

    # OAuth 2.0 credentials
    client_id: Optional[str] = Field(default=None, description="LinkedIn OAuth client ID")
    client_secret: Optional[str] = Field(
        default=None, description="LinkedIn OAuth client secret"
    )
    redirect_uri: str = Field(
        default="http://localhost:8000/callback",
        description="OAuth redirect URI",
    )

    # Access tokens (stored after OAuth flow)
    access_token: Optional[str] = Field(
        default=None, description="LinkedIn access token"
    )
    refresh_token: Optional[str] = Field(
        default=None, description="LinkedIn refresh token"
    )
    token_expires_at: Optional[str] = Field(
        default=None, description="Token expiration timestamp (ISO format)"
    )
    user_urn: Optional[str] = Field(
        default=None, description="LinkedIn user URN (urn:li:person:XXXXX)"
    )

    # API settings
    api_version: str = Field(default="v2", description="LinkedIn API version")
    rate_limit_delay: int = Field(
        default=2, ge=1, description="Delay between API calls (seconds)"
    )

    class Config:
        env_prefix = "LINKEDIN_"


class TrendSourcesConfig(BaseModel):
    """Configuration for trend data sources"""

    # RSS Feeds
    rss_enabled: bool = Field(default=True, description="Enable RSS feeds")
    rss_feeds: List[str] = Field(
        default=[
            "https://techcrunch.com/feed/",
            "https://www.theverge.com/rss/index.xml",
            "https://feeds.arstechnica.com/arstechnica/technology-lab",
        ],
        description="RSS feed URLs to fetch",
    )
    rss_max_items_per_feed: int = Field(
        default=10, ge=1, le=50, description="Max items to fetch per RSS feed"
    )

    # Hacker News
    hackernews_enabled: bool = Field(default=True, description="Enable Hacker News")
    hackernews_min_score: int = Field(
        default=100, ge=0, description="Minimum HN post score"
    )
    hackernews_max_items: int = Field(
        default=30, ge=1, le=100, description="Max items to fetch from HN"
    )

    # Reddit
    reddit_enabled: bool = Field(default=True, description="Enable Reddit")
    reddit_client_id: Optional[str] = Field(default=None, description="Reddit API client ID")
    reddit_client_secret: Optional[str] = Field(
        default=None, description="Reddit API client secret"
    )
    reddit_user_agent: str = Field(
        default="LinkedInPostGenerator/1.0", description="Reddit API user agent"
    )
    reddit_subreddits: List[str] = Field(
        default=["MachineLearning", "artificial", "technology", "programming"],
        description="Subreddits to monitor",
    )
    reddit_min_score: int = Field(
        default=50, ge=0, description="Minimum Reddit post score"
    )
    reddit_max_items_per_subreddit: int = Field(
        default=10, ge=1, le=50, description="Max items to fetch per subreddit"
    )

    # GitHub Trending
    github_enabled: bool = Field(default=True, description="Enable GitHub trending")
    github_languages: List[str] = Field(
        default=["python", "javascript", "go", "rust"],
        description="Languages to track",
    )
    github_time_range: str = Field(
        default="daily", description="Time range: daily, weekly, monthly"
    )
    github_min_stars_today: int = Field(
        default=10, ge=0, description="Minimum stars gained today"
    )
    github_max_items: int = Field(
        default=20, ge=1, le=50, description="Max trending repos to fetch"
    )

    # arXiv
    arxiv_enabled: bool = Field(default=True, description="Enable arXiv papers")
    arxiv_categories: List[str] = Field(
        default=["cs.AI", "cs.LG", "cs.CL", "cs.CV"],
        description="arXiv categories to monitor",
    )
    arxiv_max_results: int = Field(
        default=20, ge=1, le=100, description="Max papers to fetch"
    )

    # Fetch intervals
    fetch_interval_hours: int = Field(
        default=6, ge=1, le=24, description="How often to fetch trends (hours)"
    )

    class Config:
        env_prefix = "TRENDS_"


class PostGenerationConfig(BaseModel):
    """Configuration for post generation"""

    min_length: int = Field(default=200, ge=50, description="Minimum post length (chars)")
    max_length: int = Field(
        default=3000, ge=100, le=3000, description="Maximum post length (chars)"
    )
    max_hashtags: int = Field(
        default=5, ge=0, le=10, description="Maximum number of hashtags"
    )
    include_citations: bool = Field(
        default=True, description="Include source citations in posts"
    )
    generation_interval_hours: int = Field(
        default=24, ge=1, description="How often to generate posts (hours)"
    )
    posts_per_batch: int = Field(
        default=3, ge=1, le=10, description="Posts to generate per batch"
    )
    min_trend_relevance: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score for trends",
    )

    class Config:
        env_prefix = "POST_"


class StorageConfig(BaseModel):
    """Storage and database configuration"""

    database_path: Path = Field(
        default=BASE_DIR / "data" / "database.db",
        description="SQLite database file path",
    )
    posts_dir: Path = Field(
        default=BASE_DIR / "data" / "posts", description="Directory for draft posts"
    )
    logs_dir: Path = Field(
        default=BASE_DIR / "logs", description="Directory for log files"
    )
    cache_dir: Path = Field(
        default=BASE_DIR / "data" / "cache", description="Directory for cached data"
    )

    # Cleanup settings
    cleanup_old_trends_days: int = Field(
        default=30, ge=7, description="Delete trends older than N days"
    )
    cleanup_rejected_posts_days: int = Field(
        default=7, ge=1, description="Delete rejected posts older than N days"
    )

    class Config:
        env_prefix = "STORAGE_"

    @validator("database_path", "posts_dir", "logs_dir", "cache_dir")
    def create_directories(cls, v):
        """Ensure directories exist"""
        if isinstance(v, Path):
            v.parent.mkdir(parents=True, exist_ok=True)
        return v


class EngagementConfig(BaseModel):
    """Configuration for LinkedIn engagement scraping/commenting"""

    enabled: bool = Field(default=False, description="Enable LinkedIn engagement workflow")
    headless: bool = Field(default=True, description="Run browser headless for scraping")
    cookies_path: Path = Field(
        default=BASE_DIR / "data" / "linkedin_cookies.json",
        description="Playwright storage state file for LinkedIn session",
    )
    max_targets: int = Field(default=3, ge=1, le=10, description="Max posts to target per run")
    keywords: List[str] = Field(
        default=["AI", "machine learning", "LLM", "MLOps"],
        description="Keywords to search for trending posts",
    )
    influencers: List[str] = Field(
        default=[],
        description="LinkedIn profile URLs or handles to pull recent posts from",
    )
    comment_max_chars: int = Field(
        default=240, ge=60, le=400, description="Max comment length"
    )

    class Config:
        env_prefix = "ENGAGE_"


class LoggingConfig(BaseModel):
    """Logging configuration"""

    level: str = Field(
        default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR"
    )
    log_to_file: bool = Field(default=True, description="Enable file logging")
    log_to_console: bool = Field(default=True, description="Enable console logging")
    log_format: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Log message format",
    )
    rotation: str = Field(default="10 MB", description="Log rotation size")
    retention: str = Field(default="30 days", description="Log retention period")
    compression: str = Field(default="zip", description="Log compression format")

    class Config:
        env_prefix = "LOG_"


class NotificationConfig(BaseModel):
    """Notification settings"""

    enabled: bool = Field(default=False, description="Enable notifications")

    # Email notifications
    email_enabled: bool = Field(default=False, description="Enable email notifications")
    smtp_host: Optional[str] = Field(default=None, description="SMTP server host")
    smtp_port: int = Field(default=587, description="SMTP server port")
    smtp_username: Optional[str] = Field(default=None, description="SMTP username")
    smtp_password: Optional[str] = Field(default=None, description="SMTP password")
    email_from: Optional[str] = Field(default=None, description="From email address")
    email_to: Optional[str] = Field(default=None, description="To email address")

    # Slack notifications
    slack_enabled: bool = Field(default=False, description="Enable Slack notifications")
    slack_webhook_url: Optional[str] = Field(
        default=None, description="Slack webhook URL"
    )

    # Notification triggers
    notify_on_posts_ready: bool = Field(
        default=True, description="Notify when posts are ready for review"
    )
    notify_on_errors: bool = Field(default=True, description="Notify on errors")
    notify_daily_summary: bool = Field(
        default=False, description="Send daily summary"
    )

    class Config:
        env_prefix = "NOTIFICATION_"


class Settings(BaseModel):
    """Main application settings"""

    # Environment
    environment: str = Field(
        default="development", description="Environment: development, production"
    )
    debug: bool = Field(default=False, description="Enable debug mode")

    # Sub-configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    linkedin: LinkedInConfig = Field(default_factory=LinkedInConfig)
    trends: TrendSourcesConfig = Field(default_factory=TrendSourcesConfig)
    post_generation: PostGenerationConfig = Field(default_factory=PostGenerationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    engagement: EngagementConfig = Field(default_factory=EngagementConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)

    class Config:
        case_sensitive = False

    @classmethod
    def from_env(cls) -> "Settings":
        """Load settings from environment variables"""
        return cls(
            environment=os.getenv("ENVIRONMENT", "development"),
            debug=os.getenv("DEBUG", "False").lower() == "true",
            llm=LLMConfig(
                provider=os.getenv("LLM_PROVIDER", "ollama"),
                api_url=os.getenv("LLM_API_URL", "http://localhost:11434"),
                model=os.getenv("LLM_MODEL", "llama2"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1000")),
                timeout=int(os.getenv("LLM_TIMEOUT", "120")),
                openai_api_key=os.getenv("LLM_OPENAI_API_KEY"),
                openai_model=os.getenv("LLM_OPENAI_MODEL", "gpt-4"),
            ),
            linkedin=LinkedInConfig(
                client_id=os.getenv("LINKEDIN_CLIENT_ID"),
                client_secret=os.getenv("LINKEDIN_CLIENT_SECRET"),
                redirect_uri=os.getenv(
                    "LINKEDIN_REDIRECT_URI", "http://localhost:8000/callback"
                ),
                access_token=os.getenv("LINKEDIN_ACCESS_TOKEN"),
                refresh_token=os.getenv("LINKEDIN_REFRESH_TOKEN"),
                token_expires_at=os.getenv("LINKEDIN_TOKEN_EXPIRES_AT"),
                user_urn=os.getenv("LINKEDIN_USER_URN"),
            ),
            trends=TrendSourcesConfig(
                hackernews_enabled=os.getenv("TRENDS_HACKERNEWS_ENABLED", "true").lower()
                == "true",
                hackernews_min_score=int(os.getenv("TRENDS_HACKERNEWS_MIN_SCORE", "100")),
                reddit_enabled=os.getenv("TRENDS_REDDIT_ENABLED", "true").lower()
                == "true",
                reddit_client_id=os.getenv("TRENDS_REDDIT_CLIENT_ID"),
                reddit_client_secret=os.getenv("TRENDS_REDDIT_CLIENT_SECRET"),
                github_enabled=os.getenv("TRENDS_GITHUB_ENABLED", "true").lower()
                == "true",
                arxiv_enabled=os.getenv("TRENDS_ARXIV_ENABLED", "true").lower()
                == "true",
                fetch_interval_hours=int(os.getenv("TRENDS_FETCH_INTERVAL_HOURS", "6")),
            ),
            post_generation=PostGenerationConfig(
                min_length=int(os.getenv("POST_MIN_LENGTH", "200")),
                max_length=int(os.getenv("POST_MAX_LENGTH", "3000")),
                max_hashtags=int(os.getenv("POST_MAX_HASHTAGS", "5")),
                generation_interval_hours=int(
                    os.getenv("POST_GENERATION_INTERVAL_HOURS", "24")
                ),
                posts_per_batch=int(os.getenv("POST_POSTS_PER_BATCH", "3")),
                min_trend_relevance=float(os.getenv("POST_MIN_TREND_RELEVANCE", "0.5")),
            ),
            storage=StorageConfig(
                database_path=Path(
                    os.getenv("STORAGE_DATABASE_PATH", str(BASE_DIR / "data" / "database.db"))
                ),
                posts_dir=Path(
                    os.getenv("STORAGE_POSTS_DIR", str(BASE_DIR / "data" / "posts"))
                ),
                logs_dir=Path(os.getenv("STORAGE_LOGS_DIR", str(BASE_DIR / "logs"))),
                cleanup_old_trends_days=int(
                    os.getenv("STORAGE_CLEANUP_OLD_TRENDS_DAYS", "30")
                ),
            ),
            engagement=EngagementConfig(
                enabled=os.getenv("ENGAGE_ENABLED", "false").lower() == "true",
                headless=os.getenv("ENGAGE_HEADLESS", "true").lower() == "true",
                cookies_path=Path(
                    os.getenv(
                        "ENGAGE_COOKIES_PATH",
                        str(BASE_DIR / "data" / "linkedin_cookies.json"),
                    )
                ),
                max_targets=int(os.getenv("ENGAGE_MAX_TARGETS", "3")),
                keywords=[
                    k.strip()
                    for k in os.getenv(
                        "ENGAGE_KEYWORDS", "AI, machine learning, LLM, MLOps"
                    ).split(",")
                    if k.strip()
                ],
                influencers=[
                    i.strip()
                    for i in os.getenv("ENGAGE_INFLUENCERS", "").split(",")
                    if i.strip()
                ],
                comment_max_chars=int(os.getenv("ENGAGE_COMMENT_MAX_CHARS", "240")),
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                log_to_file=os.getenv("LOG_TO_FILE", "true").lower() == "true",
                log_to_console=os.getenv("LOG_TO_CONSOLE", "true").lower() == "true",
            ),
            notifications=NotificationConfig(
                enabled=os.getenv("NOTIFICATION_ENABLED", "false").lower() == "true",
                email_enabled=os.getenv("NOTIFICATION_EMAIL_ENABLED", "false").lower()
                == "true",
                smtp_host=os.getenv("NOTIFICATION_SMTP_HOST"),
                smtp_port=int(os.getenv("NOTIFICATION_SMTP_PORT", "587")),
                smtp_username=os.getenv("NOTIFICATION_SMTP_USERNAME"),
                smtp_password=os.getenv("NOTIFICATION_SMTP_PASSWORD"),
                email_from=os.getenv("NOTIFICATION_EMAIL_FROM"),
                email_to=os.getenv("NOTIFICATION_EMAIL_TO"),
                slack_enabled=os.getenv("NOTIFICATION_SLACK_ENABLED", "false").lower()
                == "true",
                slack_webhook_url=os.getenv("NOTIFICATION_SLACK_WEBHOOK_URL"),
            ),
        )


# Global settings instance
settings = Settings.from_env()


def get_settings() -> Settings:
    """Get application settings"""
    return settings
