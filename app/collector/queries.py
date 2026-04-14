"""Search query builders for Reddit complaint detection.

This module provides functions to build Reddit search queries
that target posts likely to contain complaints about specific topics.
"""

import logging
from pathlib import Path
from typing import Literal

from app.config import config

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


def _load_curated_subreddits() -> dict[str, list[str]]:
    """Load curated subreddit list from docs/ideation/reddit/*.md.

    Parses the markdown file with format:
        DOMAIN HEADER (N)
        r/subreddit — description
    """
    curated: dict[str, list[str]] = {}

    list_path = Path("docs/ideation/reddit/20260407_subredditlist.md")
    if not list_path.exists():
        project_root = Path(__file__).resolve().parents[3]
        list_path = project_root / "docs" / "ideation" / "reddit" / "20260407_subredditlist.md"

    if not list_path.exists():
        logger.warning(f"Curated subreddit list not found at {list_path}, falling back to DOMAIN_SUBREDDITS")
        return {k: list(v) for k, v in DOMAIN_SUBREDDITS.items()}

    logger.debug("Loading curated subreddits from %s", list_path)

    current_domain: str | None = None
    skipped_lines = 0
    with open(list_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            # Detect domain headers: all-caps line with parenthesized count
            # e.g. "FINANCE & MONEY (8)" or "WORK & CAREER (7)"
            if line and line == line.upper() and "(" in line and ")" in line:
                domain_name = line.split("(")[0].strip().lower()
                domain_name = domain_name.replace(" & ", "_").replace(" ", "_")
                current_domain = domain_name
                if current_domain not in curated:
                    curated[current_domain] = []
                logger.debug("Parsed domain header: '%s' -> '%s'", line[:60], domain_name)
            # Extract subreddit names from "r/name — description" lines
            elif line.startswith("r/") and current_domain:
                # Split on em-dash or en-dash or plain dash
                parsed = False
                for sep in [" — ", " – ", " - ", "\u2014", "\u2013"]:
                    if sep in line:
                        sub_name = line.split(sep)[0].strip().replace("r/", "")
                        # Strip parenthetical notes like "(AITA)" from subreddit name
                        if " (" in sub_name:
                            sub_name = sub_name.split(" (")[0].strip()
                        if sub_name:
                            curated[current_domain].append(sub_name)
                        parsed = True
                        break
                # Handle comma-separated r/ entries without descriptions
                if not parsed and "r/" in line:
                    for part in line.split(","):
                        part = part.strip()
                        if part.startswith("r/"):
                            sub_name = part.replace("r/", "").strip()
                            if sub_name:
                                curated[current_domain].append(sub_name)
                if not parsed and "r/" not in line:
                    skipped_lines += 1

    if skipped_lines:
        logger.debug("Skipped %d unparseable lines in curated list", skipped_lines)

    # Merge in the hardcoded DOMAIN_SUBREDDITS for tech coverage
    for domain, subs in DOMAIN_SUBREDDITS.items():
        if domain not in curated:
            curated[domain] = list(subs)
        else:
            existing = {s.lower() for s in curated[domain]}
            for s in subs:
                if s.lower() not in existing:
                    curated[domain].append(s)

    # Log per-domain breakdown at debug level
    for domain, subs in curated.items():
        logger.debug("  Domain '%s': %d subreddits", domain, len(subs))

    logger.info(
        "Loaded %d curated subreddits across %d domains from file",
        sum(len(v) for v in curated.values()), len(curated),
    )
    return curated


# Cache at module load time
CURATED_SUBREDDITS = _load_curated_subreddits()

# Common stop words to strip from user queries for Reddit search
_STOP_WORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "must",
    "it", "its", "this", "that", "these", "those", "i", "me", "my", "we",
    "our", "you", "your", "he", "she", "they", "them", "their", "what",
    "which", "who", "whom", "how", "when", "where", "why", "all", "each",
    "every", "both", "few", "more", "most", "other", "some", "such", "no",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "about", "above", "after", "before", "between", "into", "through",
    "during", "here", "there", "out", "up", "down", "if", "then", "once",
    "find", "get", "ideas", "unmet", "needs", "common", "complaints",
    "people", "things", "something", "anything", "everything",
})


def extract_search_keywords(query: str) -> str:
    """Extract concise search keywords from a verbose user query.

    User queries like "Find game ideas from unmet player needs and complaints"
    produce terrible Reddit search results. This strips filler words and
    returns the core topic phrase (1-3 words).

    Args:
        query: Raw user query string.

    Returns:
        Concise keyword string, e.g. "video games" or "personal finance".
    """
    words = query.lower().split()
    keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 1]

    if not keywords:
        # Fallback: use original query stripped of punctuation
        return query.strip()

    # Cap at 3 keywords for Reddit search effectiveness
    result = " ".join(keywords[:3])
    logger.debug(
        "Extracted search keywords: '%s' from query: '%s'",
        result, query,
    )
    return result


def build_complaint_query(
    topic: str,
    include_general_terms: bool = True,
    query_style: Literal["broad", "specific", "frustration", "loose"] = "broad",
) -> str:
    """Build a Reddit search query for finding complaints about a topic.

    Args:
        topic: The topic to search for (e.g., "python development").
        include_general_terms: Whether to include complaint-indicating terms.
        query_style: Style of query to build:
            - "broad": Topic AND complaint terms (original, may return 0 results)
            - "specific": Target specific complaint patterns
            - "frustration": Focus on emotional frustration language
            - "loose": Topic OR complaint terms (broader, more results)

    Returns:
        A search query string for Reddit.

    Examples:
        >>> build_complaint_query("python", query_style="broad")
        'python (problem OR issue OR complaint OR ...)'
        >>> build_complaint_query("docker", query_style="frustration")
        'docker (frustrating OR annoying OR hate OR ...)'
    """
    topic = topic.strip()

    if query_style == "loose":
        # Loose search - topic OR complaint terms
        # Casts a wide net without requiring both to match
        if include_general_terms:
            terms = COMPLAINT_TERMS[:6]
            terms_str = " OR ".join([topic] + terms)
            return f'({terms_str})'
        return topic

    elif query_style == "broad":
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
    max_subreddits: int | None = None,
) -> list[str]:
    """Get relevant subreddits for a topic.

    Matches topic keywords against known domain subreddits.

    Args:
        topic: The topic to find subreddits for.
        include_general: Whether to include general complaint subreddits.
        max_subreddits: Maximum number of subreddits to return (default from config).

    Returns:
        List of subreddit names (without r/ prefix).

    Examples:
        >>> get_subreddits_for_topic("python web development")
        ['python', 'learnpython', 'django', 'flask', 'webdev']
    """
    if max_subreddits is None:
        max_subreddits = config.max_subreddits

    topic_lower = topic.lower()
    subreddits: list[str] = []

    # Check each domain for keyword matches against curated list
    for domain, domain_subs in CURATED_SUBREDDITS.items():
        if domain in topic_lower:
            subreddits.extend(domain_subs[:5])  # Top 5 from matching domain

    # If no matches, try partial matching
    if not subreddits:
        for domain, domain_subs in CURATED_SUBREDDITS.items():
            if any(word in domain for word in topic_lower.split()):
                subreddits.extend(domain_subs[:3])

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
