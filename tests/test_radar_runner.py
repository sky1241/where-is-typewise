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


@pytest.fixture(autouse=True)
def _no_real_network(monkeypatch):
    """Default-mock the network-touching calls so tests can't accidentally hit the internet."""
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [])
    monkeypatch.setattr(runner.dach, "fetch_all", lambda *_a, **_kw: [])
    monkeypatch.setattr(runner.locale_tagger, "tag_threads_in_db", lambda *_a, **_kw: 0)


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


def test_run_persists_all_three_sources(monkeypatch, tmp_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1"), _thread("hn:2")])
    monkeypatch.setattr(runner.reddit, "client_from_env", lambda: MagicMock())
    monkeypatch.setattr(runner.reddit, "scrape_many", lambda *_a, **_kw: [_thread("reddit:a", source="reddit")])
    monkeypatch.setattr(runner.dach, "fetch_all", lambda *_a, **_kw: [_thread("dach:t3n:abc", source="dach")])
    monkeypatch.setattr(runner.locale_tagger, "tag_threads_in_db", lambda *_a, **_kw: 2)

    with patch.object(runner.scorer, "score_many", return_value=iter([])) as score_mock, \
         patch.object(runner, "Anthropic", return_value=MagicMock()):
        summary = runner.run(_minimal_config(), db_path=tmp_db)

    assert summary["fetched_hn"] == 2
    assert summary["fetched_reddit"] == 1
    assert summary["fetched_dach"] == 1
    assert summary["persisted"] == 4
    assert summary["locale_tagged"] == 2
    score_mock.assert_called_once()

    with store.connect(tmp_db) as conn:
        rows = store.query_threads(conn, limit=10)
        assert {r["id"] for r in rows} == {"hn:1", "hn:2", "reddit:a", "dach:t3n:abc"}


def test_run_skips_reddit_when_creds_missing(monkeypatch, tmp_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1")])
    monkeypatch.setattr(
        runner.reddit, "client_from_env",
        MagicMock(side_effect=runner.reddit.RedditCredsMissing("no creds")),
    )

    with patch.object(runner.scorer, "score_many") as score_mock:
        summary = runner.run(_minimal_config(), db_path=tmp_db)

    assert summary["fetched_reddit"] == 0
    assert summary["fetched_hn"] == 1
    assert summary["persisted"] == 1
    score_mock.assert_not_called()


def test_dach_keywords_override_disables_filter(monkeypatch, tmp_db):
    """Explicit `dach: {keywords: []}` in config must override global keywords -> empty filter."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    captured = {}

    def fake_fetch_all(*, feeds=None, keywords=None, client=None):
        captured["keywords"] = keywords
        return []

    monkeypatch.setattr(runner.dach, "fetch_all", fake_fetch_all)

    cfg = _minimal_config()
    cfg["dach"] = {"keywords": []}  # explicit empty list
    runner.run(cfg, db_path=tmp_db, use_reddit=False)

    assert captured["keywords"] == []  # not the global ["AI customer service"]


def test_dach_falls_back_to_global_keywords_when_no_override(monkeypatch, tmp_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    captured = {}

    def fake_fetch_all(*, feeds=None, keywords=None, client=None):
        captured["keywords"] = keywords
        return []

    monkeypatch.setattr(runner.dach, "fetch_all", fake_fetch_all)

    cfg = _minimal_config()  # no `dach` key
    runner.run(cfg, db_path=tmp_db, use_reddit=False)

    assert captured["keywords"] == ["AI customer service"]


def test_run_no_dach_flag_skips_dach(monkeypatch, tmp_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1")])
    monkeypatch.setattr(runner.dach, "fetch_all",
                        MagicMock(side_effect=AssertionError("dach must not be called")))

    summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False, use_dach=False)

    assert summary["fetched_dach"] == 0
    assert summary["persisted"] == 1


def test_run_no_tag_locale_skips_langdetect(monkeypatch, tmp_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1")])
    monkeypatch.setattr(runner.locale_tagger, "tag_threads_in_db",
                        MagicMock(side_effect=AssertionError("tagger must not be called")))

    summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False, use_dach=False, tag_locale=False)

    assert summary["locale_tagged"] == 0


def test_run_skips_scoring_when_no_anthropic_key(monkeypatch, tmp_db):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1")])

    with patch.object(runner.scorer, "score_many") as score_mock:
        summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False, use_dach=False)

    assert summary["scored"] == 0
    score_mock.assert_not_called()


def test_run_use_scoring_false_overrides_even_with_key(monkeypatch, tmp_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1")])

    with patch.object(runner.scorer, "score_many") as score_mock:
        summary = runner.run(_minimal_config(), db_path=tmp_db,
                             use_reddit=False, use_dach=False, use_scoring=False)

    assert summary["scored"] == 0
    score_mock.assert_not_called()


def test_run_scoring_writes_results_to_db(monkeypatch, tmp_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    threads = [_thread("hn:1"), _thread("hn:2")]
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: threads)
    scorings = [
        (threads[0], {"intent": "comparison", "competitors_mentioned": ["Fin"],
                      "typewise_mentioned": False, "relevance_score": 0.82, "draft_reply": "hi"}),
        (threads[1], {"intent": "research", "competitors_mentioned": [],
                      "typewise_mentioned": False, "relevance_score": 0.3, "draft_reply": ""}),
    ]

    with patch.object(runner.scorer, "score_many", return_value=iter(scorings)), \
         patch.object(runner, "Anthropic", return_value=MagicMock()):
        summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False, use_dach=False)

    assert summary["scored"] == 2

    with store.connect(tmp_db) as conn:
        row = store.get_thread(conn, "hn:1")
        assert row["intent"] == "comparison"
        assert row["competitors_mentioned"] == ["Fin"]
        assert row["relevance_score"] == pytest.approx(0.82)


def test_run_scores_only_unscored_threads(monkeypatch, tmp_db):
    """BUG-003 regression: already-scored threads must not be re-sent to the (paid) scorer."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    threads = [_thread("hn:1"), _thread("hn:2")]
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: threads)

    with store.connect(tmp_db) as conn:
        store.upsert_thread(conn, _thread("hn:1"))
        store.update_scoring(conn, "hn:1", intent="research", relevance_score=0.7, draft_reply="x")

    with patch.object(runner.scorer, "score_many", return_value=iter([])) as score_mock, \
         patch.object(runner, "Anthropic", return_value=MagicMock()):
        runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False, use_dach=False)

    score_mock.assert_called_once()
    sent = score_mock.call_args.args[0]
    assert [t["id"] for t in sent] == ["hn:2"]      # hn:1 already scored, not re-billed

    with store.connect(tmp_db) as conn:             # and its score survived the re-fetch upsert
        assert store.get_thread(conn, "hn:1")["relevance_score"] == pytest.approx(0.7)


def test_run_skips_scoring_entirely_when_all_threads_scored(monkeypatch, tmp_db):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key")
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1")])

    with store.connect(tmp_db) as conn:
        store.upsert_thread(conn, _thread("hn:1"))
        store.update_scoring(conn, "hn:1", intent="research", relevance_score=0.7, draft_reply="x")

    with patch.object(runner.scorer, "score_many") as score_mock, \
         patch.object(runner, "Anthropic", return_value=MagicMock()):
        summary = runner.run(_minimal_config(), db_path=tmp_db, use_reddit=False, use_dach=False)

    score_mock.assert_not_called()
    assert summary["scored"] == 0


def test_main_cli_returns_zero_and_prints_summary(monkeypatch, tmp_db, capsys, tmp_path):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    cfg_path = tmp_path / "config.yaml"
    cfg_path.write_text(
        "keywords: [x]\nhackernews: {max_results: 5}\nreddit: {subreddits: [], posts_per_sub: 5}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(runner.hackernews, "search_many", lambda *_a, **_kw: [_thread("hn:1")])

    rc = runner.main([
        "--config", str(cfg_path),
        "--db", str(tmp_db),
        "--no-reddit", "--no-dach", "--no-locale-tag", "--no-scoring",
    ])

    assert rc == 0
    out = capsys.readouterr().out
    assert "HN=1" in out
    assert "DACH=0" in out
    assert "persisted=1" in out
    assert "locale_tagged=0" in out
    assert "scored=0" in out
