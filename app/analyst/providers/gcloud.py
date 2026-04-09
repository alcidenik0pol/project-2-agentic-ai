"""Google Cloud Vertex AI provider using Gemini models.

This provider connects to Google Cloud Vertex AI for classification
via direct REST API calls (bypassing the deprecated vertexai SDK).
"""

import json
import logging
import re
import time
from typing import Any

import numpy as np
import requests
from google.oauth2 import service_account
import google.auth.transport.requests
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

        # Build the REST endpoint URL
        # Project ID must be lowercase for the API
        project_lower = self._project.lower()
        self._url = (
            f"https://{self._region}-aiplatform.googleapis.com/v1/"
            f"projects/{project_lower}/locations/{self._region}/"
            f"publishers/google/models/{self._model}:generateContent"
        )

        # Initialize credentials
        self._initialize_credentials()

        logger.info(f"GCloudProvider initialized with model: {self._model}")
        logger.info(f"Project: {self._project}, Region: {self._region}")

    def _initialize_credentials(self):
        """Load service account credentials for API calls."""
        try:
            if self._credentials_path:
                self._credentials = service_account.Credentials.from_service_account_file(
                    self._credentials_path,
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                logger.info(f"Loaded service account credentials from: {self._credentials_path}")
            else:
                import google.auth
                self._credentials, _ = google.auth.default(
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                logger.info("Using Application Default Credentials")
        except Exception as e:
            raise RuntimeError(f"Failed to load credentials: {e}") from e

    def _get_token(self) -> str:
        """Get a valid access token, refreshing if needed."""
        if not self._credentials.valid:
            self._credentials.refresh(google.auth.transport.requests.Request())
        return self._credentials.token

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using Vertex AI text-embedding-004 REST API.

        Batches texts into groups of 5 (Vertex AI limit per request).

        Args:
            texts: List of strings to embed.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        embedding_model = config.clustering_embedding_model
        project_lower = self._project.lower()
        embed_url = (
            f"https://{self._region}-aiplatform.googleapis.com/v1/"
            f"projects/{project_lower}/locations/{self._region}/"
            f"publishers/google/models/{embedding_model}:predict"
        )

        all_embeddings: list[list[float]] = []
        batch_size = 5

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            payload = {
                "instances": [{"content": t} for t in batch],
            }

            for attempt in range(1, self._max_retries + 1):
                try:
                    token = self._get_token()
                    response = requests.post(
                        embed_url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                        timeout=self._timeout,
                    )
                    response.raise_for_status()

                    data = response.json()
                    predictions = data.get("predictions", [])
                    for pred in predictions:
                        emb = pred.get("embeddings", {}).get("values", [])
                        if not emb:
                            raise ValueError("Empty embedding returned")
                        all_embeddings.append(emb)
                    break

                except Exception as e:
                    logger.warning(
                        f"Embedding batch {i // batch_size} attempt {attempt} failed: {e}"
                    )
                    if attempt < self._max_retries:
                        time.sleep(1.0)
                    else:
                        raise RuntimeError(
                            f"Embedding batch {i // batch_size} failed after {self._max_retries} attempts"
                        ) from e

        return np.array(all_embeddings, dtype=np.float32)

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gcloud"

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str | None:
        """Generate raw text from Gemini via REST API."""
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        token = self._get_token()
        response = requests.post(
            self._url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return None

    def generate_structured(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | None:
        """Generate structured JSON from Gemini via REST API.

        Uses responseMimeType: application/json to force valid JSON output.
        """
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "responseMimeType": "application/json",
            },
        }
        token = self._get_token()
        response = requests.post(
            self._url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", "")
        return None

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

                # Build REST request payload
                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}],
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 1024,
                    },
                }

                # Call Gemini API via REST
                token = self._get_token()
                response = requests.post(
                    self._url,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self._timeout,
                )
                response.raise_for_status()

                # Extract text from response
                data = response.json()
                raw_response = ""
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_response = parts[0].get("text", "")

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
