"""LLM prompt templates for post classification."""


CLASSIFICATION_PROMPT = """Given this Reddit post, identify the core complaint in 3 words or less.

Return ONLY a JSON object in this exact format:
{
  "theme": "core complaint theme (3 words or less)",
  "is_complaint": true/false,
  "intensity": "low" | "medium" | "high"
}

Rules:
- theme: Maximum 3 words, capture the main pain point
- is_complaint: true if expressing frustration, problem, or dissatisfaction
- intensity: "high" = strong emotion/anger, "medium" = clear complaint, "low" = mild annoyance

Post Title: {title}
Post Body: {selftext}
Subreddit: r/{subreddit}

Return ONLY the JSON object, no additional text."""

RETRY_PROMPT = """IMPORTANT: Your previous response was invalid. You MUST return ONLY valid JSON.

Analyze this Reddit post and return a JSON object with NO additional text, NO markdown, NO explanation.

Post Title: {title}
Post Body: {selftext}
Subreddit: r/{subreddit}

Required JSON format (return EXACTLY this structure):
{{"theme": "3 words max", "is_complaint": true, "intensity": "low"}}
{{"theme": "3 words max", "is_complaint": false, "intensity": "low"}}

Return ONLY the JSON, nothing else:"""
