import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch, MagicMock


def _mock_feed(*entries):
    feed = MagicMock()
    feed.entries = list(entries)
    return feed


def _mock_entry(title="Test", link="https://example.com/1", summary="Summary", published="2026-01-01"):
    e = MagicMock()
    data = {"title": title, "link": link, "summary": summary, "published": published}
    e.get.side_effect = lambda k, d="": data.get(k, d)
    return e


def test_fetch_feed_returns_articles():
    from rss import _fetch_feed
    with patch("feedparser.parse", return_value=_mock_feed(_mock_entry())):
        results = _fetch_feed("world", "BBC", "http://bbc.com/rss")
    assert len(results) == 1
    assert results[0]["title"] == "Test"
    assert results[0]["category"] == "world"
    assert results[0]["source"] == "BBC"
    assert results[0]["url"] == "https://example.com/1"


def test_fetch_feed_returns_empty_on_network_error():
    from rss import _fetch_feed
    with patch("feedparser.parse", side_effect=Exception("timeout")):
        results = _fetch_feed("world", "BBC", "http://bbc.com/rss")
    assert results == []


def test_fetch_feed_skips_entries_without_link():
    from rss import _fetch_feed
    with patch("feedparser.parse", return_value=_mock_feed(_mock_entry(link=""))):
        results = _fetch_feed("world", "BBC", "http://bbc.com/rss")
    assert results == []


def test_fetch_feed_article_id_is_md5_of_url():
    from rss import _fetch_feed
    import hashlib
    with patch("feedparser.parse", return_value=_mock_feed(_mock_entry())):
        results = _fetch_feed("world", "BBC", "http://bbc.com/rss")
    expected_id = hashlib.md5("https://example.com/1".encode()).hexdigest()
    assert results[0]["id"] == expected_id


def test_fetch_all_feeds_calls_upsert():
    from rss import fetch_all_feeds
    with patch("feedparser.parse", return_value=_mock_feed(_mock_entry())), \
         patch("rss.upsert_articles") as mock_upsert, \
         patch("rss.prune_articles"):
        count = fetch_all_feeds()
    assert mock_upsert.called
    assert count > 0
