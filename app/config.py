"""Centralized configuration for all environment variables.

IMPORTANT: All environment variables MUST be loaded through this module.
Do NOT use os.getenv() directly anywhere else in the app.

This ensures:
1. Single source of truth for all env var access
2. Easy to add validation and defaults
3. Simple to mock in tests
4. Clear visibility of what env vars the app uses
"""

import os
from dataclasses import dataclass
from typing import Literal

from dotenv import load_dotenv

# ─── DATA SOURCE TYPES ───
# All available data sources for the fetch_posts tool
DataSource = Literal[
    "reddit_live",      # Live Reddit API (legacy workflow)
    "reddit_v2",        # old.reddit.com HTML scraper (Reddit killed .json endpoints)
    "pushshift",        # HuggingFace historical via DuckDB (was "arcticshift" — misnomer)
    "sample_default",   # data/smallsample/sample_posts.json
    "sample_gaming",    # data/smallsample/gaming_test_20260416_105527.json
    "linanqiu",         # github.com/linanqiu/reddit-dataset (local JSON, Feb 2016 era)
]

# Default data source
DEFAULT_DATA_SOURCE: DataSource = "pushshift"

# Load .env file on import (only loads once)
load_dotenv()

# Single source of truth for defaults
DEFAULT_MAX_SUBREDDITS = 20


@dataclass(frozen=True)
class Config:
    """Application configuration loaded from environment variables.

    All env vars should be accessed via this class, not os.getenv().

    For Reddit public API access, only a user agent is required.
    """

    # Reddit Public API - only user agent required
    reddit_user_agent: str

    # Optional: for authenticated requests (higher rate limits)
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None

    # LLM Provider selection
    llm_provider: str = "gcloud"  # "gcloud" or "lm_studio"

    # LM Studio Configuration (for local LLM classification)
    lm_studio_base_url: str = "http://localhost:1234/v1"
    lm_studio_model: str = "qwen3.5-27b-claude-4.6-opus-reasoning-distilled"
    lm_studio_timeout: int = 30
    lm_studio_max_retries: int = 3

    # Google Cloud Vertex AI Configuration
    gcloud_project: str = "AgenticAIColumbia"
    gcloud_region: str = "us-central1"
    gcloud_model: str = "gemini-2.5-pro"
    gcloud_model_fast: str = "gemini-2.5-flash"
    gcloud_service_account_key_path: str | None = None
    gcloud_timeout: int = 30
    gcloud_max_retries: int = 3

    # Clustering Configuration
    clustering_min_k: int = 8
    clustering_max_k: int = 15
    clustering_embedding_model: str = "text-embedding-004"
    clustering_preprocess_case_normalize: bool = True
    clustering_preprocess_dedup_threshold: float = 0.95
    clustering_use_silhouette: bool = True

    # Theme Expansion Configuration
    expansion_batch_size: int = 5
    expansion_max_context_titles: int = 3
    expansion_use_cache: bool = True
    expansion_cache_ttl_seconds: int = 86400
    expansion_max_retries: int = 3

    # OpenAI + Gemini Configuration (agent framework)
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-pro"
    gemini_embedding_model: str = "gemini-embedding-2-preview"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_max_retries: int = 3
    gemini_timeout: int = 60

    # Subreddit Selection
    max_subreddits: int = DEFAULT_MAX_SUBREDDITS  # Maximum subreddits for LLM selection

    # Agent Framework Configuration
    agent_max_iterations: int = 20
    agent_enable_timing: bool = True

    # Tool result size management (prevent MALFORMED_FUNCTION_CALL)
    agent_tool_result_max_size: int = 16384  # Max chars before truncation (16KB)
    agent_tool_result_preview_chars: int = 200  # Preview length in summary
    agent_tool_result_enable_truncation: bool = True  # Master switch

    # Parallel Classification Configuration
    classification_max_workers: int = 10  # Max concurrent classification threads
    classification_request_timeout: int = 30  # Timeout per classification request (seconds)
    classification_enable_parallel: bool = True  # Master switch for parallel execution

    # Reddit API Pacing (100 requests per 10 minutes = 1 req per 6 seconds)
    reddit_requests_per_10min: int = 100  # Reddit's unauthenticated rate limit
    reddit_min_request_interval_seconds: float = 6.0  # 600s / 100 = minimum seconds between requests

    # Retry Configuration (exponential backoff for LLM API calls)
    retry_max_attempts: int = 5
    retry_initial_backoff_seconds: float = 1.0
    retry_max_backoff_seconds: float = 60.0
    retry_backoff_multiplier: float = 2.0
    retry_enable_jitter: bool = True

    # Proxy settings (for bypassing Reddit WAF blocks on data center IPs)
    proxy_enabled: bool = False
    proxy_url: str | None = None

    # Usage tracking (Gemini token limits)
    usage_limit_tokens: int = 1_000_000  # 1M tokens (~$10-15 of Gemini usage)
    usage_storage_bucket: str | None = None  # GCS bucket for usage persistence
    datasets_bucket: str | None = None  # Informational; mount configured at deploy time

    # Runtime environment: "development" or "production".
    # In development, token tracking and monthly limits are disabled.
    environment: str = "development"

    @property
    def is_development(self) -> bool:
        """True in dev mode. Disables token counting and the monthly limit gate."""
        return self.environment == "development"

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables.

        Raises:
            ValueError: If required environment variables are missing.
        """
        reddit_user_agent = os.getenv("REDDIT_USER_AGENT")

        if not reddit_user_agent:
            # Provide a sensible default
            reddit_user_agent = "complaint-analyzer:1.0 (by /u/example)"

        return cls(
            reddit_user_agent=reddit_user_agent,
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID"),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
            # LLM Provider selection
            llm_provider=os.getenv("LLM_PROVIDER", "gcloud"),
            # LM Studio Configuration
            lm_studio_base_url=os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"),
            lm_studio_model=os.getenv(
                "LM_STUDIO_MODEL", "qwen3.5-27b-claude-4.6-opus-reasoning-distilled"
            ),
            lm_studio_timeout=int(os.getenv("LM_STUDIO_TIMEOUT", "30")),
            lm_studio_max_retries=int(os.getenv("LM_STUDIO_MAX_RETRIES", "3")),
            # Google Cloud Vertex AI Configuration
            gcloud_project=os.getenv("GCLOUD_PROJECT", "AgenticAIColumbia"),
            gcloud_region=os.getenv("GCLOUD_REGION", "us-central1"),
            gcloud_model=os.getenv("GCLOUD_MODEL", "gemini-2.5-pro"),
            gcloud_model_fast=os.getenv("GCLOUD_MODEL_FAST", "gemini-2.5-flash"),
            gcloud_service_account_key_path=os.getenv("GCLOUD_SERVICE_ACCOUNT_KEY_PATH"),
            gcloud_timeout=int(os.getenv("GCLOUD_TIMEOUT", "30")),
            gcloud_max_retries=int(os.getenv("GCLOUD_MAX_RETRIES", "3")),
            # Clustering Configuration
            clustering_min_k=int(os.getenv("CLUSTERING_MIN_K", "8")),
            clustering_max_k=int(os.getenv("CLUSTERING_MAX_K", "15")),
            clustering_embedding_model=os.getenv("CLUSTERING_EMBEDDING_MODEL", "text-embedding-004"),
            clustering_preprocess_case_normalize=os.getenv("CLUSTERING_PREPROCESS_CASE_NORMALIZE", "true").lower() == "true",
            clustering_preprocess_dedup_threshold=float(os.getenv("CLUSTERING_PREPROCESS_DEDUP_THRESHOLD", "0.95")),
            clustering_use_silhouette=os.getenv("CLUSTERING_USE_SILHOUETTE", "true").lower() == "true",
            # Theme Expansion Configuration
            expansion_batch_size=int(os.getenv("EXPANSION_BATCH_SIZE", "5")),
            expansion_max_context_titles=int(os.getenv("EXPANSION_MAX_CONTEXT_TITLES", "3")),
            expansion_use_cache=os.getenv("EXPANSION_USE_CACHE", "true").lower() == "true",
            expansion_cache_ttl_seconds=int(os.getenv("EXPANSION_CACHE_TTL_SECONDS", "86400")),
            expansion_max_retries=int(os.getenv("EXPANSION_MAX_RETRIES", "3")),
            # OpenAI + Gemini Configuration
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
            gemini_embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2-preview"),
            gemini_base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
            gemini_max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "3")),
            gemini_timeout=int(os.getenv("GEMINI_TIMEOUT", "60")),
            # Subreddit Selection
            max_subreddits=int(os.getenv("MAX_SUBREDDITS", str(DEFAULT_MAX_SUBREDDITS))),
            # Agent Framework Configuration
            agent_max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "20")),
            agent_enable_timing=os.getenv("AGENT_ENABLE_TIMING", "true").lower() == "true",
            # Tool result size management
            agent_tool_result_max_size=int(os.getenv("AGENT_TOOL_RESULT_MAX_SIZE", "16384")),
            agent_tool_result_preview_chars=int(os.getenv("AGENT_TOOL_RESULT_PREVIEW_CHARS", "200")),
            agent_tool_result_enable_truncation=os.getenv("AGENT_TOOL_RESULT_ENABLE_TRUNCATION", "true").lower() == "true",
            # Parallel Classification
            classification_max_workers=int(os.getenv("CLASSIFICATION_MAX_WORKERS", "10")),
            classification_request_timeout=int(os.getenv("CLASSIFICATION_REQUEST_TIMEOUT", "30")),
            classification_enable_parallel=os.getenv("CLASSIFICATION_ENABLE_PARALLEL", "true").lower() == "true",
            # Reddit API Pacing
            reddit_requests_per_10min=int(os.getenv("REDDIT_REQUESTS_PER_10MIN", "100")),
            reddit_min_request_interval_seconds=float(os.getenv("REDDIT_MIN_REQUEST_INTERVAL_SECONDS", "6.0")),
            # Retry Configuration
            retry_max_attempts=int(os.getenv("RETRY_MAX_ATTEMPTS", "5")),
            retry_initial_backoff_seconds=float(os.getenv("RETRY_INITIAL_BACKOFF_SECONDS", "1.0")),
            retry_max_backoff_seconds=float(os.getenv("RETRY_MAX_BACKOFF_SECONDS", "60.0")),
            retry_backoff_multiplier=float(os.getenv("RETRY_BACKOFF_MULTIPLIER", "2.0")),
            retry_enable_jitter=os.getenv("RETRY_ENABLE_JITTER", "true").lower() == "true",
            # Proxy settings
            proxy_enabled=os.getenv("PROXY_ENABLED", "false").lower() == "true",
            proxy_url=os.getenv("PROXY_URL"),
            # Usage tracking
            usage_limit_tokens=int(os.getenv("USAGE_LIMIT_TOKENS", "1000000")),
            usage_storage_bucket=os.getenv("USAGE_STORAGE_BUCKET"),
            datasets_bucket=os.getenv("DATASETS_BUCKET"),
            # Runtime environment
            environment=os.getenv("APP_ENV", "development"),
        )


# Singleton instance - use this throughout the app
config = Config.from_env()

# Diagnostic logging for proxy config (helps debug Cloud Run secret mounting)
import logging
_startup_logger = logging.getLogger(__name__)
_startup_logger.info(
    "[CONFIG] proxy_enabled=%s, proxy_url=%s",
    config.proxy_enabled,
    "***set***" if config.proxy_url else "None",
)

# ─── DATA SOURCE RUNTIME OVERRIDE ───
_data_source_override: DataSource | None = None


def set_data_source_override(source: DataSource) -> None:
    """Override data_source at runtime.

    The config singleton is frozen, so the API/backend can't change
    data_source by setting os.environ after import. Use this instead.

    The data source is driven per-request by the frontend dropdown
    (web flow) or the CLI ``--data-source`` flag.
    """
    global _data_source_override
    _data_source_override = source


def get_data_source() -> DataSource:
    """Get effective data source, respecting runtime overrides."""
    override = _data_source_override
    if override is not None:
        return override
    return DEFAULT_DATA_SOURCE
