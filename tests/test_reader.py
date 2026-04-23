import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch


def test_returns_extracted_text():
    from reader import fetch_article_text
    with patch("trafilatura.fetch_url", return_value="<html>content</html>"), \
         patch("trafilatura.extract", return_value="Clean article text."):
        result = fetch_article_text("https://example.com/article")
    assert result == "Clean article text."


def test_returns_none_when_fetch_fails():
    from reader import fetch_article_text
    with patch("trafilatura.fetch_url", return_value=None):
        result = fetch_article_text("https://example.com/article")
    assert result is None


def test_returns_none_on_exception():
    from reader import fetch_article_text
    with patch("trafilatura.fetch_url", side_effect=Exception("timeout")):
        result = fetch_article_text("https://example.com/article")
    assert result is None


def test_returns_none_when_extract_returns_none():
    from reader import fetch_article_text
    with patch("trafilatura.fetch_url", return_value="<html/>"), \
         patch("trafilatura.extract", return_value=None):
        result = fetch_article_text("https://example.com/article")
    assert result is None
