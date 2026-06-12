"""Regression tests for the typewise_pricing_calculator tool."""

from __future__ import annotations

import pytest

from src.mcp_server.tools.pricing import estimate


def test_estimate_happy_path_30k_tickets():
    r = estimate(30000)
    assert r["resolved_by_ai_monthly"] == 21000  # 70% resolution rate
    assert r["typewise_monthly_cost_usd"] == 21000.0
    assert r["baseline_human_only_monthly_cost_usd"] == 180000.0
    # 5x ROI matches Typewise's homepage "5-10x ROI year one" claim
    assert r["roi_multiple_year_one"] == 5.0


def test_estimate_zero_tickets_does_not_crash():
    r = estimate(0)
    assert r["resolved_by_ai_monthly"] == 0
    assert r["typewise_monthly_cost_usd"] == 0.0
    assert r["roi_multiple_year_one"] is None


def test_estimate_negative_tickets_returns_error():
    r = estimate(-1)
    assert "error" in r


def test_estimate_resolution_rate_out_of_range_returns_error():
    assert "error" in estimate(1000, resolution_rate=1.5)
    assert "error" in estimate(1000, resolution_rate=-0.1)


def test_estimate_blended_cost_never_exceeds_baseline():
    # For any positive volume, blended cost (Typewise + handoff) should beat all-human cost.
    for tickets in [100, 1_000, 10_000, 100_000]:
        r = estimate(tickets)
        assert r["blended_monthly_cost_usd"] < r["baseline_human_only_monthly_cost_usd"]


def test_estimate_higher_resolution_rate_yields_higher_savings():
    low = estimate(10_000, resolution_rate=0.50)
    high = estimate(10_000, resolution_rate=0.90)
    assert high["monthly_savings_usd"] > low["monthly_savings_usd"]


def test_estimate_pricing_source_url_present():
    r = estimate(1000)
    assert "typewise.app" in r["pricing_source"]


@pytest.mark.parametrize(
    "tickets,expected_resolved",
    [(1000, 700), (5000, 3500), (50000, 35000)],
)
def test_estimate_resolved_count_matches_default_rate(tickets, expected_resolved):
    r = estimate(tickets)
    assert r["resolved_by_ai_monthly"] == expected_resolved


def test_estimate_roi_of_exactly_zero_is_returned_not_none():
    # human cost == AI cost per resolved ticket -> savings 0 -> ROI 0.0, a valid value.
    r = estimate(10_000, human_cost_per_ticket_usd=1.0)
    assert r["roi_multiple_year_one"] == 0.0
    assert r["roi_multiple_year_one"] is not None


def test_estimate_rejects_negative_human_cost():
    r = estimate(10_000, human_cost_per_ticket_usd=-2.0)
    assert "error" in r
    assert r["got"] == -2.0
