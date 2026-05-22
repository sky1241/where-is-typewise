"""Unit tests for src/radar/store.py — schema, upsert idempotency, scoring, queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from src.radar import store


def _thread(**over: Any) -> dict[str, Any]:
    base = {
        "id": "hn:1",
        "source": "hn",
        "locale": None,
        "url": "https://news.ycombinator.com/item?id=1",
        "title": "test",
        "body": "body",
        "author": "user",
        "created_at": "2026-05-22T08:00:00+00:00",
        "fetched_at": "2026-05-22T09:00:00+00:00",
        "intent": None,
        "competitors_mentioned": None,
        "typewise_mentioned": None,
        "relevance_score": None,
        "draft_reply": None,
    }
    base.update(over)
    return base


@pytest.fixture()
def conn():
    with store.connect(":memory:") as c:
        yield c


def test_connect_creates_threads_table(conn):
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(threads)")}
    expected = {
        "id", "source", "locale", "url", "title", "body", "author",
        "created_at", "fetched_at", "intent", "competitors_mentioned",
        "typewise_mentioned", "relevance_score", "draft_reply",
    }
    assert expected.issubset(cols)


def test_upsert_then_get_roundtrip(conn):
    t = _thread(
        competitors_mentioned=["Fin", "Decagon"],
        typewise_mentioned=True,
        relevance_score=0.82,
        intent="comparison",
        draft_reply="hi",
    )
    store.upsert_thread(conn, t)
    got = store.get_thread(conn, "hn:1")
    assert got is not None
    assert got["competitors_mentioned"] == ["Fin", "Decagon"]
    assert got["typewise_mentioned"] is True
    assert got["relevance_score"] == pytest.approx(0.82)
    assert got["intent"] == "comparison"


def test_upsert_is_idempotent(conn):
    store.upsert_thread(conn, _thread(title="v1"))
    store.upsert_thread(conn, _thread(title="v2"))
    (count,) = conn.execute("SELECT COUNT(*) FROM threads").fetchone()
    assert count == 1
    assert store.get_thread(conn, "hn:1")["title"] == "v2"


def test_upsert_many_returns_count(conn):
    threads = [_thread(id=f"hn:{i}") for i in range(5)]
    n = store.upsert_many(conn, threads)
    assert n == 5
    (count,) = conn.execute("SELECT COUNT(*) FROM threads").fetchone()
    assert count == 5


def test_get_thread_missing_returns_none(conn):
    assert store.get_thread(conn, "hn:nope") is None


def test_update_scoring_partial_does_not_clobber_existing(conn):
    store.upsert_thread(conn, _thread(intent="research", relevance_score=0.5))
    ok = store.update_scoring(
        conn, "hn:1",
        competitors_mentioned=["Sierra"],
        typewise_mentioned=False,
        draft_reply="hello",
    )
    assert ok is True
    got = store.get_thread(conn, "hn:1")
    assert got["intent"] == "research"          # preserved (COALESCE)
    assert got["relevance_score"] == pytest.approx(0.5)
    assert got["competitors_mentioned"] == ["Sierra"]
    assert got["typewise_mentioned"] is False
    assert got["draft_reply"] == "hello"


def test_update_scoring_missing_row_returns_false(conn):
    assert store.update_scoring(conn, "hn:ghost", intent="x") is False


def test_query_threads_filters_and_orders_by_score(conn):
    store.upsert_many(conn, [
        _thread(id="hn:a", relevance_score=0.9, intent="comparison", typewise_mentioned=False),
        _thread(id="hn:b", relevance_score=0.4, intent="research",   typewise_mentioned=False),
        _thread(id="hn:c", relevance_score=0.85, intent="comparison", typewise_mentioned=True),
        _thread(id="hn:d", relevance_score=None, intent="irrelevant"),
    ])
    rows = store.query_threads(conn, intent="comparison", min_score=0.8)
    assert [r["id"] for r in rows] == ["hn:a", "hn:c"]
    only_unmentioned = store.query_threads(conn, intent="comparison", typewise_mentioned=False)
    assert [r["id"] for r in only_unmentioned] == ["hn:a"]


def test_count_unmentioned_relevant_matches_acceptance_query(conn):
    now = datetime.now(timezone.utc)
    fresh = (now - timedelta(days=2)).isoformat(timespec="seconds")
    stale = (now - timedelta(days=30)).isoformat(timespec="seconds")
    store.upsert_many(conn, [
        _thread(id="hn:hot",  relevance_score=0.91, typewise_mentioned=False, created_at=fresh),
        _thread(id="hn:cold", relevance_score=0.95, typewise_mentioned=False, created_at=stale),
        _thread(id="hn:low",  relevance_score=0.50, typewise_mentioned=False, created_at=fresh),
        _thread(id="hn:has",  relevance_score=0.95, typewise_mentioned=True,  created_at=fresh),
    ])
    assert store.count_unmentioned_relevant(conn, min_score=0.7, since_days=7) == 1
    assert store.count_unmentioned_relevant(conn, min_score=0.7, since_days=None) == 2


def test_competitors_serialization_handles_none_and_tuple(conn):
    store.upsert_thread(conn, _thread(id="hn:tuple", competitors_mentioned=("Fin", "Ada")))
    got = store.get_thread(conn, "hn:tuple")
    assert got["competitors_mentioned"] == ["Fin", "Ada"]
    store.upsert_thread(conn, _thread(id="hn:none", competitors_mentioned=None))
    assert store.get_thread(conn, "hn:none")["competitors_mentioned"] is None


def test_db_file_is_created_on_disk(tmp_path):
    db_path = tmp_path / "subdir" / "radar.db"
    with store.connect(db_path) as c:
        store.upsert_thread(c, _thread())
    assert db_path.exists()
    with store.connect(db_path) as c:
        assert store.get_thread(c, "hn:1")["title"] == "test"
