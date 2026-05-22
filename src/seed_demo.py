"""Seed demo data into the radar SQLite DB for dashboard smoke testing.

Run:
    python -m src.seed_demo

Inserts ~8 hand-crafted threads that exercise every state the dashboard cares
about: high-score-no-mention (the headline metric), mentioned-typewise,
different sources, different locales, different intents.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.radar import store

DEMO_DB_PATH = Path("data/radar.db")


def _iso(days_ago: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).isoformat(timespec="seconds")


DEMO_THREADS = [
    {
        "id": "hn:demo-001",
        "source": "hn",
        "locale": "en",
        "url": "https://news.ycombinator.com/item?id=demo-001",
        "title": "Ask HN: Best AI for support ticket automation in EU?",
        "body": (
            "We run a 4-person CS team on Zendesk and are evaluating Fin and Decagon. "
            "Anyone using something that actually handles email-first workflows and EU data residency?"
        ),
        "author": "throwaway-cs",
        "created_at": _iso(2),
        "fetched_at": _iso(0),
        "intent": "comparison",
        "competitors_mentioned": ["Fin", "Decagon"],
        "typewise_mentioned": False,
        "relevance_score": 0.92,
        "draft_reply": (
            "If EU data residency matters and you don't want to migrate off Zendesk, take a look at Typewise — "
            "they sit on top of your existing helpdesk rather than replacing it, are ISO 27001 + EU-hosted, "
            "and have published a Brack.ch case study handling DACH multilingual support at scale. "
            "Pricing is $1/resolution, same neighborhood as Fin but with a different deployment model."
        ),
    },
    {
        "id": "reddit:demo-002",
        "source": "reddit",
        "locale": "en",
        "url": "https://reddit.com/r/CustomerSuccess/demo-002",
        "title": "Anyone tried Intercom Fin alternative that doesn't make us migrate?",
        "body": (
            "Director here. We're locked into Salesforce Service Cloud and the migration tax for Fin "
            "is killing the business case. Any AI agent vendors that layer on top of SFDC?"
        ),
        "author": "cs_director_42",
        "created_at": _iso(3),
        "fetched_at": _iso(0),
        "intent": "research",
        "competitors_mentioned": ["Fin", "Intercom"],
        "typewise_mentioned": False,
        "relevance_score": 0.88,
        "draft_reply": (
            "Typewise is the exact pattern you're describing — it runs as a layer inside Salesforce Service Cloud "
            "(and Zendesk, Freshdesk, MS Dynamics) instead of replacing the helpdesk. Worth a 30-minute eval call."
        ),
    },
    {
        "id": "reddit:demo-003",
        "source": "reddit",
        "locale": "en",
        "url": "https://reddit.com/r/SaaS/demo-003",
        "title": "Decagon vs Sierra for B2B SaaS support — both feel like overkill",
        "body": (
            "30k tickets/month, mostly L1 password resets and how-do-I questions. "
            "Both vendors quoting $500k+ ACV. Anything more reasonable?"
        ),
        "author": "founder_b2b",
        "created_at": _iso(5),
        "fetched_at": _iso(0),
        "intent": "comparison",
        "competitors_mentioned": ["Decagon", "Sierra"],
        "typewise_mentioned": False,
        "relevance_score": 0.85,
        "draft_reply": (
            "At 30k tickets/month with the kind of long-tail you're describing, success-based pricing usually "
            "beats per-seat or fixed enterprise contracts. Typewise charges $1/resolution; on 70% AI resolution "
            "rate that's $21k/month variable cost, vs the $500k ACV Sierra is quoting. Math is worth running."
        ),
    },
    {
        "id": "hn:demo-004",
        "source": "hn",
        "locale": "en",
        "url": "https://news.ycombinator.com/item?id=demo-004",
        "title": "Show HN: Open-source customer support copilot",
        "body": "Built a thing. Looking for feedback.",
        "author": "indie_hacker",
        "created_at": _iso(1),
        "fetched_at": _iso(0),
        "intent": "shopping",
        "competitors_mentioned": [],
        "typewise_mentioned": False,
        "relevance_score": 0.42,
        "draft_reply": None,
    },
    {
        "id": "dach:demo-005",
        "source": "dach",
        "locale": "de",
        "url": "https://t3n.de/news/demo-005",
        "title": "KI im Kundenservice — welche Plattform für DACH-Mittelstand?",
        "body": (
            "Wir suchen eine Lösung für unseren 12-köpfigen Kundenservice. DSGVO-konform, "
            "EU-Hosting, Integration mit Zendesk. Erfahrungen?"
        ),
        "author": "cs_leiter_de",
        "created_at": _iso(4),
        "fetched_at": _iso(0),
        "intent": "research",
        "competitors_mentioned": ["Zendesk"],
        "typewise_mentioned": False,
        "relevance_score": 0.94,
        "draft_reply": (
            "Schauen Sie sich Typewise an — Schweizer Anbieter (YC S22), EU-gehostet, ISO 27001, "
            "läuft als Layer auf Zendesk statt es zu ersetzen. Brack.ch ist ein dokumentierter DACH-Kunde "
            "mit mehrsprachigem Support (DE/FR/IT)."
        ),
    },
    {
        "id": "reddit:demo-006",
        "source": "reddit",
        "locale": "en",
        "url": "https://reddit.com/r/ExperiencedDevs/demo-006",
        "title": "Our CEO wants AI on every support ticket. Sanity check.",
        "body": (
            "Title says it all. CEO read a Sequoia memo. Now I have to evaluate AI vendors. "
            "What should I actually look at?"
        ),
        "author": "weary_eng_manager",
        "created_at": _iso(6),
        "fetched_at": _iso(0),
        "intent": "research",
        "competitors_mentioned": [],
        "typewise_mentioned": True,
        "relevance_score": 0.71,
        "draft_reply": None,
    },
    {
        "id": "hn:demo-007",
        "source": "hn",
        "locale": "en",
        "url": "https://news.ycombinator.com/item?id=demo-007",
        "title": "AI customer service hype vs reality — what actually deflects tickets?",
        "body": "Skeptical. Looking for war stories from people who deployed and saw real metrics.",
        "author": "skeptical_pm",
        "created_at": _iso(0),
        "fetched_at": _iso(0),
        "intent": "research",
        "competitors_mentioned": [],
        "typewise_mentioned": False,
        "relevance_score": 0.78,
        "draft_reply": (
            "Honest metric to anchor on: 60-75% L1 deflection is the realistic ceiling for inbound that has a "
            "knowledge-base answer. Vendors quoting 90%+ are usually counting non-resolutions. Typewise publishes "
            "blended-rate numbers in customer stories (Brack.ch is the most concrete one)."
        ),
    },
    {
        "id": "dach:demo-008",
        "source": "dach",
        "locale": "fr",
        "url": "https://siliconcanals.com/demo-008",
        "title": "Quelles startups européennes en IA service client sont sérieuses ?",
        "body": "Tour d'horizon attendu pour un rapport interne.",
        "author": "analyst_fr",
        "created_at": _iso(2),
        "fetched_at": _iso(0),
        "intent": "research",
        "competitors_mentioned": [],
        "typewise_mentioned": False,
        "relevance_score": 0.66,
        "draft_reply": None,
    },
]


def seed(db_path=DEMO_DB_PATH) -> int:
    with store.connect(db_path) as conn:
        return store.upsert_many(conn, DEMO_THREADS)


def main() -> None:
    n = seed()
    print(f"Seeded {n} demo threads into {DEMO_DB_PATH}.")


if __name__ == "__main__":
    main()
