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
from app.analyst.providers.base import ChatToolResponse, LLMProvider, ToolCallInfo
from app.config import config
from app.services.usage_tracker import get_usage_tracker
from app.utils.retry import retry_with_exponential_backoff

logger = logging.getLogger(__name__)


class GCloudProvider(LLMProvider):
    """LLM provider using Google Cloud Vertex AI with Gemini models."""

    def __init__(self):
        """Initialize the Google Cloud provider with configuration from config."""
        self._project = config.gcloud_project
        self._region = config.gcloud_region
        self._timeout = config.gcloud_timeout
        self._max_retries = config.gcloud_max_retries
        self._credentials_path = config.gcloud_service_account_key_path

        # Build the REST endpoint URL for the default (pro) model
        self._url = self._url_for_model(config.gcloud_model)

        # Initialize credentials
        self._initialize_credentials()

        logger.info(
            "GCloudProvider initialized: pro=%s, fast=%s",
            config.gcloud_model, config.gcloud_model_fast,
        )

    def _url_for_model(self, model: str) -> str:
        """Build Vertex AI generateContent URL for a given model name."""
        project_lower = self._project.lower()
        return (
            f"https://{self._region}-aiplatform.googleapis.com/v1/"
            f"projects/{project_lower}/locations/{self._region}/"
            f"publishers/google/models/{model}:generateContent"
        )

    def _initialize_credentials(self):
        """Load service account credentials for API calls."""
        from pathlib import Path

        # Single credentials path: project_root/docs/credentials/credentials.json
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        cred_path = project_root / "docs" / "credentials" / "credentials.json"

        try:
            if cred_path.exists():
                self._credentials = service_account.Credentials.from_service_account_file(
                    str(cred_path),
                    scopes=["https://www.googleapis.com/auth/cloud-platform"],
                )
                logger.info(f"Loaded credentials from: {cred_path}")
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

    def _record_usage(self, data: dict) -> None:
        """Extract token usage from a Gemini generateContent response and record.

        Gemini 2.5 responses include usageMetadata:
        {"promptTokenCount": N, "candidatesTokenCount": M,
         "thoughtsTokenCount": K, "totalTokenCount": T}

        ``thoughtsTokenCount`` is the reasoning tokens billed at output rate.
        Older responses and non-thinking models omit the field; we record 0.

        Skipped in development mode — see ``app.config.Config.is_development``.
        """
        usage = data.get("usageMetadata", {})
        input_tokens = usage.get("promptTokenCount", 0)
        output_tokens = usage.get("candidatesTokenCount", 0)
        thinking_tokens = usage.get("thoughtsTokenCount", 0)
        self._record_raw(input_tokens, output_tokens, thinking_tokens)

    def _record_raw(
        self,
        input_tokens: int,
        output_tokens: int,
        thinking_tokens: int = 0,
    ) -> None:
        """Record raw token counts directly (no response parsing).

        Used by ``_record_usage`` for Gemini generateContent responses and by
        callers whose endpoint returns no ``usageMetadata`` (embeddings).

        Skipped in development mode.
        """
        from app.config import config

        if config.is_development:
            return

        if input_tokens <= 0 and output_tokens <= 0 and thinking_tokens <= 0:
            return

        try:
            tracker = get_usage_tracker()
            tracker.record_usage(input_tokens, output_tokens, thinking_tokens)
            logger.debug(
                "Recorded usage: %d input, %d output, %d thinking tokens",
                input_tokens, output_tokens, thinking_tokens,
            )
        except Exception as e:
            # Don't let usage tracking failures break API calls
            logger.warning(f"Failed to record usage: {e}")

    @staticmethod
    def _estimate_embedding_tokens(texts: list[str]) -> int:
        """Rough word→token estimate for embedding usage tracking.

        The ``text-embedding-004`` endpoint does not return ``usageMetadata``,
        so we estimate input tokens for accounting. Heuristic: ~1.3 tokens per
        whitespace-split word (empirical average for English text). Used only
        for tracker visibility; Vertex AI bills on the actual token count
        regardless of what we record here.
        """
        return sum(int(len(t.split()) * 1.3) for t in texts)

    def get_embeddings(self, texts: list[str]) -> np.ndarray:
        """Generate embeddings using Vertex AI text-embedding-004 REST API.

        Batches texts into groups of 5 (Vertex AI limit per request).

        Args:
            texts: List of strings to embed.

        Returns:
            numpy array of shape (len(texts), embedding_dim).
        """
        all_embeddings: list[list[float]] = []
        batch_size = 5

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = self._get_embedding_batch(batch, i // batch_size)
            all_embeddings.extend(batch_embeddings)

        return np.array(all_embeddings, dtype=np.float32)

    @retry_with_exponential_backoff()
    def _get_embedding_batch(self, batch: list[str], batch_idx: int) -> list[list[float]]:
        """Fetch embeddings for a single batch with retry support."""
        embedding_model = config.clustering_embedding_model
        project_lower = self._project.lower()
        embed_url = (
            f"https://{self._region}-aiplatform.googleapis.com/v1/"
            f"projects/{project_lower}/locations/{self._region}/"
            f"publishers/google/models/{embedding_model}:predict"
        )

        payload = {
            "instances": [{"content": t} for t in batch],
        }

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

        # text-embedding-004 returns no usageMetadata; estimate input tokens
        # so usage tracking reflects embedding cost (billed at input rate only).
        estimated_input = self._estimate_embedding_tokens(batch)
        self._record_raw(estimated_input, 0, 0)

        predictions = data.get("predictions", [])
        result = []
        for pred in predictions:
            emb = pred.get("embeddings", {}).get("values", [])
            if not emb:
                raise ValueError("Empty embedding returned")
            result.append(emb)
        return result

    @property
    def model_name(self) -> str:
        """Return the model name being used."""
        return config.gcloud_model

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return "gcloud"

    @retry_with_exponential_backoff()
    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        use_fast: bool = False,
    ) -> str | None:
        """Generate raw text from Gemini via REST API."""
        model = config.gcloud_model_fast if use_fast else config.gcloud_model
        logger.debug("generate_text: model=%s, prompt=%d chars, temp=%.2f, max_tokens=%d", model, len(prompt), temperature, max_tokens)
        start = time.time()

        url = self._url_for_model(model)
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
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        self._record_usage(data)
        candidates = data.get("candidates", [])
        result = None
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                result = parts[0].get("text", "")

        elapsed = time.time() - start
        logger.debug("generate_text completed in %.2fs: response=%d chars", elapsed, len(result) if result else 0)
        return result

    @retry_with_exponential_backoff()
    def generate_structured(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
        use_fast: bool = False,
    ) -> str | None:
        """Generate structured JSON from Gemini via REST API.

        Uses responseMimeType: application/json to force valid JSON output.
        """
        model = config.gcloud_model_fast if use_fast else config.gcloud_model
        logger.debug("generate_structured: model=%s, prompt=%d chars, temp=%.2f, max_tokens=%d", model, len(prompt), temperature, max_tokens)
        start = time.time()

        url = self._url_for_model(model)
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
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout * 3,  # Structured output with large prompts needs more time
        )
        response.raise_for_status()
        data = response.json()
        self._record_usage(data)
        candidates = data.get("candidates", [])
        result = None
        finish_reason = ""
        if candidates:
            finish_reason = candidates[0].get("finishReason", "")
            if finish_reason == "MAX_TOKENS":
                logger.warning(
                    "generate_structured hit MAX_TOKENS limit (%d). Response may be truncated.",
                    max_tokens,
                )
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                result = parts[0].get("text", "")

        elapsed = time.time() - start
        logger.info(
            "LLM call: %s/%s generate_structured %.2fs (%d chars)",
            self.provider_name, model, elapsed, len(result) if result else 0,
            extra={"llm_call": {
                "provider": self.provider_name,
                "model": model,
                "method": "generate_structured",
                "request": payload,
                "response_summary": {
                    "elapsed_seconds": round(elapsed, 2),
                    "finish_reason": finish_reason,
                    "content_chars": len(result) if result else 0,
                },
            }},
        )
        if result:
            logger.debug("Structured response (first 500 chars): %s", result[:500])
        return result

    def chat_with_tools(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.3,
        use_fast: bool = False,
    ) -> ChatToolResponse:
        """Send a chat request with retry logic for MALFORMED_FUNCTION_CALL."""
        for attempt in range(1, self._max_retries + 1):
            response = self._chat_with_tools_internal(messages, tools, temperature, use_fast)

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

    @retry_with_exponential_backoff()
    def _chat_with_tools_internal(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float = 0.3,
        use_fast: bool = False,
    ) -> ChatToolResponse:
        """Send a chat request with tool definitions via Gemini REST API.

        Converts OpenAI-format tools/messages to Gemini format, calls
        the generateContent endpoint, and parses the response back.
        """
        logger.debug(
            "chat_with_tools called: %d messages, %d tools, temp=%.2f",
            len(messages), len(tools), temperature,
        )
        start = time.time()

        # Convert messages to Gemini contents format
        contents = self._convert_messages_to_gemini(messages)

        # Convert OpenAI tool schemas to Gemini functionDeclarations
        function_declarations = self._convert_tools_to_gemini(tools)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 8192,
            },
        }

        if function_declarations:
            payload["tools"] = [{"functionDeclarations": function_declarations}]

        model = config.gcloud_model_fast if use_fast else config.gcloud_model
        url = self._url_for_model(model)
        token = self._get_token()
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout * 3,  # Longer timeout for tool-calling with large contexts
        )
        response.raise_for_status()
        data = response.json()
        self._record_usage(data)

        logger.debug(f"Gemini chat_with_tools response: {json.dumps(data)[:1000]}")

        elapsed = time.time() - start
        parsed = self._parse_gemini_tool_response(data)
        logger.info(
            "LLM call: %s/%s chat_with_tools %.2fs (%d tool_calls)",
            self.provider_name, model, elapsed, len(parsed.tool_calls),
            extra={"llm_call": {
                "provider": self.provider_name,
                "model": model,
                "method": "chat_with_tools",
                "request": payload,
                "response_summary": {
                    "elapsed_seconds": round(elapsed, 2),
                    "finish_reason": (data.get("candidates") or [{}])[0].get("finishReason", ""),
                    "content_chars": len(parsed.content) if parsed.content else 0,
                    "tool_call_count": len(parsed.tool_calls),
                    "tool_call_names": [tc.name for tc in parsed.tool_calls],
                },
            }},
        )

        return parsed

    def _convert_messages_to_gemini(
        self, messages: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert OpenAI-format messages to Gemini contents format."""
        contents: list[dict[str, Any]] = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                # Gemini doesn't have system role in contents; prepend as user
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"System instructions: {content}"}],
                })
                contents.append({
                    "role": "model",
                    "parts": [{"text": "Understood. I will follow these instructions."}],
                })
            elif role == "user":
                contents.append({
                    "role": "user",
                    "parts": [{"text": content}],
                })
            elif role == "assistant":
                parts: list[dict[str, Any]] = []
                if content:
                    parts.append({"text": content})
                # Handle tool calls from assistant
                tool_calls = msg.get("tool_calls", [])
                for tc in tool_calls:
                    func = tc.get("function", {})
                    parts.append({
                        "functionCall": {
                            "name": func.get("name", ""),
                            "args": json.loads(func.get("arguments", "{}")),
                        }
                    })
                if not parts:
                    parts.append({"text": ""})
                contents.append({"role": "model", "parts": parts})
            elif role == "tool":
                # Tool response -> functionResponse in Gemini
                # The "name" must match the function name, not the call ID.
                # We store it in tool_call_id as "name_index" format.
                tool_call_id = msg.get("tool_call_id", "")
                tool_content = msg.get("content", "")
                # Extract function name from tool_call_id (format: "name_N")
                func_name = tool_call_id.rsplit("_", 1)[0] if "_" in tool_call_id else tool_call_id
                contents.append({
                    "role": "function",
                    "parts": [{
                        "functionResponse": {
                            "name": func_name,
                            "response": {"result": tool_content},
                        }
                    }],
                })

        return contents

    def _convert_tools_to_gemini(
        self, tools: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Convert OpenAI function-calling tool schemas to Gemini functionDeclarations."""
        declarations = []
        for tool in tools:
            func = tool.get("function", {})
            params = func.get("parameters", {})

            # Convert JSON Schema properties to Gemini schema format
            properties = params.get("properties", {})
            required = params.get("required", [])

            gemini_params: dict[str, Any] = {"type": "object"}
            if properties:
                gemini_params["properties"] = {}
                for prop_name, prop_def in properties.items():
                    gemini_params["properties"][prop_name] = {
                        "type": prop_def.get("type", "string"),
                        "description": prop_def.get("description", ""),
                    }
            if required:
                gemini_params["required"] = required

            declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": gemini_params,
            })

        return declarations

    def _parse_gemini_tool_response(self, data: dict) -> ChatToolResponse:
        """Parse Gemini generateContent response into ChatToolResponse."""
        candidates = data.get("candidates", [])
        if not candidates:
            logger.warning("No candidates in Gemini response")
            return ChatToolResponse(content="No response from model")

        parts = candidates[0].get("content", {}).get("parts", [])
        content_parts = []
        tool_calls = []

        for i, part in enumerate(parts):
            if "text" in part:
                content_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(ToolCallInfo(
                    id=f"{fc.get('name', 'call')}_{i}",
                    name=fc.get("name", ""),
                    arguments=json.dumps(fc.get("args", {})),
                ))

        if not content_parts and not tool_calls:
            # Check for finish reason
            finish_reason = candidates[0].get("finishReason", "unknown")
            logger.warning(f"Empty response from Gemini. finishReason={finish_reason}, parts={parts}")

        return ChatToolResponse(
            content="\n".join(content_parts) if content_parts else None,
            tool_calls=tool_calls,
        )

    def classify_post(
        self,
        post_data: dict[str, Any],
        subreddit: str,
        category: str,
        comments_count: int,
        use_fast: bool = False,
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

        # Pick model based on use_fast flag
        model = config.gcloud_model_fast if use_fast else config.gcloud_model

        # Try classification with parse-level retries
        for attempt in range(1, self._max_retries + 1):
            try:
                # Use retry prompt for subsequent attempts
                prompt_template = RETRY_PROMPT if attempt > 1 else CLASSIFICATION_PROMPT
                prompt = prompt_template.format(
                    title=title, selftext=selftext, subreddit=subreddit
                )

                raw_response = self._classify_post_call(prompt, model)
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
                # If the retry decorator exhausted retries, stop here
                enriched.classification_attempts = attempt
                enriched.classification_error = str(e)
                return enriched

            enriched.classification_attempts = attempt

        # All parse retries exhausted
        enriched.classification_error = f"Failed after {self._max_retries} attempts"
        logger.error(f"Post {post_id} classification failed after all retries")
        return enriched

    @retry_with_exponential_backoff()
    def _classify_post_call(self, prompt: str, model: str) -> str:
        """Single Gemini REST API call for post classification with retry support."""
        url = self._url_for_model(model)
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 256,
                # Classification is structured JSON extraction at temp=0.1
                # ({theme, is_complaint, intensity}) — no reasoning needed.
                # Disabling thinking on Flash saves billed reasoning tokens
                # (Flash supports thinkingBudget=0; Pro minimum is 128).
                "thinkingConfig": {"thinkingBudget": 0},
            },
        }

        token = self._get_token()
        response = requests.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout,
        )
        response.raise_for_status()

        data = response.json()
        self._record_usage(data)
        raw_response = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                raw_response = parts[0].get("text", "")
        return raw_response

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
