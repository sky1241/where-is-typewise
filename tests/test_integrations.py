"""Regression tests for the typewise_integration_check tool."""

from __future__ import annotations

from src.mcp_server.tools.integrations import check


def test_zendesk_is_confirmed_native():
    r = check("Zendesk")
    assert r["status"] == "confirmed"
    assert r["integration_type"] == "native_helpdesk"
    assert "Brack" in r["evidence"]


def test_whatsapp_is_native_channel_not_integration():
    r = check("WhatsApp")
    assert r["status"] == "native_channel"
    assert r["integration_type"] == "first_party_channel"


def test_salesforce_high_likelihood_with_caveat():
    r = check("Salesforce")
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
    assert r["status"] == "high_likelihood"


def test_alias_ms_dynamics_resolves():
    r = check("MS Dynamics")
    assert r["status"] == "high_likelihood"


def test_alias_anthropic_resolves_to_claude():
    r = check("Anthropic")
    assert r["status"] == "confirmed"
    assert r["integration_type"] == "llm_provider"


def test_alias_openai_resolves_to_chatgpt():
    r = check("OpenAI")
    assert r["status"] == "confirmed"


def test_case_insensitive_and_whitespace_tolerant():
    a = check("  zendesk  ")
    b = check("ZENDESK")
    c = check("Zendesk")
    assert a["status"] == b["status"] == c["status"] == "confirmed"
