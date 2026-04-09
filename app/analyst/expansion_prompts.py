"""Prompt templates for theme expansion."""

THEME_EXPANSION_PROMPT = """You are analyzing Reddit complaints to improve semantic clustering.

Your task: Expand each short theme label into a full, descriptive sentence that captures the essence of the complaint.

For each theme, you'll receive:
1. The theme label (2-4 words)
2. 3 example post titles that exemplify this complaint

Your expanded description should:
- Be 10-20 words long
- Include specific details from the post titles
- Capture the emotional nuance (frustration, anxiety, confusion)
- Use natural language similar to the original posts
- Focus on the pain point, not solutions

Output format: Return ONLY a JSON object mapping each theme to its expanded description.

Example input:
{{
  "workplace frustration": ["My boss ignored my PTO request", "I hate my corporate job", "Toxic work environment"]
}}

Example output:
{{
  "workplace frustration": "Frustration with toxic workplace environments, unreasonable management demands, and lack of work-life balance"
}}

Real data to process:
{themes_data}

Return ONLY the JSON object, no additional text."""

EXPANSION_RETRY_PROMPT = """IMPORTANT: Your previous response was invalid. Return ONLY valid JSON.

Expand these theme labels into full descriptions:
{themes_data}

Output format (return EXACTLY this structure):
{{"theme": "expanded description as a full sentence"}}

Return ONLY the JSON, nothing else:"""
