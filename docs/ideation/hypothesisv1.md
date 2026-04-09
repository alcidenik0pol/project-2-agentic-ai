Build the hypothesis agent. It takes the cluster table (name, post count, upvotes, sample post titles) and outputs 3 business ideas in structured JSON. That's your Step 3, your structured output grab-bag item, and your most grader-visible deliverable all in one.


The hypothesis agent is the simplest agent in the whole system — deliberately. It has one job: take the cluster table and produce business ideas grounded in the data.

Input it receives:
The cluster table from the EDA step. Concretely something like:
json[
  {"cluster": "Workplace Scheduling Abuse", "post_count": 34, "total_upvotes": 48200, "sample_titles": ["Boss scheduled me during class", "Manager ignored my PTO request", "Last minute Saturday shift"]},
  {"cluster": "Tax Filing Friction", "post_count": 18, "total_upvotes": 12400, "sample_titles": ["TurboTax charged me twice", "Can't figure out self-employment taxes", "IRS letter panic"]}
]

What it does:
Single LLM call to Gemini 2.5 Flash with a structured output schema. The prompt says: "You are a business analyst. Given these Reddit complaint clusters ranked by signal strength, identify the top 3 unmet needs and propose a specific business idea for each. Ground every claim in the data provided."
Output schema:
json{
  "ideas": [
    {
      "rank": 1,
      "idea_name": "ShiftShield",
      "pain_point": "Hourly workers have no recourse when managers violate agreed schedules",
      "product_description": "Mobile app that logs agreed availability in writing, auto-generates dispute messages, connects to labor board resources",
      "evidence": {
        "cluster": "Workplace Scheduling Abuse",
        "post_count": 34,
        "total_upvotes": 48200,
        "supporting_posts": ["Boss scheduled me during class", "Manager ignored my PTO request"]
      },
      "confidence": "high"
    }
  ]
}

Why it's simple to build but high value for the rubric:
The hypothesis is derived from data not model weights — the agent can only reference clusters and upvote counts it was explicitly given. The structured JSON output satisfies the structured output grab-bag item. The evidence field with specific post counts and titles satisfies the rubric requirement to "cite evidence and explain reasoning."
The whole agent is essentially one well-crafted prompt plus a Pydantic output schema. Two hours of work maximum.


# Implementation
The prompt:
pythonHYPOTHESIS_PROMPT = """
You are a business analyst specializing in identifying unmet market needs from social data.

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

Clusters:
{clusters_json}
"""

The Pydantic schema:
pythonfrom pydantic import BaseModel
from typing import Literal

class Evidence(BaseModel):
    cluster_name: str
    post_count: int
    total_upvotes: int
    supporting_post_titles: list[str]  # top 3 by upvotes

class BusinessIdea(BaseModel):
    rank: int
    idea_name: str                        # short brandable name
    pain_point: str                       # one sentence, plain language
    product_description: str             # what it does, specifically
    target_user: str                      # who experiences this pain
    evidence: Evidence
    confidence: Literal["high", "medium", "low"]
    confidence_reasoning: str            # why high/medium/low

class HypothesisOutput(BaseModel):
    ideas: list[BusinessIdea]
    analysis_summary: str                # 2-3 sentences on overall pattern
    data_limitations: str                # honest caveat about the dataset

The agent call:
pythonimport json
from app.analyst.providers.gcloud import GCloudProvider

async def run_hypothesis_agent(clusters: list[dict]) -> HypothesisOutput:
    provider = GCloudProvider()
    
    prompt = HYPOTHESIS_PROMPT.format(
        clusters_json=json.dumps(clusters, indent=2)
    )
    
    raw = await provider.generate_text(
        prompt=prompt,
        temperature=0.3,      # low temp for factual grounding
        max_tokens=2000
    )
    
    parsed = json.loads(raw)
    return HypothesisOutput(**parsed)

One thing to add to the provider: your generate_text() currently doesn't support response schema enforcement. Add this to your Gemini API call:
python"generationConfig": {
    "responseMimeType": "application/json",
    "temperature": temperature
}
responseMimeType: application/json forces Gemini to output valid JSON every time, eliminating the markdown code block parsing problem you hit earlier with the expansion step.

Wire it in after clustering:
python# After ThemeClusterer returns clusters
cluster_table = [
    {
        "cluster_name": c.name,
        "post_count": c.post_count,
        "total_upvotes": c.total_upvotes,
        "sample_titles": get_top_titles(c, n=3)
    }
    for c in clustering_result.clusters
]

hypothesis = await run_hypothesis_agent(cluster_table)
That's the entire agent. Want me to write the test for it too, or move to the frontend?