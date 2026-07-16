"""Tests for BusinessIdea.core_features list-to-string coercion.

Regression guard for a crash where the LLM returned `core_features` as a JSON
array instead of a comma-separated string, taking down the whole hypothesis
step with 5 identical ValidationErrors.

Run standalone:
    conda run -n agentic-ai-p2 python scripts/tests/test_business_idea_coercion.py
"""

from app.analyst.models import BusinessIdea, HypothesisEvidence, HypothesisOutput


def _evidence() -> HypothesisEvidence:
    """Minimal valid evidence block reused across ideas."""
    return HypothesisEvidence(
        cluster_name="Test Cluster",
        cluster_themes=["theme a", "theme b"],
        post_count=10,
        total_upvotes=500,
        shown_post_count=0,
        supporting_posts=[],
    )


def _idea(rank: int, core_features) -> BusinessIdea:
    """Build a BusinessIdea with only core_features varying."""
    return BusinessIdea(
        rank=rank,
        idea_name=f"Idea {rank}",
        pain_point="Users complain about X",
        solution_description="A thing that does Y",
        core_features=core_features,
        revenue_model="$10/mo subscription",
        first_user_step="Sign up and connect account",
        target_user="Indie developers",
        evidence=_evidence(),
        confidence="high",
        confidence_reasoning="Strong signal",
    )


def test_list_coerced_to_string():
    """A JSON array must be joined into a comma-separated string."""
    idea = _idea(1, core_features=["feature a", "feature b", "feature c"])
    assert idea.core_features == "feature a, feature b, feature c", (
        f"Expected comma-joined string, got: {idea.core_features!r}"
    )
    print("✓ List ['a','b','c'] coerced to 'feature a, feature b, feature c'")


def test_empty_list_becomes_none():
    """An empty list should normalize to None (no features)."""
    idea = _idea(1, core_features=[])
    assert idea.core_features is None, (
        f"Expected None for empty list, got: {idea.core_features!r}"
    )
    print("✓ Empty list [] coerced to None")


def test_string_passthrough():
    """A plain comma-separated string must pass through unchanged."""
    idea = _idea(1, core_features="feature a, feature b")
    assert idea.core_features == "feature a, feature b", (
        f"Expected passthrough, got: {idea.core_features!r}"
    )
    print("✓ Plain string passes through unchanged")


def test_none_passthrough():
    """None must pass through unchanged."""
    idea = _idea(1, core_features=None)
    assert idea.core_features is None, (
        f"Expected None, got: {idea.core_features!r}"
    )
    print("✓ None passes through unchanged")


def test_full_hypothesis_output_with_list_features():
    """End-to-end regression: the exact shape that crashed pushshift/linanqiu.

    5 ideas, each with core_features as a JSON array. This must validate
    cleanly through HypothesisOutput, and every idea must end up with a
    string core_features.
    """
    ideas = [_idea(rank, core_features=[f"feature {i}" for i in range(3)]) for rank in range(1, 6)]
    output = HypothesisOutput(
        ideas=ideas,
        analysis_summary="A pattern across clusters.",
        data_limitations="Sample is small.",
        source_cluster_count=5,
    )
    assert len(output.ideas) == 5
    for idea in output.ideas:
        assert isinstance(idea.core_features, str), (
            f"Expected str for idea #{idea.rank}, got {type(idea.core_features).__name__}: "
            f"{idea.core_features!r}"
        )
    print("✓ Full HypothesisOutput (5 ideas, list-valued core_features) validates")


if __name__ == "__main__":
    test_list_coerced_to_string()
    test_empty_list_becomes_none()
    test_string_passthrough()
    test_none_passthrough()
    test_full_hypothesis_output_with_list_features()
    print("\n✅ All tests passed!")
