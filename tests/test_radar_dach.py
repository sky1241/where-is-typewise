"""Unit tests for src/radar/dach.py — RSS via httpx.MockTransport, no network."""

from __future__ import annotations

import httpx
import pytest

from src.radar import dach


_SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>t3n.de</title>
    <link>https://t3n.de</link>
    <item>
      <title>AI customer service revolution in Germany</title>
      <link>https://t3n.de/news/ai-cs-1</link>
      <guid isPermaLink="false">t3n-guid-1</guid>
      <pubDate>Thu, 22 May 2026 08:00:00 GMT</pubDate>
      <description>&lt;p&gt;Eine ausfuhrliche Analyse zu AI customer service tools.&lt;/p&gt;</description>
      <author>author@example.com</author>
    </item>
    <item>
      <title>Pizza recipes 2026</title>
      <link>https://t3n.de/news/pizza</link>
      <guid isPermaLink="false">t3n-guid-2</guid>
      <pubDate>Thu, 22 May 2026 09:00:00 GMT</pubDate>
      <description>How to make great pizza dough.</description>
    </item>
    <item>
      <title>Best AI support tool for ecommerce</title>
      <link>https://t3n.de/news/ai-cs-2</link>
      <guid isPermaLink="false">t3n-guid-3</guid>
      <pubDate>Thu, 22 May 2026 10:00:00 GMT</pubDate>
      <description>&lt;p&gt;Vergleich der AI-CS Werkzeuge.&lt;/p&gt;</description>
    </item>
  </channel>
</rss>
"""


def _mock_client(responder) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(responder))


def test_fetch_feed_maps_entries_to_thread_schema():
    def responder(request):
        assert "t3n.de" in str(request.url)
        return httpx.Response(200, content=_SAMPLE_RSS)

    with _mock_client(responder) as client:
        threads = dach.fetch_feed(name="t3n", url="https://t3n.de/rss.xml", locale="de", client=client)

    assert len(threads) == 3  # no keyword filter -> all entries
    t = threads[0]
    assert t["id"].startswith("dach:t3n:")
    assert t["source"] == "dach"
    assert t["locale"] == "de"
    assert t["url"] == "https://t3n.de/news/ai-cs-1"
    assert t["title"] == "AI customer service revolution in Germany"
    assert "Analyse" in t["body"]  # HTML stripped, content preserved
    assert "<p>" not in t["body"]  # tags removed
    assert t["created_at"] == "2026-05-22T08:00:00+00:00"
    assert t["fetched_at"]
    assert t["author"] == "author@example.com"
    assert t["typewise_mentioned"] is None  # unscored
    assert t["relevance_score"] is None


def test_fetch_feed_keyword_filter_excludes_non_matching():
    def responder(_request):
        return httpx.Response(200, content=_SAMPLE_RSS)

    with _mock_client(responder) as client:
        threads = dach.fetch_feed(
            name="t3n", url="https://t3n.de/rss.xml", locale="de",
            keywords=["AI customer service", "AI support tool"],
            client=client,
        )

    assert len(threads) == 2
    titles = {t["title"] for t in threads}
    assert "Pizza recipes 2026" not in titles


def test_fetch_feed_locale_set_per_feed():
    def responder(_request):
        return httpx.Response(200, content=_SAMPLE_RSS)

    with _mock_client(responder) as client:
        de_threads = dach.fetch_feed(name="t3n", url="https://t3n.de/rss.xml", locale="de", client=client)
        en_threads = dach.fetch_feed(name="canals", url="https://siliconcanals.com/feed/", locale="en", client=client)

    assert all(t["locale"] == "de" for t in de_threads)
    assert all(t["locale"] == "en" for t in en_threads)


def test_fetch_feed_raises_on_http_error():
    def responder(_request):
        return httpx.Response(500, text="boom")

    with _mock_client(responder) as client:
        with pytest.raises(httpx.HTTPStatusError):
            dach.fetch_feed(name="t3n", url="https://t3n.de/rss.xml", locale="de", client=client)


def test_fetch_feed_handles_missing_pubdate():
    rss = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>x</title>
<item><title>no date</title><link>https://x/1</link><guid>g1</guid><description>body</description></item>
</channel></rss>"""

    def responder(_r):
        return httpx.Response(200, content=rss)

    with _mock_client(responder) as client:
        [t] = dach.fetch_feed(name="x", url="https://x/", locale="en", client=client)
    assert t["created_at"] is None
    assert t["title"] == "no date"


def test_fetch_all_dedupes_across_feeds():
    shared_rss = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>x</title>
<item><title>shared</title><link>https://x/shared</link><guid>shared-guid</guid><description>body</description></item>
</channel></rss>"""
    other_rss = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>y</title>
<item><title>other</title><link>https://y/other</link><guid>other-guid</guid><description>body</description></item>
</channel></rss>"""

    def responder(request):
        if "feed_a" in str(request.url):
            return httpx.Response(200, content=shared_rss)
        return httpx.Response(200, content=other_rss)

    feeds = [
        {"name": "feed_a", "url": "https://example.com/feed_a", "locale": "de"},
        # Same name+entry → same id → dedup wins one of them
        {"name": "feed_a", "url": "https://example.com/feed_a", "locale": "de"},
        {"name": "feed_b", "url": "https://example.com/feed_b", "locale": "en"},
    ]

    with _mock_client(responder) as client:
        threads = dach.fetch_all(feeds, client=client)

    ids = sorted(t["id"] for t in threads)
    assert len(ids) == 2  # the shared entry deduped
    assert ids[0].startswith("dach:feed_a:")
    assert ids[1].startswith("dach:feed_b:")


def test_fetch_all_skips_failing_feed(caplog):
    def responder(request):
        if "bad" in str(request.url):
            return httpx.Response(500, text="boom")
        return httpx.Response(200, content=_SAMPLE_RSS)

    feeds = [
        {"name": "bad", "url": "https://bad.example/", "locale": "de"},
        {"name": "good", "url": "https://good.example/", "locale": "en"},
    ]

    with _mock_client(responder) as client, caplog.at_level("WARNING"):
        threads = dach.fetch_all(feeds, client=client)

    assert len(threads) == 3  # only the good feed's entries
    assert all(t["id"].startswith("dach:good:") for t in threads)
    assert any("bad" in r.message for r in caplog.records)


def test_default_feeds_shape():
    """Defaults must be valid feed dicts so callers don't have to construct their own."""
    assert len(dach.DEFAULT_FEEDS) >= 3
    for f in dach.DEFAULT_FEEDS:
        assert "name" in f and "url" in f and "locale" in f
        assert f["url"].startswith("http")
