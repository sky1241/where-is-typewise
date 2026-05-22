"""Unit tests for src/radar/scorer.py — Anthropic client is mocked, no network/$$."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.radar import scorer


def _fake_response(tool_input: dict[str, Any] | None, *, stop_reason: str = "tool_use") -> SimpleNamespace:
    blocks = []
    if tool_input is not None:
        blocks.append(SimpleNamespace(type="tool_use", name="score_thread", input=tool_input))
    return SimpleNamespace(content=blocks, stop_reason=stop_reason)


def _make_client(*responses):
    client = MagicMock()
    client.messages.create.side_effect = list(responses)
    return client


def _thread(**over):
    base = {
        "id": "hn:1",
        "source": "hn",
        "url": "https://news.ycombinator.com/item?id=1",
        "title": "Best AI tools for EU customer support?",
        "body": "We get 30k tickets/mo, Fin is too expensive...",
    }
    base.update(over)
    return base


def test_score_thread_returns_normalized_dict():
    payload = {
        "intent": "comparison",
        "competitors_mentioned": ["Fin", "Decagon"],
        "typewise_mentioned": False,
        "relevance_score": 0.82,
        "draft_reply": "If you're looking at EU-friendly options, Typewise might be worth a look.",
    }
    client = _make_client(_fake_response(payload))

    out = scorer.score_thread(_thread(), client=client)

    assert out["intent"] == "comparison"
    assert out["competitors_mentioned"] == ["Fin", "Decagon"]
    assert out["typewise_mentioned"] is False
    assert out["relevance_score"] == pytest.approx(0.82)
    assert out["draft_reply"].startswith("If you're")


def test_score_thread_request_shape_enables_prompt_caching():
    client = _make_client(_fake_response({
        "intent": "research", "competitors_mentioned": [], "typewise_mentioned": False,
        "relevance_score": 0.3, "draft_reply": "",
    }))

    scorer.score_thread(_thread(), client=client)
    call = client.messages.create.call_args
    kw = call.kwargs

    assert kw["model"] == "claude-haiku-4-5"
    assert kw["tool_choice"] == {"type": "tool", "name": "score_thread"}
    assert kw["tools"][0]["name"] == "score_thread"
    system_block = kw["system"][0]
    assert system_block["type"] == "text"
    assert system_block["cache_control"] == {"type": "ephemeral"}
    assert "Typewise" in system_block["text"]


def test_score_thread_keeps_per_thread_content_out_of_system_prompt():
    """Per-thread data must NOT bleed into the cached system block (would silently kill cache hits)."""
    client = _make_client(_fake_response({
        "intent": "research", "competitors_mentioned": [], "typewise_mentioned": False,
        "relevance_score": 0.2, "draft_reply": "",
    }))
    thread = _thread(title="UNIQUE_TITLE_MARKER_XYZ", body="UNIQUE_BODY_MARKER_QPR")

    scorer.score_thread(thread, client=client)
    kw = client.messages.create.call_args.kwargs

    assert "UNIQUE_TITLE_MARKER_XYZ" not in kw["system"][0]["text"]
    assert "UNIQUE_BODY_MARKER_QPR"  not in kw["system"][0]["text"]
    user_content = kw["messages"][0]["content"]
    assert "UNIQUE_TITLE_MARKER_XYZ" in user_content
    assert "UNIQUE_BODY_MARKER_QPR"  in user_content


def test_score_thread_system_prompt_is_byte_stable_across_calls():
    """Cache prefix invariant: identical competitors → byte-identical system block."""
    client = _make_client(
        _fake_response({"intent": "research", "competitors_mentioned": [], "typewise_mentioned": False, "relevance_score": 0.1, "draft_reply": ""}),
        _fake_response({"intent": "research", "competitors_mentioned": [], "typewise_mentioned": False, "relevance_score": 0.1, "draft_reply": ""}),
    )

    scorer.score_thread(_thread(id="hn:a"), client=client, competitors=["Fin", "Decagon"])
    scorer.score_thread(_thread(id="hn:b"), client=client, competitors=["Decagon", "Fin"])  # reordered

    s1 = client.messages.create.call_args_list[0].kwargs["system"][0]["text"]
    s2 = client.messages.create.call_args_list[1].kwargs["system"][0]["text"]
    assert s1 == s2  # sorted internally so reorder doesn't invalidate cache


def test_score_thread_raises_when_tool_not_called():
    client = _make_client(_fake_response(None, stop_reason="end_turn"))
    with pytest.raises(scorer.ScorerError, match="score_thread"):
        scorer.score_thread(_thread(), client=client)


def test_score_thread_rejects_invalid_intent():
    client = _make_client(_fake_response({
        "intent": "bogus_intent", "competitors_mentioned": [], "typewise_mentioned": False,
        "relevance_score": 0.5, "draft_reply": "",
    }))
    with pytest.raises(scorer.ScorerError, match="intent"):
        scorer.score_thread(_thread(), client=client)


def test_score_thread_rejects_out_of_range_score():
    client = _make_client(_fake_response({
        "intent": "research", "competitors_mentioned": [], "typewise_mentioned": False,
        "relevance_score": 1.5, "draft_reply": "",
    }))
    with pytest.raises(scorer.ScorerError, match="out of"):
        scorer.score_thread(_thread(), client=client)


def test_score_thread_rejects_non_numeric_score():
    client = _make_client(_fake_response({
        "intent": "research", "competitors_mentioned": [], "typewise_mentioned": False,
        "relevance_score": "high", "draft_reply": "",
    }))
    with pytest.raises(scorer.ScorerError, match="numeric"):
        scorer.score_thread(_thread(), client=client)


def test_score_many_yields_thread_scoring_pairs():
    client = _make_client(
        _fake_response({"intent": "comparison", "competitors_mentioned": ["Fin"], "typewise_mentioned": False, "relevance_score": 0.8, "draft_reply": "A"}),
        _fake_response({"intent": "research",   "competitors_mentioned": [],      "typewise_mentioned": False, "relevance_score": 0.3, "draft_reply": ""}),
    )
    threads = [_thread(id="hn:1"), _thread(id="hn:2")]

    results = list(scorer.score_many(threads, client=client))

    assert len(results) == 2
    assert results[0][0]["id"] == "hn:1"
    assert results[0][1]["intent"] == "comparison"
    assert results[1][0]["id"] == "hn:2"
    assert results[1][1]["draft_reply"] == ""


def test_score_many_skip_drops_bad_threads_by_default():
    client = _make_client(
        _fake_response({"intent": "comparison", "competitors_mentioned": [], "typewise_mentioned": False, "relevance_score": 0.7, "draft_reply": "A"}),
        _fake_response(None, stop_reason="end_turn"),  # this one fails
        _fake_response({"intent": "research",   "competitors_mentioned": [], "typewise_mentioned": False, "relevance_score": 0.2, "draft_reply": ""}),
    )
    threads = [_thread(id=f"hn:{i}") for i in range(3)]

    results = list(scorer.score_many(threads, client=client))

    assert [t["id"] for t, _ in results] == ["hn:0", "hn:2"]


def test_score_many_raise_propagates_first_error():
    client = _make_client(
        _fake_response({"intent": "comparison", "competitors_mentioned": [], "typewise_mentioned": False, "relevance_score": 0.7, "draft_reply": "A"}),
        _fake_response(None, stop_reason="end_turn"),
    )
    threads = [_thread(id="hn:1"), _thread(id="hn:2")]

    gen = scorer.score_many(threads, client=client, on_error="raise")
    next(gen)
    with pytest.raises(scorer.ScorerError):
        next(gen)


def test_score_many_invalid_on_error_rejected():
    with pytest.raises(ValueError, match="on_error"):
        list(scorer.score_many([_thread()], client=_make_client(), on_error="bogus"))
