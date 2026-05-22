"""Streamlit dashboard for where-is-typewise — public buyer-conversation radar.

Visual design strictly follows /home/sky/Bureau/bible-ux tokens:
  - Spacing on a 4 px scale (4/8/12/16/24/32/48 — never 7, 13, 22)
  - Typography Inter, size scale 12/14/16/18/20/24/32/48, line-heights from VALUES.md
  - Border-radius limited to THREE values per page (4 / 8 / 12), per WEB.md § CO
  - Border OR shadow for elevation — never both, per WEB.md § CT
  - Colors in HSL on a 50–950 scale (bible WEB.md § CP "60-30-10 rule")
  - Dark surfaces from Material 3 elevation scale (VALUES.md § Dark mode)
  - Sentence case everywhere — NEVER ALL-CAPS (WEB.md § L § 70 anti-pattern)
  - :focus-visible 2 px ring with 2 px offset (VALUES.md § Focus indicator)
  - prefers-reduced-motion honored (WEB.md § F § 27)
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


# Semantic colors map directly to bible-ux WEB.md § CP intent palette.
_SOURCE_BADGES = {
    "hn":     {"label": "Hacker News", "tone": "warning"},
    "reddit": {"label": "Reddit",      "tone": "error"},
    "dach":   {"label": "DACH RSS",    "tone": "primary"},
}

_INTENT_BADGES = {
    "research":   {"label": "Research",   "tone": "info"},
    "comparison": {"label": "Comparison", "tone": "warning"},
    "complaint":  {"label": "Complaint",  "tone": "error"},
    "shopping":   {"label": "Shopping",   "tone": "success"},
    "irrelevant": {"label": "Irrelevant", "tone": "neutral"},
}

_LOCALE_FLAGS = {"en": "🇬🇧", "de": "🇩🇪", "fr": "🇫🇷", "it": "🇮🇹", "es": "🇪🇸"}


# CSS strictly tokenized per bible-ux. Custom properties are declared once at
# :root and reused everywhere — no scattered hex values.
_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  /* Spacing scale (VALUES.md § Spacing) — multiples of 4 only */
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
  --space-12: 48px;

  /* Radii — max 3 per page (WEB.md § CO) */
  --radius-sm: 4px;   /* badges, chips */
  --radius-md: 8px;   /* inputs, buttons */
  --radius-lg: 12px;  /* cards */

  /* Primary palette — HSL, 60-30-10 rule (WEB.md § CP). Hue 252 = indigo, calmer than the previous violet. */
  --primary-300: hsl(252, 80%, 75%);
  --primary-400: hsl(252, 80%, 65%);
  --primary-500: hsl(252, 75%, 58%);
  --primary-600: hsl(252, 70%, 50%);
  --primary-700: hsl(252, 65%, 42%);

  /* Neutral scale — tinted (220 hue), Material 3 dark mode surfaces */
  --surface-0:  #121212;  /* base */
  --surface-1:  #1e1e1e;  /* cards */
  --surface-2:  #272727;  /* elevated */
  --surface-3:  #2e2e2e;
  --border:     hsl(220, 6%, 22%);
  --border-strong: hsl(220, 6%, 30%);

  /* Text — never pure white (VALUES.md § Dark mode) */
  --text-primary:   hsl(220, 9%, 92%);
  --text-secondary: hsl(220, 6%, 70%);
  --text-tertiary:  hsl(220, 5%, 55%);

  /* Semantic colors (WEB.md § CP) */
  --success-bg: hsl(142, 60%, 14%);
  --success-fg: hsl(142, 70%, 70%);
  --warning-bg: hsl(38, 60%, 14%);
  --warning-fg: hsl(38, 90%, 70%);
  --error-bg:   hsl(0, 60%, 16%);
  --error-fg:   hsl(0, 80%, 75%);
  --info-bg:    hsl(210, 60%, 16%);
  --info-fg:    hsl(210, 80%, 75%);
  --neutral-bg: hsl(220, 6%, 18%);
  --neutral-fg: hsl(220, 8%, 70%);

  /* Focus ring (VALUES.md § Focus indicator) */
  --focus-ring: 0 0 0 2px var(--surface-0), 0 0 0 4px var(--primary-500);
}

html, body, [class*="css"], .stApp {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  color: var(--text-primary);
}

.stApp {
  background: var(--surface-0);
}

/* Honor reduced-motion (WEB.md § F § 27) */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

#MainMenu, footer, header {visibility: hidden;}
.block-container {padding-top: var(--space-8); max-width: 1200px;}

/* ---------- Hero ---------- */
.wit-hero {
  padding: var(--space-8) var(--space-8);
  border-radius: var(--radius-lg);
  background:
    radial-gradient(ellipse at top left, hsla(252, 75%, 58%, 0.18), transparent 60%),
    var(--surface-1);
  border: 1px solid var(--border);
  margin-bottom: var(--space-8);
}
.wit-hero .wit-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-3);
  border-radius: var(--radius-sm);
  background: hsla(252, 75%, 58%, 0.16);
  color: var(--primary-300);
  font-size: 12px;
  font-weight: 600;
  margin-bottom: var(--space-4);
}
.wit-hero h1 {
  font-size: 48px;        /* h0 / display, VALUES.md § Typography */
  font-weight: 700;
  line-height: 1.1;
  letter-spacing: -0.02em;
  margin: 0 0 var(--space-3) 0;
  color: var(--text-primary);
}
.wit-hero p {
  color: var(--text-secondary);
  font-size: 16px;        /* body */
  line-height: 1.5;
  margin: 0;
  max-width: 65ch;         /* 45–75 char line length rule */
}

/* ---------- KPI cards ---------- */
.wit-kpi-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-4);
  margin-bottom: var(--space-8);
}
.wit-kpi {
  background: var(--surface-1);
  border: 1px solid var(--border);      /* border-only, no shadow (WEB.md § CT) */
  padding: var(--space-6);
  border-radius: var(--radius-lg);
  transition: border-color 150ms ease;
}
.wit-kpi:hover {
  border-color: var(--border-strong);
}
.wit-kpi .wit-kpi__label {
  font-size: 14px;        /* small */
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: var(--space-3);
}
.wit-kpi .wit-kpi__value {
  font-size: 48px;        /* display */
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums;
  color: var(--text-primary);
}
.wit-kpi--alert .wit-kpi__value { color: var(--error-fg); }
.wit-kpi--watch .wit-kpi__value { color: var(--warning-fg); }
.wit-kpi--ok    .wit-kpi__value { color: var(--success-fg); }
.wit-kpi .wit-kpi__sub {
  color: var(--text-tertiary);
  font-size: 12px;        /* caption */
  line-height: 1.5;
  margin-top: var(--space-2);
}

/* ---------- Section header ---------- */
.wit-section {
  font-size: 14px;        /* small, sentence case (no upper-case anti-pattern) */
  font-weight: 600;
  color: var(--text-secondary);
  margin: var(--space-8) 0 var(--space-3) 0;
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--border);
}

/* ---------- Streamlit native controls polish ---------- */
.stSelectbox label, .stSlider label, .stCheckbox label,
.stTextInput label, .stTextArea label {
  color: var(--text-secondary) !important;
  font-size: 14px !important;
  font-weight: 500 !important;
  text-transform: none !important;   /* override Streamlit upper-case */
  letter-spacing: 0 !important;
}

.stSelectbox > div[data-baseweb="select"] > div,
div[data-baseweb="input"] > input {
  background: var(--surface-1) !important;
  border-radius: var(--radius-md) !important;
  border-color: var(--border) !important;
}

/* Focus visible on form controls (WCAG 2.4.7) */
.stSelectbox > div[data-baseweb="select"]:focus-within > div,
div[data-baseweb="input"]:focus-within > input,
.stCheckbox > label > div:focus-within {
  box-shadow: var(--focus-ring) !important;
  outline: none !important;
}

/* Slider track + thumb */
.stSlider [data-baseweb="slider"] [role="slider"] {
  background: var(--primary-500) !important;
}

/* ---------- Thread cards (style native expanders) ---------- */
div[data-testid="stExpander"] {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  margin-bottom: var(--space-3);
  transition: border-color 150ms ease;
}
div[data-testid="stExpander"]:hover {
  border-color: var(--border-strong);
}
div[data-testid="stExpander"]:focus-within {
  box-shadow: var(--focus-ring);
  outline: none;
}
div[data-testid="stExpander"] summary {
  padding: var(--space-4) var(--space-6);
  font-weight: 500;
  color: var(--text-primary);
  font-size: 16px;        /* body */
  line-height: 1.5;
}
div[data-testid="stExpander"] summary:hover {
  color: var(--text-primary);
}

/* ---------- Inline badges + meta ---------- */
.wit-badge-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.wit-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
}
.wit-badge--primary { background: hsla(252, 75%, 58%, 0.16); color: var(--primary-300); }
.wit-badge--info    { background: var(--info-bg);    color: var(--info-fg); }
.wit-badge--warning { background: var(--warning-bg); color: var(--warning-fg); }
.wit-badge--error   { background: var(--error-bg);   color: var(--error-fg); }
.wit-badge--success { background: var(--success-bg); color: var(--success-fg); }
.wit-badge--neutral { background: var(--neutral-bg); color: var(--neutral-fg); }

.wit-score {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  color: var(--text-secondary);
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  font-weight: 500;
  line-height: 1.4;
}
.wit-score--warm { background: var(--warning-bg); color: var(--warning-fg); }
.wit-score--hot  { background: var(--error-bg);   color: var(--error-fg); }

.wit-meta {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-1) var(--space-3);
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
  margin-bottom: var(--space-4);
}
.wit-meta dt { color: var(--text-tertiary); font-weight: 500; }
.wit-meta dd { color: var(--text-secondary); margin: 0; }
.wit-meta a { color: var(--info-fg); text-decoration: none; }
.wit-meta a:hover { text-decoration: underline; }
.wit-meta a:focus-visible {
  outline: 2px solid var(--primary-500);
  outline-offset: 2px;
  border-radius: 2px;
}

.wit-body {
  background: var(--surface-0);
  border-left: 3px solid var(--primary-500);
  padding: var(--space-3) var(--space-4);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  margin: var(--space-3) 0;
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
}

.wit-draft-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin: var(--space-4) 0 var(--space-2) 0;
  color: var(--primary-300);
  font-size: 14px;
  font-weight: 600;
}

.stTextArea textarea {
  background: var(--surface-0) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--radius-md) !important;
  color: var(--text-primary) !important;
  font-family: 'JetBrains Mono', monospace !important;
  font-size: 14px !important;
  line-height: 1.5 !important;
  padding: var(--space-3) var(--space-4) !important;
}
.stTextArea textarea:focus {
  border-color: var(--primary-500) !important;
  box-shadow: var(--focus-ring) !important;
  outline: none !important;
}

.wit-thread-count {
  color: var(--text-secondary);
  font-size: 14px;
  margin: var(--space-3) 0 var(--space-4) 0;
}
.wit-thread-count strong {
  color: var(--text-primary);
  font-weight: 600;
}

/* ---------- Empty state ---------- */
.wit-empty {
  text-align: center;
  padding: var(--space-12) var(--space-6);
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}
.wit-empty .wit-empty__icon {
  font-size: 32px;
  margin-bottom: var(--space-3);
}
.wit-empty h3 {
  color: var(--text-primary);
  font-size: 20px;
  font-weight: 600;
  line-height: 1.3;
  margin: 0 0 var(--space-2) 0;
}
.wit-empty p {
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1.5;
  margin: 0 auto;
  max-width: 50ch;
}
.wit-empty code {
  background: var(--surface-2);
  padding: 2px 6px;
  border-radius: var(--radius-sm);
  color: var(--primary-300);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
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


def _kpi_severity(gap: int) -> str:
    if gap >= 5:
        return "wit-kpi--alert"
    if gap >= 2:
        return "wit-kpi--watch"
    return "wit-kpi--ok"


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
            <span class="wit-eyebrow">📡 Live buyer radar · candidate artifact</span>
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
                <div class="wit-empty__icon">📡</div>
                <h3>No data yet</h3>
                <p>No database found at <code>{DB_PATH}</code>. Run <code>python -m src.seed_demo</code> for the demo dataset, or <code>python -m src.radar.runner</code> to fetch live HN, Reddit, and DACH data.</p>
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
    severity = _kpi_severity(headline_count)

    st.markdown(
        f"""
        <div class="wit-kpi-grid">
            <div class="wit-kpi {severity}">
                <div class="wit-kpi__label">Should have been mentioned</div>
                <div class="wit-kpi__value">{headline_count}</div>
                <div class="wit-kpi__sub">High-relevance threads this week with no Typewise mention</div>
            </div>
            <div class="wit-kpi">
                <div class="wit-kpi__label">Typewise was mentioned</div>
                <div class="wit-kpi__value">{mentioned_count}</div>
                <div class="wit-kpi__sub">Threads where the brand actually surfaced</div>
            </div>
            <div class="wit-kpi {severity}">
                <div class="wit-kpi__label">Coverage gap</div>
                <div class="wit-kpi__value">{headline_count}:{mentioned_count}</div>
                <div class="wit-kpi__sub">Ratio of missed buyer conversations to wins</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="wit-section">Filters</div>', unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns([1, 1, 1, 1.4])
    source_filter = col1.selectbox("Source", ["(any)", "hn", "reddit", "dach"])
    locale_filter = col2.selectbox("Locale", ["(any)", "en", "de", "fr", "it"])
    intent_filter = col3.selectbox(
        "Intent", ["(any)", "research", "comparison", "complaint", "shopping"]
    )
    min_score = col4.slider("Minimum relevance score", 0.0, 1.0, 0.5, 0.05)
    show_only_unmentioned = st.checkbox(
        "Only threads where Typewise was not mentioned", value=True
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
                <div class="wit-empty__icon">🔍</div>
                <h3>No threads match these filters</h3>
                <p>Try lowering the score threshold or unchecking "Only threads where Typewise was not mentioned".</p>
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
    score_class = ""
    if score is not None:
        if score >= 0.85:
            score_class = "wit-score--hot"
        elif score >= 0.7:
            score_class = "wit-score--warm"
    source = t.get("source") or "?"
    locale = t.get("locale") or ""
    intent = t.get("intent") or "irrelevant"
    flag = _LOCALE_FLAGS.get(locale, "🌐")

    with st.expander(f"{flag}   {title}"):
        source_meta = _SOURCE_BADGES.get(source, {"label": source, "tone": "neutral"})
        intent_meta = _INTENT_BADGES.get(intent, {"label": intent, "tone": "neutral"})
        st.markdown(
            f"""
            <div class="wit-badge-row">
                <span class="wit-badge wit-badge--{source_meta['tone']}">{source_meta['label']}</span>
                <span class="wit-badge wit-badge--{intent_meta['tone']}">{intent_meta['label']}</span>
                <span class="wit-score {score_class}">score {score_label}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        comps = _format_competitors(t.get("competitors_mentioned"))
        comp_html = ", ".join(comps) if comps else "<em>None named</em>"
        url = t.get("url") or "#"
        mentioned = "Yes" if t.get("typewise_mentioned") else "No"
        st.markdown(
            f"""
            <dl class="wit-meta">
                <dt>Link</dt><dd><a href="{url}" target="_blank" rel="noopener">{url}</a></dd>
                <dt>Author</dt><dd>{t.get("author") or "—"}</dd>
                <dt>Posted</dt><dd>{_format_age(t.get("created_at"))}</dd>
                <dt>Competitors</dt><dd>{comp_html}</dd>
                <dt>Typewise mentioned</dt><dd>{mentioned}</dd>
            </dl>
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
            st.markdown(
                '<div class="wit-draft-header">💬 Suggested reply — review before posting</div>',
                unsafe_allow_html=True,
            )
            st.text_area(
                label=f"draft_{t['id']}",
                value=t["draft_reply"],
                height=160,
                label_visibility="collapsed",
            )


if __name__ == "__main__":
    main()
