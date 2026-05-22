"""Score radar threads via Claude — intent / competitors / typewise mention / relevance / draft reply.

Uses Claude Haiku 4.5 by default with prompt caching on a frozen system prompt:
across a batch of N threads the system block is served from cache (~0.1× input cost)
after the first call. Anything per-thread (title, body) lives in the user message,
after the cache breakpoint, so caching stays warm.

Structured output is forced via tool_use with `tool_choice` pinned to `score_thread`,
so Claude always returns parseable JSON.
"""

from __future__ import annotations

from typing import Any, Iterable, Iterator

from anthropic import Anthropic

_DEFAULT_MODEL = "claude-haiku-4-5"

_INTENT_VALUES = ["research", "comparison", "complaint", "shopping", "irrelevant"]

_DEFAULT_COMPETITORS = [
    "Intercom", "Fin", "Zendesk", "Decagon", "Sierra",
    "Ada", "Forethought", "Kustomer", "Lorikeet", "Crisp",
]


def _build_system(competitors: list[str]) -> str:
    comps = ", ".join(sorted(competitors))
    return (
        "You are an analyst classifying buyer-conversation posts from Reddit and "
        "Hacker News for Typewise — a Swiss-based AI customer-service product targeting "
        "DACH and EU mid-market/enterprise (Galaxus, TUI, IVECO, Brack.ch, Wincasa, Planzer).\n\n"
        "For each thread you receive, you MUST call the `score_thread` tool exactly once. "
        "Do not respond with prose. The tool input is the full classification.\n\n"
        "Scoring rules:\n"
        "  intent — pick exactly one:\n"
        "    research      = open exploration, no clear buying intent\n"
        "    comparison    = evaluating named CS-AI products against each other\n"
        "    complaint     = expressing pain with current CS or current vendor\n"
        "    shopping      = explicitly asking for a recommendation / RFP-shaped\n"
        "    irrelevant    = off-topic for CS-AI buyer conversations\n\n"
        f"  competitors_mentioned — list of CS-AI products named in the thread. "
        f"Recognized set: {comps}. Include only products from this set that are explicitly "
        "named. Empty list if none.\n\n"
        "  typewise_mentioned — true iff 'Typewise' (case-insensitive) appears in title or body.\n\n"
        "  relevance_score — 0.0 to 1.0 — how relevant this thread is to Typewise's "
        "go-to-market. Anchor points: 0.0 irrelevant; 0.4 adjacent but not actionable; "
        "0.7 a real buyer conversation where a CS-AI vendor could meaningfully respond; "
        "0.9+ a high-intent prospect explicitly shopping for what Typewise sells.\n\n"
        "  draft_reply — a short, human-quality reply (≤ 4 sentences) the Typewise team "
        "could post in the thread. No emojis, no marketing fluff, no 'as an AI'. If "
        "intent is 'irrelevant' or relevance_score < 0.5, return an empty string instead."
    )


_TOOL_SCHEMA: dict[str, Any] = {
    "name": "score_thread",
    "description": "Record the structured scoring for one buyer-conversation thread.",
    "input_schema": {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "intent",
            "competitors_mentioned",
            "typewise_mentioned",
            "relevance_score",
            "draft_reply",
        ],
        "properties": {
            "intent": {
                "type": "string",
                "enum": _INTENT_VALUES,
                "description": "One-word classification of the thread's intent.",
            },
            "competitors_mentioned": {
                "type": "array",
                "items": {"type": "string"},
                "description": "CS-AI competitor product names explicitly mentioned.",
            },
            "typewise_mentioned": {
                "type": "boolean",
                "description": "True iff 'Typewise' is named (case-insensitive).",
            },
            "relevance_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 1,
                "description": "Go-to-market relevance for Typewise, 0..1.",
            },
            "draft_reply": {
                "type": "string",
                "description": "Short human-quality reply (≤4 sentences), or '' if not worth replying.",
            },
        },
    },
}


def _user_prompt(thread: dict[str, Any]) -> str:
    return (
        f"Source: {thread.get('source', 'unknown')}\n"
        f"Title: {thread.get('title') or ''}\n"
        f"Body:\n{thread.get('body') or '(empty)'}\n"
        f"URL: {thread.get('url') or ''}"
    )


class ScorerError(RuntimeError):
    """Raised when Claude's response does not contain a parseable score_thread tool call."""


def _extract_tool_input(response: Any) -> dict[str, Any]:
    for block in getattr(response, "content", []) or []:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "score_thread":
            payload = getattr(block, "input", None)
            if not isinstance(payload, dict):
                raise ScorerError(f"score_thread tool_use.input was not a dict: {payload!r}")
            return payload
    stop = getattr(response, "stop_reason", "unknown")
    raise ScorerError(f"Claude did not invoke score_thread (stop_reason={stop!r})")


def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
    intent = payload.get("intent")
    if intent not in _INTENT_VALUES:
        raise ScorerError(f"intent {intent!r} not in {_INTENT_VALUES}")
    comps_raw = payload.get("competitors_mentioned") or []
    if not isinstance(comps_raw, list):
        raise ScorerError(f"competitors_mentioned must be a list, got {type(comps_raw).__name__}")
    score_raw = payload.get("relevance_score")
    try:
        score = float(score_raw)
    except (TypeError, ValueError) as exc:
        raise ScorerError(f"relevance_score {score_raw!r} not numeric") from exc
    if not 0.0 <= score <= 1.0:
        raise ScorerError(f"relevance_score {score} out of [0, 1]")
    return {
        "intent": intent,
        "competitors_mentioned": [str(c) for c in comps_raw],
        "typewise_mentioned": bool(payload.get("typewise_mentioned", False)),
        "relevance_score": score,
        "draft_reply": str(payload.get("draft_reply") or ""),
    }


def score_thread(
    thread: dict[str, Any],
    *,
    client: Anthropic | None = None,
    model: str = _DEFAULT_MODEL,
    competitors: list[str] | None = None,
    max_tokens: int = 1024,
) -> dict[str, Any]:
    """Score one thread; returns a dict with the five scorer fields.

    The Anthropic client is injectable so tests pass a Mock and skip the real API.
    """
    client = client or Anthropic()
    comps = competitors if competitors is not None else list(_DEFAULT_COMPETITORS)
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=[
            {
                "type": "text",
                "text": _build_system(comps),
                "cache_control": {"type": "ephemeral"},
            }
        ],
        tools=[_TOOL_SCHEMA],
        tool_choice={"type": "tool", "name": "score_thread"},
        messages=[{"role": "user", "content": _user_prompt(thread)}],
    )
    return _normalize(_extract_tool_input(response))


def score_many(
    threads: Iterable[dict[str, Any]],
    *,
    client: Anthropic | None = None,
    model: str = _DEFAULT_MODEL,
    competitors: list[str] | None = None,
    on_error: str = "skip",
) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Yield (thread, scoring) pairs. Shares one client so the cached system prefix stays warm.

    on_error:
        "skip"  — drop threads whose scoring fails (default; runner-friendly)
        "raise" — re-raise the first ScorerError
    """
    if on_error not in {"skip", "raise"}:
        raise ValueError(f"on_error must be 'skip' or 'raise', got {on_error!r}")
    client = client or Anthropic()
    for t in threads:
        try:
            scoring = score_thread(t, client=client, model=model, competitors=competitors)
        except ScorerError:
            if on_error == "raise":
                raise
            continue
        yield t, scoring
