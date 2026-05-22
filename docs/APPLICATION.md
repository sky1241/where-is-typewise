# Application — Typewise AI Growth Engineer

> Draft of the candidacy email. Replace with your own voice before sending. Tone: short, direct, no fluff.

---

**Subject:** Not a CV — three links and a 30-day plan

Hi David, Janis,

You asked for "something built." Here are three URLs:

- **Live dashboard** — `[INSERT_STREAMLIT_URL]` — Reddit + Hacker News + DACH RSS radar. Counts the threads this week where Typewise should have been in the discussion. Zero this week so far. The radar shows you the gap.
- **Repo** — https://github.com/sky1241/where-is-typewise — four Typewise tools exposed as an MCP server, plus the radar. 125 tests green. One silent bug found, fixed, documented (BUGS.md, BUG-001).
- **Loom (90 s)** — `[INSERT_LOOM_URL]` — me triggering all four MCP tools from Claude Desktop with one buyer prompt, then the radar showing 5 unmentioned DACH/HN threads ready for reply drafts.

### Why this composition won't repeat what 20 other candidates send you

1. **MCP server.** You pushed [`mcp-chaos-rig`](https://github.com/Typewise) to your GitHub two days before this job posting opened. I built `typewise-mcp` to plug Typewise into any dev's Claude Desktop in 30 seconds — `typewise_compare`, `typewise_pricing_calculator`, `typewise_find_case_study`, `typewise_integration_check`. No other candidate prompting an LLM will spot this signal in time.

2. **Radar.** Solves the verbatim brief: *"make CS buyers find Typewise through any creative, non-paid, AI-powered means."* Reddit + HN + Claude scorer + draft reply per thread, never auto-posted.

3. **DACH moat.** I'm Swiss, CET, multilingual. The radar already pulls t3n.de, deutsche-startups.de, siliconcanals.com — 45 threads/cycle in markets where your US competitors (Sierra, Decagon) don't penetrate. Galaxus, TUI, IVECO, Brack.ch are already on this side of the Atlantic. The next 50 enterprise wins are too.

### What I'd build in month 1

| Week | Channel | Deliverable |
|---|---|---|
| 1 | Reddit + HN radar, scaled | Daily auto-run via GitHub Actions, alerts to a Slack/Discord channel when a thread crosses 0.8 relevance |
| 1 | LinkedIn cadence (David + Janis) | Three-post template per week, hijacking the "augmentation, not replacement" thesis that Sierra/Decagon can't credibly play |
| 2 | Show HN of the new agent platform | First Typewise Show HN since 2020 (the old keyboard B2C product). Anchored on the multi-agent orchestration architecture + EU data residency. |
| 2 | DACH community infiltration | t3n editorial pitch, OMR Slack participation, Support Driven Slack listener. No spam — actual conversation. |
| 3 | "X vs Typewise" comparison pages | `typewise.app/compare/typewise-vs-fin`, `vs-decagon`, `vs-sierra`. Programmatic SEO subdomain à la `fin.ai/learn`. |
| 3 | Founder podcast booking | Pitch deck for No Priors, The CX Cast, Be Customer Led, Punk CX. The "augment, don't replace" angle. |
| 4 | G2 review collection | Customer-success-incentivized review campaign, target Leader Mid-Market badge by month 3. |
| 4 | First measurable signal | Demand-side: G2 pageview lift, branded search lift, qualified inbound from at least one targeted channel. |

I'll iterate from whichever of those lights up first. No attachment to channels — only to signal.

### A few specifics I noticed during my audit

- Your YC profile says 12 employees; the job posting says 20. Soft mismatch — flag for the hiring page.
- Your homepage no longer mentions ETH Zurich — that was a 2022-2023 narrative anchor. Worth deciding whether to revive it for European enterprise.
- "60+ enterprise customers" in the job posting vs "more than 50" in the Feb 2026 PR. Pick one number and hold it.
- No Decagon / Sierra / Lorikeet comparison content on your blog yet. Your competitor mapping is one generation behind the SERP.

Honest disclosure: I'm earlier in my coding journey than my output suggests — first sustained-coding year. I'm AI-native, I ship fast, I think in systems, and I won't pretend to be a marketer with a five-year B2B SaaS résumé. What I can prove is in those three URLs.

Available CET. Let's talk.

— Sky
[email]
[github.com/sky1241](https://github.com/sky1241)

---

## Pre-send checklist

- [ ] Replace `[INSERT_STREAMLIT_URL]` with the deployed dashboard URL
- [ ] Replace `[INSERT_LOOM_URL]` with the Loom recording URL
- [ ] Replace `[email]` and confirm `github.com/sky1241` is the right handle
- [ ] Re-read out loud — anything sounding LLM-generated, rewrite in your voice
- [ ] Send to: David (CEO) — find on LinkedIn, look for an email pattern (`david@typewise.app` likely)
- [ ] CC Janis (CTO) if you can find a direct email
