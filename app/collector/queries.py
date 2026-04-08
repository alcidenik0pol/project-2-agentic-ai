"""Search query builders for Reddit complaint detection.

This module provides functions to build Reddit search queries
that target posts likely to contain complaints about specific topics.
"""

import logging
from typing import Literal

logger = logging.getLogger(__name__)

# Terms that indicate frustration or complaints
COMPLAINT_TERMS = [
    "problem",
    "issue",
    "complaint",
    "frustrating",
    "annoying",
    "hate",
    "wish there was",
    "why is there no",
    "missing",
    "broken",
    "doesn't work",
    "terrible",
    "awful",
    "pain point",
    "struggle",
    "difficulty",
]

# Subreddits for general complaint discovery
GENERAL_COMPLAINT_SUBREDDITS = [
    "AskReddit",
    "rant",
    "complaints",
    "unpopularopinion",
]

# Common tech/developer subreddits by domain
DOMAIN_SUBREDDITS = {
    "programming": ["programming", "learnprogramming", "coding", "compsci"],
    "python": ["python", "learnpython", "Pythonforengineers", "django", "flask"],
    "javascript": ["javascript", "learnjavascript", "node", "reactjs", "vuejs"],
    "webdev": ["webdev", "web_design", "frontend", "Backend"],
    "data": ["datascience", "MachineLearning", "analytics", "sql"],
    "devops": ["devops", "kubernetes", "docker", "aws", "sysadmin"],
    "mobile": ["androiddev", "iOSProgramming", "flutterdev", "reactnative"],
    "gaming": ["gaming", "Games", "truegaming", "patientgamers"],
    "finance": ["personalfinance", "investing", "financialindependence"],
    "fitness": ["fitness", "bodybuilding", "loseit", "running"],
    "startups": ["startups", "entrepreneur", "smallbusiness", "SaaS"],
}


def build_complaint_query(
    topic: str,
    include_general_terms: bool = True,
    query_style: Literal["broad", "specific", "frustration"] = "broad",
) -> str:
    """Build a Reddit search query for finding complaints about a topic.

    Args:
        topic: The topic to search for (e.g., "python development").
        include_general_terms: Whether to include complaint-indicating terms.
        query_style: Style of query to build:
            - "broad": Cast wide net, find any mentions
            - "specific": Target specific complaint patterns
            - "frustration": Focus on emotional frustration language

    Returns:
        A search query string for Reddit.

    Examples:
        >>> build_complaint_query("python", query_style="broad")
        'python (problem OR issue OR complaint OR ...)'
        >>> build_complaint_query("docker", query_style="frustration")
        'docker (frustrating OR annoying OR hate OR ...)'
    """
    topic = topic.strip()

    if query_style == "broad":
        # Broad search - topic with any complaint indicator
        if include_general_terms:
            terms = COMPLAINT_TERMS[:8]  # Top 8 most common
            terms_str = " OR ".join(terms)
            return f'({topic}) AND ({terms_str})'
        return topic

    elif query_style == "specific":
        # Specific complaint patterns
        patterns = [
            f'"wish there was" {topic}',
            f'"why is there no" {topic}',
            f'{topic} "doesn\'t work"',
            f'{topic} "no solution"',
            f'{topic} problem',
            f'{topic} broken',
        ]
        return " OR ".join(f'({p})' for p in patterns)

    elif query_style == "frustration":
        # Focus on emotional language
        frustration_terms = [
            "frustrating",
            "annoying",
            "hate",
            "terrible",
            "awful",
            "worst",
            "impossible",
            "nightmare",
        ]
        terms_str = " OR ".join(frustration_terms)
        return f'({topic}) AND ({terms_str})'

    else:
        raise ValueError(f"Unknown query_style: {query_style}")


def get_subreddits_for_topic(
    topic: str,
    include_general: bool = True,
    max_subreddits: int = 5,
) -> list[str]:
    """Get relevant subreddits for a topic.

    Matches topic keywords against known domain subreddits.

    Args:
        topic: The topic to find subreddits for.
        include_general: Whether to include general complaint subreddits.
        max_subreddits: Maximum number of subreddits to return.

    Returns:
        List of subreddit names (without r/ prefix).

    Examples:
        >>> get_subreddits_for_topic("python web development")
        ['python', 'learnpython', 'django', 'flask', 'webdev']
    """
    topic_lower = topic.lower()
    subreddits: list[str] = []

    # Check each domain for keyword matches
    for domain, domain_subs in DOMAIN_SUBREDDITS.items():
        if domain in topic_lower:
            subreddits.extend(domain_subs[:3])  # Top 3 from matching domain

    # If no matches, try partial matching
    if not subreddits:
        for domain, domain_subs in DOMAIN_SUBREDDITS.items():
            if any(word in domain for word in topic_lower.split()):
                subreddits.extend(domain_subs[:2])

    # Add general complaint subreddits if requested
    if include_general and len(subreddits) < max_subreddits:
        subreddits.extend(GENERAL_COMPLAINT_SUBREDDITS[:2])

    # Deduplicate and limit
    seen = set()
    unique = []
    for sub in subreddits:
        if sub.lower() not in seen:
            seen.add(sub.lower())
            unique.append(sub)
            if len(unique) >= max_subreddits:
                break

    return unique


def build_search_queries(
    topic: str,
    styles: list[str] | None = None,
) -> list[tuple[str, str]]:
    """Build multiple search queries for comprehensive coverage.

    Args:
        topic: The topic to search for.
        styles: List of query styles to use. Defaults to all styles.

    Returns:
        List of (query, style) tuples.

    Examples:
        >>> build_search_queries("python")
        [('python (problem OR issue ...)', 'broad'),
         ('((wish there was) python) ...', 'specific'),
         ('(python) AND (frustrating ...)', 'frustration')]
    """
    if styles is None:
        styles = ["broad", "specific", "frustration"]

    queries = []
    for style in styles:
        try:
            query = build_complaint_query(topic, query_style=style)  # type: ignore
            queries.append((query, style))
        except ValueError as e:
            logger.warning(f"Skipping invalid query style {style}: {e}")

    return queries
