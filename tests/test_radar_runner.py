"""Unit tests for src/radar/runner.py — every external call is mocked."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.radar import runner, store


def _thread(thread_id: str, source: str = "hn") -> dict:
    return {
        "id": thread_id,
        "source": source,
        "locale": None,
        "url": f"https://example.com/{thread_id}",
        "title": f"thread {thread_id}",
        "body": "x",
        "author": "u",
        "created_at": "2026-05-22T00:00:00+00:00",
        "fetched_at": "2026-05-22T00:00:00+00:00",
        "intent": None,
        "competitors_mentioned": None,
        "typewise_mentioned": None,
        "relevance_score": None,
        "draft_reply": None,
    }


def _minimal_config() -> dict:
    return {
        "keywords": ["AI customer service"],
        "hackernews": {"max_results": 50},
        "reddit": {"subreddits": ["CustomerSuccess"], "posts_per_sub": 50},
        "competitors": ["Fin", "Decagon"],
    }


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "radar.db"


def test_load_config_parses_yaml(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("keywords:\n  - foo\nreddit:\n  subreddits: [bar]\n", encoding="utf-8")

    cfg = runner.load_config(cfg_path)

    assert cfg["keywords"] == ["foo"]
    assert cfg["reddit"]["subreddits"] == ["bar"]


def test_load_config_rejects_non_mapping(tmp_path: Path):
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text("- just a list\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        runner.load_config(cfg_path)


def test_run_persists_hn_and_reddit_when_creds_available(monkeypatch, tmp_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    hn_threads = [_thread("hn:1"), _thread("hn:2")]
    reddit_threads = [_thread("reddit:a", source="reddit")]

    with patch.object(runner.hackernews, "search_many", return_value=hn_threads) as hn_mock, \
         patch.object(runner.reddit, "client_from_env", return_value=MagicMock()), \
         patch.object(runner.reddit, "scrape_many", return_value=reddit_threads), \
         patch.object(runner.scorer, "score_many", return_value=iter([])) as score_mock, \
         patch.object(runner, "Anthropic", return_value=MagicMock()):
        summary = runner.run(_minimal_config(), db_path=tmp_db)

    assert summary["fetched_hn"] == 2
    assert summary["fetched_reddit"] == 1
    assert summary["persisted"] == 3
    hn_mock.assert_called_once()
    score_mock.assert_called_once()  # scoring attempted because key was set

    with store.connect(tmp_db) as conn:
        rows = store.query_threads(conn, limit=10)
        assert {r["id"] for r in rows} == {"hn:1", "hn:2", "reddit:a"}


def test_run_skips_reddit_when_creds_missing(monkeypatch, tmp_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with patch.object(runner.hackernews, "search_many", return_value=[_thread("hn:1")]), \
         patch.object(runner.reddit, "client_from_env",
                      side_effect=runner.reddit.RedditCredsMissing("no creds")), \
         patch.object(runner.scorer, "score_many") as score_mock:
        summary = runner.run(_minimal_config(), db_path=tmp_db)

    assert summary["fetched_reddit"] == 0
    assert summary["fetched_hn"] == 1
    assert summary["persisted"] == 1
    score_mock.assert_not_called()  # no anthropic key


def test_run_skips_scoring_when_no_anthropic_key(monkeypatch, tmp_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with patch.object(runner.hackernews, "search_many", return_value=[_thread("hn:1")]), \
         patch.object(runner.scorer, "score_many") as score_mock:
        summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False)

    assert summary["scored"] == 0
    score_mock.assert_not_called()


def test_run_use_scoring_false_overrides_even_with_key(monkeypatch, tmp_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    with patch.object(runner.hackernews, "search_many", return_value=[_thread("hn:1")]), \
         patch.object(runner.scorer, "score_many") as score_mock:
        summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False, use_scoring=False)

    assert summary["scored"] == 0
    score_mock.assert_not_called()


def test_run_scoring_writes_results_to_db(monkeypatch, tmp_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    threads = [_thread("hn:1"), _thread("hn:2")]
    scorings = [
        (threads[0], {"intent": "comparison", "competitors_mentioned": ["Fin"],
                      "typewise_mentioned": False, "relevance_score": 0.82, "draft_reply": "hi"}),
        (threads[1], {"intent": "research", "competitors_mentioned": [],
                      "typewise_mentioned": False, "relevance_score": 0.3, "draft_reply": ""}),
    ]

    with patch.object(runner.hackernews, "search_many", return_value=threads), \
         patch.object(runner.scorer, "score_many", return_value=iter(scorings)), \
         patch.object(runner, "Anthropic", return_value=MagicMock()):
        summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False)

    assert summary["scored"] == 2

    with store.connect(tmp_db) as conn:
        row = store.get_thread(conn, "hn:1")
        assert row["intent"] == "comparison"
        assert row["competitors_mentioned"] == ["Fin"]
        assert row["relevance_score"] == pytest.approx(0.82)


def test_main_cli_returns_zero_and_prints_summary(monkeypatch, tmp_db, capsys, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "keywords: [x]\nhackernews: {max_results: 5}\nreddit: {subreddits: [], posts_per_sub: 5}\n",
        encoding="utf-8",
    )

    with patch.object(runner.hackernews, "search_many", return_value=[_thread("hn:1")]):
        rc = runner.main(["--config", str(cfg_path), "--db", str(tmp_db), "--no-reddit", "--no-scoring"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "HN=1" in out
    assert "persisted=1" in out
    assert "scored=0" in out
