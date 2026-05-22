"""MCP protocol-level integration tests.

These prove the tools are exposed via the MCP server interface (not just importable
as Python functions). They simulate what Claude Desktop sees when it lists & calls
tools through the FastMCP runtime.
"""

from __future__ import annotations

import json

import pytest

from src.mcp_server.server import mcp

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_server_exposes_four_tools():
    tools = await mcp.list_tools()
    names = sorted(t.name for t in tools)
    assert names == sorted([
        "typewise_compare",
        "typewise_pricing_calculator",
        "typewise_find_case_study",
        "typewise_integration_check",
    ]), f"Unexpected tool set: {names}"


async def test_compare_tool_schema_advertises_competitor_arg():
    tools = await mcp.list_tools()
    by_name = {t.name: t for t in tools}
    schema = by_name["typewise_compare"].inputSchema
    assert "competitor" in schema["properties"]
    assert "competitor" in schema.get("required", [])


async def test_pricing_tool_schema_advertises_int_tickets_arg():
    tools = await mcp.list_tools()
    by_name = {t.name: t for t in tools}
    schema = by_name["typewise_pricing_calculator"].inputSchema
    props = schema["properties"]
    assert props["monthly_tickets"]["type"] == "integer"
    # resolution_rate has a default, so it should NOT be in required.
    required = schema.get("required", [])
    assert "monthly_tickets" in required
    assert "resolution_rate" not in required


async def test_compare_tool_callable_via_mcp_returns_structured_dict():
    result = await mcp.call_tool("typewise_compare", {"competitor": "Fin"})
    # FastMCP returns a list of content items + a structured payload.
    payload = _payload(result)
    assert payload["typewise"]["name"] == "Typewise"
    assert payload["competitor"]["name"] == "Fin by Intercom"
    assert "recommended_positioning" in payload


async def test_pricing_tool_callable_via_mcp_30k_returns_5x_roi():
    result = await mcp.call_tool(
        "typewise_pricing_calculator",
        {"monthly_tickets": 30000},
    )
    payload = _payload(result)
    assert payload["roi_multiple_year_one"] == 5.0


async def test_case_study_tool_callable_via_mcp_returns_brack_for_dach_retail():
    result = await mcp.call_tool(
        "typewise_find_case_study",
        {"industry": "retail", "company_size": "mid_market", "region": "DACH"},
    )
    payload = _payload(result)
    assert payload["best_match"]["customer"] == "Brack.ch"


async def test_integration_check_tool_callable_via_mcp_returns_zendesk_confirmed():
    result = await mcp.call_tool(
        "typewise_integration_check",
        {"platform": "Zendesk"},
    )
    payload = _payload(result)
    assert payload["status"] == "confirmed"


def _payload(result) -> dict:
    """Extract the structured dict payload from a FastMCP call_tool result.

    FastMCP can return either a tuple (content, structured_payload) or just content.
    The structured payload is the canonical dict-shape; fall back to JSON-decoding
    the first text content otherwise.
    """
    if isinstance(result, tuple):
        # (content, structured) form
        _, structured = result
        if isinstance(structured, dict):
            # Some versions wrap the dict under a 'result' key.
            return structured.get("result", structured)
        return structured
    if isinstance(result, list) and result:
        first = result[0]
        text = getattr(first, "text", None)
        if text:
            return json.loads(text)
    raise AssertionError(f"Unrecognized call_tool result shape: {type(result)} -> {result!r}")
