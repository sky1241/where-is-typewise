"""Unit tests for src/radar/reddit.py — PRAW client is mocked, no network."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest

from src.radar import reddit as radar_reddit


def _fake_submission(sub_id: str = "abc1", **over: Any) -> SimpleNamespace:
    base = {
        "id": sub_id,
        "title": "Looking for AI customer support tools",
        "selftext": "we get 30k tickets/mo, what's everyone using?",
        "author": "buyer42",
        "created_utc": 1747900000,  # 2025-05-22 fixed epoch
        "permalink": f"/r/CustomerSuccess/comments/{sub_id}/test/",
        "url": f"https://reddit.com/r/CustomerSuccess/comments/{sub_id}/",
    }
    base.update(over)
    return SimpleNamespace(**base)


def _fake_reddit(submissions_by_sub: dict[str, list[Any]], listing: str = "new") -> MagicMock:
    reddit = MagicMock()

    def subreddit(name: str) -> MagicMock:
        sub = MagicMock()
        listing_fn = MagicMock(side_effect=lambda limit: iter(submissions_by_sub.get(name, [])[:limit]))
        setattr(sub, listing, listing_fn)
        return sub

    reddit.subreddit.side_effect = subreddit
    return reddit


def test_client_from_env_raises_when_creds_missing(monkeypatch):
    monkeypatch.delenv("REDDIT_CLIENT_ID", raising=False)
    monkeypatch.delenv("REDDIT_CLIENT_SECRET", raising=False)
    with pytest.raises(radar_reddit.RedditCredsMissing):
        radar_reddit.client_from_env()


def test_client_from_env_builds_readonly_when_creds_present(monkeypatch):
    monkeypatch.setenv("REDDIT_CLIENT_ID", "id123")
    monkeypatch.setenv("REDDIT_CLIENT_SECRET", "secret123")
    monkeypatch.setenv("REDDIT_USER_AGENT", "test-ua/0.1")
    r = radar_reddit.client_from_env()
    assert r.config.client_id == "id123"
    assert r.read_only is True


def test_scrape_subreddit_maps_submission_to_thread_schema():
    sub_obj = _fake_submission("xyz9")
    reddit = _fake_reddit({"CustomerSuccess": [sub_obj]})

    threads = radar_reddit.scrape_subreddit("CustomerSuccess", limit=10, reddit=reddit)

    assert len(threads) == 1
    t = threads[0]
    assert t["id"] == "reddit:xyz9"
    assert t["source"] == "reddit"
    assert t["url"] == "https://www.reddit.com/r/CustomerSuccess/comments/xyz9/test/"
    assert t["title"] == "Looking for AI customer support tools"
    assert t["body"] == "we get 30k tickets/mo, what's everyone using?"
    assert t["author"] == "buyer42"
    assert t["created_at"].startswith("2025-")  # epoch-derived
    assert t["fetched_at"]
    assert t["typewise_mentioned"] is None
    assert t["relevance_score"] is None


def test_scrape_subreddit_handles_deleted_author_and_no_selftext():
    sub_obj = _fake_submission("del1", author=None, selftext="")
    reddit = _fake_reddit({"SaaS": [sub_obj]})

    [thread] = radar_reddit.scrape_subreddit("SaaS", limit=10, reddit=reddit)

    assert thread["author"] is None
    assert thread["body"] == ""
    assert thread["title"]


def test_scrape_subreddit_rejects_unknown_listing():
    with pytest.raises(ValueError, match="listing"):
        radar_reddit.scrape_subreddit("SaaS", listing="bogus", reddit=MagicMock())


def test_scrape_subreddit_respects_limit():
    submissions = [_fake_submission(f"id{i}") for i in range(100)]
    reddit = _fake_reddit({"CustomerService": submissions})

    threads = radar_reddit.scrape_subreddit("CustomerService", limit=3, reddit=reddit)

    assert len(threads) == 3
    assert [t["id"] for t in threads] == ["reddit:id0", "reddit:id1", "reddit:id2"]


def test_scrape_many_dedupes_across_subreddits():
    shared = _fake_submission("dup1")
    unique_a = _fake_submission("a1")
    unique_b = _fake_submission("b1")
    reddit = _fake_reddit({
        "SaaS": [shared, unique_a],
        "CustomerSuccess": [shared, unique_b],
    })

    threads = radar_reddit.scrape_many(["SaaS", "CustomerSuccess"], limit_per_sub=10, reddit=reddit)

    ids = sorted(t["id"] for t in threads)
    assert ids == ["reddit:a1", "reddit:b1", "reddit:dup1"]


def test_submission_missing_id_raises():
    bad_sub = SimpleNamespace(title="t", selftext="", author=None, created_utc=0, permalink="/x/")
    reddit = _fake_reddit({"x": [bad_sub]})
    with pytest.raises(ValueError, match="id"):
        radar_reddit.scrape_subreddit("x", reddit=reddit)
