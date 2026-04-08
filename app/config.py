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
    gcloud_model: str = "gemini-2.5-flash-001"
    gcloud_service_account_key_path: str | None = None
    gcloud_timeout: int = 30
    gcloud_max_retries: int = 3

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
            gcloud_model=os.getenv("GCLOUD_MODEL", "gemini-2.5-flash-001"),
            gcloud_service_account_key_path=os.getenv("GCLOUD_SERVICE_ACCOUNT_KEY_PATH"),
            gcloud_timeout=int(os.getenv("GCLOUD_TIMEOUT", "30")),
            gcloud_max_retries=int(os.getenv("GCLOUD_MAX_RETRIES", "3")),
        )


# Singleton instance - use this throughout the app
config = Config.from_env()
