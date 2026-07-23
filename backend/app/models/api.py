"""Pydantic models for the REST API request/response payloads."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ── Request models ──

class AnalysisRequest(BaseModel):
    """POST /api/v1/analysis request body."""
    query: str = Field(..., min_length=3, max_length=500, description="Topic to analyze")
    data_source: Literal[
        "reddit_live",
        "reddit_v2",
        "reddit_v3",
        "pushshift",
        "sample_default",
        "sample_gaming",
        "linanqiu",
    ] = Field("pushshift", description="Data source for analysis")


class CancelRequest(BaseModel):
    """WebSocket cancel message."""
    run_id: str


# ── Response models ──

class AnalysisResponse(BaseModel):
    """POST /api/v1/analysis 202 response."""
    run_id: str
    websocket_url: str


class HealthResponse(BaseModel):
    """GET /api/v1/health response."""
    status: str = "healthy"
    version: str = "1.0.0"
    llm_provider: str
    data_source: str


class RateLimitStatus(BaseModel):
    """GET /api/v1/rate-limit response."""
    requests_in_window: int
    requests_remaining: int
    seconds_until_reset: float
    is_throttled: bool
    limit: int = 10
    seconds_until_next_request: float = 0.0


class UsageResponse(BaseModel):
    """GET /api/v1/usage response - Gemini token usage stats."""
    tracking_enabled: bool = Field(
        True, description="False in development mode: token counting and limits are off"
    )
    used: int = Field(..., description="Total tokens used this month")
    limit: int = Field(..., description="Monthly token limit")
    remaining: int = Field(..., description="Tokens remaining")
    percent_remaining: float = Field(..., description="Percentage of quota remaining (0-100)")
    resets_at: str = Field(..., description="ISO datetime when usage resets")
    month: str = Field(..., description="Current billing month (YYYY-MM)")
    input_tokens: int = Field(0, description="Input/prompt tokens used")
    output_tokens: int = Field(0, description="Output/completion tokens used (visible candidates)")
    thinking_tokens: int = Field(0, description="Gemini 2.5 reasoning tokens (billed at output rate)")


class SupportingPostAPI(BaseModel):
    """A single Reddit post cited as evidence."""
    title: str
    url: str
    upvotes: int
    subreddit: str
    created_utc: str | None = None


class HypothesisEvidenceAPI(BaseModel):
    """Evidence supporting a business idea."""
    cluster_name: str
    cluster_themes: list[str] = Field(default_factory=list)
    post_count: int
    total_upvotes: int
    shown_post_count: int = 0
    supporting_posts: list[SupportingPostAPI] = Field(default_factory=list)


class BusinessIdeaAPI(BaseModel):
    """A single business hypothesis."""
    rank: int
    idea_name: str
    pain_point: str
    solution_description: str
    core_features: str | None = None
    revenue_model: str | None = None
    first_user_step: str | None = None
    target_user: str
    evidence: HypothesisEvidenceAPI
    confidence: Literal["high", "medium", "low"]
    confidence_reasoning: str


class HypothesisOutputAPI(BaseModel):
    """Complete hypothesis result."""
    ideas: list[BusinessIdeaAPI] = Field(default_factory=list)
    analysis_summary: str = ""
    data_limitations: str = ""
    source_cluster_count: int = 0
    processing_time_seconds: float = 0.0
    model_used: str = ""
    generated_at: datetime | None = None


class ResultResponse(BaseModel):
    """GET /api/v1/results/{run_id} response."""
    run_id: str
    status: Literal["completed", "failed", "running"]
    hypothesis: HypothesisOutputAPI | None = None
    report_content: str | None = None
    agent_results: dict[str, Any] | None = None
    classification_eda: dict[str, Any] | None = None
    clustering_eda: dict[str, Any] | None = None
    error: str | None = None


# ── WebSocket message models ──

class WSMessage(BaseModel):
    """Generic WebSocket message envelope."""
    type: str
    data: dict[str, Any] = Field(default_factory=dict)
