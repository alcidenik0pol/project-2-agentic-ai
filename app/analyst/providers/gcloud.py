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
        logger.debug("generate_text called: prompt=%d chars, temp=%.2f, max_tokens=%d", len(prompt), temperature, max_tokens)
        start = time.time()

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
        result = None
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                result = parts[0].get("text", "")

        elapsed = time.time() - start
        logger.debug("generate_text completed in %.2fs: response=%d chars", elapsed, len(result) if result else 0)
        return result

    def generate_structured(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> str | None:
        """Generate structured JSON from Gemini via REST API.

        Uses responseMimeType: application/json to force valid JSON output.
        """
        logger.debug("generate_structured called: prompt=%d chars, temp=%.2f, max_tokens=%d", len(prompt), temperature, max_tokens)
        start = time.time()

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
            timeout=self._timeout * 3,  # Structured output with large prompts needs more time
        )
        response.raise_for_status()
        data = response.json()
        candidates = data.get("candidates", [])
        result = None
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                result = parts[0].get("text", "")

        elapsed = time.time() - start
        logger.debug(
            "generate_structured completed in %.2fs: response=%d chars",
            elapsed, len(result) if result else 0,
        )
        if result:
            logger.debug("Structured response (first 500 chars): %s", result[:500])
        return result

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

        token = self._get_token()
        response = requests.post(
            self._url,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self._timeout * 3,  # Longer timeout for tool-calling with large contexts
        )
        response.raise_for_status()
        data = response.json()

        logger.debug(f"Gemini chat_with_tools response: {json.dumps(data)[:1000]}")

        elapsed = time.time() - start
        logger.info("chat_with_tools completed in %.2fs", elapsed)

        return self._parse_gemini_tool_response(data)

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
