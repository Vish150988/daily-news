import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import patch
from reader import fetch_article_text


def test_returns_extracted_text():
    with patch("trafilatura.fetch_url", return_value="<html>content</html>"), \
         patch("trafilatura.extract", return_value="Clean article text."):
        result = fetch_article_text("https://example.com/article")
    assert result == "Clean article text."


def test_returns_none_when_fetch_fails():
    with patch("trafilatura.fetch_url", return_value=None):
        result = fetch_article_text("https://example.com/article")
    assert result is None


def test_returns_none_on_exception():
    with patch("trafilatura.fetch_url", side_effect=Exception("timeout")):
        result = fetch_article_text("https://example.com/article")
    assert result is None


def test_returns_none_when_extract_returns_none():
    with patch("trafilatura.fetch_url", return_value="<html/>"), \
         patch("trafilatura.extract", return_value=None):
        result = fetch_article_text("https://example.com/article")
    assert result is None
