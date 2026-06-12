"""Unit tests for src/radar/hackernews.py — Algolia mapping + dedupe via httpx.MockTransport."""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
import pytest

from src.radar import hackernews


def _algolia_fixture(hits: list[dict[str, Any]]) -> dict[str, Any]:
    return {"hits": hits, "nbHits": len(hits), "hitsPerPage": len(hits)}


def _mock_client(responder) -> httpx.Client:
    transport = httpx.MockTransport(responder)
    return httpx.Client(transport=transport)


def test_search_maps_algolia_hit_to_thread_schema():
    hit = {
        "objectID": "38291837",
        "title": "Show HN: My new CS-AI agent",
        "url": "https://example.com/show",
        "author": "pg",
        "created_at": "2026-05-20T14:32:00.000Z",
        "story_text": "We built X",
    }

    def responder(request: httpx.Request) -> httpx.Response:
        assert request.url.host == "hn.algolia.com"
        assert request.url.params["query"] == "AI customer service"
        assert request.url.params["tags"] == "story"
        return httpx.Response(200, json=_algolia_fixture([hit]))

    with _mock_client(responder) as client:
        threads = hackernews.search("AI customer service", max_results=10, client=client)

    assert len(threads) == 1
    t = threads[0]
    assert t["id"] == "hn:38291837"
    assert t["source"] == "hn"
    assert t["url"] == "https://example.com/show"
    assert t["title"] == "Show HN: My new CS-AI agent"
    assert t["body"] == "We built X"
    assert t["author"] == "pg"
    assert t["created_at"].startswith("2026-05-20T14:32:00")
    assert t["fetched_at"]  # set
    assert t["typewise_mentioned"] is None
    assert t["relevance_score"] is None
    assert t["draft_reply"] is None
    assert t["locale"] is None


def test_search_strips_escaped_html_from_body():
    # Algolia returns story_text as escaped HTML — the stored body must be plain text.
    hit = {
        "objectID": "48243325",
        "title": "Show HN: Plain text please",
        "author": "demo",
        "created_at": "2026-05-23T10:00:00.000Z",
        "story_text": "Letterbook (&lt;a href=&quot;https:&#x2F;&#x2F;letterbook.ai&quot;&gt;https:&#x2F;&#x2F;letterbook.ai&lt;&#x2F;a&gt;) solves tickets.&lt;p&gt;Watch our demo",
    }

    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_algolia_fixture([hit]))

    with _mock_client(responder) as client:
        threads = hackernews.search("AI customer service", max_results=10, client=client)

    body = threads[0]["body"]
    assert "&#x2F;" not in body and "&lt;" not in body and "<a " not in body and "<p>" not in body
    assert "https://letterbook.ai" in body
    assert "Watch our demo" in body


def test_search_synthesizes_hn_item_url_when_missing():
    hit = {"objectID": "999", "title": "Ask HN: tools?", "author": "anon", "created_at": "2026-05-22T00:00:00.000Z"}

    def responder(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_algolia_fixture([hit]))

    with _mock_client(responder) as client:
        threads = hackernews.search("ask hn", client=client)

    assert threads[0]["url"] == "https://news.ycombinator.com/item?id=999"


def test_search_clamps_max_results_and_raises_for_status():
    captured: dict[str, Any] = {}

    def responder(request: httpx.Request) -> httpx.Response:
        captured["params"] = dict(request.url.params)
        return httpx.Response(500, text="boom")

    with _mock_client(responder) as client:
        with pytest.raises(httpx.HTTPStatusError):
            hackernews.search("q", max_results=99999, client=client)

    assert int(captured["params"]["hitsPerPage"]) == 1000  # clamped


def test_search_many_dedupes_by_thread_id():
    duplicate_hit = {
        "objectID": "42",
        "title": "shared",
        "url": "https://example.com/42",
        "author": "x",
        "created_at": "2026-05-22T00:00:00.000Z",
    }
    unique_hit = {
        "objectID": "43",
        "title": "unique",
        "url": "https://example.com/43",
        "author": "y",
        "created_at": "2026-05-22T00:00:00.000Z",
    }

    def responder(request: httpx.Request) -> httpx.Response:
        q = request.url.params["query"]
        if q == "alpha":
            return httpx.Response(200, json=_algolia_fixture([duplicate_hit]))
        if q == "beta":
            return httpx.Response(200, json=_algolia_fixture([duplicate_hit, unique_hit]))
        return httpx.Response(200, json=_algolia_fixture([]))

    with _mock_client(responder) as client:
        threads = hackernews.search_many(["alpha", "beta"], max_per_query=10, client=client)

    ids = sorted(t["id"] for t in threads)
    assert ids == ["hn:42", "hn:43"]


def test_hit_missing_objectid_raises():
    bad_hit = {"title": "no id"}

    def responder(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_algolia_fixture([bad_hit]))

    with _mock_client(responder) as client:
        with pytest.raises(ValueError, match="objectID"):
            hackernews.search("q", client=client)


@pytest.mark.skipif(
    os.environ.get("RADAR_SKIP_NETWORK") == "1",
    reason="RADAR_SKIP_NETWORK=1 — offline mode",
)
def test_live_algolia_smoke():
    """Hits the real Algolia HN endpoint. Skip with RADAR_SKIP_NETWORK=1."""
    try:
        threads = hackernews.search("hacker news", max_results=3)
    except httpx.HTTPError as exc:
        # HTTPError covers transport errors AND HTTPStatusError (429/5xx from
        # raise_for_status) — a rate-limited Algolia must skip, not redden CI.
        pytest.skip(f"network unreachable or rate-limited: {exc}")
    assert len(threads) >= 1
    t = threads[0]
    assert t["id"].startswith("hn:")
    assert t["source"] == "hn"
    assert t["url"].startswith("http")
    assert t["title"]
    json.dumps(t)  # serializable end-to-end
