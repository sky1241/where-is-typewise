"""typewise-mcp — MCP server exposing Typewise as evaluable tools inside Claude Desktop / Code.

Run:
    python -m src.mcp_server.server

Or wire into Claude Desktop via claude_desktop_config.json (see README).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from src.mcp_server.tools import case_study as case_study_mod
from src.mcp_server.tools import compare as compare_mod
from src.mcp_server.tools import influencer_finder as influencer_finder_mod
from src.mcp_server.tools import integrations as integrations_mod
from src.mcp_server.tools import linkedin_post as linkedin_post_mod
from src.mcp_server.tools import podcast_pitch as podcast_pitch_mod
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


@mcp.tool()
def typewise_find_case_study(
    industry: str,
    company_size: str | None = None,
    region: str | None = None,
) -> dict:
    """Find the Typewise customer story closest to a prospect's profile.

    Args:
        industry: Prospect's industry, free-form (e.g. "retail", "logistics", "saas", "energy").
        company_size: Optional sizing hint ("smb", "mid_market", "scaleup", "enterprise").
        region: Optional region hint ("DACH", "EU", "global", "Switzerland", etc.).

    Returns:
        Dict with best_match, up to two alternates, and reasoning for the pick.
    """
    return case_study_mod.find(
        industry=industry,
        company_size=company_size,
        region=region,
    )


@mcp.tool()
def typewise_integration_check(platform: str) -> dict:
    """Tell whether Typewise integrates with the named platform.

    Args:
        platform: Free-form platform name (e.g. "Zendesk", "MS Dynamics", "HubSpot", "Discord").

    Returns:
        Dict with status (confirmed / native_channel / high_likelihood / unknown / unlikely),
        evidence, and a next-step recommendation honest about confidence level.
    """
    return integrations_mod.check(platform)


@mcp.tool()
def typewise_podcast_pitch(podcast_name: str) -> dict:
    """Draft a guest-pitch package for a named CX/CS-AI podcast.

    Args:
        podcast_name: Free-form podcast name (case + spacing tolerant). Aliases
            resolve common host names too (e.g. "Sarah Guo" → "No Priors").

    Returns:
        Dict with podcast metadata, a 3-paragraph recommended_pitch tuned to the
        host's known angle, four anchor talking_points, the next concrete step
        (contact channel), and an evidence URL pointing at a recent episode.
        Unknown names return the curated index of 10 podcasts.
    """
    return podcast_pitch_mod.pitch(podcast_name)


@mcp.tool()
def typewise_linkedin_post(topic: str) -> dict:
    """Assemble a LinkedIn-post template tuned to a growth topic.

    Args:
        topic: Free-form topic name. Aliases resolve common variants
            (e.g. "gdpr" → "eu_data_residency"; "vs sierra" → "augment_vs_replace").

    Returns:
        Dict with the assembled draft_post (hook + insight + cta), length in
        chars (kept in the 600–1500 LinkedIn sweet spot), 3–5 hashtags, tone
        notes, the target audience persona, and the LinkedIn pattern this
        template was inspired by. Unknown topics return the curated list of 6.
    """
    return linkedin_post_mod.generate(topic)


@mcp.tool()
def typewise_influencer_finder(topic: str, max_results: int = 3) -> dict:
    """Surface the best-matched CX/AI influencer(s) for a given growth topic.

    Args:
        topic: Free-form topic (e.g. "ai agents", "CX leadership", "community").
            Aliases resolve to a controlled topic vocabulary so ranking is
            deterministic across calls.
        max_results: Cap on the number of ranked matches (default 3).

    Returns:
        Dict with up to `max_results` ranked best_matches (each enriched with a
        per-match match_reason), the query tags it resolved to, and reasoning
        that explains the ranking. Unknown topics fall back to the highest-
        audience influencer with the fallback honestly flagged in the reasoning.
    """
    return influencer_finder_mod.find(topic, max_results=max_results)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
