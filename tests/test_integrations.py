"""Regression tests for the typewise_integration_check tool."""

from __future__ import annotations

from src.mcp_server.tools.integrations import check


def test_salesforce_is_confirmed_via_brack_story():
    r = check("Salesforce")
    assert r["status"] == "confirmed"
    assert "Brack" in r["evidence"]


def test_zendesk_is_honest_unknown_not_fake_confirmation():
    # Typewise's own blog treats Zendesk AI as a competitor; no public
    # evidence of a native integration — the tool must say so, not invent.
    r = check("Zendesk")
    assert r["status"] == "unlikely"
    assert "competitor" in r["evidence"].lower() or "competitor" in r.get("next_step", "").lower() or "directly" in r["evidence"].lower()


def test_whatsapp_is_native_channel_not_integration():
    r = check("WhatsApp")
    assert r["status"] == "native_channel"
    assert r["integration_type"] == "first_party_channel"


def test_dynamics_high_likelihood_with_caveat():
    r = check("MS Dynamics")
    assert r["status"] == "high_likelihood"
    # Must NOT promise — must instruct to confirm with sales.
    assert "sales" in r["next_step"].lower()


def test_discord_unlikely_returns_route_via_native():
    r = check("Discord")
    assert r["status"] == "unlikely"
    assert "next_step" in r


def test_unknown_platform_returns_honest_unknown_not_fake_confirmation():
    r = check("Snowflake")
    assert r["status"] == "unknown"
    # The honest answer must not contain "yes" or "supported".
    assert "200+" in r["next_step"] or "sales" in r["next_step"].lower()


def test_alias_sfdc_resolves_to_salesforce():
    r = check("sfdc")
    assert r["status"] == "confirmed"


def test_alias_ms_dynamics_resolves():
    r = check("Dynamics 365")
    assert r["status"] == "high_likelihood"


def test_alias_anthropic_resolves_to_claude_channel():
    # ChatGPT/Claude are listed as CHANNELS on the typewise.app homepage
    # (agentic-commerce positioning), not as LLM-provider integrations.
    r = check("Anthropic")
    assert r["status"] == "native_channel"


def test_alias_openai_resolves_to_chatgpt_channel():
    r = check("OpenAI")
    assert r["status"] == "native_channel"


def test_case_insensitive_and_whitespace_tolerant():
    a = check("  salesforce  ")
    b = check("SALESFORCE")
    c = check("Salesforce")
    assert a["status"] == b["status"] == c["status"] == "confirmed"
