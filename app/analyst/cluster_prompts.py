"""LLM prompt templates for cluster naming."""


CLUSTER_NAMING_PROMPT = """You are an analyst grouping user complaints into semantic clusters.

Below is a list of complaint themes that have been algorithmically grouped together.
Give this cluster a short, descriptive name (3-5 words) that captures the common thread.

Themes in this cluster:
{themes}

Rules:
- 3-5 words maximum
- Use plain, descriptive language (not marketing jargon)
- Focus on the pain point, not the solution
- Return ONLY the cluster name, nothing else
- IMPORTANT: Do not truncate your response. The name must be a complete, grammatically correct phrase. If your response ends with "&", "and", "or", a comma, or is obviously cut off, you have failed. Write a complete name.

Cluster name:"""
