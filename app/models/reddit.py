"""Pydantic models for Reddit data structures.

These models define the schema for Reddit posts and comments
collected for complaint clustering and business idea discovery.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RedditPost(BaseModel):
    """A Reddit post with metadata for complaint analysis.

    Attributes:
        id: Reddit post ID for deduplication.
        title: Main complaint/topic text.
        selftext: Post body, often contains detailed complaint.
        url: Permalink for evidence traceability.
        subreddit: Niche context (r/python, r/AskReddit, etc.).
        upvotes: Primary signal - how many people have this problem.
        num_comments: Secondary signal - discussion intensity.
        upvote_ratio: Percentage of upvotes (uncontroversial vs divisive).
        created_utc: Unix timestamp for recency filtering.
        author: Author name for spam filtering.
        link_flair_text: Some subs have "complaint", "help", "rant" flairs.
    """

    id: str
    title: str
    selftext: str | None = None
    url: str
    subreddit: str
    upvotes: int = Field(default=0, ge=0)
    num_comments: int = Field(default=0, ge=0)
    upvote_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    created_utc: float
    author: str | None = None
    link_flair_text: str | None = None
    distinguished: str | None = None  # "moderator", "admin", or None
    stickied: bool = False

    @property
    def created_datetime(self) -> datetime:
        """Convert Unix timestamp to datetime."""
        return datetime.fromtimestamp(self.created_utc)

    @property
    def combined_text(self) -> str:
        """Get title + selftext combined for text analysis."""
        if self.selftext:
            return f"{self.title}\n\n{self.selftext}"
        return self.title


class RedditComment(BaseModel):
    """A Reddit comment with threading context.

    Attributes:
        id: Reddit comment ID.
        post_id: Parent post ID for linking back.
        parent_id: Parent comment ID for threaded context.
        body: Comment text where people discuss solutions or validate pain.
        upvotes: Highly-upvoted comments = validated pain points.
        author: Comment author name.
        level: 0 = top-level reply, 1+ = nested replies.
    """

    id: str
    post_id: str
    parent_id: str | None = None
    body: str
    upvotes: int = Field(default=0, ge=0)
    author: str | None = None
    level: int = Field(default=0, ge=0)


class PostWithComments(BaseModel):
    """A Reddit post with its comments and computed analysis signals.

    Attributes:
        post: The parent Reddit post.
        comments: List of comments on this post.
        complaint_score: Engagement-weighted score for ranking.
        solution_mentions: Extracted solution names from comments.
        is_unsolved: True if comments indicate no solution exists.
    """

    post: RedditPost
    comments: list[RedditComment] = Field(default_factory=list)
    complaint_score: float = Field(default=0.0, ge=0.0)
    solution_mentions: list[str] = Field(default_factory=list)
    is_unsolved: bool = Field(default=False)

    @property
    def total_comment_upvotes(self) -> int:
        """Sum of upvotes across all comments."""
        return sum(c.upvotes for c in self.comments)

    def calculate_complaint_score(self) -> float:
        """Calculate engagement-weighted complaint score.

        Formula: upvotes * (1 + num_comments/100)
        This weights posts with high engagement more heavily.
        """
        base_score = self.post.upvotes
        comment_weight = 1 + (self.post.num_comments / 100)
        return base_score * comment_weight

    def model_post_init(self, __context: Any) -> None:
        """Calculate complaint score after initialization."""
        if self.complaint_score == 0.0:
            self.complaint_score = self.calculate_complaint_score()


class CollectionResult(BaseModel):
    """Result of a data collection run for a topic.

    Attributes:
        topic: The search topic used.
        collected_at: Timestamp of collection.
        posts: All posts collected with their comments.
        total_posts: Count of posts.
        total_comments: Count of comments across all posts.
        subreddits_queried: List of subreddits searched.
        requests_made: Number of API requests used.
        collection_time_seconds: Total time for collection.
        rate_limit_status: Final rate limit state after collection (for frontend).
    """

    topic: str
    collected_at: datetime = Field(default_factory=datetime.now)
    posts: list[PostWithComments] = Field(default_factory=list)
    subreddits_queried: list[str] = Field(default_factory=list)
    requests_made: int = Field(default=0, ge=0)
    collection_time_seconds: float = Field(default=0.0, ge=0.0)
    rate_limit_status: dict | None = None

    @property
    def total_posts(self) -> int:
        """Total number of posts collected."""
        return len(self.posts)

    @property
    def total_comments(self) -> int:
        """Total number of comments across all posts."""
        return sum(len(p.comments) for p in self.posts)

    def to_json(self) -> str:
        """Serialize to JSON string for caching."""
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "CollectionResult":
        """Deserialize from JSON string."""
        return cls.model_validate_json(json_str)
