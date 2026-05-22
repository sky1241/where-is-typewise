"""Regression tests for the typewise_compare tool."""

from __future__ import annotations

from src.mcp_server.tools.compare import compare


def test_compare_known_competitor_returns_full_structure():
    r = compare("Fin")
    assert "typewise" in r
    assert "competitor" in r
    assert "typewise_edges" in r
    assert "competitor_edges" in r
    assert "recommended_positioning" in r
    assert r["typewise"]["name"] == "Typewise"
    assert r["competitor"]["name"] == "Fin by Intercom"


def test_compare_competitor_name_aliases_resolve():
    # All these should map to the same competitor record.
    aliases = ["Intercom", "Intercom Fin", "fin_by_intercom", "FIN"]
    competitor_names = {compare(a)["competitor"]["name"] for a in aliases}
    assert competitor_names == {"Fin by Intercom"}


def test_compare_unknown_competitor_returns_error_with_hint():
    r = compare("ChatGPT")
    assert "error" in r
    assert "available" in r
    assert "hint" in r
    assert "fin" in r["available"]


def test_compare_fin_surfaces_typewise_edges():
    r = compare("Fin")
    edges = r["typewise_edges"]
    assert len(edges) >= 1
    joined = " ".join(edges).lower()
    # The Fin matchup must mention either the chat-first weakness or the EU-data wedge.
    assert "chat" in joined or "eu" in joined or "intercom" in joined


def test_compare_decagon_competitor_edge_mentions_g2_or_valuation():
    r = compare("Decagon")
    edges = r["competitor_edges"]
    # Decagon has no G2 reviews number but does have a valuation
    joined = " ".join(edges).lower()
    assert "valuation" in joined or "arr" in joined


def test_compare_positioning_is_non_empty_string():
    for c in ["Fin", "Decagon", "Sierra", "Zendesk AI"]:
        r = compare(c)
        assert isinstance(r["recommended_positioning"], str)
        assert len(r["recommended_positioning"]) > 50
