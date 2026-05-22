"""Streamlit dashboard for where-is-typewise — public buyer-conversation radar.

Visual design follows bible-ux principles (4 px spacing base, ≥4.5:1 contrast,
clear hierarchy) and uses a single CSS injection so the dashboard renders the
same way on Streamlit Community Cloud as it does locally.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import streamlit as st
except ImportError:  # streamlit is optional for unit tests of the pure helpers
    st = None  # type: ignore[assignment]

from src.radar import store

DB_PATH = Path(os.environ.get("WIT_DB_PATH", "data/radar.db"))


_SOURCE_BADGES = {
    "hn":     {"label": "Hacker News", "bg": "#ff6600", "fg": "#ffffff"},
    "reddit": {"label": "Reddit",      "bg": "#ff4500", "fg": "#ffffff"},
    "dach":   {"label": "DACH RSS",    "bg": "#7c3aed", "fg": "#ffffff"},
}

_INTENT_BADGES = {
    "research":   {"label": "RESEARCH",   "bg": "#1f2937", "fg": "#93c5fd"},
    "comparison": {"label": "COMPARISON", "bg": "#1f2937", "fg": "#fbbf24"},
    "complaint":  {"label": "COMPLAINT",  "bg": "#1f2937", "fg": "#f87171"},
    "shopping":   {"label": "SHOPPING",   "bg": "#1f2937", "fg": "#34d399"},
    "irrelevant": {"label": "IRRELEVANT", "bg": "#1f2937", "fg": "#6b7280"},
}

_LOCALE_FLAGS = {"en": "🇬🇧", "de": "🇩🇪", "fr": "🇫🇷", "it": "🇮🇹", "es": "🇪🇸"}


_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #0a0e1a 0%, #0f1320 100%);
}

#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: 2rem; max-width: 1200px;}

/* ------- Hero ------- */
.wit-hero {
    padding: 32px 36px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(124,58,237,0.18) 0%, rgba(37,99,235,0.12) 100%);
    border: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 28px;
}
.wit-hero h1 {
    font-size: 2.5rem; font-weight: 800; letter-spacing: -0.02em;
    margin: 0 0 8px 0; color: #f9fafb;
    background: linear-gradient(90deg, #f9fafb, #c4b5fd);
    -webkit-background-clip: text; background-clip: text;
    -webkit-text-fill-color: transparent;
}
.wit-hero .wit-tag {
    display: inline-block; padding: 4px 10px; border-radius: 999px;
    background: rgba(124,58,237,0.22); color: #c4b5fd;
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; margin-bottom: 14px;
}
.wit-hero p {
    color: #9ca3af; font-size: 1.02rem; line-height: 1.55; margin: 0; max-width: 680px;
}

/* ------- Metric cards ------- */
.wit-metric-grid {
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 24px;
}
.wit-metric {
    background: #161b29; border: 1px solid rgba(255,255,255,0.06);
    padding: 22px 24px; border-radius: 12px;
    transition: border-color .2s ease, transform .2s ease;
}
.wit-metric:hover {border-color: rgba(124,58,237,0.45); transform: translateY(-2px);}
.wit-metric .wit-label {
    font-size: 0.72rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #9ca3af; margin-bottom: 12px;
}
.wit-metric .wit-value {
    font-size: 2.8rem; font-weight: 800; line-height: 1; letter-spacing: -0.02em;
    font-variant-numeric: tabular-nums; color: #f9fafb;
}
.wit-metric.gap-hot .wit-value {color: #f87171;}
.wit-metric.gap-warm .wit-value {color: #fbbf24;}
.wit-metric.gap-good .wit-value {color: #34d399;}
.wit-metric .wit-sub {color: #6b7280; font-size: 0.82rem; margin-top: 8px;}

/* ------- Section titles ------- */
.wit-section-title {
    font-size: 0.78rem; font-weight: 700; letter-spacing: 0.1em;
    text-transform: uppercase; color: #9ca3af;
    margin: 28px 0 12px 0; padding-bottom: 8px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

/* ------- Thread cards (style the native expanders) ------- */
div[data-testid="stExpander"] {
    background: #161b29; border: 1px solid rgba(255,255,255,0.06);
    border-radius: 12px; margin-bottom: 12px;
    transition: border-color .2s ease;
}
div[data-testid="stExpander"]:hover {border-color: rgba(124,58,237,0.35);}
div[data-testid="stExpander"] summary {
    padding: 16px 20px; font-weight: 600; color: #e5e7eb; font-size: 0.98rem;
}
div[data-testid="stExpander"] summary:hover {color: #ffffff;}

/* Badges injected via st.markdown inside the expander */
.wit-badge {
    display: inline-block; padding: 3px 9px; border-radius: 6px;
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.06em;
    margin-right: 6px; vertical-align: middle;
}
.wit-score {
    display: inline-block; padding: 3px 10px; border-radius: 6px;
    background: #1f2937; color: #e5e7eb; font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem; font-weight: 600; margin-left: 6px;
}
.wit-score.hot {background: rgba(248,113,113,0.18); color: #fca5a5;}
.wit-score.warm {background: rgba(251,191,36,0.18); color: #fcd34d;}

.wit-meta {
    color: #9ca3af; font-size: 0.86rem; margin: 6px 0;
}
.wit-meta a {color: #93c5fd; text-decoration: none;}
.wit-meta a:hover {text-decoration: underline;}

.wit-body {
    background: #0d1119; border-left: 3px solid rgba(124,58,237,0.45);
    padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 10px 0;
    color: #d1d5db; font-size: 0.92rem; line-height: 1.55;
}

.wit-draft-label {
    font-size: 0.72rem; font-weight: 700; letter-spacing: 0.08em;
    text-transform: uppercase; color: #c4b5fd;
    margin: 16px 0 6px 0;
}
.stTextArea textarea {
    background: #0d1119 !important; border-color: rgba(124,58,237,0.25) !important;
    color: #e5e7eb !important; font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.88rem !important; line-height: 1.55 !important;
}

/* ------- Filter controls polish ------- */
.stSelectbox label, .stSlider label, .stCheckbox label {
    color: #9ca3af !important; font-size: 0.78rem !important;
    font-weight: 600 !important; letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

/* Hide the "thread count" line padding artifacts */
.wit-thread-count {
    color: #9ca3af; font-size: 0.9rem; margin: 12px 0;
}
.wit-thread-count strong {color: #f9fafb; font-weight: 700;}

/* Empty state */
.wit-empty {
    text-align: center; padding: 60px 20px; color: #9ca3af;
    background: #161b29; border: 1px dashed rgba(255,255,255,0.1);
    border-radius: 12px;
}
.wit-empty h3 {color: #e5e7eb; font-size: 1.1rem; margin-bottom: 8px;}
.wit-empty code {
    background: #0d1119; padding: 2px 6px; border-radius: 4px;
    color: #c4b5fd; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem;
}
</style>
"""


def _format_competitors(value):
    if not value:
        return None
    return list(value)


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


def _count_mentioned_recent(conn, *, since_days: int = 7) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=since_days)).isoformat(timespec="seconds")
    sql = "SELECT COUNT(*) FROM threads WHERE typewise_mentioned = 1 AND created_at >= ?"
    (n,) = conn.execute(sql, (cutoff,)).fetchone()
    return int(n)


def _gap_severity(gap: int) -> str:
    if gap >= 5:
        return "gap-hot"
    if gap >= 2:
        return "gap-warm"
    return "gap-good"


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
    st.markdown(_CSS, unsafe_allow_html=True)

    st.markdown(
        """
        <div class="wit-hero">
            <div class="wit-tag">📡 Live Buyer Radar · Candidate Artifact</div>
            <h1>where-is-typewise</h1>
            <p>Surfacing the Reddit, Hacker News and DACH RSS conversations where Typewise should have appeared in the discussion — and didn't. Built solo in four hours as the candidate artifact for the Typewise AI Growth Engineer role.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not DB_PATH.exists():
        st.markdown(
            f"""
            <div class="wit-empty">
                <h3>No data yet</h3>
                <p>No database found at <code>{DB_PATH}</code>.</p>
                <p>Run <code>python -m src.seed_demo</code> for the demo dataset,<br>
                or <code>python -m src.radar.runner</code> to fetch live HN + Reddit + DACH data.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    with store.connect(DB_PATH) as conn:
        _render_dashboard(conn)


def _render_dashboard(conn) -> None:
    headline_count = store.count_unmentioned_relevant(conn, min_score=0.7, since_days=7)
    mentioned_count = _count_mentioned_recent(conn, since_days=7)
    severity = _gap_severity(headline_count)

    st.markdown(
        f"""
        <div class="wit-metric-grid">
            <div class="wit-metric {severity}">
                <div class="wit-label">Should have been mentioned</div>
                <div class="wit-value">{headline_count}</div>
                <div class="wit-sub">High-relevance threads this week, no Typewise mention</div>
            </div>
            <div class="wit-metric">
                <div class="wit-label">Typewise was mentioned</div>
                <div class="wit-value">{mentioned_count}</div>
                <div class="wit-sub">Threads where the brand actually surfaced</div>
            </div>
            <div class="wit-metric {severity}">
                <div class="wit-label">Coverage gap</div>
                <div class="wit-value">{headline_count}:{mentioned_count}</div>
                <div class="wit-sub">Ratio of missed buyer conversations to wins</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="wit-section-title">Filters</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.4])
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

    st.markdown(
        f'<div class="wit-thread-count"><strong>{len(threads)}</strong> thread(s) matching filters</div>',
        unsafe_allow_html=True,
    )

    if not threads:
        st.markdown(
            """
            <div class="wit-empty">
                <h3>No matches</h3>
                <p>Try widening the filters — lower the score threshold, or untick "only unmentioned".</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    for t in threads:
        _render_thread(t)


def _render_thread(t: dict) -> None:
    title = t.get("title") or "(no title)"
    score = t.get("relevance_score")
    score_label = f"{score:.2f}" if score is not None else "—"
    score_class = "hot" if (score or 0) >= 0.85 else ("warm" if (score or 0) >= 0.7 else "")
    source = t.get("source") or "?"
    locale = t.get("locale") or ""
    intent = t.get("intent") or "—"
    flag = _LOCALE_FLAGS.get(locale, "🌐")

    header = f"{flag}  {title}"
    with st.expander(header):
        # Badges row
        source_badge = _SOURCE_BADGES.get(source, {"label": source.upper(), "bg": "#374151", "fg": "#e5e7eb"})
        intent_badge = _INTENT_BADGES.get(intent, {"label": intent.upper(), "bg": "#1f2937", "fg": "#9ca3af"})
        st.markdown(
            f"""
            <div style="margin-bottom: 10px;">
                <span class="wit-badge" style="background:{source_badge['bg']};color:{source_badge['fg']};">{source_badge['label']}</span>
                <span class="wit-badge" style="background:{intent_badge['bg']};color:{intent_badge['fg']};">{intent_badge['label']}</span>
                <span class="wit-score {score_class}">score {score_label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        comps = _format_competitors(t.get("competitors_mentioned"))
        comp_html = ", ".join(comps) if comps else "<em style='color:#6b7280'>none</em>"
        url = t.get("url") or "#"
        st.markdown(
            f"""
            <div class="wit-meta">
                <strong>URL:</strong> <a href="{url}" target="_blank">{url}</a><br>
                <strong>Author:</strong> {t.get("author") or "—"} · <strong>Posted:</strong> {_format_age(t.get("created_at"))}<br>
                <strong>Competitors mentioned:</strong> {comp_html}<br>
                <strong>Typewise mentioned:</strong> {"✅ yes" if t.get("typewise_mentioned") else "❌ no"}
            </div>
            """,
            unsafe_allow_html=True,
        )

        if t.get("body"):
            body_excerpt = t["body"][:600] + ("…" if len(t["body"]) > 600 else "")
            st.markdown(
                f'<div class="wit-body">{body_excerpt}</div>',
                unsafe_allow_html=True,
            )

        if t.get("draft_reply"):
            st.markdown('<div class="wit-draft-label">💬 Suggested reply (Claude draft — review before posting)</div>', unsafe_allow_html=True)
            st.text_area(
                label=f"draft_{t['id']}",
                value=t["draft_reply"],
                height=160,
                label_visibility="collapsed",
            )


if __name__ == "__main__":
    main()
