import re
import urllib.request
import urllib.parse
from typing import Optional

# Keywords that indicate a line is an ad, nav, or non-content
_JUNK_KEYWORDS = [
    "register now", "tickets are going fast", "sign up", "subscribe",
    "newsletter", "cookie policy", "privacy policy", "terms of service",
    "terms of use", "access denied", "403 forbidden", "not found",
    "page cannot be found", "page not found", "all rights reserved",
    "copyright", "follow us on", "share this", "related articles",
    "read more", "click here to", "advertisement", "sponsored",
    "promoted", "close", "skip to content", "submit", "search",
    "menu", "home", "about us", "contact us", "careers", "log in",
    "sign in", "credit:", "getty images", "loading comments",
    "most read", "trending", "popular", "you may also like",
    "recommended for you", "editor's pick", "loading loading",
    "has been separating the signal from the noise",
]

_BIO_KEYWORDS = [
    "is a reporter", "is a writer", "is a journalist", "is an editor",
    "is a senior", "is a contributing", "previously written for",
    "has written for", "has previously", "master of arts",
    "bachelor's degree", "master's degree", "phd in", "dr.",
    "professor of", "is a correspondent", "is a columnist",
]

_SOCIAL_DOMAINS = [
    "bsky.app", "mastodon.social", "facebook.com", "youtube.com",
    "twitter.com", "x.com", "instagram.com", "linkedin.com",
    "reddit.com", "tiktok.com",
]


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
    with urllib.request.urlopen(req, timeout=8) as resp:
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

    # Remove markdown images completely
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", text)
    # Convert markdown links to just their text
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    # Remove any raw HTML tags Jina sometimes leaves behind
    text = re.sub(r"</?(?:p|div|span|br|hr|h[1-6]|strong|em|b|i|u|a|img|ul|ol|li|blockquote|code|pre|table|tr|td|th)[^>]*>", "", text, flags=re.IGNORECASE)

    lines = []
    for line in text.splitlines():
        stripped = line.strip()

        # Skip empty/very short lines
        if len(stripped) < 25:
            continue

        # Skip bullet points (nav links)
        if re.match(r"^[\*\-\+]\s+", stripped):
            continue

        # Skip numbered list items (Most Read, etc.)
        if re.match(r"^\d+\.\s+", stripped):
            continue

        # Skip lines that are just URLs
        if re.match(r"^https?://", stripped):
            continue

        # Skip image caption lines
        if re.match(r"^Image\s+\d+:", stripped, re.IGNORECASE):
            continue

        # Skip cookie consent walls
        cookie_count = stripped.lower().count("cookie")
        if cookie_count >= 2:
            continue

        # Skip junk keywords
        lower_line = stripped.lower()
        if any(kw in lower_line for kw in _JUNK_KEYWORDS):
            continue

        # Skip author bios
        if any(kw in lower_line for kw in _BIO_KEYWORDS):
            continue

        # Skip social media / footer links
        if any(domain in lower_line for domain in _SOCIAL_DOMAINS):
            continue

        # Skip lines with many caps (often nav/button text)
        if stripped.isupper() and len(stripped) < 60:
            continue

        lines.append(stripped)

    cleaned = "\n\n".join(lines)
    return cleaned.strip() if len(cleaned) > 200 else None


def _strip_jina_header(text: str) -> str:
    """Remove Jina AI reader header metadata."""
    for marker in ("Markdown Content:\n", "Markdown Content:", "Markdown Content"):
        idx = text.find(marker)
        if idx != -1:
            text = text[idx + len(marker):]
            break
    return text.strip()


def _stdlib_extract(url: str) -> Optional[str]:
    """Pure-Python fallback article extractor using only stdlib."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; DailyNewsApp/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            # Limit to 500KB to avoid huge pages
            html = resp.read(500_000).decode("utf-8", errors="ignore")

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
