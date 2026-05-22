"""Regression tests for the typewise_find_case_study tool."""

from __future__ import annotations

from src.mcp_server.tools.case_study import find


def test_retail_midmarket_dach_returns_brack():
    r = find("retail", "mid_market", "DACH")
    assert r["best_match"]["customer"] == "Brack.ch"
    # Industry + size + region should all contribute.
    assert "ecommerce" in r["reasoning"]
    assert "mid_market" in r["reasoning"]


def test_logistics_enterprise_returns_dpd():
    r = find("logistics", "enterprise")
    assert r["best_match"]["customer"] == "DPD"


def test_freight_aliases_to_logistics():
    # "freight" should resolve to logistics via the alias map.
    r = find("freight", "enterprise")
    assert r["best_match"]["industry"] == "logistics"


def test_saas_returns_superhuman():
    r = find("saas")
    assert r["best_match"]["customer"] == "Superhuman"


def test_unknown_industry_falls_back_to_enterprise():
    r = find("crypto_exchange")
    assert r["best_match"]["company_size"] == "enterprise"
    assert "No customer story directly matched" in r["reasoning"]


def test_alternates_capped_at_two():
    r = find("ecommerce")
    assert len(r["alternates"]) <= 2


def test_alternates_excludes_best_match():
    r = find("ecommerce", "mid_market", "DACH")
    best_id = r["best_match"]["id"]
    alt_ids = {a["id"] for a in r["alternates"]}
    assert best_id not in alt_ids


def test_region_heuristic_boosts_dach_when_relevant():
    # With DACH region hint, a DACH retailer should beat a non-DACH one (Superhuman = global/US).
    with_dach = find("retail", "mid_market", "DACH")
    without_region = find("retail", "mid_market")
    # Brack.ch should still win in both, but the reasoning should mention region in the DACH call.
    assert "Region" in with_dach["reasoning"]
    assert "Region" not in without_region["reasoning"]
