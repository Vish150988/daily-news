import re
import urllib.request
import urllib.parse
from typing import Optional


def fetch_article_text(url: str) -> Optional[str]:
    """Fetch and extract clean article text from a URL.

    Tiers:
      1. trafilatura (desktop, best quality)
      2. Jina AI reader API (mobile, fast, good quality)
      3. stdlib regex extractor (offline fallback)
    """
    # 1. Desktop: trafilatura
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(
                downloaded, include_comments=False, include_tables=False
            )
            if text:
                return text
    except ImportError:
        pass
    except Exception:
        pass

    # 2. Mobile: Jina AI reader (fast, high-quality extraction)
    try:
        return _jina_extract(url)
    except Exception:
        pass

    # 3. Fallback: pure-Python extractor
    return _stdlib_extract(url)


def _jina_extract(url: str) -> Optional[str]:
    """Use Jina AI reader API to extract article text."""
    jina_url = f"https://r.jina.ai/http://{urllib.parse.quote(url, safe='')}"
    req = urllib.request.Request(
        jina_url,
        headers={"User-Agent": "DailyNews/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        text = resp.read().decode("utf-8", errors="ignore")

    if not text or len(text.strip()) < 200:
        return None

    lower = text.lower()
    if any(bad in lower for bad in [
        "not found", "access denied", "403 forbidden",
        "page cannot be found", "page not found"
    ]):
        return None

    # Strip Jina header metadata
    text = _strip_jina_header(text)

    # Clean markdown link syntax: [text](url) -> text, ![alt](url) -> alt
    text = re.sub(r"!?\[([^\]]+)\]\([^)]+\)", r"\1", text)

    # Remove lines that are just URLs or short nav items
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if len(stripped) < 3:
            continue
        if stripped.startswith(("http://", "https://")):
            continue
        if stripped in ("Close", "Skip to content", "Submit", "Search"):
            continue
        lines.append(stripped)

    cleaned = "\n".join(lines)
    return cleaned.strip() if len(cleaned) > 200 else None


def _strip_jina_header(text: str) -> str:
    """Remove Jina AI reader header metadata."""
    for marker in ("Markdown Content:", "Markdown Content"):
        idx = text.find(marker)
        if idx != -1:
            text = text[idx + len(marker):]
            text = text.lstrip(":\n ")
            break
    return text


def _stdlib_extract(url: str) -> Optional[str]:
    """Pure-Python fallback article extractor using only stdlib."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DailyNewsApp/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        # Strip common non-content blocks
        html = re.sub(
            r"<(script|style|nav|header|footer|aside|noscript|iframe|svg|form|"
            r"button|input|select|textarea|label|meta|link|head|advertisement|"
            r"banner|promo|newsletter|subscribe|cookie-consent)"
            r"[^>]*>.*?</\1>",
            " ",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )

        # Try to isolate article content
        article_match = re.search(
            r"<article[^>]*>(.*?)</article>",
            html,
            re.DOTALL | re.IGNORECASE,
        )
        if article_match:
            html = article_match.group(1)
        else:
            main_match = re.search(
                r"<main[^>]*>(.*?)</main>",
                html,
                re.DOTALL | re.IGNORECASE,
            )
            if main_match:
                html = main_match.group(1)
            else:
                div_match = re.search(
                    r'<div[^>]*class=["\'][^"\']*(?:article|content|story|post)[^"\']*["\'][^>]*>(.*?)</div>',
                    html,
                    re.DOTALL | re.IGNORECASE,
                )
                if div_match:
                    html = div_match.group(1)

        # Extract <p> tags
        paragraphs = re.findall(
            r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE
        )
        clean_paras = []
        for p in paragraphs:
            p = re.sub(r"<[^>]+>", " ", p)
            p = re.sub(r"\s+", " ", p).strip()
            if len(p) > 40:
                clean_paras.append(p)

        if clean_paras:
            return "\n\n".join(clean_paras)[:8000]

        # Final fallback: largest text block
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:8000] if len(text) > 300 else None

    except Exception:
        return None
