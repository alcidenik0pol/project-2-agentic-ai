"""LM Studio provider using OpenAI-compatible API.

This provider connects to a local LM Studio instance running an LLM server.
"""

import json
import logging
import re
import time
from typing import Any

import numpy as np
from openai import OpenAI
from pydantic import ValidationError

from app.analyst.models import ComplaintClassification, EnrichedPost
from app.analyst.prompts import CLASSIFICATION_PROMPT, RETRY_PROMPT
from app.analyst.providers.base import ChatToolResponse, LLMProvider, ToolCallInfo
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

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str | None:
        """Generate raw text from LM Studio via OpenAI-compatible API."""
        logger.debug("generate_text called: prompt=%d chars, temp=%.2f, max_tokens=%d", len(prompt), temperature, max_tokens)
        start = time.time()

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        result = response.choices[0].message.content or None

        elapsed = time.time() - start
        logger.debug("generate_text completed in %.2fs: response=%d chars", elapsed, len(result) if result else 0)
        return result

    def generate_structured(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | None:
        """Generate structured JSON from LM Studio.

        Note: LM Studio doesn't support responseMimeType, so we use
        generate_text() and parse the result. Less reliable than GCloud.
        """
        return self.generate_text(prompt, temperature, max_tokens)

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.3,
    ) -> ChatToolResponse:
        """Send a chat request with retry logic for MALFORMED_FUNCTION_CALL."""
        for attempt in range(1, self._max_retries + 1):
            response = self._chat_with_tools_internal(messages, tools, temperature)

            # Check for empty response (MALFORMED_FUNCTION_CALL symptom)
            if not response.content and not response.tool_calls:
                logger.warning(
                    f"Empty response from {self.provider_name} (attempt {attempt}/{self._max_retries}). "
                    f"Retrying in 1s..."
                )
                if attempt < self._max_retries:
                    time.sleep(1.0)
                    continue
                else:
                    logger.error(f"Max retries reached for {self.provider_name} chat_with_tools")

            return response

        return ChatToolResponse(content="Error: Failed after retries")

    def _chat_with_tools_internal(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.3,
    ) -> ChatToolResponse:
        """Send a chat request with tool definitions via OpenAI SDK."""
        logger.debug(
            "chat_with_tools called: %d messages, %d tools, temp=%.2f",
            len(messages), len(tools), temperature,
        )
        start = time.time()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self._client.chat.completions.create(**kwargs)
        message = response.choices[0].message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append(ToolCallInfo(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=tc.function.arguments,
                ))

        elapsed = time.time() - start
        logger.info(
            "chat_with_tools completed in %.2fs: content=%d chars, %d tool_calls",
            elapsed, len(message.content) if message.content else 0, len(tool_calls),
        )
        return ChatToolResponse(
            content=message.content,
            tool_calls=tool_calls,
        )

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using LM Studio's OpenAI-compatible embeddings endpoint.

        Args:
            texts: List of strings to embed.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        response = self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        embeddings = [item.embedding for item in response.data]
        return np.array(embeddings, dtype=np.float32)

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
