"""typewise_influencer_finder — surface the right CX influencer(s) for a given topic.

Curated dataset of 12 CX/AI influencers in `data/influencers.json`. Topic
matching is tag-overlap-based on a controlled vocabulary so the same query
always returns the same ranking.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "influencers.json"


# Maps free-form topic queries to the controlled topic vocabulary used in
# influencers.json. Keeping this lean so scoring stays deterministic.
_TOPIC_ALIASES = {
    "ai":                  ["ai", "automation"],
    "ai_agents":           ["ai_agents", "ai", "automation"],
    "agents":              ["ai_agents", "ai"],
    "automation":          ["automation", "ai"],
    "cx":                  ["customer_experience"],
    "customer_experience": ["customer_experience"],
    "cs":                  ["cs_operations", "cs_leadership", "customer_experience"],
    "cs_operations":       ["cs_operations"],
    "cs_leadership":       ["cs_leadership", "leadership"],
    "cx_leadership":       ["cs_leadership", "leadership", "customer_experience"],
    "contact_center":      ["contact_center", "cs_operations"],
    "community":           ["community"],
    "podcast":             [],
    "podcast_guest":       [],
    "vc":                  ["venture_capital"],
    "venture":             ["venture_capital"],
    "deep_tech":           ["deep_tech", "ai"],
    "books":               ["books"],
    "speaking":            ["speaking"],
    "social":              ["social_customer_care"],
    "journey_mapping":     ["journey_mapping"],
    "voc":                 ["voice_of_customer"],
    "employee_experience": ["employee_experience"],
    "loyalty":             ["loyalty"],
    "leadership":          ["leadership", "cs_leadership"],
}


def _load() -> list[dict]:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)["influencers"]


def _normalize_query(topic: str) -> list[str]:
    """Map a free-form topic query to a list of controlled-vocabulary tags."""
    key = topic.strip().lower().replace(" ", "_").replace("-", "_")
    direct = _TOPIC_ALIASES.get(key)
    if direct is not None:
        return direct
    # Fall back: the query itself, in case it already matches a tag.
    return [key]


def _score_influencer(influencer: dict, query_tags: list[str]) -> int:
    """Score by tag overlap. Higher = better fit."""
    if not query_tags:
        return 0
    tags = set(influencer.get("topics_focus", []))
    return sum(1 for q in query_tags if q in tags)


def find(topic: str, *, max_results: int = 3) -> dict:
    """Find the influencer(s) best matched to a topic.

    Args:
        topic: Free-form topic (e.g. "ai agents", "CX leadership", "VC", "community").
               Aliases resolve to controlled-vocabulary tags.
        max_results: Cap on the number of ranked matches (default 3).

    Returns:
        Dict with the original query, the list of tags it resolved to, up to
        `max_results` ranked best_matches (each enriched with a per-match
        `match_reason` string), and reasoning that explains the ranking.

        When nothing matches the controlled tags, falls back to the highest-
        audience influencer rather than returning nothing — useful as a
        "growth team sanity default" while preserving honesty in the
        reasoning field.
    """
    data = _load()
    query_tags = _normalize_query(topic)
    scored = [
        (_score_influencer(i, query_tags), -i["audience_size"], i)
        for i in data
    ]
    # Sort on (score, -audience) only — never on the dict itself, which would
    # raise TypeError the first time two influencers tie on both keys.
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)

    # Filter out zero-score hits unless they're the only thing we have.
    positive = [s for s in scored if s[0] > 0]

    if not positive:
        # Fallback: largest-audience influencer, honestly flagged.
        fallback = sorted(data, key=lambda i: -i["audience_size"])[0]
        return {
            "query": topic,
            "query_tags": query_tags,
            "best_matches": [{
                **fallback,
                "match_reason": (
                    f"No controlled-tag match for '{topic}'. Falling back to the highest-audience "
                    f"influencer in the dataset ({fallback['name']}, {fallback['audience_size']:,}) "
                    "as a sane default — verify topic fit manually before reaching out."
                ),
            }],
            "reasoning": (
                f"Query '{topic}' didn't match any tag in the controlled vocabulary. "
                "Returned the highest-audience influencer as a fallback, not as a recommendation."
            ),
        }

    top = positive[:max_results]
    best_matches = []
    for score, _neg_audience, influencer in top:
        overlap = [t for t in query_tags if t in set(influencer["topics_focus"])]
        best_matches.append({
            **influencer,
            "match_reason": (
                f"Topic overlap on {overlap} ({score} tag match{'es' if score > 1 else ''}); "
                f"audience {influencer['audience_size']:,}; "
                f"best channel = {influencer['best_outreach_channel']}."
            ),
        })

    return {
        "query": topic,
        "query_tags": query_tags,
        "best_matches": best_matches,
        "reasoning": (
            f"Matched {len(positive)} influencer(s) on the controlled-tag overlap with {query_tags}. "
            f"Top {len(best_matches)} returned, ranked by tag-overlap then audience size."
        ),
    }
