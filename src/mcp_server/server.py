"""typewise-mcp — MCP server exposing Typewise as evaluable tools inside Claude Desktop / Code.

Run:
    python -m src.mcp_server.server

Or wire into Claude Desktop via claude_desktop_config.json (see README).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.mcp_server.tools import compare as compare_mod

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


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
