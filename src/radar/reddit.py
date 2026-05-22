"""Reddit scraper via PRAW (read-only, script-type OAuth app).

Reads credentials from environment (loads `.env` via python-dotenv if present):
    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
    REDDIT_USER_AGENT          (optional — defaults to a project-tagged UA)

Creating a Reddit app: https://www.reddit.com/prefs/apps — type "script", redirect_uri
http://localhost:8000 (unused for read-only), copy the client_id (under the app name)
and the secret. No password / username needed for public-thread read access.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Iterable

try:
    from dotenv import load_dotenv  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover — python-dotenv is in requirements.txt
    def load_dotenv(*_a: Any, **_kw: Any) -> bool:
        return False

import praw

_DEFAULT_USER_AGENT = "where-is-typewise:v0.1 (by /u/sky1241)"
_REDDIT_URL = "https://www.reddit.com"


class RedditCredsMissing(RuntimeError):
    """Raised when REDDIT_CLIENT_ID or REDDIT_CLIENT_SECRET are not in the environment."""


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _utc_from_epoch(epoch: float | int | None) -> str | None:
    if epoch is None:
        return None
    return datetime.fromtimestamp(float(epoch), tz=timezone.utc).isoformat(timespec="seconds")


def client_from_env() -> praw.Reddit:
    """Build a read-only PRAW client from env vars. Loads `.env` if present."""
    load_dotenv()
    client_id = os.environ.get("REDDIT_CLIENT_ID")
    client_secret = os.environ.get("REDDIT_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise RedditCredsMissing(
            "REDDIT_CLIENT_ID / REDDIT_CLIENT_SECRET not set. "
            "Create a script-type app at https://www.reddit.com/prefs/apps and export them."
        )
    user_agent = os.environ.get("REDDIT_USER_AGENT", _DEFAULT_USER_AGENT)
    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )
    reddit.read_only = True
    return reddit


def _submission_to_thread(submission: Any, fetched_at: str) -> dict[str, Any]:
    sub_id = getattr(submission, "id", None)
    if not sub_id:
        raise ValueError(f"submission missing id: {submission!r}")
    author = getattr(submission, "author", None)
    permalink = getattr(submission, "permalink", "") or ""
    url = f"{_REDDIT_URL}{permalink}" if permalink else getattr(submission, "url", "") or ""
    return {
        "id": f"reddit:{sub_id}",
        "source": "reddit",
        "locale": None,
        "url": url,
        "title": getattr(submission, "title", "") or "",
        "body": getattr(submission, "selftext", "") or "",
        "author": None if author is None else str(author),
        "created_at": _utc_from_epoch(getattr(submission, "created_utc", None)),
        "fetched_at": fetched_at,
        "intent": None,
        "competitors_mentioned": None,
        "typewise_mentioned": None,
        "relevance_score": None,
        "draft_reply": None,
    }


def scrape_subreddit(
    name: str,
    *,
    limit: int = 50,
    listing: str = "new",
    reddit: praw.Reddit | None = None,
) -> list[dict[str, Any]]:
    """Scrape `limit` posts from a single subreddit.

    Args:
        name: subreddit name without the `r/` prefix (e.g. "CustomerSuccess").
        limit: max submissions to pull (PRAW caps at ~1000 per listing).
        listing: "new" (default — best for fresh buyer chatter), "hot", or "top".
        reddit: optional pre-built PRAW client (lets tests inject a Mock).

    Returns:
        List of thread dicts shaped for store.upsert_thread.
    """
    if listing not in {"new", "hot", "top"}:
        raise ValueError(f"unsupported listing: {listing!r}")
    reddit = reddit or client_from_env()
    subreddit = reddit.subreddit(name)
    fetcher = getattr(subreddit, listing)
    fetched_at = _now_utc_iso()
    return [_submission_to_thread(s, fetched_at) for s in fetcher(limit=limit)]


def scrape_many(
    names: Iterable[str],
    *,
    limit_per_sub: int = 50,
    listing: str = "new",
    reddit: praw.Reddit | None = None,
) -> list[dict[str, Any]]:
    """Scrape several subreddits and de-duplicate by thread id (first wins)."""
    reddit = reddit or client_from_env()
    seen: dict[str, dict[str, Any]] = {}
    for name in names:
        for thread in scrape_subreddit(name, limit=limit_per_sub, listing=listing, reddit=reddit):
            seen.setdefault(thread["id"], thread)
    return list(seen.values())
