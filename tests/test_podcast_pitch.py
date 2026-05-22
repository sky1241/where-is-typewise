"""Regression tests for the typewise_podcast_pitch tool."""

from __future__ import annotations

from src.mcp_server.tools.podcast_pitch import pitch


def test_known_podcast_returns_full_structure():
    r = pitch("No Priors")
    assert "podcast" in r
    assert "recommended_pitch" in r
    assert "talking_points" in r
    assert "next_step" in r
    assert "evidence" in r
    assert r["podcast"]["name"] == "No Priors"
    assert "Sarah Guo" in r["podcast"]["host"]


def test_pitch_length_in_outreach_range():
    """Pitch should be substantial (200+ chars) but not a wall of text (<2000)."""
    r = pitch("No Priors")
    assert 200 <= len(r["recommended_pitch"]) < 2000


def test_pitch_references_host_first_name():
    """The opener should address the host by their first name."""
    r = pitch("Modern Customer")
    assert "Blake" in r["recommended_pitch"]


def test_alias_host_name_resolves_to_podcast():
    """Aliasing common host names should land on the right podcast."""
    by_host = pitch("Sarah Guo")
    by_show = pitch("No Priors")
    assert by_host["podcast"]["name"] == by_show["podcast"]["name"]


def test_alias_cx_cast_short_form_resolves():
    """'CX Cast' (no 'The') should still resolve to 'The CX Cast'."""
    r = pitch("CX Cast")
    assert r["podcast"]["name"] == "The CX Cast"


def test_unknown_podcast_returns_error_with_curated_list():
    r = pitch("Joe Rogan Experience")
    assert "error" in r
    assert "available" in r
    assert len(r["available"]) == 10
    assert "no_priors" in r["available"]


def test_talking_points_are_exactly_four_strings():
    r = pitch("Be Customer Led")
    assert len(r["talking_points"]) == 4
    for tp in r["talking_points"]:
        assert isinstance(tp, str)
        assert len(tp) > 20


def test_every_podcast_has_an_evidence_url():
    """No evidence-less pitches — every podcast must point at a concrete recent episode page."""
    for name in ["No Priors", "The CX Cast", "Modern Customer", "Be Customer Led",
                 "Punk CX", "Support Driven", "20VC", "SaaStr", "Lenny", "Acquired"]:
        r = pitch(name)
        assert "evidence" in r
        assert r["evidence"].startswith("http")


def test_case_and_whitespace_tolerant():
    a = pitch("  no priors  ")
    b = pitch("NO PRIORS")
    c = pitch("No Priors")
    assert a["podcast"]["name"] == b["podcast"]["name"] == c["podcast"]["name"]


def test_pitch_references_typewise_brand():
    """A pitch must clearly identify Typewise — otherwise it's a generic AI cold email."""
    r = pitch("20VC")
    assert "Typewise" in r["recommended_pitch"]
