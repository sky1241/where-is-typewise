"""Regression tests for the Streamlit launcher entry point.

Catches BUG-001: running `streamlit run src/app.py` directly puts only `src/`
on sys.path, which breaks `from src.radar import store` imports. The fix is
the root-level `streamlit_app.py` launcher; this test makes sure no future
change moves it back or re-introduces the import-from-src pattern.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_root_streamlit_app_file_exists():
    assert (REPO_ROOT / "streamlit_app.py").is_file(), (
        "streamlit_app.py must live at the repo root — Streamlit Community Cloud "
        "auto-discovers it there, and running `streamlit run streamlit_app.py` puts "
        "the repo root on sys.path so `from src.radar import store` resolves."
    )


def test_root_streamlit_app_imports_main_from_src_app():
    spec = importlib.util.spec_from_file_location(
        "streamlit_app", REPO_ROOT / "streamlit_app.py"
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    assert callable(getattr(module, "main", None)), (
        "streamlit_app.py must expose a callable `main` so the dashboard launches"
    )


def test_running_streamlit_app_with_src_only_on_syspath_would_fail():
    """Simulate the broken invocation pattern to prove the bug exists outside the fix.

    This is a documentation test: it asserts the exact ModuleNotFoundError that
    `streamlit run src/app.py` produces, so anyone reading the test understands
    why streamlit_app.py is required.
    """
    code = (
        "import sys; sys.path = [r'" + str(REPO_ROOT / "src") + "']; "
        "import importlib; "
        "spec = importlib.util.spec_from_file_location('app', r'" + str(REPO_ROOT / "src" / "app.py") + "'); "
        "module = importlib.util.module_from_spec(spec); "
        "spec.loader.exec_module(module)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=10,
    )
    # The point of the test: WITHOUT the root launcher, this exact error happens.
    assert result.returncode != 0
    combined = (result.stdout + result.stderr).lower()
    assert "no module named 'src'" in combined or "modulenotfounderror" in combined, (
        f"Expected the src-on-syspath-only path to fail with ModuleNotFoundError. "
        f"Got stdout={result.stdout!r} stderr={result.stderr!r}"
    )


def test_running_streamlit_app_with_repo_root_on_syspath_succeeds():
    """The fix: with the repo root on sys.path (what streamlit_app.py provides), app.py imports cleanly."""
    code = (
        "import sys; sys.path.insert(0, r'" + str(REPO_ROOT) + "'); "
        "from src import app; assert callable(app.main)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"app.py must be importable when repo root is on sys.path. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
