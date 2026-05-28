"""Regression tests: scraped content must be escaped in the dashboard render."""

import importlib

app = importlib.import_module("src.app")


class _FakeExpander:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _FakeSt:
    """Minimal Streamlit stand-in that records every rendered HTML chunk."""

    def __init__(self):
        self.chunks = []

    def expander(self, label, *args, **kwargs):
        self.chunks.append(label)
        return _FakeExpander()

    def markdown(self, body, *args, **kwargs):
        self.chunks.append(str(body))

    def text_area(self, *args, **kwargs):
        self.chunks.append(str(kwargs.get("value", "")))


def _render(thread):
    fake = _FakeSt()
    original = app.st
    app.st = fake
    try:
        app._render_thread(thread)
    finally:
        app.st = original
    return "".join(fake.chunks)


def test_script_tag_in_title_is_escaped():
    out = _render(
        {"id": 1, "title": "<script>alert(1)</script>", "url": "https://news.ycombinator.com/item?id=1"}
    )
    assert "&lt;script&gt;" in out
    assert "<script>alert(1)</script>" not in out


def test_javascript_url_is_neutralized():
    assert app._safe_url("javascript:alert(1)") == "#"
    assert app._safe_url("data:text/html,<script>x</script>") == "#"
    assert app._safe_url("https://news.ycombinator.com") == "https://news.ycombinator.com"

    out = _render({"id": 2, "title": "ok", "url": "javascript:alert(1)"})
    assert "javascript:alert(1)" not in out


def test_img_onerror_in_body_is_escaped():
    out = _render(
        {"id": 3, "title": "ok", "url": "https://example.com", "body": '<img src=x onerror="alert(1)">'}
    )
    assert "&lt;img" in out
    assert '<img src=x onerror="alert(1)">' not in out
