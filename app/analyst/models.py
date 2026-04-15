"""Pydantic models for post classification."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ComplaintClassification(BaseModel):
    """Classification result for a single Reddit post."""

    theme: str = Field(..., description="Core complaint theme in 3 words or less")
    is_complaint: bool = Field(..., description="Whether the post expresses a complaint")
    intensity: Literal["low", "medium", "high"] = Field(
        ..., description="Intensity level of the complaint"
    )


class EnrichedPost(BaseModel):
    """A Reddit post enriched with classification data."""

    # Original post data
    subreddit: str
    category: str
    post: dict[str, Any]
    comments_count: int

    # Classification data
    classification: ComplaintClassification | None = None
    classification_error: str | None = None
    classification_attempts: int = 0

    @property
    def post_id(self) -> str:
        """Extract the Reddit post ID."""
        return self.post.get("id", "unknown")

    @property
    def title(self) -> str:
        """Extract the post title."""
        return self.post.get("title", "")

    @property
    def selftext(self) -> str:
        """Extract the post body text."""
        return self.post.get("selftext", "")


class ClassificationResult(BaseModel):
    """Container for batch classification results with metadata."""

    # Results
    posts: list[EnrichedPost]

    # Metadata
    source_files: list[str] = Field(default_factory=list)
    classified_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_seconds: float = 0.0
    model_used: str = ""

    @property
    def total_posts(self) -> int:
        """Total number of posts in the result."""
        return len(self.posts)

    @property
    def successful_classifications(self) -> int:
        """Count of successfully classified posts."""
        return sum(1 for p in self.posts if p.classification is not None)

    @property
    def failed_classifications(self) -> int:
        """Count of failed classifications."""
        return sum(1 for p in self.posts if p.classification_error is not None)


class ThemeCluster(BaseModel):
    """A cluster of related complaint themes."""

    cluster_id: int = Field(..., description="Unique cluster identifier")
    name: str = Field(..., description="LLM-generated cluster name (3-5 words)")
    themes: list[str] = Field(default_factory=list, description="Canonical themes in this cluster")
    post_count: int = Field(0, description="Total posts across all themes in cluster")
    total_upvotes: int = Field(0, description="Sum of upvotes across all posts in cluster")


class ThemeExpansion(BaseModel):
    """Result of expanding a theme label into a full description."""

    original_theme: str = Field(..., description="Canonical theme (e.g., 'workplace frustration')")
    expanded_description: str = Field(..., description="Full sentence for embedding")
    post_titles_used: list[str] = Field(default_factory=list, description="Titles used as context")
    expansion_method: str = Field(..., description="'llm' | 'fallback_simple' | 'fallback_original'")


class BatchExpansionResult(BaseModel):
    """Results from expanding multiple themes in batch."""

    expansions: dict[str, ThemeExpansion] = Field(default_factory=dict)
    themes_failed: list[str] = Field(default_factory=list)
    processing_time_seconds: float = 0.0
    api_calls_made: int = 0
    cache_hits: int = 0


class ClusteringResult(BaseModel):
    """Result of the theme clustering pipeline."""

    clusters: list[ThemeCluster] = Field(default_factory=list)
    posts: list[dict[str, Any]] = Field(default_factory=list)
    original_theme_count: int = 0
    canonical_theme_count: int = 0
    cluster_count: int = 0
    processing_time_seconds: float = 0.0
    provider_used: str = ""
    embedding_model: str = ""


class SupportingPost(BaseModel):
    """A single Reddit post cited as evidence."""

    title: str = Field(..., description="Post title")
    url: str = Field(..., description="Full Reddit URL")
    upvotes: int = Field(..., description="Post upvote count")
    subreddit: str = Field(..., description="Subreddit name")


class HypothesisEvidence(BaseModel):
    """Evidence supporting a business idea from cluster data."""

    cluster_name: str
    cluster_themes: list[str] = Field(
        default_factory=list, description="Themes grouped into this cluster"
    )
    post_count: int = Field(..., description="Total posts in cluster")
    total_upvotes: int = Field(
        ..., description="Sum of upvotes across all cluster posts"
    )
    shown_post_count: int = Field(
        0, description="Number of posts shown as evidence"
    )
    supporting_posts: list[SupportingPost] = Field(
        default_factory=list, description="Top posts by upvotes with full metadata"
    )
    # Legacy field — accepted from old hypothesis files but excluded from output
    supporting_post_titles: list[str] = Field(
        default_factory=list, exclude=True
    )


class BusinessIdea(BaseModel):
    """A single business hypothesis derived from complaint clusters."""

    rank: int = Field(..., ge=1, le=5)
    idea_name: str = Field(..., description="Short brandable name")
    pain_point: str = Field(..., description="One sentence, plain language")
    solution_description: str = Field(..., description="What it does, specifically")
    core_features: str | None = Field(
        None, description="3-5 specific features (comma-separated)"
    )
    revenue_model: str | None = Field(
        None, description="How it makes money - be explicit with pricing"
    )
    first_user_step: str | None = Field(
        None, description="What the user does in the first 30 seconds"
    )
    target_user: str = Field(..., description="Who experiences this pain")
    evidence: HypothesisEvidence
    confidence: Literal["high", "medium", "low"]
    confidence_reasoning: str = Field(..., description="Why high/medium/low")


class HypothesisOutput(BaseModel):
    """Complete hypothesis generation result."""

    ideas: list[BusinessIdea] = Field(..., min_length=1, max_length=5)
    analysis_summary: str = Field(..., description="2-3 sentences on overall pattern")
    data_limitations: str = Field(..., description="Honest caveat about the dataset")
    source_cluster_count: int = Field(..., description="Number of clusters analyzed")
    processing_time_seconds: float = 0.0
    model_used: str = ""
    generated_at: datetime = Field(default_factory=datetime.utcnow)
