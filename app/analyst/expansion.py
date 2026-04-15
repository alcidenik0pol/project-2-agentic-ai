"""Theme expansion: expand short theme labels into full descriptions for better embeddings."""

import json
import logging
import re
import time
from typing import Any

from app.analyst.expansion_prompts import EXPANSION_RETRY_PROMPT, THEME_EXPANSION_PROMPT
from app.analyst.models import BatchExpansionResult, ThemeExpansion
from app.config import config

logger = logging.getLogger(__name__)


class ThemeExpander:
    """Expand short theme labels into full descriptions for embedding generation."""

    def __init__(
        self,
        provider: Any,
        batch_size: int = 10,
        max_context_titles: int = 3,
        use_cache: bool = True,
        cache_ttl_seconds: int = 86400,
    ):
        self.provider = provider
        self.batch_size = batch_size
        self.max_context_titles = max_context_titles
        self.use_cache = use_cache
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[ThemeExpansion, float]] = {}

    def expand_themes(
        self,
        canonical_themes: list[str],
        theme_to_posts: dict[str, list[int]],
        posts: list[dict[str, Any]],
    ) -> BatchExpansionResult:
        """Expand all themes in batch, using LLM with post titles as context."""
        start = time.time()
        expansions: dict[str, ThemeExpansion] = {}
        themes_failed: list[str] = []
        api_calls = 0
        cache_hits = 0
        total_llm_time = 0.0  # Track cumulative LLM call time

        # Build context map
        context_map = self._build_context_map(canonical_themes, theme_to_posts, posts)

        # Prepare themes with context
        themes_with_context: list[tuple[str, list[str]]] = []
        for theme in canonical_themes:
            context_titles = [t for _, t, _ in context_map.get(theme, [])]
            themes_with_context.append((theme, context_titles))

        # Batch processing
        for i in range(0, len(themes_with_context), self.batch_size):
            batch = themes_with_context[i : i + self.batch_size]

            # Check cache first
            uncached: list[tuple[str, list[str]]] = []
            for theme, context in batch:
                cached = self._get_cached(theme)
                if cached:
                    expansions[theme] = cached
                    cache_hits += 1
                else:
                    uncached.append((theme, context))

            if not uncached:
                continue

            # LLM expansion for uncached themes
            try:
                batch_start = time.time()
                llm_results = self._expand_batch(uncached)
                total_llm_time += time.time() - batch_start
                for theme, expansion in zip([t for t, _ in uncached], llm_results):
                    expansions[theme] = expansion
                    self._set_cached(theme, expansion)
                    if expansion.expansion_method != "llm":
                        themes_failed.append(theme)
                api_calls += 1
            except Exception as e:
                logger.warning(f"Batch expansion failed: {e}")
                for theme, context in uncached:
                    fallback = self._get_fallback_expansion(theme, [c for c in context])
                    expansions[theme] = fallback
                    themes_failed.append(theme)

        elapsed = time.time() - start
        return BatchExpansionResult(
            expansions=expansions,
            themes_failed=themes_failed,
            processing_time_seconds=round(elapsed, 2),
            api_calls_made=api_calls,
            cache_hits=cache_hits,
            llm_time_seconds=round(total_llm_time, 2),
        )

    def _build_context_map(
        self,
        themes: list[str],
        theme_to_posts: dict[str, list[int]],
        posts: list[dict[str, Any]],
    ) -> dict[str, list[tuple[int, str, int]]]:
        """Build context map with titles sorted by upvotes.

        Returns:
            {theme: [(upvotes, title, post_index), ...]} sorted by upvotes desc.
        """
        context_map: dict[str, list[tuple[int, str, int]]] = {}
        for theme in themes:
            post_indices = theme_to_posts.get(theme, [])
            candidates: list[tuple[int, str, int]] = []
            for idx in post_indices:
                if idx >= len(posts):
                    continue
                upvotes = posts[idx].get("post", {}).get("upvotes", 0)
                title = posts[idx].get("post", {}).get("title", "")
                if title:
                    candidates.append((upvotes, title, idx))
            candidates.sort(key=lambda x: x[0], reverse=True)
            context_map[theme] = candidates[: self.max_context_titles]
        return context_map

    def _expand_batch(
        self, themes_with_context: list[tuple[str, list[str]]]
    ) -> list[ThemeExpansion]:
        """Expand a batch of themes in one LLM call."""
        themes_data = {theme: titles for theme, titles in themes_with_context}

        max_retries = getattr(self.provider, "_max_retries", config.expansion_max_retries)

        for attempt in range(1, max_retries + 1):
            try:
                prompt_template = (
                    EXPANSION_RETRY_PROMPT if attempt > 1 else THEME_EXPANSION_PROMPT
                )
                prompt = prompt_template.format(themes_data=json.dumps(themes_data))
                raw = self.provider.generate_text(
                    prompt, temperature=0.3, max_tokens=2048, use_fast=True,
                )
                if raw:
                    parsed = self._parse_json_response(raw)
                    if parsed:
                        results = []
                        for theme, titles in themes_with_context:
                            desc = parsed.get(theme)
                            if desc:
                                results.append(
                                    ThemeExpansion(
                                        original_theme=theme,
                                        expanded_description=desc,
                                        post_titles_used=titles,
                                        expansion_method="llm",
                                    )
                                )
                            else:
                                results.append(self._get_fallback_expansion(theme, titles))
                        return results
                    else:
                        raise ValueError("Failed to extract JSON from LLM response")
            except Exception as e:
                logger.warning(f"LLM expansion attempt {attempt} failed: {e}")
                if attempt < max_retries:
                    time.sleep(1.0 * attempt)

        # All retries failed
        return [
            self._get_fallback_expansion(t, titles) for t, titles in themes_with_context
        ]

    @staticmethod
    def _parse_json_response(raw: str) -> dict[str, str] | None:
        """Parse JSON from LLM response, handling markdown code blocks and truncation."""
        text = raw.strip()

        # Tier 1: Direct JSON parse
        try:
            result = json.loads(text)
            if isinstance(result, dict):
                return result
        except (json.JSONDecodeError, ValueError):
            pass

        # Tier 2: Extract from markdown code blocks
        patterns = [
            r"```json\s*([\s\S]*?)\s*```",
            r"```\s*([\s\S]*?)\s*```",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    result = json.loads(match.group(1).strip())
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, ValueError):
                    continue

        # Tier 3: Find bare JSON object (handles truncation by trying to close it)
        match = re.search(r"\{[\s\S]*", text)
        if match:
            json_str = match.group(0)
            # If truncated, try to close it
            if not json_str.rstrip().endswith("}"):
                # Count unclosed braces and add closers
                open_count = json_str.count("{") - json_str.count("}")
                if open_count > 0:
                    json_str += "]" * (json_str.count("[") - json_str.count("]"))
                    json_str += "}" * open_count
                try:
                    result = json.loads(json_str)
                    if isinstance(result, dict):
                        return result
                except (json.JSONDecodeError, ValueError):
                    pass

        return None

    def _get_fallback_expansion(
        self, theme: str, post_titles: list[str]
    ) -> ThemeExpansion:
        """Generate fallback expansion without LLM."""
        if post_titles:
            truncated = post_titles[0][:50]
            description = f"{theme.capitalize()}: {truncated}"
            method = "fallback_simple"
        else:
            description = f"Issues related to {theme}"
            method = "fallback_original"
        return ThemeExpansion(
            original_theme=theme,
            expanded_description=description,
            post_titles_used=post_titles,
            expansion_method=method,
        )

    def _get_cached(self, theme: str) -> ThemeExpansion | None:
        """Retrieve cached expansion if still valid."""
        if not self.use_cache:
            return None
        if theme in self._cache:
            expansion, timestamp = self._cache[theme]
            if time.time() - timestamp < self.cache_ttl_seconds:
                return expansion
            del self._cache[theme]
        return None

    def _set_cached(self, theme: str, expansion: ThemeExpansion) -> None:
        """Store expansion in cache."""
        if self.use_cache:
            self._cache[theme] = (expansion, time.time())
