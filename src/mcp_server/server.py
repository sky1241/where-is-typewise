"""typewise-mcp — MCP server exposing Typewise as evaluable tools inside Claude Desktop / Code.

Run:
    python -m src.mcp_server.server

Or wire into Claude Desktop via claude_desktop_config.json (see README).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.mcp_server.tools import compare as compare_mod
from src.mcp_server.tools import pricing as pricing_mod

mcp = FastMCP("typewise-mcp")


@mcp.tool()
def typewise_compare(competitor: str) -> dict:
    """Compare Typewise with a named competitor for a buyer-evaluation conversation.

    Args:
        competitor: Name of the competitor product (e.g. "Fin", "Decagon", "Sierra", "Zendesk AI").

    Returns:
        Structured comparison with typewise profile, competitor profile, edges for each side,
        and a one-sentence recommended positioning tuned to this specific matchup.
    """
    return compare_mod.compare(competitor)


@mcp.tool()
def typewise_pricing_calculator(
    monthly_tickets: int,
    resolution_rate: float = 0.70,
    human_cost_per_ticket_usd: float = 6.0,
) -> dict:
    """Estimate Typewise cost and ROI at $1/resolution pricing for a given ticket volume.

    Args:
        monthly_tickets: Number of inbound support tickets per month.
        resolution_rate: Share of tickets the AI is expected to fully resolve (0..1, default 0.70).
        human_cost_per_ticket_usd: Fully-loaded blended human cost per ticket (default $6).

    Returns:
        Monthly + annual cost figures, savings, year-one ROI multiple, and the assumptions used.
    """
    return pricing_mod.estimate(
        monthly_tickets=monthly_tickets,
        resolution_rate=resolution_rate,
        human_cost_per_ticket_usd=human_cost_per_ticket_usd,
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
