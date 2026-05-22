"""SQLite store for radar threads.

Schema for radar `threads`. Idempotent upserts
keyed on `id` (e.g. `hn:38291837`, `reddit:abc123`) so re-running scrapers is safe.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator

DEFAULT_DB_PATH = Path("data/radar.db")

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    locale TEXT,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    author TEXT,
    created_at TEXT,
    fetched_at TEXT,
    intent TEXT,
    competitors_mentioned TEXT,
    typewise_mentioned INTEGER,
    relevance_score REAL,
    draft_reply TEXT
);
CREATE INDEX IF NOT EXISTS idx_threads_source ON threads(source);
CREATE INDEX IF NOT EXISTS idx_threads_score  ON threads(relevance_score);
CREATE INDEX IF NOT EXISTS idx_threads_typew  ON threads(typewise_mentioned);
"""

_COLUMNS = (
    "id", "source", "locale", "url", "title", "body", "author",
    "created_at", "fetched_at", "intent", "competitors_mentioned",
    "typewise_mentioned", "relevance_score", "draft_reply",
)


def _ensure_parent(path: Path) -> None:
    if str(path) == ":memory:":
        return
    path.parent.mkdir(parents=True, exist_ok=True)


def _serialize_competitors(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return json.dumps(list(value), ensure_ascii=False)


def _deserialize_competitors(value: str | None) -> list[str] | None:
    if not value:
        return None
    try:
        decoded = json.loads(value)
    except json.JSONDecodeError:
        return None
    return list(decoded) if isinstance(decoded, list) else None


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = {k: row[k] for k in row.keys()}
    d["competitors_mentioned"] = _deserialize_competitors(d.get("competitors_mentioned"))
    tw = d.get("typewise_mentioned")
    d["typewise_mentioned"] = None if tw is None else bool(tw)
    return d


@contextmanager
def connect(path: str | Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    """Open (and lazily create) the radar SQLite DB, applying schema on first open."""
    p = Path(path) if path != ":memory:" else path
    if isinstance(p, Path):
        _ensure_parent(p)
        conn = sqlite3.connect(p)
    else:
        conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
        yield conn
    finally:
        conn.close()


def upsert_thread(conn: sqlite3.Connection, thread: dict[str, Any]) -> None:
    """Insert or replace a single thread row. Idempotent on `id`."""
    payload = {col: thread.get(col) for col in _COLUMNS}
    payload["competitors_mentioned"] = _serialize_competitors(payload["competitors_mentioned"])
    tw = payload["typewise_mentioned"]
    payload["typewise_mentioned"] = None if tw is None else int(bool(tw))
    placeholders = ", ".join(f":{c}" for c in _COLUMNS)
    sql = f"INSERT OR REPLACE INTO threads ({', '.join(_COLUMNS)}) VALUES ({placeholders})"
    conn.execute(sql, payload)
    conn.commit()


def upsert_many(conn: sqlite3.Connection, threads: Iterable[dict[str, Any]]) -> int:
    """Bulk upsert; returns count of rows written."""
    n = 0
    for t in threads:
        upsert_thread(conn, t)
        n += 1
    return n


def get_thread(conn: sqlite3.Connection, thread_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)).fetchone()
    return _row_to_dict(row) if row else None


def update_scoring(
    conn: sqlite3.Connection,
    thread_id: str,
    *,
    intent: str | None = None,
    competitors_mentioned: list[str] | None = None,
    typewise_mentioned: bool | None = None,
    relevance_score: float | None = None,
    draft_reply: str | None = None,
) -> bool:
    """Update scorer-owned columns for one thread. Returns True if a row was updated."""
    tw = None if typewise_mentioned is None else int(bool(typewise_mentioned))
    cur = conn.execute(
        """
        UPDATE threads SET
            intent = COALESCE(?, intent),
            competitors_mentioned = COALESCE(?, competitors_mentioned),
            typewise_mentioned = COALESCE(?, typewise_mentioned),
            relevance_score = COALESCE(?, relevance_score),
            draft_reply = COALESCE(?, draft_reply)
        WHERE id = ?
        """,
        (
            intent,
            _serialize_competitors(competitors_mentioned),
            tw,
            relevance_score,
            draft_reply,
            thread_id,
        ),
    )
    conn.commit()
    return cur.rowcount > 0


def query_threads(
    conn: sqlite3.Connection,
    *,
    source: str | None = None,
    locale: str | None = None,
    intent: str | None = None,
    typewise_mentioned: bool | None = None,
    min_score: float | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    """List threads matching the supplied filters, ordered by relevance_score DESC NULLS LAST."""
    clauses: list[str] = []
    params: list[Any] = []
    if source is not None:
        clauses.append("source = ?")
        params.append(source)
    if locale is not None:
        clauses.append("locale = ?")
        params.append(locale)
    if intent is not None:
        clauses.append("intent = ?")
        params.append(intent)
    if typewise_mentioned is not None:
        clauses.append("typewise_mentioned = ?")
        params.append(int(bool(typewise_mentioned)))
    if min_score is not None:
        clauses.append("relevance_score >= ?")
        params.append(min_score)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    params.append(int(limit))
    # `where` is composed only of literal predicate strings from this function (e.g. "source = ?")
    # plus the literal "WHERE"/"AND" connectors. Every caller-supplied value flows through `params`
    # as a bound parameter — never into the SQL text — so bandit B608 is a false positive here.
    sql = (
        f"SELECT * FROM threads {where} "  # nosec B608
        "ORDER BY relevance_score IS NULL, relevance_score DESC LIMIT ?"
    )
    return [_row_to_dict(r) for r in conn.execute(sql, params).fetchall()]


def count_unmentioned_relevant(
    conn: sqlite3.Connection,
    *,
    min_score: float = 0.7,
    since_days: int | None = 7,
) -> int:
    """Acceptance-test helper: threads where Typewise wasn't mentioned but score is high.

    Acceptance SQL:
        SELECT COUNT(*) FROM threads WHERE typewise_mentioned=0 AND relevance_score > 0.7
    Adds an optional `since_days` window on `created_at` (ISO-8601 strings sort correctly).
    """
    sql = "SELECT COUNT(*) FROM threads WHERE typewise_mentioned = 0 AND relevance_score > ?"
    params: list[Any] = [min_score]
    if since_days is not None:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat(timespec="seconds")
        sql += " AND created_at >= ?"
        params.append(cutoff)
    (count,) = conn.execute(sql, params).fetchone()
    return int(count)
