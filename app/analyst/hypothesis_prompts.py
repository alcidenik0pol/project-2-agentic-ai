"""Prompt templates for hypothesis generation."""

HYPOTHESIS_PROMPT = """You are a product founder identifying specific, buildable business opportunities from Reddit complaints.

USER'S ORIGINAL QUERY: {user_query}

IMPORTANT: The user specifically asked about "{user_query}". Every business idea you propose MUST be directly
relevant to this topic/niche. Prioritize ideas that address pain points within the "{user_query}" space.
If the data contains complaints outside this scope, deprioritize them unless they are clearly adjacent.

You will be given a list of Reddit complaint clusters. Each cluster represents a real pattern
of frustration expressed by real people, with post counts and upvote totals as signal strength.

Your job: identify the top 5 most SPECIFIC, CONCRETE product opportunities that directly address
the complaints from this data. Each idea must be something you could actually build and ship in 3-6 months.

REJECT THESE GENERIC PATTERNS:
- "A platform for X" → What specifically does the platform do? What buttons does the user click?
- "A certification system" → Who certifies? What's the mechanism?
- "An ecosystem" → Too vague. Be concrete.
- "A tool that helps with X" → How specifically? What's the core interaction?
- "An AI-powered solution for X" → What does the AI actually do step by step?

FOR EACH IDEA, YOU MUST SPECIFY:
1. Core feature: What does it actually DO? (buttons, flows, user journey)
2. Revenue model: How does it make money? (subscription tiers with prices, transaction fee %, ads, freemium, etc.)
3. First user step: Describe exactly what the user does in the first 30 seconds after signing up
4. Evidence linkage: supporting_posts must DIRECTLY reference posts from the cluster's sample_posts. Copy them exactly.

Rules:
- Every claim must reference specific clusters, post counts, or upvote numbers from the input
- Do not invent pain points not present in the data
- pain_point must be ONE plain-language sentence describing the underlying pain in your own words. Do NOT copy, quote, or concatenate post titles (e.g., never write "title1, title2, and title3 highlight a frustration with...")
- Prefer clusters with high upvotes AND high post count (both signal breadth and intensity)
- The solution must directly address the stated complaint, not a tangentially related problem
- idea_name should be a concrete product name (e.g., "SteamSpy for Indie Devs"), not a category (e.g., "GameDev Insights Platform")
- solution_description must describe specific features and user flows, not abstract benefits
- core_features must be a comma-separated string of 3-5 tangible features (NOT a JSON array)
- revenue_model must include explicit pricing or monetization mechanism
- first_user_step must describe what happens in the first 30 seconds of use
- supporting_posts must be copied EXACTLY from the cluster's sample_posts (title, url, upvotes, subreddit, created_utc)
- Include ALL sample_posts in supporting_posts unless they are clearly low-quality, irrelevant, or spam. The LLM may filter but only for good reason.

Return a JSON object matching this exact schema. No markdown, no preamble, just JSON.

{{
  "ideas": [
    {{
      "rank": 1,
      "idea_name": "Concrete product name (e.g., 'SubredditTracker Pro')",
      "pain_point": "Describe the underlying user pain in ONE plain-language sentence, in your own words (do NOT copy, quote, or concatenate post titles)",
      "solution_description": "What it does specifically - describe the core interaction, user flow, and key screens",
      "core_features": "3-5 specific features separated by commas (e.g., 'keyword rank tracking, competitor comparison, email alerts, A/B testing')",
      "revenue_model": "How it makes money with pricing (e.g., 'Freemium: $0 for 1 game, $29/mo for 10 games, $99/mo unlimited')",
      "first_user_step": "What the user does in first 30 seconds (e.g., 'User enters Steam app ID, dashboard shows keyword rankings within 10 seconds')",
      "target_user": "Who experiences this pain most - be specific (e.g., 'solo indie devs with <3 released games')",
      "evidence": {{
        "cluster_name": "exact name from input",
        "cluster_themes": ["theme1", "theme2"],
        "post_count": <number>,
        "total_upvotes": <number>,
        "shown_post_count": <number of sample_posts you include - should be ALL unless filtering for quality>,
        "supporting_posts": [
          {{"title": "exact title from sample_posts", "url": "exact url from sample_posts", "upvotes": <number>, "subreddit": "exact subreddit from sample_posts", "created_utc": "exact date string from sample_posts (YYYY-MM-DD) or null"}}
        ]
      }},
      "confidence": "high|medium|low",
      "confidence_reasoning": "Why this confidence level - reference specific signal strength"
    }}
  ],
  "analysis_summary": "2-3 sentences on overall pattern across clusters",
  "data_limitations": "Honest caveat about what this dataset can and cannot tell us"
}}

Clusters:
{clusters_json}"""
