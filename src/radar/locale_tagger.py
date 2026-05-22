"""Set `locale` on threads via langdetect — meant for HN/Reddit rows where locale is NULL.

DACH threads get their locale pre-set at fetch time (the feed's primary language is
known); this module fills in the rest. langdetect is probabilistic, so we seed it for
reproducibility and refuse to guess on very short snippets.
"""

from __future__ import annotations

import logging
import sqlite3
from typing import Any

from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0

logger = logging.getLogger("radar.locale_tagger")

MIN_TEXT_LEN = 20


def detect_locale(thread: dict[str, Any], *, default: str | None = None) -> str | None:
    """Return a 2-letter locale code (e.g. 'en', 'de', 'fr') or `default` when undecidable.

    Concatenates title+body, ignores anything shorter than MIN_TEXT_LEN chars to avoid
    langdetect's high false-positive rate on tiny snippets.
    """
    pieces = [thread.get("title") or "", thread.get("body") or ""]
    text = " ".join(p for p in pieces if p).strip()
    if len(text) < MIN_TEXT_LEN:
        return default
    try:
        return detect(text)
    except LangDetectException:
        return default


def tag_threads_in_db(
    conn: sqlite3.Connection,
    *,
    only_untagged: bool = True,
    default: str | None = None,
) -> int:
    """Set the `locale` column for threads that don't have one.

    Args:
        conn: connection from store.connect (Row factory expected).
        only_untagged: when True (default) only touches rows where locale IS NULL.
            When False, re-runs detection on every row — useful after bulk imports.
        default: locale string to use when langdetect refuses or text is too short.
            None means leave the row untouched.

    Returns:
        Number of rows updated.
    """
    sql = "SELECT id, title, body FROM threads"
    if only_untagged:
        sql += " WHERE locale IS NULL"
    rows = conn.execute(sql).fetchall()
    updated = 0
    for row in rows:
        locale = detect_locale({"title": row["title"], "body": row["body"]}, default=default)
        if locale is None:
            continue
        conn.execute("UPDATE threads SET locale = ? WHERE id = ?", (locale, row["id"]))
        updated += 1
    conn.commit()
    return updated
