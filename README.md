# where-is-typewise

[![Live demo](https://img.shields.io/badge/demo-live-22c55e?style=flat-square)](https://where-is-typewise-knsgq4frwunfgefuxp4w3a.streamlit.app)
[![Tests](https://img.shields.io/badge/tests-125%20passing-22c55e?style=flat-square)](https://github.com/sky1241/where-is-typewise/actions/workflows/tests.yml)
[![Python](https://img.shields.io/badge/python-3.12-3776ab?style=flat-square)](runtime.txt)
[![License](https://img.shields.io/badge/license-MIT-6c5cf0?style=flat-square)](LICENSE)

A live radar that scans Reddit, Hacker News, and DACH RSS feeds for conversations where customer-service leaders are evaluating AI tools — and surfaces every thread where Typewise should have appeared in the discussion but didn't.

Built as a candidate artifact for the [Typewise AI Growth Engineer](https://www.ycombinator.com/companies/typewise/jobs/HmCzfBK-ai-growth-engineer) role. Not a deck. A working system.

## 🔗 Live demo

**[where-is-typewise.streamlit.app](https://where-is-typewise-knsgq4frwunfgefuxp4w3a.streamlit.app)** — the dashboard running on real seed data, with one click required to evaluate.

![Dashboard screenshot — five high-relevance threads this week with no Typewise mention; the top one is a German DACH retail post at score 0.94, with a Claude-drafted reply ready for human review](docs/dashboard.png)

## What it does

1. **Scrapes** Reddit (`r/CustomerSuccess`, `r/SaaS`, `r/CustomerService`, `r/ExperiencedDevs`), Hacker News (Algolia API), and DACH RSS feeds (t3n.de, deutsche-startups.de, siliconcanals.com) for posts matching a keyword list ("AI customer service", "Fin alternative", "Zendesk AI alternative", …).
2. **Scores** each thread with Claude Haiku 4.5 (tool-use, prompt-cached system prompt): buyer intent, competitors mentioned, whether Typewise was mentioned, relevance score 0–1.
3. **Drafts** a contextual human-style reply that Typewise's team could post — never auto-posted, always a suggestion for human review.
4. **Surfaces** everything on a public Streamlit dashboard with the count that matters: *threads this week where Typewise should have been in the conversation*.
5. **Exposes** Typewise itself as an [MCP server](https://modelcontextprotocol.io) so any dev can evaluate the product from inside Claude Desktop or Cursor — four tools (`compare`, `pricing`, `case_study`, `integration_check`).

## Why this exists

Today, when a CS leader types "best AI customer service platform" into Google, they find Intercom Fin (2,900+ G2 reviews) and Zendesk. They don't find Typewise (29 G2 reviews, 0 Reddit mentions indexed, last HN post in 2020 on the old keyboard product).

The Typewise job posting puts it plainly: *"make CS buyers find Typewise through any creative, non-paid, AI-powered means that work."*

This repo is one such means.

## Quickstart

```bash
git clone https://github.com/sky1241/where-is-typewise
cd where-is-typewise
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in REDDIT_CLIENT_ID, REDDIT_SECRET, ANTHROPIC_API_KEY
```

### Run the MCP server (plat principal)

```bash
python -m src.mcp_server.server
```

This boots a local MCP server exposing four tools:

- `typewise_compare(competitor)` — structured comparison vs Fin, Decagon, Sierra, Zendesk AI, with the recommended one-sentence positioning for that specific matchup
- `typewise_pricing_calculator(monthly_tickets, resolution_rate=0.70, human_cost_per_ticket_usd=6.0)` — cost + year-one ROI at the public $1/resolution price
- `typewise_find_case_study(industry, company_size, region)` — the closest-matching Typewise customer story plus up to two alternates and the reasoning
- `typewise_integration_check(platform)` — does Typewise integrate with X? Returns an honest confidence tier (confirmed / native_channel / high_likelihood / unlikely / unknown), never a fake yes

Verified via the MCP runtime, not just Python imports (see `tests/test_mcp_integration.py`):

```text
Tool count: 4
  - typewise_compare(['competitor'])
  - typewise_pricing_calculator(['monthly_tickets', 'resolution_rate', 'human_cost_per_ticket_usd'])
  - typewise_find_case_study(['industry', 'company_size', 'region'])
  - typewise_integration_check(['platform'])
```

### Wire into Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "typewise": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "/absolute/path/to/where-is-typewise"
    }
  }
}
```

Restart Claude Desktop. Then ask:

> *"I'm evaluating Typewise for a 30k-ticket-per-month DACH e-commerce retailer running Zendesk. Compare them with Fin, estimate ROI, find me the closest case study, and confirm Zendesk integration."*

Claude will fire `typewise_compare`, `typewise_pricing_calculator`, `typewise_find_case_study`, and `typewise_integration_check` in a single turn and synthesize a buyer-ready brief.

## Tests

```bash
python -m pytest tests/ -v
forge          # regression check vs baseline (forge-shield, optional)
```

Current state: **125 tests, all green** (MCP unit + protocol-level integration + radar + dashboard). Latest forge run:

```text
FORGE REPORT — PASS
Tests: 125 | Passed: 125 | Failed: 0 | Duration: 8.4s
```

One silent bug found during the build (BUG-001, Streamlit launcher) — caught via visual screenshot audit, fixed, documented in [BUGS.md](BUGS.md), 4 regression tests added.

### Run the live dashboard (Streamlit)

```bash
python -m src.seed_demo                # load 8 hand-crafted demo threads
streamlit run streamlit_app.py         # launch the dashboard at http://localhost:8501
```

> ⚠️ Always run via `streamlit_app.py` at the repo root, never `streamlit run src/app.py` directly — see [BUGS.md](BUGS.md) BUG-001 for why.

![Dashboard screenshot — 5 threads where Typewise should have been mentioned, top thread in German (DACH moat visible), Claude-drafted replies ready for human review](docs/dashboard.png)

The dashboard shows, in real time:

- **Headline metric** — threads this week where Typewise should have been mentioned but wasn't
- **Coverage gap** — vs threads where Typewise *was* mentioned
- **Filters** — source (Reddit / HN / DACH), locale (en / de / fr / it), buyer intent (research / comparison / complaint / shopping), minimum relevance score
- **Per-thread expander** — URL, author, age, competitors mentioned, body, and the Claude-drafted reply ready for a human reviewer to send

## What I'd build in month 1 if Typewise hired me

A condensed view:

| Week | Channel / system | Deliverable |
|---|---|---|
| 1 | Reddit + HN radar, scaled | Daily auto-run via GitHub Actions, Slack/Discord alerts at relevance ≥ 0.8 |
| 1 | Founder LinkedIn cadence (David + Janis) | 3 posts/week on the "augment, don't replace" thesis Sierra/Decagon can't credibly play |
| 2 | Show HN of the new agent platform | First Typewise Show HN since 2020 (the old keyboard product). Anchor: multi-agent orchestration + EU data residency. |
| 2 | DACH community infiltration | t3n editorial pitch, OMR Slack, Support Driven listener. No spam — conversation. |
| 3 | "X vs Typewise" comparison subdomain | Programmatic SEO à la `fin.ai/learn` — `typewise-vs-fin`, `vs-decagon`, `vs-sierra` |
| 3 | Founder podcast booking | No Priors, The CX Cast, Be Customer Led, Punk CX — augment-don't-replace pitch |
| 4 | G2 review collection campaign | Target Leader Mid-Market badge by month 3 |
| 4 | First measurable signal | G2 pageview lift, branded search lift, qualified inbound from at least one channel |

No attachment to channels — only to signal. I iterate to whatever lights up first.

## Why this composition, not a generic Claude-prompted answer

Twenty other candidates will prompt Claude for "what should I build for Typewise" and ship variants of a Reddit scraper. That's the LLM's default. Three things make this artifact harder to copy:

1. **MCP server.** You pushed [`mcp-chaos-rig`](https://github.com/Typewise) to your GitHub two days before this job opened. An LLM that hasn't seen that won't propose an MCP integration.
2. **DACH geographic moat.** I'm Swiss / CET / multilingual. A candidate outside the region can't credibly run the t3n.de or OMR Slack channel work.
3. **The bug audit.** I shipped fast, then ran a "no silent bugs" pass that caught a runtime crash pytest missed. That's documented in [BUGS.md](BUGS.md). It's the work most people skip.

## Status

Built solo across two Claude Code instances in ~4 hours. **Shippable state**, deploy-ready.

## Roadmap

- [x] Hacker News scraper (Algolia API, no auth)
- [x] Reddit scraper (PRAW, read-only, env-based creds)
- [x] DACH RSS scrapers (t3n.de, deutsche-startups.de, siliconcanals.com)
- [x] Locale tagging (langdetect, deterministic seed)
- [x] Claude scorer (Haiku 4.5, tool_use, prompt-cached system prompt)
- [x] SQLite store with idempotent upserts
- [x] Streamlit dashboard with filters + draft replies
- [x] MCP server with 4 tools wired into Claude Desktop
- [x] 125 pytest tests, forge regression baseline, GitHub Actions CI
- [x] BUG-001 (silent Streamlit crash) found visually, fixed, regression-tested
- [ ] Deploy to Streamlit Community Cloud — see [docs/DEPLOY.md](docs/DEPLOY.md)
- [ ] Record the 90-second demo walkthrough

## Stack

Python 3.11+ · MCP SDK · Anthropic SDK (Claude Haiku 4.5) · PRAW · feedparser · httpx · BeautifulSoup · langdetect · SQLite · Streamlit · pytest · forge-shield · GitHub Actions · Streamlit Community Cloud (deploy target)

## Ethics

Drafted replies are **suggestions for a human reviewer**, never auto-posted. Reddit and HN community norms explicitly prohibit drive-by promotion; this tool exists to surface conversations, not to spam them.

## License

MIT
