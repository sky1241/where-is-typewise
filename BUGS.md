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

## BUG-001: Streamlit dashboard crashed with ModuleNotFoundError at runtime, invisible to pytest

- **Status**: FIXED
- **Symptom**: opening the dashboard in a browser showed a red error banner: `ModuleNotFoundError: No module named 'src'` at `src/app.py:14 — from src.radar import store`. The full 78-test pytest suite was green; forge reported zero failures.
- **Root cause**: `streamlit run src/app.py` puts the *file's parent directory* on sys.path — i.e. only `src/` — so the import `from src.radar import store` can't find the `src` package. pytest, in contrast, runs from the repo root, which puts the project root on sys.path and resolves the import. The two environments diverge, and unit tests cannot catch it.
- **Fix**: added `streamlit_app.py` at the repo root that does `from src.app import main` then calls it. Streamlit Community Cloud auto-discovers root-level `streamlit_app.py`. The canonical launch command is now `streamlit run streamlit_app.py`. README updated accordingly.
- **Test**: `tests/test_streamlit_entrypoint.py` — four tests: (a) root file exists, (b) it exposes a `main` callable, (c) reproduces the original failure by simulating the broken sys.path so the bug stays falsifiable, (d) proves the fix works when repo root is on sys.path.
- **Regression**: none — the move only added a new entry-point file; `src/app.py` is unchanged structurally and remains directly importable for tests.
- **How it was found**: visual inspection of a Playwright screenshot during a "no silent bugs" audit. **Lesson: green tests are not a substitute for actually running the user-facing surface and looking at it.**

