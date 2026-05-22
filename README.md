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
pip install -r requirements.txt
cp .env.example .env  # fill in REDDIT_CLIENT_ID, REDDIT_SECRET, ANTHROPIC_API_KEY
python -m src.scraper_reddit
python -m src.scraper_hn
python -m src.scorer
streamlit run src/app.py
```

## Status

Work in progress. Built solo in ~4 hours. See [TODO](#roadmap).

## Roadmap

- [ ] Reddit scraper (PRAW, 4 subs)
- [ ] Hacker News scraper (Algolia API)
- [ ] Claude-based scorer + reply drafter
- [ ] Streamlit dashboard
- [ ] Public deploy (Fly.io)
- [ ] Video walkthrough

## Stack

Python · PRAW · Anthropic SDK (Claude Sonnet 4.6) · SQLite · Streamlit · Fly.io

## Ethics

Drafted replies are **suggestions for a human reviewer**, never auto-posted. Reddit and HN community norms explicitly prohibit drive-by promotion; this tool exists to surface conversations, not to spam them.

## License

MIT
