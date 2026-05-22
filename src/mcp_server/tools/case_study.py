"""typewise_find_case_study — surface the Typewise customer story closest to a prospect's profile."""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "case_studies.json"

_INDUSTRY_ALIASES = {
    "e-commerce": "ecommerce",
    "online_retail": "ecommerce",
    "retail": "ecommerce",
    "shop": "ecommerce",
    "marketplace": "ecommerce",
    "shipping": "logistics",
    "delivery": "logistics",
    "freight": "logistics",
    "transport": "logistics",
    "software": "saas",
    "b2b_saas": "saas",
    "tech": "saas",
    "energy": "utilities",
    "utility": "utilities",
    "consumer_packaged_goods": "cpg",
    "fmcg": "cpg",
    "manufacturing": "automotive",
    "industrial": "automotive",
    "hospitality": "travel",
    "tourism": "travel",
    "wellness": "consumer_goods",
    "health_devices": "consumer_goods",
}

_SIZE_ALIASES = {
    "small": "smb",
    "smb": "smb",
    "startup": "smb",
    "midsize": "mid_market",
    "midmarket": "mid_market",
    "mid": "mid_market",
    "mid_market": "mid_market",
    "growth": "scaleup",
    "scaleup": "scaleup",
    "scale_up": "scaleup",
    "large": "enterprise",
    "enterprise": "enterprise",
    "fortune_500": "enterprise",
    "f500": "enterprise",
}


def _norm_industry(s: str) -> str:
    key = s.strip().lower().replace(" ", "_").replace("-", "_")
    return _INDUSTRY_ALIASES.get(key, key)


def _norm_size(s: str | None) -> str | None:
    if not s:
        return None
    key = s.strip().lower().replace(" ", "_").replace("-", "_")
    return _SIZE_ALIASES.get(key, key)


def _load() -> list[dict]:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)["case_studies"]


def _size_match_score(case_size: str, target_size: str | None) -> int:
    if target_size is None:
        return 0
    if case_size == target_size:
        return 3
    # Forgiving partial match: "mid_market_to_enterprise" should match both "mid_market" and "enterprise"
    if target_size in case_size:
        return 2
    return 0


def find(industry: str, company_size: str | None = None, region: str | None = None) -> dict:
    """Find the Typewise case study(ies) closest to a prospect's profile.

    Args:
        industry: Prospect's industry — free-form (e.g. "retail", "logistics", "saas", "energy").
        company_size: Optional sizing hint ("smb", "mid_market", "scaleup", "enterprise").
        region: Optional region hint ("DACH", "EU", "global", "Switzerland", etc.).

    Returns:
        Dict with:
          - best_match: the single closest case study (or null if none)
          - alternates: up to 2 secondary matches
          - reasoning: why best_match was picked
    """
    studies = _load()
    target_industry = _norm_industry(industry)
    target_size = _norm_size(company_size)
    target_region = (region or "").strip().lower()

    scored: list[tuple[int, dict]] = []
    for cs in studies:
        score = 0
        if cs["industry"] == target_industry:
            score += 5
        score += _size_match_score(cs.get("company_size", ""), target_size)
        if target_region:
            cs_region = (cs.get("region") or "").lower()
            if target_region in cs_region or cs_region in target_region:
                score += 2
        if score > 0:
            scored.append((score, cs))

    scored.sort(key=lambda x: -x[0])

    if not scored:
        # Nothing matched — return a generalist enterprise case as fallback.
        fallback = next((cs for cs in studies if cs.get("company_size") == "enterprise"), studies[0])
        return {
            "best_match": fallback,
            "alternates": [],
            "reasoning": (
                f"No customer story directly matched industry='{industry}'. "
                f"Returning a high-profile enterprise reference ({fallback['customer']}) "
                "that demonstrates Typewise can handle enterprise-scale support."
            ),
        }

    best = scored[0][1]
    alternates = [s[1] for s in scored[1:3]]
    reasoning_parts = [f"Industry match on '{target_industry}'."]
    if target_size:
        reasoning_parts.append(f"Sizing aligned with '{target_size}'.")
    if target_region:
        reasoning_parts.append(f"Region heuristic on '{region}'.")
    reasoning_parts.append(f"Best match: {best['customer']} (score {scored[0][0]}).")
    return {
        "best_match": best,
        "alternates": alternates,
        "reasoning": " ".join(reasoning_parts),
    }
