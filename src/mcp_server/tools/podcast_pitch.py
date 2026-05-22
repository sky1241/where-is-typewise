"""typewise_podcast_pitch — surface a guest-pitch draft for a named CX/CS-AI podcast.

Curated dataset of 10 podcasts in `data/podcasts.json`. The function returns
a structured dict any Typewise team member can paste into an outreach DM,
with the recommended Typewise angle tuned to that specific host.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "podcasts.json"


_PODCAST_ALIASES = {
    "no_priors":               "no_priors",
    "sarah_guo":               "no_priors",
    "elad_gil":                "no_priors",
    "cx_cast":                 "the_cx_cast",
    "the_cx_cast":             "the_cx_cast",
    "forrester":               "the_cx_cast",
    "modern_customer":         "modern_customer_podcast",
    "the_modern_customer":     "modern_customer_podcast",
    "blake_morgan":            "modern_customer_podcast",
    "be_customer_led":         "be_customer_led",
    "bill_staikos":            "be_customer_led",
    "punk_cx":                 "punk_cx",
    "adrian_swinscoe":         "punk_cx",
    "support_driven":          "support_driven_podcast",
    "support_driven_podcast":  "support_driven_podcast",
    "20vc":                    "twenty_vc",
    "twenty_vc":               "twenty_vc",
    "harry_stebbings":         "twenty_vc",
    "saastr":                  "saastr_podcast",
    "saastr_podcast":          "saastr_podcast",
    "jason_lemkin":            "saastr_podcast",
    "lenny":                   "lennys_podcast",
    "lennys_podcast":          "lennys_podcast",
    "lenny_rachitsky":         "lennys_podcast",
    "acquired":                "acquired",
}


def _load() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)["podcasts"]


def _normalize(name: str) -> str:
    key = name.strip().lower().replace(" ", "_").replace("-", "_").replace("'", "")
    return _PODCAST_ALIASES.get(key, key)


def _draft_pitch(podcast: dict) -> str:
    """Build a 3-paragraph guest-pitch draft anchored on the host's known angle."""
    name = podcast["name"]
    host = podcast["host"]
    host_angle = podcast["host_angle"]
    angle = podcast["recommended_typewise_angle"]
    para1 = (
        f"Hi {host.split(',')[0].strip()} — I lead growth at Typewise (YC S22, Zurich). "
        f"Long-time listener of {name}, and I think there's a fit for your audience around the "
        "'augment, don't replace' thesis our category is missing."
    )
    para2 = (
        f"Quick context: Typewise is an AI agent platform that runs on top of existing helpdesks "
        f"(Zendesk, Salesforce, Freshdesk). EU-hosted, ETH Zurich research roots, 50+ enterprise "
        f"customers including Unilever, DPD, IVECO, Brack.ch. We're explicitly not chasing the "
        f"Fin/Sierra/Decagon 'replace the helpdesk' narrative."
    )
    para3 = (
        f"For {name} specifically, I'd lead with: {angle} "
        f"Happy to share concrete metrics from the Brack.ch deployment (multilingual DACH retail) "
        f"as the case-study spine. 25–30 min, available CET. Open to dates Q3."
    )
    return f"{para1}\n\n{para2}\n\n{para3}"


def _talking_points(podcast: dict) -> list[str]:
    """Generic-but-tuned talking points to anchor the host's questions."""
    return [
        "Pivot story: B2C keyboard (2M downloads) → B2B agent platform → enterprise EU/DACH",
        "Multi-agent orchestration: AI Supervisor + Specialist + Knowledge + Action agents",
        "Why 'augment inside helpdesk' beats 'replace helpdesk' for boards watching headcount",
        f"Specific to {podcast['host'].split(',')[0].strip()}: {podcast['host_angle']}",
    ]


def pitch(podcast_name: str) -> dict:
    """Return a podcast-pitch package for a named CX/CS-AI podcast.

    Args:
        podcast_name: Free-form name of the podcast (case + spacing tolerant).
                      Aliases resolve common host names too (e.g. "Sarah Guo").

    Returns:
        Dict with podcast metadata, a 3-paragraph recommended_pitch, four
        talking_points, the next concrete step, and the evidence link
        (recent_episode_url). Unknown names return the curated index instead
        of inventing data.
    """
    data = _load()
    key = _normalize(podcast_name)
    podcast = data.get(key)

    if podcast is None:
        return {
            "error": f"Unknown podcast '{podcast_name}'.",
            "available": sorted(data.keys()),
            "hint": (
                "Try one of the canonical names (e.g. 'No Priors', 'The CX Cast', "
                "'Modern Customer', 'Be Customer Led', 'Punk CX', 'Support Driven', "
                "'20VC', 'SaaStr', 'Lenny', 'Acquired') or a known host name."
            ),
        }

    return {
        "podcast": {
            "name": podcast["name"],
            "host": podcast["host"],
            "focus": podcast["focus"],
            "audience_size": podcast["audience_size"],
        },
        "recommended_pitch": _draft_pitch(podcast),
        "talking_points": _talking_points(podcast),
        "next_step": podcast["contact_hint"],
        "evidence": podcast["recent_episode_url"],
        "host_angle_used": podcast["host_angle"],
    }
