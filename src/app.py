"""Streamlit dashboard for where-is-typewise — public buyer-conversation radar."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

try:
    import streamlit as st
except ImportError:  # streamlit is optional for unit tests of the pure helpers
    st = None  # type: ignore[assignment]

from src.radar import store

DB_PATH = Path(os.environ.get("WIT_DB_PATH", "data/radar.db"))


def _format_competitors(value):
    if not value:
        return "—"
    return ", ".join(value)


def _format_age(iso_ts: str | None) -> str:
    if not iso_ts:
        return "—"
    try:
        ts = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    except ValueError:
        return iso_ts
    now = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    delta = now - ts
    days = delta.days
    if days >= 1:
        return f"{days}d ago"
    hours = delta.seconds // 3600
    if hours >= 1:
        return f"{hours}h ago"
    return f"{max(delta.seconds // 60, 1)}m ago"


def main() -> None:
    if st is None:
        raise ImportError(
            "streamlit is not installed in this environment. "
            "Run: pip install -r requirements.txt"
        )
    st.set_page_config(
        page_title="where-is-typewise — buyer radar",
        layout="wide",
        page_icon="📡",
    )

    st.title("📡 where-is-typewise")
    st.caption(
        "Live radar of Reddit + Hacker News conversations where Typewise should have "
        "appeared in the discussion but didn't."
    )

    if not DB_PATH.exists():
        st.warning(
            f"No database found at `{DB_PATH}`. "
            "Run `python -m src.radar.runner` (once Phase 2 lands) or "
            "`python -m src.seed_demo` to load a demo dataset."
        )
        return

    with store.connect(DB_PATH) as conn:
        _render_dashboard(conn)


def _render_dashboard(conn) -> None:
    headline_count = store.count_unmentioned_relevant(conn, min_score=0.7, since_days=7)
    mentioned_count = _count_mentioned_recent(conn, since_days=7)

    col_a, col_b, col_c = st.columns(3)
    col_a.metric(
        "Threads this week where Typewise should have been mentioned",
        headline_count,
    )
    col_b.metric("Threads this week where Typewise WAS mentioned", mentioned_count)
    col_c.metric(
        "Coverage gap",
        f"{headline_count}:{mentioned_count}" if mentioned_count else f"{headline_count}:0",
    )

    st.divider()
    st.subheader("Filters")

    col1, col2, col3, col4 = st.columns(4)
    source_filter = col1.selectbox("Source", ["(any)", "hn", "reddit", "dach"])
    locale_filter = col2.selectbox("Locale", ["(any)", "en", "de", "fr", "it"])
    intent_filter = col3.selectbox(
        "Intent", ["(any)", "research", "comparison", "complaint", "shopping"]
    )
    min_score = col4.slider("Min relevance score", 0.0, 1.0, 0.5, 0.05)

    show_only_unmentioned = st.checkbox(
        "Only threads where Typewise was NOT mentioned", value=True
    )

    threads = store.query_threads(
        conn,
        source=None if source_filter == "(any)" else source_filter,
        locale=None if locale_filter == "(any)" else locale_filter,
        intent=None if intent_filter == "(any)" else intent_filter,
        typewise_mentioned=False if show_only_unmentioned else None,
        min_score=min_score,
        limit=100,
    )

    st.write(f"**{len(threads)} thread(s) matching filters**")

    for t in threads:
        _render_thread(t)


def _render_thread(t: dict) -> None:
    title = t.get("title") or "(no title)"
    score = t.get("relevance_score")
    score_label = f"{score:.2f}" if score is not None else "—"
    source = t.get("source") or "?"
    intent = t.get("intent") or "—"

    with st.expander(f"[{source}] {title}  ·  score {score_label}  ·  {intent}"):
        st.markdown(f"**URL:** {t.get('url', '—')}")
        st.markdown(f"**Author:** {t.get('author') or '—'}  ·  {_format_age(t.get('created_at'))}")
        st.markdown(f"**Competitors mentioned:** {_format_competitors(t.get('competitors_mentioned'))}")
        st.markdown(f"**Typewise mentioned:** {'yes' if t.get('typewise_mentioned') else 'no'}")
        if t.get("body"):
            st.markdown("**Thread body:**")
            st.text(t["body"][:600] + ("…" if len(t["body"]) > 600 else ""))
        if t.get("draft_reply"):
            st.markdown("**Suggested reply (Claude draft — review before posting):**")
            st.text_area(
                label=f"draft_{t['id']}",
                value=t["draft_reply"],
                height=160,
                label_visibility="collapsed",
            )


def _count_mentioned_recent(conn, *, since_days: int = 7) -> int:
    from datetime import timedelta
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat(timespec="seconds")
    sql = "SELECT COUNT(*) FROM threads WHERE typewise_mentioned = 1 AND created_at >= ?"
    (n,) = conn.execute(sql, (cutoff,)).fetchone()
    return int(n)


if __name__ == "__main__":
    main()
