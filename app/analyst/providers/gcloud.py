"""Google Cloud Vertex AI provider using Gemini models.

This provider connects to Google Cloud Vertex AI for classification.
"""

import json
import logging
import re
from typing import Any

from pydantic import ValidationError

from app.analyst.models import ComplaintClassification, EnrichedPost
from app.analyst.prompts import CLASSIFICATION_PROMPT, RETRY_PROMPT
from app.analyst.providers.base import LLMProvider
from app.config import config

logger = logging.getLogger(__name__)


class GCloudProvider(LLMProvider):
    """LLM provider using Google Cloud Vertex AI with Gemini models."""

    def __init__(self):
        """Initialize the Google Cloud provider with configuration from config."""
        self._project = config.gcloud_project
        self._region = config.gcloud_region
        self._model = config.gcloud_model
        self._timeout = config.gcloud_timeout
        self._max_retries = config.gcloud_max_retries
        self._credentials_path = config.gcloud_service_account_key_path

        # Initialize Vertex AI
        self._initialize_vertex_ai()

        logger.info(f"GCloudProvider initialized with model: {self._model}")
        logger.info(f"Project: {self._project}, Region: {self._region}")

    def _initialize_vertex_ai(self):
        """Initialize Vertex AI client with credentials."""
        try:
            import google.auth
            from google.oauth2 import service_account
            import vertexai
            from vertexai.generative_models import GenerativeModel

            # Load credentials
            if self._credentials_path:
                credentials = service_account.Credentials.from_service_account_file(
                    self._credentials_path
                )
                logger.info(f"Loaded service account credentials from: {self._credentials_path}")
            else:
                # Use default credentials (ADC)
                credentials, project = google.auth.default()
                logger.info("Using Application Default Credentials")

            # Initialize Vertex AI
            vertexai.init(
                project=self._project,
                location=self._region,
                credentials=credentials,
            )

            # Create the generative model
            self._client = GenerativeModel(self._model)

        except ImportError as e:
            raise ImportError(
                "google-cloud-aiplatform is required for Google Cloud provider. "
                "Install with: pip install google-cloud-aiplatform"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Vertex AI: {e}") from e

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gcloud"

    def classify_post(
        self,
        post_data: dict[str, Any],
        subreddit: str,
        category: str,
        comments_count: int,
    ) -> EnrichedPost:
        """Classify a single Reddit post with retry logic.

        Args:
            post_data: Raw post dictionary from Reddit API
            subreddit: Subreddit name
            category: Post category
            comments_count: Number of comments fetched

        Returns:
            EnrichedPost with classification or error details
        """
        import time

        enriched = EnrichedPost(
            subreddit=subreddit,
            category=category,
            post=post_data,
            comments_count=comments_count,
        )

        title = post_data.get("title", "")
        selftext = post_data.get("selftext", "")
        post_id = post_data.get("id", "unknown")

        # Try classification with retries
        for attempt in range(1, self._max_retries + 1):
            try:
                # Use retry prompt for subsequent attempts
                prompt_template = RETRY_PROMPT if attempt > 1 else CLASSIFICATION_PROMPT
                prompt = prompt_template.format(
                    title=title, selftext=selftext, subreddit=subreddit
                )

                # Call Gemini API
                response = self._client.generate_content(
                    prompt,
                    generation_config={
                        "temperature": 0.1,
                        "max_output_tokens": 1024,
                    },
                )

                # Extract text from response
                raw_response = response.text if response.text else ""

                logger.info(f"Raw Gemini response for {post_id}: {raw_response[:500] if raw_response else '<EMPTY>'}")
                classification = self.parse_classification(raw_response)

                if classification:
                    enriched.classification = classification
                    enriched.classification_attempts = attempt
                    logger.debug(f"Post {post_id} classified successfully (attempt {attempt})")
                    return enriched

                logger.warning(
                    f"Post {post_id} parse failed on attempt {attempt}, retrying..."
                )

            except Exception as e:
                logger.warning(f"Post {post_id} error on attempt {attempt}: {e}")

            enriched.classification_attempts = attempt

            # Add delay before retry
            if attempt < self._max_retries:
                time.sleep(1.0)

        # All retries exhausted
        enriched.classification_error = f"Failed after {self._max_retries} attempts"
        logger.error(f"Post {post_id} classification failed after all retries")
        return enriched

    def parse_classification(self, raw_response: str) -> ComplaintClassification | None:
        """Parse LLM response into classification with 3-tier fallback.

        Args:
            raw_response: Raw text from LLM

        Returns:
            ComplaintClassification or None if parsing fails
        """
        response_text = raw_response.strip()

        # Handle empty responses
        if response_text in ('...', '…', ''):
            logger.warning("LLM returned empty response")
            return None

        # Tier 1: Direct JSON parse
        try:
            data = json.loads(response_text)
            return ComplaintClassification(**data)
        except (json.JSONDecodeError, ValueError, ValidationError, KeyError, TypeError) as e:
            logger.debug(f"Direct parse failed: {e}")

        # Tier 2: Extract JSON from markdown code blocks or bare objects
        json_patterns = [
            r"```json\s*([\s\S]*?)\s*```",  # ```json ... ```
            r"```\s*([\s\S]*?)\s*```",       # ``` ... ```
            r"\{[^{}]*\}",                    # Bare JSON object (no nested braces)
            r"\{[\s\S]*?\}",                  # Bare JSON object (greedy, for complex cases)
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                try:
                    json_str = match if isinstance(match, str) else match
                    # For bare object patterns, use the full match
                    if pattern.startswith(r"\{"):
                        json_str = match
                    data = json.loads(json_str)
                    return ComplaintClassification(**data)
                except (json.JSONDecodeError, ValueError, ValidationError, KeyError, TypeError, IndexError) as e:
                    logger.debug(f"Pattern parse failed: {e}")
                    continue

        # Tier 3: Return None (caller will handle retry/failure)
        logger.warning(f"Failed to parse classification. Full response:\n{response_text}")
        return None
