"""Tests for the Streamlit dashboard helpers and the seed_demo loader."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src import app
from src import seed_demo
from src.radar import store


@pytest.fixture
def memory_db_with_demo():
    with store.connect(":memory:") as conn:
        store.upsert_many(conn, seed_demo.DEMO_THREADS)
        yield conn


# --- helpers ---

def test_format_competitors_none_returns_none():
    assert app._format_competitors(None) is None
    assert app._format_competitors([]) is None


def test_format_competitors_list_returns_list():
    assert app._format_competitors(["Fin", "Decagon"]) == ["Fin", "Decagon"]


def test_format_age_handles_none_gracefully():
    assert app._format_age(None) == "—"


def test_format_age_returns_days_for_old_thread():
    five_days_ago = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat(timespec="seconds")
    assert app._format_age(five_days_ago) == "5d ago"


def test_format_age_returns_hours_for_today_thread():
    three_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(timespec="seconds")
    assert app._format_age(three_hours_ago) == "3h ago"


def test_format_age_returns_minutes_for_very_recent():
    five_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(timespec="seconds")
    assert "m ago" in app._format_age(five_min_ago)


def test_format_age_invalid_string_returned_raw():
    assert app._format_age("not-a-timestamp") == "not-a-timestamp"


# --- seed_demo ---

def test_seed_demo_inserts_eight_threads(memory_db_with_demo):
    threads = store.query_threads(memory_db_with_demo, min_score=0.0, limit=50)
    assert len(threads) == len(seed_demo.DEMO_THREADS)


def test_seed_demo_meets_acceptance_criterion(memory_db_with_demo):
    """Acceptance criterion: count_unmentioned_relevant >= 5."""
    count = store.count_unmentioned_relevant(memory_db_with_demo, min_score=0.7, since_days=7)
    assert count >= 5


def test_seed_demo_includes_dach_locale_threads(memory_db_with_demo):
    de_threads = store.query_threads(memory_db_with_demo, locale="de", min_score=0.0, limit=20)
    assert len(de_threads) >= 1
    fr_threads = store.query_threads(memory_db_with_demo, locale="fr", min_score=0.0, limit=20)
    assert len(fr_threads) >= 1


def test_seed_demo_top_thread_is_high_relevance_unmentioned(memory_db_with_demo):
    threads = store.query_threads(memory_db_with_demo, min_score=0.0, limit=20)
    top = threads[0]
    assert top["relevance_score"] >= 0.9
    assert top["typewise_mentioned"] is False


# --- _count_mentioned_recent ---

def test_count_mentioned_recent_matches_seed(memory_db_with_demo):
    n = app._count_mentioned_recent(memory_db_with_demo, since_days=14)
    # Exactly one demo thread has typewise_mentioned=True.
    assert n == 1


# --- BUG-002 regression: headline metrics must not be zeroed by a time window ---

def test_headline_counts_old_hot_threads_without_time_window():
    """BUG-002: hot threads older than any 7-day window must still drive the headline."""
    with store.connect(":memory:") as conn:
        old = (datetime.now(timezone.utc) - timedelta(days=120)).isoformat(timespec="seconds")
        store.upsert_thread(conn, {
            "id": "hn:old-hot", "source": "hn", "locale": "en",
            "url": "https://news.ycombinator.com/item?id=1", "title": "old but hot",
            "body": "", "author": "a", "created_at": old, "fetched_at": old,
            "intent": None, "competitors_mentioned": None, "typewise_mentioned": None,
            "relevance_score": None, "draft_reply": None,
        })
        store.update_scoring(conn, "hn:old-hot", intent="shopping",
                             typewise_mentioned=False, relevance_score=0.9)

        # The dashboard's calls (no window) must see the thread...
        assert store.count_unmentioned_relevant(conn, min_score=0.7, since_days=None) == 1
        assert app._count_mentioned(conn) == 0
        # ...while the old windowed contract would have zeroed it (the bug).
        assert store.count_unmentioned_relevant(conn, min_score=0.7, since_days=7) == 0
