# where-is-typewise

A live radar that scans Reddit and Hacker News for conversations where customer service leaders are evaluating AI tools — and shows every thread where Typewise should have appeared in the discussion but didn't.

Built as a candidate artifact for the [Typewise AI Growth Engineer](https://www.ycombinator.com/companies/typewise/jobs/HmCzfBK-ai-growth-engineer) role. Not a deck. A working system.

## What it does

1. **Scrapes** Reddit (r/CustomerSuccess, r/SaaS, r/CustomerService, r/ExperiencedDevs) and Hacker News (Algolia API) for posts matching a keyword list ("AI customer service", "Fin alternative", "Zendesk AI alternative", …).
2. **Scores** each thread with Claude (Sonnet 4.6): buyer intent, competitors mentioned, whether Typewise was mentioned.
3. **Drafts** a contextual human-style reply that Typewise's team could post — never auto-posted, always a suggestion for review.
4. **Surfaces** everything on a public Streamlit dashboard with the count that matters: *threads this week where Typewise should have been in the conversation*.

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

Current state: **41 tests, all green** (34 unit tests + 7 MCP protocol-level integration tests). Latest forge run:

```text
FORGE REPORT — PASS
Tests: 41 | Passed: 41 | Failed: 0 | Duration: 3.6s
```

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

## Status

Work in progress. Built solo in ~4 hours. See [TODO](#roadmap).

## Roadmap

- [ ] Reddit scraper (PRAW, 4 subs)
- [ ] Hacker News scraper (Algolia API)
- [ ] Claude-based scorer + reply drafter
- [ ] Streamlit dashboard
- [ ] Public deploy (Fly.io)
- [ ] Loom walkthrough

## Stack

Python · PRAW · Anthropic SDK (Claude Sonnet 4.6) · SQLite · Streamlit · Fly.io

## Ethics

Drafted replies are **suggestions for a human reviewer**, never auto-posted. Reddit and HN community norms explicitly prohibit drive-by promotion; this tool exists to surface conversations, not to spam them.

## License

MIT
