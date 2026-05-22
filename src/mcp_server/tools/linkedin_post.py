"""typewise_linkedin_post — assemble a LinkedIn-post draft from a curated template by topic.

Six topics covered (augment_vs_replace, eu_data_residency, dach_case_study,
agent_vs_chatbot, multi_agent_orchestration, helpdesk_layer_not_replacement)
— each tuned to a known LinkedIn pattern from CX/AI founder accounts.
"""

from __future__ import annotations

import json
from pathlib import Path

_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "linkedin_templates.json"


_TOPIC_ALIASES = {
    "augment":                       "augment_vs_replace",
    "augment_vs_replace":            "augment_vs_replace",
    "replace_vs_augment":            "augment_vs_replace",
    "vs_sierra":                     "augment_vs_replace",
    "vs_decagon":                    "augment_vs_replace",
    "eu_data":                       "eu_data_residency",
    "eu_data_residency":             "eu_data_residency",
    "data_residency":                "eu_data_residency",
    "gdpr":                          "eu_data_residency",
    "compliance":                    "eu_data_residency",
    "dach":                          "dach_case_study",
    "dach_case_study":               "dach_case_study",
    "multilingual":                  "dach_case_study",
    "agent_vs_chatbot":              "agent_vs_chatbot",
    "chatbot_vs_agent":              "agent_vs_chatbot",
    "ai_agents":                     "agent_vs_chatbot",
    "multi_agent":                   "multi_agent_orchestration",
    "multi_agent_orchestration":     "multi_agent_orchestration",
    "orchestration":                 "multi_agent_orchestration",
    "deep_tech":                     "multi_agent_orchestration",
    "helpdesk":                      "helpdesk_layer_not_replacement",
    "helpdesk_layer":                "helpdesk_layer_not_replacement",
    "helpdesk_layer_not_replacement":"helpdesk_layer_not_replacement",
    "integration_first":             "helpdesk_layer_not_replacement",
}


def _load() -> dict:
    with _DATA_PATH.open(encoding="utf-8") as f:
        return json.load(f)["templates"]


def _normalize(topic: str) -> str:
    key = topic.strip().lower().replace(" ", "_").replace("-", "_")
    return _TOPIC_ALIASES.get(key, key)


def _assemble_post(template: dict) -> str:
    """Stitch hook + insight + CTA into a single post body."""
    return f"{template['hook']}\n\n{template['insight']}\n\n{template['cta']}"


def generate(topic: str) -> dict:
    """Return a LinkedIn-post template package for the given growth topic.

    Args:
        topic: Free-form topic name (case + spacing tolerant). Aliases resolve
               common variants (e.g. "eu data" → "eu_data_residency").

    Returns:
        Dict with topic metadata, the assembled draft_post (hook+insight+cta),
        hashtags, tone_notes, the inspired_by reference, and length stats so
        the caller can verify the post is in the LinkedIn sweet spot (600–1500
        chars). Unknown topics return the curated list instead of inventing.
    """
    data = _load()
    key = _normalize(topic)
    template = data.get(key)

    if template is None:
        return {
            "error": f"Unknown topic '{topic}'.",
            "available": sorted(data.keys()),
            "hint": (
                "Try one of: augment_vs_replace, eu_data_residency, dach_case_study, "
                "agent_vs_chatbot, multi_agent_orchestration, helpdesk_layer_not_replacement. "
                "Aliases work too — 'gdpr', 'multilingual', 'orchestration', etc."
            ),
        }

    draft = _assemble_post(template)
    return {
        "topic": template["topic"],
        "label": template["label"],
        "draft_post": draft,
        "length_chars": len(draft),
        "hashtags": template["hashtags"],
        "tone_notes": template["tone_notes"],
        "target_audience": template["target_audience"],
        "inspired_by": template["inspired_by"],
        "next_step": (
            "Rewrite in David's or Janis's voice — posting verbatim looks AI-generated. "
            "Fill in any {placeholder} fields with real customer/metric values before posting."
        ),
    }
