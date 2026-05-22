"""typewise_integration_check — tell a dev whether Typewise integrates with a given platform."""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "integrations.json"

_PLATFORM_ALIASES = {
    "ms_dynamics": "microsoft_dynamics_365",
    "ms_dynamics_365": "microsoft_dynamics_365",
    "dynamics": "microsoft_dynamics_365",
    "dynamics_365": "microsoft_dynamics_365",
    "salesforce": "salesforce_service_cloud",
    "sfdc": "salesforce_service_cloud",
    "service_cloud": "salesforce_service_cloud",
    "hubspot": "hubspot_service_hub",
    "ms_teams": "microsoft_teams",
    "teams": "microsoft_teams",
    "anthropic": "claude",
    "openai": "chatgpt",
    "gpt": "chatgpt",
}


def _norm(name: str) -> str:
    key = name.strip().lower().replace(" ", "_").replace("-", "_")
    return _PLATFORM_ALIASES.get(key, key)


def _load() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)


def check(platform: str) -> dict:
    """Tell whether Typewise integrates with the named platform.

    Args:
        platform: Free-form platform name (e.g. "Zendesk", "MS Dynamics", "HubSpot", "Discord").

    Returns:
        Dict with status (confirmed / channel / high_likelihood / unknown / unlikely),
        integration_type, evidence, and a "what to do" hint for the buyer.
    """
    data = _load()
    key = _norm(platform)

    if key in data["confirmed_native"]:
        rec = data["confirmed_native"][key]
        return {
            "platform": platform,
            "status": "confirmed",
            "integration_type": rec["type"],
            "evidence": rec["evidence"],
            "next_step": f"Public material confirms this integration. Docs hint: {rec.get('docs_hint', 'see typewise.app')}",
        }

    if key in data["channels_native"]:
        note = data["channels_native"][key]
        return {
            "platform": platform,
            "status": "native_channel",
            "integration_type": "first_party_channel",
            "evidence": f"{platform} is a native Typewise channel: {note}",
            "next_step": "No integration needed — comes with the product.",
        }

    if key in data["high_likelihood_via_200plus_claim"]:
        rec = data["high_likelihood_via_200plus_claim"][key]
        return {
            "platform": platform,
            "status": "high_likelihood",
            "integration_type": rec["type"],
            "confidence": rec["confidence"],
            "evidence": rec["evidence"],
            "next_step": (
                "Typewise advertises 200+ integrations and this platform fits their standard enterprise stack. "
                "Confirm with sales — do not promise it to a prospect without written confirmation."
            ),
        }

    if key in data["not_supported_or_unknown"]:
        return {
            "platform": platform,
            "status": "unlikely",
            "evidence": data["not_supported_or_unknown"][key],
            "next_step": "Not advertised publicly. Recommend the prospect either route their channel through email/chat (which Typewise handles natively) or open a feature request with sales.",
        }

    return {
        "platform": platform,
        "status": "unknown",
        "evidence": "This platform isn't in the curated public-source dataset.",
        "next_step": (
            "Not enough public material to answer. Ask Typewise sales directly — they advertise 200+ integrations, "
            "and many are not listed publicly. Provide the prospect's exact use case so sales can map to a real integration."
        ),
    }
