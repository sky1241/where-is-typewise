# Battle Plan — where-is-typewise

**Goal:** ship a candidate artifact for [Typewise AI Growth Engineer](https://www.ycombinator.com/companies/typewise/jobs/HmCzfBK-ai-growth-engineer) in ~4 hours that no other candidate can copy by prompting Claude/GPT.

**Why this composition wins:**

1. **MCP server** — Typewise pushed `mcp-chaos-rig` to their GitHub on May 20, 2026, two days before this job post went live. They are investing hard in the Model Context Protocol. No generic LLM-suggested artifact will spot this signal. *This is the plat principal.*
2. **Reddit + HN radar** — solves the literal job description verbatim ("make CS buyers find Typewise through any creative, non-paid, AI-powered means"). *Bonus dish.*
3. **DACH angle** — Typewise's customer base is DACH/EU (Galaxus, TUI, IVECO, Beurer, Brack.ch, Wincasa, Planzer). US competitors (Sierra, Decagon, Fin) don't penetrate these markets. A scanner that surfaces DACH-region buyer conversations on forums where US growth tools never look is a candidate-specific moat that other applicants (likely US/India) cannot replicate. *Geographic side dish.*

---

## Time budget (strict, 4h total)

| Phase | Duration | Output |
|---|---|---|
| 0. Battle plan + repo (this file) | 15 min | committed |
| 1. MCP server (`typewise-mcp`) | 90 min | working server + Claude Desktop config |
| 2. Reddit + HN radar | 60 min | scrapers + scorer + SQLite |
| 3. DACH forum extension | 30 min | extra source + locale tagging |
| 4. Streamlit dashboard | 30 min | public URL |
| 5. Deploy + README polish + Loom | 30 min | shareable |

If anything blows the budget, the rule is: **ship the MCP, drop everything else**. The MCP is the differentiator.

---

## Phase 1 — MCP server (`typewise-mcp`)

**What it is:** a local MCP server that exposes Typewise as a set of tools any dev can use from Claude Desktop or Claude Code to evaluate the product without leaving their IDE.

**Why it wins:** Typewise's own engineers ship MCP code. Speaking MCP to them is speaking their dialect. No LLM suggests this spontaneously.

### Tools the server exposes

| Tool name | What it does | Data source |
|---|---|---|
| `typewise_compare(competitor: str)` | Returns a structured comparison vs Fin/Decagon/Sierra/Zendesk | Scraped from public Typewise blog + competitor sites |
| `typewise_pricing_calculator(monthly_tickets: int)` | Returns estimated cost at $1/resolution + ROI vs human agent | Public pricing page |
| `typewise_find_case_study(industry: str, company_size: str)` | Returns the most relevant Typewise customer story | typewise.app/customer-stories scrape |
| `typewise_integration_check(platform: str)` | Tells you if Typewise integrates with Zendesk / Salesforce / Freshdesk / HubSpot etc., with docs link | Public integrations page |
| `typewise_search_blog(query: str)` | Semantic search over Typewise blog content | Local embeddings of blog posts |

### Stack

- Python 3.11+
- `mcp` SDK (official Anthropic Python MCP SDK)
- `httpx` for fetching public Typewise pages
- `beautifulsoup4` for HTML parsing
- Local JSON cache (no DB needed for MCP layer)

### Files to create

```
src/mcp_server/
├── __init__.py
├── server.py              # MCP server entry point, registers all tools
├── tools/
│   ├── __init__.py
│   ├── compare.py         # typewise_compare
│   ├── pricing.py         # typewise_pricing_calculator
│   ├── case_study.py      # typewise_find_case_study
│   ├── integrations.py    # typewise_integration_check
│   └── blog_search.py     # typewise_search_blog
├── data/
│   ├── competitors.json   # static comparison matrix (curated from audit)
│   ├── case_studies.json  # scraped once at build time
│   └── integrations.json
└── cache/                 # runtime cache, gitignored
```

### Acceptance test (Phase 1 done means…)

1. `python -m src.mcp_server.server` starts without errors
2. Claude Desktop config snippet works (in README): `claude_desktop_config.json` example pasted
3. From Claude Desktop, asking *"Compare Typewise with Fin for a 50k-ticket-per-month e-commerce company"* triggers `typewise_compare` and `typewise_pricing_calculator` and returns coherent output
4. 90-second Loom shows the above interaction live

### Risks

- **MCP SDK version drift.** The MCP spec moves fast. Pin exact version in `requirements.txt`.
- **Typewise has no public API.** Everything must be scraped from their public site. If we hit anti-bot, fall back to pre-curated static JSON committed in `data/`.
- **Time overrun on tool count.** If running long, ship 3 tools instead of 5. `compare` + `pricing` + `case_study` is the MVP.

---

## Phase 2 — Reddit + HN radar

**What it is:** a Python pipeline that scrapes Reddit and Hacker News for posts matching CS-AI keywords, scores them via Claude, and surfaces threads where Typewise should have appeared but didn't.

**Why it stays in the bundle:** matches the verbatim job description, easy to demo, generates ongoing value past hiring day.

### Files to create

```
src/radar/
├── __init__.py
├── reddit.py              # PRAW scraper, 4 subreddits, 50 posts each
├── hackernews.py          # HN Algolia API, no auth
├── scorer.py              # Claude scoring: intent, competitors_mentioned, typewise_mentioned, draft_reply
├── store.py               # SQLite persistence
└── runner.py              # python -m src.radar.runner runs full pipeline
```

### Schema (SQLite, `data/radar.db`)

```sql
CREATE TABLE threads (
    id TEXT PRIMARY KEY,            -- "reddit:abc123" or "hn:38291837"
    source TEXT NOT NULL,           -- 'reddit' | 'hn' | 'dach'
    locale TEXT,                    -- 'en' | 'de' | 'fr' | 'it'
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT,
    author TEXT,
    created_at TIMESTAMP,
    fetched_at TIMESTAMP,
    intent TEXT,                    -- 'research' | 'comparison' | 'complaint' | 'shopping' | 'irrelevant'
    competitors_mentioned TEXT,     -- JSON array
    typewise_mentioned BOOLEAN,
    relevance_score REAL,           -- 0..1
    draft_reply TEXT
);
```

### Acceptance test (Phase 2 done means…)

1. `python -m src.radar.runner` fetches at least 100 threads, scores them, persists to SQLite
2. SQL query `SELECT COUNT(*) FROM threads WHERE typewise_mentioned=0 AND relevance_score > 0.7` returns ≥ 5 rows for the last 7 days
3. At least one draft_reply is human-quality (no obvious LLM tells, contextual, suggests Typewise without being spammy)

### Risks

- **Reddit OAuth setup.** Requires creating a Reddit app (5 min, one-time). Document in README.
- **Claude API cost.** With 100 threads × scoring + drafting = ~$0.50. Negligible but flag in README.
- **Reddit rate limits.** PRAW handles this but adds latency. Use `posts_per_sub: 50` to stay safe.

---

## Phase 3 — DACH forum extension

**What it is:** extend the radar to scan DACH (Germany, Austria, Switzerland) and Francophone communities where US CS-AI competitors don't show up.

**Why it's the personal moat:** I'm Swiss-based, French/some German, in CET. A candidate in San Francisco or Bangalore cannot credibly attack these channels.

### Sources

| Source | Method | Notes |
|---|---|---|
| `t3n.de` (DE startup/tech news) | RSS + keyword filter | public RSS |
| `deutsche-startups.de` | RSS | public |
| `OMR Slack` (DE marketing community) | Manual seed list of relevant channels — no scraping (ToS) | document in README as "human channel to attack, not automate" |
| XING groups (DE LinkedIn) | Manual — flag in README as a recommended outreach target | no API |
| HackerNews FR / French tech forums (Hacker News, Indie Hackers FR) | Same as HN, locale-tagged | reuse HN scraper |
| `siliconcanals.com` (EU startup news) | RSS | covers EU CS-AI landscape |

### Code addition

```
src/radar/
├── dach.py                # RSS scrapers for t3n, deutsche-startups, siliconcanals
└── locale_tagger.py       # langdetect to tag locale on existing threads
```

### Acceptance test (Phase 3 done means…)

1. At least 20 DACH-locale threads in DB
2. At least 1 DACH thread flagged where Typewise should have been mentioned (likely high — these are exactly Typewise's home market)

### Risks

- **RSS feeds sparse on CS-AI topics.** If signal is low, scope shrinks to a curated list of *"DACH channels to attack manually, not via scraper"* in README — still valuable strategic insight.

---

## Phase 4 — Streamlit dashboard

**What it is:** a single-page dashboard showing the radar output. Public URL.

### Layout

```
┌─────────────────────────────────────────────────────────┐
│ where-is-typewise — Live buyer-conversation radar       │
│                                                          │
│ Threads this week where Typewise should have been: 12   │
│ Threads this week where Typewise WAS mentioned: 0       │
│                                                          │
│ [Filter: source ▼] [locale ▼] [intent ▼] [min score ▼] │
│                                                          │
│ ┌─ Thread #1 ──────────────────────────────────────┐    │
│ │ r/CustomerSuccess · 2 days ago · intent: research│    │
│ │ "Best AI for support automation in EU?"          │    │
│ │ Mentions: Fin, Zendesk AI                        │    │
│ │ Suggested reply ▼                                │    │
│ │   [draft text from Claude]                       │    │
│ └──────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### Files

```
src/app.py                 # Streamlit single-file app
```

### Acceptance test

- `streamlit run src/app.py` opens a working page
- Filters work
- Drafts are copy-pasteable

---

## Phase 5 — Deploy + README + Loom

### Deploy targets (in order of preference)

1. **Streamlit Community Cloud** — free, public, plugs to GitHub repo, auto-rebuilds. Best.
2. **Fly.io** — free tier, more flexible, requires Dockerfile.
3. **Railway** — paid but simple.

Streamlit Community Cloud requires no Dockerfile and no secrets in the repo (uses `.streamlit/secrets.toml` server-side). Go with that.

### README polish

- Hero section: 1-paragraph what + why + who it's for
- 3 demo gifs/screenshots: MCP in Claude Desktop, radar dashboard, DACH thread example
- Quickstart in <5 commands
- "What I'd build in month 1 if you hire me" section — DACH community infiltration plan, Show HN of new product, founder LinkedIn cadence à la Jesse Zhang
- Honest "limitations" section — no hidden lies, no overclaim

### Loom script (90 seconds max)

1. (0:00–0:10) "Hi, this is my candidate artifact for Typewise. Three liens, three things."
2. (0:10–0:35) **MCP demo** — open Claude Desktop, type "compare Typewise with Fin for a 30k-ticket EU retail company", watch tools fire, return comparison + pricing. Zoom on the tool call.
3. (0:35–0:55) **Radar demo** — open the public dashboard, filter to "this week, no typewise mention, score > 0.7", show a real Reddit thread + the draft reply.
4. (0:55–1:15) **DACH angle** — show a t3n.de or siliconcanals thread the radar caught, point out US competitors don't track this.
5. (1:15–1:30) "I'd start month 1 with X, Y, Z. The radar runs daily, the MCP server installs in 30 seconds. Email in description."

---

## Debug strategy

- **Per-phase isolation**: each phase is its own subpackage with its own `python -m` entry point. Phases don't share state at runtime except via the SQLite DB.
- **Smoke tests**: each phase has a 1-command smoke test in `tests/test_smoke_phase_N.py`. Runs in CI.
- **Forge** *(my own debug toolchain — debug-client multi-SAST orchestrator, used for QA passes on the code)* will run before final push: Bandit (security), Ruff (lint), pyright (types) at minimum.
- **No silent failures**: every scraper logs to stdout and `data/radar.log`. If Reddit OAuth fails, the log says so loudly.

---

## What ships if time runs out

Priority order — if I only have N hours, ship the first N items:

1. MCP server with 3 tools (`compare`, `pricing`, `case_study`) — 60 min minimum
2. README that pitches the candidacy honestly
3. Reddit scraper + Claude scorer + SQLite — 45 min
4. Streamlit dashboard — 30 min
5. HN scraper — 15 min
6. DACH RSS extension — 30 min
7. Streamlit Cloud deploy — 15 min
8. Loom — 20 min

Sum of the must-ships (1–4): 2h15. That gives 1h45 of buffer for the rest. Realistic.

---

## What this proves to Typewise

| What they ask for | What this artifact shows |
|---|---|
| "AI-native to the core" | MCP server speaks their newest protocol obsession |
| "Builder mindset, ship systems autonomously" | One repo, one person, 4 hours, deployed, demoable |
| "Growth obsession" | Radar literally surfaces buyer conversations, draft replies ready |
| "Speed and bias to action" | 4 hours, no deck, working code |
| "Treat this like your own startup" | DACH angle exploits a real moat they're not using |
| "Don't send a CV. Send something you built." | three URLs, zero PDF |

---

*Last updated: 2026-05-22. This plan is a commitment, not a wishlist — if a chunk slips, the next commit message says so.*
