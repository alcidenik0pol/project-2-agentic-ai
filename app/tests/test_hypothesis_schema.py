# ═══════════════════════════════════════════════════════════════════════════
# Schema regression tests for HypothesisOutput after the empty-ideas fix.
#
# Background: prod run 9f4359465e0f returned {"ideas": [], "analysis_summary": "..."}
# for an off-topic query. Pydantic rejected the empty list (min_length=1) and
# the RuntimeError was swallowed by the tool wrapper, so the user saw an
# apologetic prose report instead of a structured "no relevant findings" result.
# These tests lock in the relaxed contract so a future tightening reintroduces
# the bug only if someone also updates the tests.
# ═══════════════════════════════════════════════════════════════════════════
"""Tests for HypothesisOutput schema relaxation (allows ideas: [])."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.analyst.models import BusinessIdea, HypothesisEvidence, HypothesisOutput


def test_empty_ideas_is_valid():
    """The fix: HypothesisOutput(ideas=[], ...) must succeed, not raise."""
    out = HypothesisOutput(ideas=[], analysis_summary="no relevant data")
    assert out.ideas == []
    assert out.analysis_summary == "no relevant data"


def test_optional_fields_have_safe_defaults():
    """All four relaxed fields must default to empty/zero, not be required."""
    out = HypothesisOutput()
    assert out.ideas == []
    assert out.analysis_summary == ""
    assert out.data_limitations == ""
    assert out.source_cluster_count == 0


def test_data_limitations_holds_off_topic_explanation():
    """The recommended slot for the "why no ideas" caveat."""
    out = HypothesisOutput(
        ideas=[],
        data_limitations="All 4 clusters were about r/mildlyinfuriating image macros, not gaming mice.",
    )
    assert out.data_limitations.startswith("All 4 clusters")


def test_ideas_still_capped_at_5():
    """max_length=5 must still be enforced when ideas are populated."""
    evidence = HypothesisEvidence(
        cluster_name="x", post_count=1, total_upvotes=1,
    )
    idea = BusinessIdea(
        rank=1, idea_name="x", pain_point="x", solution_description="x",
        target_user="x", evidence=evidence, confidence="low",
        confidence_reasoning="x",
    )
    with pytest.raises(ValidationError):
        HypothesisOutput(ideas=[idea] * 6)


def test_business_idea_still_requires_all_fields():
    """A regression guard: if we have an idea at all, every sub-field must be present.

    The relaxation is on HypothesisOutput only — not on the contents of an idea.
    """
    with pytest.raises(ValidationError):
        BusinessIdea(rank=1, idea_name="x")  # type: ignore[call-arg]
