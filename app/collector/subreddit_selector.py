"""LLM-based subreddit selection and ranking.

Uses an LLM to dynamically select the most relevant subreddits
for a given topic from the curated knowledge base, with a
keyword-based fallback if the LLM call fails.
"""

import json
import logging

from app.analyst.providers.base import LLMProvider
from app.collector.subreddit_loader import load_subreddit_descriptions, format_subreddit_for_prompt
from app.collector.queries import CURATED_SUBREDDITS
from app.config import config

logger = logging.getLogger(__name__)

SUBREDDIT_SELECTION_PROMPT = """You are selecting relevant subreddits for Reddit complaint analysis.

TOPIC: {topic}

AVAILABLE SUBREDDITS:
{subreddit_list}

Your task:
1. Select ALL subreddits that could contain complaints about this topic
2. Rank them by relevance (most relevant first)
3. Return EXACTLY {max_subreddits} subreddits (or fewer if topic is very niche)

Rules:
- Consider both direct topic matches AND adjacent domains
- Include general complaint subreddits if topic is broad
- Use the descriptions to understand each subreddit's focus
- Return subreddit names WITHOUT "r/" prefix

Output format (strict JSON):
{{
    "selected": ["subreddit1", "subreddit2", ...],
    "reasoning": "Brief explanation"
}}
"""


def _get_provider() -> LLMProvider:
    """Get the configured LLM provider."""
    from app.analyst.providers import get_provider
    return get_provider(config.llm_provider)


def _build_description_list() -> str:
    """Build subreddit list from JSON descriptions for LLM prompt."""
    descriptions = load_subreddit_descriptions(
        min_subscribers=1000,
        include_over18=False,
    )

    if not descriptions:
        logger.warning("No descriptions loaded, using legacy format")
        return _build_legacy_list()

    # Format by subscriber count (descending), limit to 60
    formatted = []
    for name, metadata in sorted(
        descriptions.items(),
        key=lambda x: -x[1].get("subscribers", 0),
    ):
        formatted.append(format_subreddit_for_prompt(name, metadata))

    logger.info("Built description list with %d subreddits", len(formatted[:60]))
    return "\n".join(formatted[:60])


def _build_legacy_list() -> str:
    """Fallback: build list from legacy curated format."""
    formatted = []
    for domain, subs in CURATED_SUBREDDITS.items():
        formatted.append(f"\n{domain.upper()}:\n" + ", ".join(subs[:20]))
    return "\n".join(formatted)


def select_subreddits_with_llm(
    topic: str,
    curated_subreddits: dict[str, list[str]] | None = None,
    max_subreddits: int | None = None,
    provider: LLMProvider | None = None,
) -> list[str]:
    """Use LLM to select and rank relevant subreddits for a topic.

    Args:
        topic: The user's topic/niche
        curated_subreddits: Dict mapping domains to subreddit lists (legacy, optional)
        max_subreddits: Maximum number of subreddits to return (default from config)
        provider: LLM provider (uses default if None)

    Returns:
        List of selected subreddit names (without r/ prefix), ranked by relevance
    """
    if max_subreddits is None:
        max_subreddits = config.max_subreddits

    if provider is None:
        provider = _get_provider()

    # Build subreddit list with descriptions (falls back to legacy)
    subreddit_list = _build_description_list()

    prompt = SUBREDDIT_SELECTION_PROMPT.format(
        topic=topic,
        subreddit_list=subreddit_list,
        max_subreddits=max_subreddits,
    )

    logger.debug(
        "Subreddit selection prompt for topic '%s': %d chars",
        topic, len(prompt),
    )

    try:
        response = provider.generate_structured(
            prompt=prompt,
            temperature=0.3,
            max_tokens=4096,
            use_fast=True,
        )

        if not response:
            logger.warning(
                "LLM returned empty response for subreddit selection (topic='%s')",
                topic,
            )
            return _fallback_selection(topic, max_subreddits)

        logger.debug(
            "Subreddit selection raw response (%d chars): %s",
            len(response), response[:500],
        )

        result = json.loads(response)
        selected = result.get("selected", [])

        if not selected:
            logger.warning(
                "LLM returned empty subreddit list (topic='%s', response keys=%s)",
                topic, list(result.keys()),
            )
            return _fallback_selection(topic, max_subreddits)

        # Validate subreddit names (basic sanity check)
        validated = [s for s in selected if s and isinstance(s, str) and len(s) < 50]
        rejected = len(selected) - len(validated)
        if rejected:
            logger.debug("Rejected %d invalid subreddit names from LLM output", rejected)
        logger.info(f"LLM selected {len(validated)} subreddits for topic '{topic}'")
        if result.get("reasoning"):
            logger.info(f"LLM reasoning: {result['reasoning']}")

        # Persist subreddit selection log
        try:
            from app.agents.tools.run_logger import save_subreddit_selection
            save_subreddit_selection(
                topic=topic,
                selected=validated[:max_subreddits],
                reasoning=result.get("reasoning", ""),
                prompt=prompt,
                fallback_used=False,
                available_count=subreddit_list.count("\n") + 1,
            )
        except Exception as log_err:
            logger.warning(f"Failed to save subreddit selection log: {log_err}")

        return validated[:max_subreddits]

    except json.JSONDecodeError as e:
        logger.error(
            "LLM subreddit selection returned invalid JSON (topic='%s'): %s. "
            "Raw response (%d chars): %s",
            topic, e, len(response) if response else 0,
            response[:500] if response else "<none>",
        )
        return _fallback_selection(topic, max_subreddits)
    except Exception as e:
        logger.error(
            "LLM subreddit selection failed (topic='%s', error_type=%s): %s",
            topic, type(e).__name__, e,
        )
        return _fallback_selection(topic, max_subreddits)


def _fallback_selection(
    topic: str,
    max_subreddits: int,
) -> list[str]:
    """Fallback keyword-based selection if LLM fails."""
    curated_subreddits = CURATED_SUBREDDITS
    logger.info("Using fallback keyword-based subreddit selection for topic '%s'", topic)
    topic_lower = topic.lower()
    topic_words = topic_lower.split()
    scored: list[tuple[int, str]] = []

    # Score each domain by topic overlap
    for domain, subs in curated_subreddits.items():
        score = 0
        if domain in topic_lower:
            score += 3  # Direct domain match
        elif any(word in domain for word in topic_words):
            score += 2  # Partial domain match
        # Also check if subreddit names match topic words
        for sub in subs:
            if any(word in sub.lower() for word in topic_words):
                score += 1
                break

        if score > 0:
            logger.debug(
                "Fallback: domain '%s' matched (score=%d), adding %d subreddits",
                domain, score, len(subs),
            )
            for sub in subs:
                scored.append((score, sub))

    if not scored:
        logger.warning("Fallback: no domains matched topic '%s', using general subreddits only", topic)

    # Sort by score descending, then take top subreddits
    scored.sort(key=lambda x: -x[0])
    selected = [sub for _, sub in scored]

    # Add general complaint subreddits as fallback
    general = ["AskReddit", "rant", "offmychest", "unpopularopinion", "complaints"]
    selected.extend(general)

    # Deduplicate and cap
    seen = set()
    unique = []
    for s in selected:
        sl = s.lower()
        if sl not in seen:
            seen.add(sl)
            unique.append(s)
            if len(unique) >= max_subreddits:
                break

    logger.info(
        "Fallback selection returned %d subreddits (%d from domain matches, %d general, %d duplicates removed)",
        len(unique), len(scored), len(general), len(selected) - len(unique),
    )

    # Persist fallback selection log
    try:
        from app.agents.tools.run_logger import save_subreddit_selection
        save_subreddit_selection(
            topic=topic,
            selected=unique,
            reasoning="Keyword-based fallback (LLM call failed)",
            prompt="",
            fallback_used=True,
        )
    except Exception as log_err:
        logger.warning(f"Failed to save subreddit selection log: {log_err}")

    return unique
