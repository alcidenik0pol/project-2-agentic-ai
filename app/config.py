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
from dotenv import load_dotenv

# Load .env file on import (only loads once)
load_dotenv()


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
    gcloud_model: str = "gemini-2.5-flash"
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
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-2-preview"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    gemini_max_retries: int = 3
    gemini_timeout: int = 60

    # Agent Framework Configuration
    agent_mode: str = "test"  # "test" (sample data) or "live" (Reddit API)
    agent_max_iterations: int = 20
    agent_enable_timing: bool = True

    # Tool result size management (prevent MALFORMED_FUNCTION_CALL)
    agent_tool_result_max_size: int = 4096  # Max chars before truncation (4KB)
    agent_tool_result_preview_chars: int = 200  # Preview length in summary
    agent_tool_result_enable_truncation: bool = True  # Master switch

    # Reddit API Pacing (for production stability)
    reddit_requests_per_minute: int = 10  # Reddit's unauthenticated rate limit
    reddit_request_pacing_sleep: float = 0.0  # Extra sleep between requests (seconds)

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
            gcloud_model=os.getenv("GCLOUD_MODEL", "gemini-2.5-flash"),
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
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
            gemini_embedding_model=os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-2-preview"),
            gemini_base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"),
            gemini_max_retries=int(os.getenv("GEMINI_MAX_RETRIES", "3")),
            gemini_timeout=int(os.getenv("GEMINI_TIMEOUT", "60")),
            # Agent Framework Configuration
            agent_mode=os.getenv("AGENT_MODE", "test"),
            agent_max_iterations=int(os.getenv("AGENT_MAX_ITERATIONS", "20")),
            agent_enable_timing=os.getenv("AGENT_ENABLE_TIMING", "true").lower() == "true",
            # Tool result size management
            agent_tool_result_max_size=int(os.getenv("AGENT_TOOL_RESULT_MAX_SIZE", "4096")),
            agent_tool_result_preview_chars=int(os.getenv("AGENT_TOOL_RESULT_PREVIEW_CHARS", "200")),
            agent_tool_result_enable_truncation=os.getenv("AGENT_TOOL_RESULT_ENABLE_TRUNCATION", "true").lower() == "true",
            # Reddit API Pacing
            reddit_requests_per_minute=int(os.getenv("REDDIT_REQUESTS_PER_MINUTE", "10")),
            reddit_request_pacing_sleep=float(os.getenv("REDDIT_REQUEST_PACING_SLEEP", "0.0")),
        )


# Singleton instance - use this throughout the app
config = Config.from_env()
