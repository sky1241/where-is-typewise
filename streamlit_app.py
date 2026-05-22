"""Streamlit Cloud entry point.

Streamlit Community Cloud auto-discovers `streamlit_app.py` at the repo root.
Running `streamlit run src/app.py` directly puts `src/` on sys.path instead
of the project root, which breaks the `from src.radar import store` imports.
This launcher keeps the real implementation in `src/app.py` (testable, importable)
while making the dashboard runnable from a single canonical command:

    streamlit run streamlit_app.py
"""

from src.app import main

if __name__ == "__main__":
    main()
