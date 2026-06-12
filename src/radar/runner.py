"""Radar orchestrator — fetch HN + Reddit + DACH RSS, locale-tag, score via Claude, persist.

Run from the repo root:

    python -m src.radar.runner --db data/radar.db

Degrades gracefully when secrets / feeds are missing:
  * No REDDIT_CLIENT_ID / SECRET → skip Reddit, log a warning, keep going on HN.
  * Dead RSS feed                → skip that feed, log a warning, keep going.
  * No ANTHROPIC_API_KEY         → skip scoring, persist unscored threads.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover — anthropic is in requirements.txt
    Anthropic = None  # type: ignore[assignment]

from src.radar import dach, hackernews, locale_tagger, reddit, scorer, store

logger = logging.getLogger("radar.runner")

_DEFAULT_CONFIG_PATH = Path("config.yaml")
_DEFAULT_DB_PATH = Path("data/radar.db")


def load_config(path: str | Path = _DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    """Load config.yaml; raises FileNotFoundError if missing."""
    with Path(path).open(encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    if not isinstance(cfg, dict):
        raise ValueError(f"config.yaml must be a mapping at top level, got {type(cfg).__name__}")
    return cfg


def _fetch_hn(config: dict[str, Any]) -> list[dict[str, Any]]:
    keywords = config.get("keywords") or []
    hn_cfg = config.get("hackernews") or {}
    max_results = int(hn_cfg.get("max_results", 50))
    by_date = bool(hn_cfg.get("by_date", True))
    since_days = hn_cfg.get("since_days")
    since_days = int(since_days) if since_days is not None else None
    if not keywords:
        logger.warning("no keywords in config — skipping HN fetch")
        return []
    threads = hackernews.search_many(
        keywords, max_per_query=max_results, by_date=by_date, since_days=since_days
    )
    logger.info(
        "HN: fetched %d unique threads across %d queries (by_date=%s, since_days=%s)",
        len(threads), len(keywords), by_date, since_days,
    )
    return threads


def _fetch_reddit(config: dict[str, Any]) -> list[dict[str, Any]]:
    reddit_cfg = config.get("reddit") or {}
    subs = reddit_cfg.get("subreddits") or []
    limit_per_sub = int(reddit_cfg.get("posts_per_sub", 50))
    if not subs:
        logger.warning("no subreddits in config — skipping Reddit fetch")
        return []
    try:
        client = reddit.client_from_env()
    except reddit.RedditCredsMissing as exc:
        logger.warning("Reddit creds missing — skipping Reddit fetch (%s)", exc)
        return []
    threads = reddit.scrape_many(subs, limit_per_sub=limit_per_sub, reddit=client)
    logger.info("Reddit: fetched %d unique threads across %d subreddits", len(threads), len(subs))
    return threads


def _fetch_dach(config: dict[str, Any]) -> list[dict[str, Any]]:
    """`dach.keywords` overrides the global `keywords` list — pass an empty list to disable
    filtering entirely (DACH feeds are general startup news; tight filters often kill the
    signal and the radar target of >=20 DACH threads/day relies on a wide net here)."""
    dach_cfg = config.get("dach") or {}
    feeds = dach_cfg.get("feeds")
    keywords = dach_cfg["keywords"] if "keywords" in dach_cfg else (config.get("keywords") or [])
    threads = dach.fetch_all(feeds=feeds, keywords=keywords)
    feed_count = len(feeds) if feeds is not None else len(dach.DEFAULT_FEEDS)
    logger.info("DACH: fetched %d threads across %d feeds", len(threads), feed_count)
    return threads


def _tag_locales(db_path: Path) -> int:
    with store.connect(db_path) as conn:
        n = locale_tagger.tag_threads_in_db(conn, only_untagged=True)
    logger.info("Locale-tagged %d previously-untagged threads", n)
    return n


def _filter_unscored(threads: list[dict[str, Any]], *, db_path: Path) -> list[dict[str, Any]]:
    """Keep only threads with no relevance_score in the DB yet.

    Scoring is the only paid step of the cycle; re-fetched threads keep their
    existing score (store upsert COALESCEs scorer-owned columns), so re-scoring
    them would spend API budget for zero new information."""
    with store.connect(db_path) as conn:
        return [
            t for t in threads
            if (existing := store.get_thread(conn, t["id"])) is None
            or existing["relevance_score"] is None
        ]


def _score_and_persist(
    threads: list[dict[str, Any]],
    *,
    config: dict[str, Any],
    db_path: Path,
    anthropic_client: Any,
) -> int:
    competitors = config.get("competitors") or None
    scored = 0
    with store.connect(db_path) as conn:
        for thread, scoring in scorer.score_many(
            threads,
            client=anthropic_client,
            competitors=competitors,
            on_error="skip",
        ):
            store.update_scoring(conn, thread["id"], **scoring)
            scored += 1
    logger.info("Scored %d / %d threads", scored, len(threads))
    return scored


def run(
    config: dict[str, Any],
    *,
    db_path: Path = _DEFAULT_DB_PATH,
    use_reddit: bool = True,
    use_dach: bool = True,
    use_scoring: bool = True,
    tag_locale: bool = True,
) -> dict[str, int]:
    """Run one cycle. Returns a summary dict with fetch/persist/tag/score counts."""
    hn_threads = _fetch_hn(config)
    reddit_threads = _fetch_reddit(config) if use_reddit else []
    dach_threads = _fetch_dach(config) if use_dach else []
    all_threads = hn_threads + reddit_threads + dach_threads

    with store.connect(db_path) as conn:
        persisted = store.upsert_many(conn, all_threads)
    logger.info("Persisted %d threads to %s", persisted, db_path)

    locale_tagged = _tag_locales(db_path) if tag_locale else 0

    scored = 0
    if use_scoring and all_threads:
        unscored = _filter_unscored(all_threads, db_path=db_path)
        if not unscored:
            logger.info(
                "All %d fetched threads already scored — skipping scoring entirely",
                len(all_threads),
            )
        elif Anthropic is None:
            logger.warning("anthropic SDK not importable — skipping scoring")
        elif not os.environ.get("ANTHROPIC_API_KEY"):
            logger.warning("ANTHROPIC_API_KEY not set — skipping scoring")
        else:
            logger.info(
                "Scoring %d new threads (%d already scored, not re-billed)",
                len(unscored),
                len(all_threads) - len(unscored),
            )
            scored = _score_and_persist(
                unscored,
                config=config,
                db_path=db_path,
                anthropic_client=Anthropic(),
            )

    return {
        "fetched_hn": len(hn_threads),
        "fetched_reddit": len(reddit_threads),
        "fetched_dach": len(dach_threads),
        "persisted": persisted,
        "locale_tagged": locale_tagged,
        "scored": scored,
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m src.radar.runner", description=__doc__)
    p.add_argument("--config", type=Path, default=_DEFAULT_CONFIG_PATH, help="Path to config.yaml")
    p.add_argument("--db", type=Path, default=_DEFAULT_DB_PATH, help="SQLite DB path")
    p.add_argument("--no-reddit", action="store_true", help="Skip Reddit fetch")
    p.add_argument("--no-dach", action="store_true", help="Skip DACH RSS fetch")
    p.add_argument("--no-locale-tag", action="store_true", help="Skip langdetect post-pass")
    p.add_argument("--no-scoring", action="store_true", help="Persist threads unscored")
    p.add_argument("-v", "--verbose", action="store_true", help="DEBUG-level logs")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )
    config = load_config(args.config)
    summary = run(
        config,
        db_path=args.db,
        use_reddit=not args.no_reddit,
        use_dach=not args.no_dach,
        use_scoring=not args.no_scoring,
        tag_locale=not args.no_locale_tag,
    )
    print(
        f"HN={summary['fetched_hn']} "
        f"Reddit={summary['fetched_reddit']} "
        f"DACH={summary['fetched_dach']} "
        f"persisted={summary['persisted']} "
        f"locale_tagged={summary['locale_tagged']} "
        f"scored={summary['scored']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
