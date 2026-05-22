"""Unit tests for src/radar/locale_tagger.py — uses real langdetect (deterministic, seeded)."""

from __future__ import annotations

import pytest

from src.radar import locale_tagger, store


def test_detect_locale_english():
    thread = {
        "title": "Best AI customer support tool for enterprise",
        "body": "We are evaluating multiple AI customer service products for our team.",
    }
    assert locale_tagger.detect_locale(thread) == "en"


def test_detect_locale_german():
    thread = {
        "title": "Die besten KI-Werkzeuge fuer den Kundenservice",
        "body": "Eine ausfuhrliche Analyse der besten Anbieter im DACH-Raum.",
    }
    assert locale_tagger.detect_locale(thread) == "de"


def test_detect_locale_french():
    thread = {
        "title": "Les meilleurs outils d'IA pour le service client",
        "body": "Une analyse approfondie des solutions d'intelligence artificielle pour les centres de contact.",
    }
    assert locale_tagger.detect_locale(thread) == "fr"


def test_detect_locale_too_short_returns_default():
    thread = {"title": "Hi", "body": ""}
    assert locale_tagger.detect_locale(thread) is None
    assert locale_tagger.detect_locale(thread, default="en") == "en"


def test_detect_locale_empty_returns_default():
    assert locale_tagger.detect_locale({"title": None, "body": None}) is None
    assert locale_tagger.detect_locale({}, default="xx") == "xx"


def test_detect_locale_combines_title_and_body():
    """Each piece alone is below threshold, but together they cross MIN_TEXT_LEN."""
    thread = {"title": "Une question", "body": "sur la qualite du support."}
    assert len((thread["title"] or "") + (thread["body"] or "")) >= locale_tagger.MIN_TEXT_LEN
    assert locale_tagger.detect_locale(thread) == "fr"


@pytest.fixture()
def conn():
    with store.connect(":memory:") as c:
        yield c


def _seed_thread(conn, *, thread_id, locale, title, body):
    t = {
        "id": thread_id, "source": "hn", "locale": locale,
        "url": "https://x/", "title": title, "body": body, "author": "u",
        "created_at": "2026-05-22T00:00:00+00:00",
        "fetched_at": "2026-05-22T00:00:00+00:00",
        "intent": None, "competitors_mentioned": None, "typewise_mentioned": None,
        "relevance_score": None, "draft_reply": None,
    }
    store.upsert_thread(conn, t)


def test_tag_threads_in_db_updates_only_null_by_default(conn):
    _seed_thread(conn, thread_id="hn:1", locale=None,
                 title="English title", body="This is a complete English sentence for langdetect.")
    _seed_thread(conn, thread_id="hn:2", locale="xx",  # pre-tagged, shouldn't change
                 title="Beliebte deutsche Werkzeuge fuer Kundenservice",
                 body="Eine ausfuhrliche Analyse im DACH-Raum.")

    n = locale_tagger.tag_threads_in_db(conn)

    assert n == 1
    assert store.get_thread(conn, "hn:1")["locale"] == "en"
    assert store.get_thread(conn, "hn:2")["locale"] == "xx"  # untouched


def test_tag_threads_in_db_only_untagged_false_overwrites(conn):
    _seed_thread(conn, thread_id="hn:1", locale="xx",
                 title="This is clearly English text",
                 body="A complete sentence in English for the detector.")

    n = locale_tagger.tag_threads_in_db(conn, only_untagged=False)

    assert n == 1
    assert store.get_thread(conn, "hn:1")["locale"] == "en"


def test_tag_threads_in_db_skips_too_short(conn):
    _seed_thread(conn, thread_id="hn:short", locale=None, title="Hi", body="")
    _seed_thread(conn, thread_id="hn:long",  locale=None,
                 title="A reasonably long English sentence to trigger langdetect.",
                 body="With additional body text to be safe.")

    n = locale_tagger.tag_threads_in_db(conn)

    assert n == 1
    assert store.get_thread(conn, "hn:short")["locale"] is None
    assert store.get_thread(conn, "hn:long")["locale"] == "en"


def test_tag_threads_in_db_applies_default_when_provided(conn):
    _seed_thread(conn, thread_id="hn:short", locale=None, title="Hi", body="")

    n = locale_tagger.tag_threads_in_db(conn, default="en")

    assert n == 1
    assert store.get_thread(conn, "hn:short")["locale"] == "en"


def test_detect_is_deterministic_across_runs():
    """DetectorFactory.seed=0 in the module → same input → same output."""
    thread = {
        "title": "A reasonably long sentence that mixes some signals",
        "body":  "to demonstrate the seeded detection is stable.",
    }
    first = locale_tagger.detect_locale(thread)
    for _ in range(5):
        assert locale_tagger.detect_locale(thread) == first
