"""LM Studio provider using OpenAI-compatible API.

This provider connects to a local LM Studio instance running an LLM server.
"""

import json
import logging
import re
from typing import Any

from openai import OpenAI
from pydantic import ValidationError

from app.analyst.models import ComplaintClassification, EnrichedPost
from app.analyst.prompts import CLASSIFICATION_PROMPT, RETRY_PROMPT
from app.analyst.providers.base import LLMProvider
from app.config import config

logger = logging.getLogger(__name__)


class LMStudioProvider(LLMProvider):
    """LLM provider using LM Studio's OpenAI-compatible API."""

    def __init__(self):
        """Initialize the LM Studio provider with configuration from config."""
        self._base_url = config.lm_studio_base_url
        self._model = config.lm_studio_model
        self._timeout = config.lm_studio_timeout
        self._max_retries = config.lm_studio_max_retries

        # Initialize OpenAI client pointing to LM Studio
        # Force HTTP/1.1 and single connection to prevent request queuing
        import httpx
        http_client = httpx.Client(
            limits=httpx.Limits(max_connections=1, max_keepalive_connections=1),
        )
        self._client = OpenAI(
            base_url=self._base_url,
            api_key="lm-studio",  # LM Studio doesn't need real API key
            timeout=self._timeout,
            http_client=http_client,
        )

        logger.info(f"LMStudioProvider initialized with model: {self._model}")
        logger.info(f"LM Studio URL: {self._base_url}")

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return self._model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "lm_studio"

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

                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,  # Low temperature for consistent JSON output
                    max_tokens=1024,  # Reasoning models need more tokens for thinking + output
                )

                # Get content from message (primary) or reasoning_content (some APIs)
                message = response.choices[0].message
                raw_response = message.content or ""

                # Some reasoning models put output in model_extra or other fields
                if not raw_response and hasattr(message, 'model_extra') and message.model_extra:
                    raw_response = message.model_extra.get('reasoning_content', '') or \
                                   message.model_extra.get('content', '')

                # Debug: log full response structure if content is empty
                if not raw_response:
                    logger.debug(f"Empty response for {post_id}. Message attrs: {dir(message)}")
                    logger.debug(f"Full response: {response}")

                logger.info(f"Raw LLM response for {post_id}: {raw_response[:500] if raw_response else '<EMPTY>'}")
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

            # Add longer delay before retry (reasoning models need more time)
            if attempt < self._max_retries:
                time.sleep(2.0)  # 2 seconds between retries

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

        # Handle reasoning models that output thinking blocks
        # Remove various thinking/reasoning tag formats
        thinking_patterns = [
            r'<think[\s\S]*?</think\|?>',      # <think...</think|> or <think...</think|>
            r'<\|channel\|>analysis<\|message\|>[\s\S]*?<\|end\|>',  # Qwen reasoning format
            r'<\|[^>]*\|>[\s\S]*?<\|end\|>',   # Generic special token blocks
            r'🔏[\s\S]*?🔏',                    # 🔏...🔏 reasoning blocks
            r'\{\|[\s\S]*?\|\}',                # {|...|} thinking blocks
            r'\[\|[\s\S]*?\|\]',                # [|...|] thinking blocks
            r'<reasoning>[\s\S]*?</reasoning>', # <reasoning>...</reasoning>
            r'\*\*Reasoning\*\*:[\s\S]*?(?=\*\*|\n\n|\Z)',  # **Reasoning**: ...
        ]
        for pattern in thinking_patterns:
            response_text = re.sub(pattern, '', response_text)
        response_text = response_text.strip()

        # Also handle ellipsis-only responses (common from reasoning models)
        if response_text in ('...', '…', ''):
            logger.warning("LLM returned empty/ellipsis response (likely reasoning model)")
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
        # Log FULL response for debugging (not truncated)
        logger.warning(f"Failed to parse classification. Full response:\n{response_text}")
        return None
