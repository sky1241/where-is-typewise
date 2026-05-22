"""Regression tests for the typewise_linkedin_post tool."""

from __future__ import annotations

import pytest

from src.mcp_server.tools.linkedin_post import generate


_ALL_TOPICS = [
    "augment_vs_replace",
    "eu_data_residency",
    "dach_case_study",
    "agent_vs_chatbot",
    "multi_agent_orchestration",
    "helpdesk_layer_not_replacement",
]


def test_known_topic_returns_full_structure():
    r = generate("eu_data_residency")
    for key in (
        "topic", "label", "draft_post", "length_chars",
        "hashtags", "tone_notes", "target_audience", "inspired_by", "next_step",
    ):
        assert key in r


def test_draft_post_in_linkedin_sweet_spot():
    """LinkedIn engagement peaks at 600–1500 chars; templates must respect it."""
    for topic in _ALL_TOPICS:
        r = generate(topic)
        assert 600 <= r["length_chars"] <= 1500, (
            f"{topic} draft is {r['length_chars']} chars — outside LinkedIn sweet spot"
        )


def test_hashtags_count_in_range():
    """Three to five hashtags is the LinkedIn sweet spot; more reads spammy."""
    for topic in _ALL_TOPICS:
        r = generate(topic)
        assert 3 <= len(r["hashtags"]) <= 5


def test_alias_gdpr_resolves_to_eu_data_residency():
    assert generate("GDPR")["topic"] == "eu_data_residency"


def test_alias_orchestration_resolves_to_multi_agent():
    assert generate("orchestration")["topic"] == "multi_agent_orchestration"


def test_alias_vs_sierra_resolves_to_augment_vs_replace():
    assert generate("vs sierra")["topic"] == "augment_vs_replace"


def test_unknown_topic_returns_error_with_curated_list():
    r = generate("crypto winter")
    assert "error" in r
    assert "available" in r
    assert sorted(r["available"]) == sorted(_ALL_TOPICS)


def test_draft_assembles_hook_insight_cta_in_order():
    """The first line of the draft must be the hook, last paragraph the CTA."""
    r = generate("augment_vs_replace")
    lines = r["draft_post"].split("\n\n")
    assert len(lines) == 3
    assert "rip-and-replace" in lines[0].lower()  # hook


def test_next_step_warns_against_verbatim_posting():
    """The tool must remind the user to rewrite — posting AI-templates verbatim looks bad."""
    r = generate("dach_case_study")
    assert "voice" in r["next_step"].lower() or "verbatim" in r["next_step"].lower()


@pytest.mark.parametrize("topic", _ALL_TOPICS)
def test_every_topic_has_an_inspired_by_reference(topic):
    """Templates must credit the pattern they're derived from — anti-bullshit hygiene."""
    r = generate(topic)
    assert r["inspired_by"]
    assert len(r["inspired_by"]) > 20


def test_case_insensitive_and_whitespace_tolerant():
    a = generate("  GDPR  ")
    b = generate("gdpr")
    assert a["topic"] == b["topic"]
