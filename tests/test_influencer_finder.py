"""Regression tests for the typewise_influencer_finder tool."""

from __future__ import annotations

from src.mcp_server.tools.influencer_finder import find


def test_known_topic_returns_full_structure():
    r = find("ai agents")
    assert "query" in r
    assert "query_tags" in r
    assert "best_matches" in r
    assert "reasoning" in r
    assert len(r["best_matches"]) >= 1


def test_ai_agents_surfaces_sarah_guo_at_top():
    """Sarah Guo has 3 of the 3 AI-agent tags and the largest audience — must rank first."""
    r = find("ai agents")
    assert r["best_matches"][0]["name"] == "Sarah Guo"


def test_community_surfaces_nate_brown():
    """Nate Brown is the only influencer with the 'community' tag."""
    r = find("community")
    assert r["best_matches"][0]["id"] == "nate_brown"


def test_cx_leadership_surfaces_a_cx_leader():
    """Jeanne Bliss has cco_role / leadership tags — must surface."""
    r = find("CX leadership")
    names = [m["name"] for m in r["best_matches"]]
    assert "Jeanne Bliss" in names or any(
        "cs_leadership" in m["topics_focus"] for m in r["best_matches"]
    )


def test_unknown_topic_falls_back_with_honest_reasoning():
    r = find("crypto trading")
    assert len(r["best_matches"]) == 1
    fallback = r["best_matches"][0]
    assert "No controlled-tag match" in fallback["match_reason"]
    assert "fallback" in r["reasoning"].lower()


def test_max_results_cap_respected():
    r = find("customer_experience", max_results=2)
    assert len(r["best_matches"]) <= 2


def test_default_max_results_is_three():
    r = find("customer_experience")
    assert len(r["best_matches"]) <= 3


def test_match_reason_always_present_and_non_empty():
    r = find("ai agents")
    for m in r["best_matches"]:
        assert m["match_reason"]
        assert len(m["match_reason"]) > 20


def test_every_match_has_an_outreach_channel():
    r = find("ai")
    for m in r["best_matches"]:
        assert m["best_outreach_channel"] in {"linkedin", "twitter", "newsletter", "podcast"}


def test_audience_size_is_always_int():
    r = find("customer_experience")
    for m in r["best_matches"]:
        assert isinstance(m["audience_size"], int)


def test_no_influencer_listed_twice_in_results():
    r = find("customer_experience")
    ids = [m["id"] for m in r["best_matches"]]
    assert len(ids) == len(set(ids))


def test_query_tags_normalize_aliases():
    """'cx' should resolve to ['customer_experience']."""
    r = find("cx")
    assert r["query_tags"] == ["customer_experience"]


def test_case_and_whitespace_tolerant():
    a = find("  AI Agents  ")
    b = find("ai_agents")
    assert a["best_matches"][0]["id"] == b["best_matches"][0]["id"]
