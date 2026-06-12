"""typewise_pricing_calculator — estimate cost and ROI at Typewise's $1/resolution pricing."""

from __future__ import annotations

# Industry-default assumptions, documented inline so a reviewer can challenge them.
_DEFAULT_RESOLUTION_RATE = 0.70  # share of tickets the AI fully resolves without human handoff
_DEFAULT_HUMAN_COST_PER_TICKET_USD = 6.0  # fully-loaded blended cost per human-handled ticket
_TYPEWISE_PRICE_PER_RESOLUTION_USD = 1.0  # public pricing as of 2026-05-22


def estimate(
    monthly_tickets: int,
    resolution_rate: float = _DEFAULT_RESOLUTION_RATE,
    human_cost_per_ticket_usd: float = _DEFAULT_HUMAN_COST_PER_TICKET_USD,
) -> dict:
    """Estimate Typewise cost, baseline cost, and savings for a given monthly ticket volume.

    Args:
        monthly_tickets: Number of inbound support tickets per month.
        resolution_rate: Share of tickets the AI is expected to fully resolve (0..1).
        human_cost_per_ticket_usd: Fully-loaded blended human cost per ticket (USD).

    Returns:
        Dict with monthly and annual figures, ROI multiple, and the assumptions used.
    """
    if monthly_tickets < 0:
        return {"error": "monthly_tickets must be non-negative", "got": monthly_tickets}
    if not 0.0 <= resolution_rate <= 1.0:
        return {"error": "resolution_rate must be in [0, 1]", "got": resolution_rate}
    if human_cost_per_ticket_usd < 0:
        return {"error": "human_cost_per_ticket_usd must be non-negative", "got": human_cost_per_ticket_usd}

    resolved = int(monthly_tickets * resolution_rate)
    typewise_monthly_cost = resolved * _TYPEWISE_PRICE_PER_RESOLUTION_USD
    baseline_monthly_cost = monthly_tickets * human_cost_per_ticket_usd
    # Even unresolved tickets still cost the human rate, since they get handed off.
    blended_monthly_cost = (
        resolved * _TYPEWISE_PRICE_PER_RESOLUTION_USD
        + (monthly_tickets - resolved) * human_cost_per_ticket_usd
    )
    monthly_savings = baseline_monthly_cost - blended_monthly_cost
    annual_savings = monthly_savings * 12

    # ROI is savings relative to what Typewise costs; undefined when Typewise costs nothing.
    if typewise_monthly_cost > 0:
        roi_multiple_year_one = annual_savings / (typewise_monthly_cost * 12)
    else:
        roi_multiple_year_one = None

    return {
        "inputs": {
            "monthly_tickets": monthly_tickets,
            "resolution_rate": resolution_rate,
            "human_cost_per_ticket_usd": human_cost_per_ticket_usd,
        },
        "resolved_by_ai_monthly": resolved,
        "typewise_monthly_cost_usd": round(typewise_monthly_cost, 2),
        "blended_monthly_cost_usd": round(blended_monthly_cost, 2),
        "baseline_human_only_monthly_cost_usd": round(baseline_monthly_cost, 2),
        "monthly_savings_usd": round(monthly_savings, 2),
        "annual_savings_usd": round(annual_savings, 2),
        "roi_multiple_year_one": round(roi_multiple_year_one, 2) if roi_multiple_year_one is not None else None,
        "assumptions_note": (
            "Defaults: 70% AI resolution rate, $6 fully-loaded blended human cost per ticket. "
            "Both are industry-default starting points and should be tuned to the prospect's actual data "
            "during a discovery call."
        ),
        "pricing_source": "https://typewise.app (public pricing page, $1/resolution as of 2026-05-22)",
    }
