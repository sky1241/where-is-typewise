"""Hacker News scraper via the Algolia public search API (no auth).

Search endpoint: https://hn.algolia.com/api/v1/search
Docs: https://hn.algolia.com/api

Returns thread dicts shaped to match the `threads` SQLite schema in src/radar/store.py
(unscored fields left as None — the scorer fills those later).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

import httpx

_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"
_HN_ITEM_URL = "https://news.ycombinator.com/item?id={}"
_DEFAULT_TIMEOUT = 15.0


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _algolia_created_to_iso(created_at: str | None) -> str | None:
    """Algolia returns ISO-8601 already (e.g. '2026-05-20T14:32:00.000Z') — normalize to seconds."""
    if not created_at:
        return None
    s = created_at.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s).astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        return created_at


def _hit_to_thread(hit: dict[str, Any], fetched_at: str) -> dict[str, Any]:
    object_id = str(hit.get("objectID") or "").strip()
    if not object_id:
        raise ValueError(f"hit missing objectID: {hit!r}")
    url = hit.get("url") or _HN_ITEM_URL.format(object_id)
    title = hit.get("title") or hit.get("story_title") or ""
    body = hit.get("story_text") or hit.get("comment_text") or ""
    return {
        "id": f"hn:{object_id}",
        "source": "hn",
        "locale": None,
        "url": url,
        "title": title,
        "body": body,
        "author": hit.get("author"),
        "created_at": _algolia_created_to_iso(hit.get("created_at")),
        "fetched_at": fetched_at,
        "intent": None,
        "competitors_mentioned": None,
        "typewise_mentioned": None,
        "relevance_score": None,
        "draft_reply": None,
    }


def search(
    query: str,
    *,
    max_results: int = 50,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Search HN stories matching `query` via Algolia.

    Args:
        query: free-text search terms (Algolia handles tokenization).
        max_results: hitsPerPage cap (Algolia maxes at 1000 but 50 is the project default).
        client: optional pre-configured httpx.Client (lets tests inject a MockTransport).

    Returns:
        List of thread dicts in `threads` schema order; unscored fields are None.
    """
    params = {
        "query": query,
        "tags": "story",
        "hitsPerPage": max(1, min(int(max_results), 1000)),
    }
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=_DEFAULT_TIMEOUT)
    try:
        resp = client.get(_ALGOLIA_URL, params=params)
        resp.raise_for_status()
        payload = resp.json()
    finally:
        if owns_client:
            client.close()
    fetched_at = _now_utc_iso()
    return [_hit_to_thread(hit, fetched_at) for hit in payload.get("hits", [])]


def search_many(
    queries: Iterable[str],
    *,
    max_per_query: int = 50,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Run `search` for several queries and de-duplicate by thread id (first occurrence wins)."""
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=_DEFAULT_TIMEOUT)
    seen: dict[str, dict[str, Any]] = {}
    try:
        for q in queries:
            for thread in search(q, max_results=max_per_query, client=client):
                seen.setdefault(thread["id"], thread)
    finally:
        if owns_client:
            client.close()
    return list(seen.values())
