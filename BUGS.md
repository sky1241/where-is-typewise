# BUGS — where-is-typewise

> Format: each bug has an ID, status, symptom, root cause, fix, and test.
> Keep this file accurate — your AI assistant (or future you) will read it before fixing bugs.

<!-- TEMPLATE
## BUG-XXX: [short description]
- **Status**: OPEN / FIXED / WONTFIX
- **Symptom**: what happens
- **Root cause**: WHY it happens (not just where)
- **Fix**: what was done (commit hash if fixed)
- **Test**: which test covers this (file:test_name)
- **Regression**: did the fix break anything else?
-->

## BUG-003: Re-fetched threads silently wiped their scores — every refresh re-billed the full thread set

- **Status**: FIXED
- **Symptom**: Each radar cycle re-scored (and re-paid) every thread it fetched, even threads already scored in a previous run. On a ~300-thread dataset, every refresh cost a full ~$0.50 cycle instead of the cents that the handful of genuinely new threads should cost. Nothing failed: the dashboard looked right, all tests were green, only the API bill knew.
- **Root cause**: two compounding issues. (1) `store.upsert_thread` used `INSERT OR REPLACE`, which replaces the *entire* row — re-fetched threads arrive from scrapers with scoring fields set to `None`, so the replace wiped `relevance_score`, `intent`, `draft_reply`, `competitors_mentioned`, and `typewise_mentioned` that a previous (paid) scoring run had written. (2) `runner.run` then sent *all* fetched threads to the scorer without checking what was already scored — consistent with the wiped DB, and ruinous.
- **Fix**: `upsert_thread` now uses `INSERT ... ON CONFLICT(id) DO UPDATE` with `COALESCE` on the scorer-owned columns, so a re-fetch refreshes fetch-owned fields (title, body, fetched_at, …) without touching paid scoring. `runner.run` filters the batch through `_filter_unscored` and only sends threads whose `relevance_score` is still NULL — already-scored threads are never re-billed.
- **Test**: `tests/test_radar_store.py::test_refetch_upsert_preserves_existing_scoring`, `tests/test_radar_runner.py::test_run_scores_only_unscored_threads`, `tests/test_radar_runner.py::test_run_skips_scoring_entirely_when_all_threads_scored`.
- **Regression**: none — `upsert` keeps its insert/refresh semantics for fetch-owned fields (`test_upsert_is_idempotent` still passes unchanged), and a thread upserted *with* explicit scoring values still stores them (COALESCE prefers the incoming non-NULL value).
- **How it was found**: reviewing the Anthropic API bill, not the test suite. The cost per refresh didn't drop as the dataset matured, which only makes sense if scoring work was being repeated. **Lesson: for systems that spend money per operation, the invoice is a monitoring surface — a metric can look correct while the cost graph proves it isn't.**

## BUG-002: Dashboard headline metrics zeroed by a 7-day window on real HN data

- **Status**: FIXED
- **Symptom**: After replacing the seed_demo data with the real 324-thread scored dataset, the live dashboard showed "Should have been mentioned: 0", "Typewise was mentioned: 0", coverage gap "0:0", even though 5 threads in the DB had relevance_score >= 0.7. The filter line said "64 thread(s) matching filters" so the data was clearly there — but the headline metrics insisted everything was zero.
- **Root cause**: `_count_mentioned_recent(..., since_days=7)` and `store.count_unmentioned_relevant(..., since_days=7)` filtered `created_at >= now - 7 days`. Hacker News Algolia search returns the highest-relevance threads sorted by relevance, NOT by recency. The top 5 hot threads in the indexed dataset were created Mar 2024, May/Aug/Oct 2025, and Feb 2026 — none of them inside the last 7 days. So the headline metric correctly returned zero according to its broken contract; the contract itself misrepresented how HN search works.
- **Fix**: dropped the time window on the dashboard headline metrics — pass `since_days=None`. Added a `_count_mentioned(conn)` helper that counts across the whole indexed dataset. Updated sub-labels from "threads this week" to "threads in the radar" / "across the indexed dataset" to stay honest about what the number reflects. `_count_mentioned_recent` kept with a `since_days=30` default so the existing test_app.py tests (which pass `since_days=14`) continue to pass.
- **Test**: existing test suite already exercises the helpers; manual visual smoke at `http://localhost:8501` after the fix returned the expected `Metrics: ['5', '0', '5:0']` and `64 thread(s) matching filters`. Real HN URLs in the table all resolve.
- **Regression**: none — the only changed surface is the dashboard render. The store APIs are unchanged.
- **How it was found**: a screenshot of the deployed Streamlit Cloud dashboard after the real DB was pushed. Same pattern as BUG-001 — pytest can't catch what the user-facing surface silently misrepresents. **Lesson: every change that touches a metric needs a visual or live-API verification, not just tests.**

## BUG-001: Streamlit dashboard crashed with ModuleNotFoundError at runtime, invisible to pytest

- **Status**: FIXED
- **Symptom**: opening the dashboard in a browser showed a red error banner: `ModuleNotFoundError: No module named 'src'` at `src/app.py:14 — from src.radar import store`. The full 78-test pytest suite was green; forge reported zero failures.
- **Root cause**: `streamlit run src/app.py` puts the *file's parent directory* on sys.path — i.e. only `src/` — so the import `from src.radar import store` can't find the `src` package. pytest, in contrast, runs from the repo root, which puts the project root on sys.path and resolves the import. The two environments diverge, and unit tests cannot catch it.
- **Fix**: added `streamlit_app.py` at the repo root that does `from src.app import main` then calls it. Streamlit Community Cloud auto-discovers root-level `streamlit_app.py`. The canonical launch command is now `streamlit run streamlit_app.py`. README updated accordingly.
- **Test**: `tests/test_streamlit_entrypoint.py` — four tests: (a) root file exists, (b) it exposes a `main` callable, (c) reproduces the original failure by simulating the broken sys.path so the bug stays falsifiable, (d) proves the fix works when repo root is on sys.path.
- **Regression**: none — the move only added a new entry-point file; `src/app.py` is unchanged structurally and remains directly importable for tests.
- **How it was found**: visual inspection of a Playwright screenshot during a "no silent bugs" audit. **Lesson: green tests are not a substitute for actually running the user-facing surface and looking at it.**

