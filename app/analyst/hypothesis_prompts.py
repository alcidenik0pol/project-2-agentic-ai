"""Prompt templates for hypothesis generation."""

HYPOTHESIS_PROMPT = """You are a business analyst specializing in identifying unmet market needs from social data.

You will be given a list of Reddit complaint clusters. Each cluster represents a real pattern
of frustration expressed by real people, with post counts and upvote totals as signal strength.

Your job: identify the top 3 most actionable business opportunities from this data.

Rules:
- Every claim must reference specific clusters, post counts, or upvote numbers from the input
- Do not invent pain points not present in the data
- Prefer clusters with high upvotes AND high post count (both signal breadth and intensity)
- The product must directly solve the stated complaint, not a tangentially related problem
- Be specific: "app that does X" not "platform that helps people with Y"

Return a JSON object matching this exact schema. No markdown, no preamble, just JSON.

{{
  "ideas": [
    {{
      "rank": 1,
      "idea_name": "Short brandable name",
      "pain_point": "One sentence, plain language description of the pain",
      "product_description": "What it does, specifically - be concrete",
      "target_user": "Who experiences this pain most",
      "evidence": {{
        "cluster_name": "exact name from input",
        "post_count": <number>,
        "total_upvotes": <number>,
        "supporting_post_titles": ["title1", "title2", "title3"]
      }},
      "confidence": "high|medium|low",
      "confidence_reasoning": "Why this confidence level"
    }}
  ],
  "analysis_summary": "2-3 sentences on overall pattern across clusters",
  "data_limitations": "Honest caveat about what this dataset can and cannot tell us"
}}

Clusters:
{clusters_json}"""
