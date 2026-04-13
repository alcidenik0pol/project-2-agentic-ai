"""OpenAI-compatible provider using Google Gemini via OpenAI SDK.

Uses the OpenAI Python SDK pointed at Google's OpenAI-compatible endpoint.
Single API key, single client for both chat and embeddings.
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


class OpenAIGeminiProvider(LLMProvider):
    """LLM provider using Gemini via OpenAI-compatible endpoint."""

    def __init__(self):
        if not config.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for OpenAIGeminiProvider")

        self._model = config.gemini_model
        self._embedding_model = config.gemini_embedding_model
        self._max_retries = config.gemini_max_retries

        self._client = OpenAI(
            api_key=config.gemini_api_key,
            base_url=config.gemini_base_url,
            timeout=config.gemini_timeout,
        )

        logger.info(f"OpenAIGeminiProvider initialized: model={self._model}, embedding={self._embedding_model}")

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "openai_gemini"

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> str | None:
        logger.debug("generate_text called: prompt=%d chars, temp=%.2f, max_tokens=%d", len(prompt), temperature, max_tokens)
        start = time.time()
        try:
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
        except Exception as e:
            elapsed = time.time() - start
            logger.error("generate_text failed after %.2fs: %s", elapsed, e)
            return None

    def generate_structured(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | None:
        logger.debug("generate_structured called: prompt=%d chars, temp=%.2f, max_tokens=%d", len(prompt), temperature, max_tokens)
        start = time.time()
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
            )
            result = response.choices[0].message.content or None
            elapsed = time.time() - start
            logger.debug(
                "generate_structured completed in %.2fs: response=%d chars",
                elapsed, len(result) if result else 0,
            )
            if result:
                logger.debug("Structured response (first 500 chars): %s", result[:500])
            return result
        except Exception as e:
            elapsed = time.time() - start
            logger.error("generate_structured failed after %.2fs: %s", elapsed, e)
            return None

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

        try:
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
        except Exception as e:
            elapsed = time.time() - start
            logger.error("chat_with_tools failed after %.2fs: %s", elapsed, e)
            return ChatToolResponse(content=f"Error: {e}")

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        all_embeddings: list[list[float]] = []
        batch_size = 20  # Gemini allows larger batches than Vertex AI

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            for attempt in range(1, self._max_retries + 1):
                try:
                    response = self._client.embeddings.create(
                        model=self._embedding_model,
                        input=batch,
                    )
                    batch_embeddings = [item.embedding for item in response.data]
                    all_embeddings.extend(batch_embeddings)
                    break
                except Exception as e:
                    logger.warning(f"Embedding batch {i // batch_size} attempt {attempt} failed: {e}")
                    if attempt < self._max_retries:
                        time.sleep(1)
                    else:
                        raise

        return np.array(all_embeddings, dtype=np.float32)

    def classify_post(
        self,
        post_data: dict[str, Any],
        subreddit: str,
        category: str,
        comments_count: int,
    ) -> EnrichedPost:
        enriched = EnrichedPost(
            subreddit=subreddit,
            category=category,
            post=post_data,
            comments_count=comments_count,
        )

        title = post_data.get("title", "")
        selftext = post_data.get("selftext", "")
        post_id = post_data.get("id", "unknown")

        for attempt in range(1, self._max_retries + 1):
            try:
                prompt_template = RETRY_PROMPT if attempt > 1 else CLASSIFICATION_PROMPT
                prompt = prompt_template.format(
                    title=title, selftext=selftext, subreddit=subreddit
                )

                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=1024,
                )

                raw_response = response.choices[0].message.content or ""
                logger.info(f"Raw response for {post_id}: {raw_response[:300] if raw_response else '<EMPTY>'}")

                classification = self.parse_classification(raw_response)
                if classification:
                    enriched.classification = classification
                    enriched.classification_attempts = attempt
                    return enriched

                logger.warning(f"Post {post_id} parse failed on attempt {attempt}")

            except Exception as e:
                logger.warning(f"Post {post_id} error on attempt {attempt}: {e}")

            enriched.classification_attempts = attempt
            if attempt < self._max_retries:
                time.sleep(1)

        enriched.classification_error = f"Failed after {self._max_retries} attempts"
        return enriched

    def parse_classification(self, raw_response: str) -> ComplaintClassification | None:
        response_text = raw_response.strip()

        if response_text in ("...", "…", ""):
            return None

        # Tier 1: Direct JSON parse
        try:
            data = json.loads(response_text)
            return ComplaintClassification(**data)
        except (json.JSONDecodeError, ValueError, ValidationError, KeyError, TypeError):
            pass

        # Tier 2: Extract JSON from markdown code blocks or bare objects
        json_patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
            r"\{[\s\S]*?\}",
        ]
        for pattern in json_patterns:
            matches = re.findall(pattern, response_text)
            for match in matches:
                try:
                    data = json.loads(match)
                    return ComplaintClassification(**data)
                except (json.JSONDecodeError, ValueError, ValidationError, KeyError, TypeError):
                    continue

        logger.warning(f"Failed to parse classification. Response:\n{response_text[:500]}")
        return None
