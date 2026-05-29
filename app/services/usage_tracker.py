"""Token usage tracking with GCS persistence and monthly auto-reset.

Tracks Gemini API token usage to enforce monthly limits.
Usage data persists to GCS in production, falls back to local file in development.
"""

import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class UsageStats:
    """Current usage statistics."""
    input_tokens: int
    output_tokens: int
    total_tokens: int
    month: str  # YYYY-MM format


class UsageTracker:
    """Track Gemini token usage with GCS persistence and monthly reset.

    Features:
    - Persists usage to GCS bucket (or local file in dev)
    - Auto-resets on the 1st of each month
    - Thread-safe with in-memory caching
    - Extracts token counts from Gemini usageMetadata
    """

    def __init__(
        self,
        bucket_name: str | None = None,
        limit: int = 1_000_000,
        local_path: Path | None = None,
    ):
        """Initialize usage tracker.

        Args:
            bucket_name: GCS bucket name (if None, uses local storage)
            limit: Monthly token limit (default 1M)
            local_path: Local file path for dev/fallback storage
        """
        self.bucket_name = bucket_name
        self.limit = limit
        self._local_path = local_path or Path("data/usage")
        self._local_path.mkdir(parents=True, exist_ok=True)

        # In-memory cache
        self._cache: dict[str, Any] = {}
        self._cache_month: str | None = None
        self._lock = threading.Lock()

        # GCS client (lazy-loaded)
        self._gcs_client = None

        logger.info(
            "UsageTracker initialized: bucket=%s, limit=%d, local_path=%s",
            bucket_name, limit, self._local_path
        )

    def _get_month_key(self) -> str:
        """Get current month key in YYYY-MM format."""
        return datetime.now().strftime("%Y-%m")

    def _get_storage_filename(self) -> str:
        """Get storage filename for current month."""
        return f"usage-{self._get_month_key()}.json"

    def _get_gcs_client(self):
        """Lazy-load GCS client."""
        if self._gcs_client is None and self.bucket_name:
            try:
                from google.cloud import storage
                self._gcs_client = storage.Client()
                logger.info("GCS client initialized")
            except ImportError:
                logger.warning("google-cloud-storage not installed, using local storage")
            except Exception as e:
                logger.warning(f"Failed to initialize GCS client: {e}, using local storage")
        return self._gcs_client

    def _load_from_gcs(self) -> dict[str, Any]:
        """Load usage data from GCS bucket."""
        client = self._get_gcs_client()
        if not client or not self.bucket_name:
            return self._load_from_local()

        try:
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(self._get_storage_filename())

            if blob.exists():
                content = blob.download_as_string()
                data = json.loads(content)
                logger.debug("Loaded usage from GCS: %s", data)
                return data
            else:
                logger.debug("No usage file in GCS, returning empty")
                return self._empty_usage()
        except Exception as e:
            logger.warning(f"GCS load failed: {e}, falling back to local")
            return self._load_from_local()

    def _save_to_gcs(self, data: dict[str, Any]) -> None:
        """Save usage data to GCS bucket."""
        client = self._get_gcs_client()
        if not client or not self.bucket_name:
            self._save_to_local(data)
            return

        try:
            bucket = client.bucket(self.bucket_name)
            blob = bucket.blob(self._get_storage_filename())
            blob.upload_from_string(
                json.dumps(data, indent=2),
                content_type="application/json"
            )
            logger.debug("Saved usage to GCS: %s", data)
        except Exception as e:
            logger.warning(f"GCS save failed: {e}, saving to local")
            self._save_to_local(data)

    def _load_from_local(self) -> dict[str, Any]:
        """Load usage data from local file."""
        filepath = self._local_path / self._get_storage_filename()
        if filepath.exists():
            try:
                with open(filepath) as f:
                    data = json.load(f)
                logger.debug("Loaded usage from local: %s", data)
                return data
            except Exception as e:
                logger.warning(f"Failed to load local usage file: {e}")
        return self._empty_usage()

    def _save_to_local(self, data: dict[str, Any]) -> None:
        """Save usage data to local file."""
        filepath = self._local_path / self._get_storage_filename()
        try:
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved usage to local: %s", filepath)
        except Exception as e:
            logger.error(f"Failed to save local usage file: {e}")

    def _empty_usage(self) -> dict[str, Any]:
        """Return empty usage data structure."""
        return {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
            "month": self._get_month_key(),
            "updated_at": datetime.now().isoformat(),
        }

    def _ensure_cache_current(self) -> dict[str, Any]:
        """Ensure cache is loaded and current month."""
        current_month = self._get_month_key()

        # If cache is stale or for different month, reload
        if not self._cache or self._cache_month != current_month:
            self._cache = self._load_from_gcs()
            self._cache_month = current_month

            # If loaded data is from old month, reset to zero
            if self._cache.get("month") != current_month:
                logger.info(
                    "New month detected (was %s, now %s), resetting usage",
                    self._cache.get("month"), current_month
                )
                self._cache = self._empty_usage()

        return self._cache

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record token usage from an API call.

        Args:
            input_tokens: Number of input/prompt tokens
            output_tokens: Number of output/completion tokens
        """
        with self._lock:
            data = self._ensure_cache_current()

            data["input_tokens"] = data.get("input_tokens", 0) + input_tokens
            data["output_tokens"] = data.get("output_tokens", 0) + output_tokens
            data["total_tokens"] = data["input_tokens"] + data["output_tokens"]
            data["updated_at"] = datetime.now().isoformat()
            data["month"] = self._get_month_key()

            self._cache = data
            self._save_to_gcs(data)

            logger.debug(
                "Recorded usage: +%d in, +%d out = %d total (limit: %d)",
                input_tokens, output_tokens, data["total_tokens"], self.limit
            )

    def get_usage(self) -> UsageStats:
        """Get current usage statistics."""
        with self._lock:
            data = self._ensure_cache_current()
            return UsageStats(
                input_tokens=data.get("input_tokens", 0),
                output_tokens=data.get("output_tokens", 0),
                total_tokens=data.get("total_tokens", 0),
                month=data.get("month", self._get_month_key()),
            )

    def is_limit_exceeded(self) -> bool:
        """Check if monthly limit has been exceeded."""
        return self.get_usage().total_tokens >= self.limit

    def get_remaining_tokens(self) -> int:
        """Get number of tokens remaining."""
        return max(0, self.limit - self.get_usage().total_tokens)

    def get_remaining_percent(self) -> float:
        """Get remaining capacity as percentage (0-100)."""
        return max(0.0, self.get_remaining_tokens() / self.limit * 100)

    def get_next_reset_date(self) -> datetime:
        """Get the date when usage resets (1st of next month)."""
        now = datetime.now()
        if now.month == 12:
            return datetime(now.year + 1, 1, 1)
        return datetime(now.year, now.month + 1, 1)


def _create_usage_tracker() -> UsageTracker:
    """Create usage tracker from config (lazy import to avoid circular deps)."""
    from app.config import config

    return UsageTracker(
        bucket_name=getattr(config, "usage_storage_bucket", None),
        limit=getattr(config, "usage_limit_tokens", 1_000_000),
    )


# Lazy singleton - created on first access
_usage_tracker: UsageTracker | None = None
_tracker_lock = threading.Lock()


def get_usage_tracker() -> UsageTracker:
    """Get or create the usage tracker singleton."""
    global _usage_tracker
    if _usage_tracker is None:
        with _tracker_lock:
            if _usage_tracker is None:
                _usage_tracker = _create_usage_tracker()
    return _usage_tracker


# Convenience alias for simple imports
usage_tracker = property(lambda _: get_usage_tracker())
