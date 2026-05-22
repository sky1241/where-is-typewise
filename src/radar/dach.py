"""DACH / EU startup-tech RSS scrapers — extends the radar past US-centric HN.

Three default feeds (none CS-AI-specific, so we keyword-filter):
  - t3n.de                    (DE general startup/tech)
  - deutsche-startups.de      (DE startup news)
  - siliconcanals.com         (EU startup news, English)

Threads land with `source="dach"` and a pre-set `locale` (the feed's primary language).
Use `locale_tagger.tag_threads_in_db` afterwards for HN/Reddit threads where `locale`
is still NULL.
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Iterable

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("radar.dach")

_USER_AGENT = "where-is-typewise/0.1 (+https://github.com/sky1241/where-is-typewise)"
_DEFAULT_TIMEOUT = 15.0

DEFAULT_FEEDS: list[dict[str, str | None]] = [
    {"name": "t3n",               "url": "https://t3n.de/rss.xml",                "locale": "de"},
    {"name": "deutsche-startups", "url": "https://www.deutsche-startups.de/feed/", "locale": "de"},
    {"name": "siliconcanals",     "url": "https://siliconcanals.com/feed/",        "locale": "en"},
]


def _stable_id(feed_name: str, entry: Any) -> str:
    raw = entry.get("id") or entry.get("link") or entry.get("title") or ""
    if not raw:
        raise ValueError(f"feed {feed_name!r} entry has no id, link, or title")
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
    return f"dach:{feed_name}:{digest}"


def _entry_body_html(entry: Any) -> str:
    content_list = entry.get("content") or []
    if isinstance(content_list, list) and content_list:
        first = content_list[0]
        if isinstance(first, dict):
            value = first.get("value")
            if value:
                return value
    return entry.get("summary") or ""


def _strip_html(html: str) -> str:
    if not html:
        return ""
    return BeautifulSoup(html, "html.parser").get_text(separator=" ", strip=True)


def _entry_created_iso(entry: Any) -> str | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    try:
        dt = datetime(*parsed[:6], tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None
    return dt.isoformat(timespec="seconds")


def _matches_any_keyword(text: str, keywords: list[str]) -> bool:
    """Empty keyword list → accept everything (caller's choice)."""
    if not keywords:
        return True
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in keywords)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def fetch_feed(
    *,
    name: str,
    url: str,
    locale: str | None,
    keywords: list[str] | None = None,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch and parse one RSS feed, optionally keyword-filtered.

    Args:
        name: short feed identifier used in the thread id (`dach:<name>:<hash>`).
        url: RSS endpoint.
        locale: pre-set on each returned thread (e.g. "de", "en") — saves the
            locale_tagger from re-detecting on threads whose source language is
            already known.
        keywords: case-insensitive substrings; an entry is kept iff at least one
            matches title+body. None or [] → keep every entry.
        client: optional httpx.Client (lets tests inject MockTransport).
    """
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True)
    try:
        resp = client.get(url, headers={"User-Agent": _USER_AGENT})
        resp.raise_for_status()
        raw = resp.content
    finally:
        if owns_client:
            client.close()

    parsed = feedparser.parse(raw)
    fetched_at = _now_utc_iso()
    kws = keywords or []
    threads: list[dict[str, Any]] = []
    for entry in parsed.entries:
        title = (entry.get("title") or "").strip()
        body = _strip_html(_entry_body_html(entry))
        if not _matches_any_keyword(f"{title} {body}", kws):
            continue
        threads.append({
            "id": _stable_id(name, entry),
            "source": "dach",
            "locale": locale,
            "url": entry.get("link") or "",
            "title": title,
            "body": body,
            "author": entry.get("author"),
            "created_at": _entry_created_iso(entry),
            "fetched_at": fetched_at,
            "intent": None,
            "competitors_mentioned": None,
            "typewise_mentioned": None,
            "relevance_score": None,
            "draft_reply": None,
        })
    return threads


def fetch_all(
    feeds: Iterable[dict[str, Any]] | None = None,
    *,
    keywords: list[str] | None = None,
    client: httpx.Client | None = None,
) -> list[dict[str, Any]]:
    """Fetch every configured feed and deduplicate by thread id (first wins).

    A failing feed (HTTP error, connection refused) logs a warning and is skipped —
    a single dead feed must not break the radar cycle.
    """
    feeds_list = list(feeds) if feeds is not None else DEFAULT_FEEDS
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=_DEFAULT_TIMEOUT, follow_redirects=True)
    seen: dict[str, dict[str, Any]] = {}
    try:
        for feed in feeds_list:
            try:
                threads = fetch_feed(
                    name=feed["name"],
                    url=feed["url"],
                    locale=feed.get("locale"),
                    keywords=keywords,
                    client=client,
                )
            except (httpx.HTTPError, httpx.RequestError) as exc:
                logger.warning("feed %s (%s) failed: %s", feed.get("name"), feed.get("url"), exc)
                continue
            for t in threads:
                seen.setdefault(t["id"], t)
    finally:
        if owns_client:
            client.close()
    return list(seen.values())
