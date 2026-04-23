import re
import urllib.request
from html.parser import HTMLParser
from typing import Optional


def fetch_article_text(url: str) -> Optional[str]:
    """Fetch and extract clean article text from a URL.

    Uses trafilatura on desktop (if installed) for high-quality extraction.
    Falls back to a pure-Python stdlib extractor on mobile (Android/iOS)
    where trafilatura's C dependencies are unavailable.
    Returns None if extraction fails.
    """
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except ImportError:
        return _stdlib_extract(url)
    except Exception:
        return None


def _stdlib_extract(url: str) -> Optional[str]:
    """Pure-Python fallback article extractor using only stdlib."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DailyNewsApp/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Strip scripts, styles, nav, header, footer blocks
        html = re.sub(
            r"<(script|style|nav|header|footer|aside)[^>]*>.*?</\1>",
            " ",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # Remove remaining tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        return text[:4000] if len(text) > 200 else None
    except Exception:
        return None
