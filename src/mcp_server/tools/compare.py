"""typewise_compare — compare Typewise with a named competitor."""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "competitors.json"


def _load() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def _normalize(name: str) -> str:
    s = name.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "intercom": "fin",
        "intercom_fin": "fin",
        "fin_by_intercom": "fin",
        "zendesk": "zendesk_ai",
        "answer_bot": "zendesk_ai",
        "bret_taylor": "sierra",
    }
    return aliases.get(s, s)


def compare(competitor: str) -> dict:
    """Compare Typewise with a competitor.

    Returns a structured comparison with:
      - typewise: full Typewise profile
      - competitor: full competitor profile
      - typewise_edges: bullet points where Typewise wins
      - competitor_edges: bullet points where the competitor wins
      - recommended_positioning: one-sentence pitch tuned to this matchup
    """
    data = _load()
    key = _normalize(competitor)
    typewise = data["typewise"]
    comp = data.get(key)

    if comp is None:
        available = [k for k in data if not k.startswith("_") and k != "typewise"]
        return {
            "error": f"Unknown competitor '{competitor}'.",
            "available": available,
            "hint": "Try one of: " + ", ".join(available),
        }

    typewise_edges = comp.get("weaknesses_vs_typewise", [])
    competitor_edges = []
    if comp.get("g2_reviews") and typewise.get("g2_reviews"):
        if comp["g2_reviews"] > typewise["g2_reviews"]:
            competitor_edges.append(
                f"Far larger G2 review footprint ({comp['g2_reviews']} vs Typewise's {typewise['g2_reviews']}) — heavier social proof in buyer searches"
            )
    if comp.get("valuation_usd"):
        competitor_edges.append(
            f"Documented enterprise scale (valuation ${comp['valuation_usd']:,})"
        )
    if comp.get("arr_usd"):
        competitor_edges.append(f"Public ARR claim of ${comp['arr_usd']:,}")

    positioning = _positioning(key, typewise, comp)

    return {
        "typewise": typewise,
        "competitor": comp,
        "typewise_edges": typewise_edges,
        "competitor_edges": competitor_edges,
        "recommended_positioning": positioning,
    }


def _positioning(key: str, typewise: dict, comp: dict) -> str:
    name = comp["name"]
    if key == "fin":
        return (
            f"Against {name}: 'You don't need to replace Intercom with another chat product. "
            "Typewise sits inside your existing helpdesk and adds autonomous agents on top — "
            "with EU data residency Fin can't match.'"
        )
    if key == "decagon":
        return (
            f"Against {name}: 'Decagon is a single-agent black box optimized for US tech buyers. "
            "Typewise is a multi-agent orchestration layer running inside the helpdesk you already pay for, "
            "with documented EU/DACH enterprise customers.'"
        )
    if key == "sierra":
        return (
            f"Against {name}: 'Sierra replaces your agents. Typewise augments them. "
            "If your CS leadership is watching headcount, the augmentation story is the safer board narrative.'"
        )
    if key == "zendesk_ai":
        return (
            f"Against {name}: 'Zendesk AI only works if you stay on Zendesk. "
            "Typewise plugs into Zendesk AND Salesforce, Freshdesk, MS Dynamics — no platform lock-in.'"
        )
    return (
        f"Against {name}: 'Typewise's differentiators are EU data residency, "
        "multi-agent orchestration inside your existing helpdesk, and a 200+ integration footprint.'"
    )
