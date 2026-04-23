import trafilatura
from typing import Optional


def fetch_article_text(url: str) -> Optional[str]:
    """Fetch and extract clean article text from a URL.

    Returns None if the page cannot be fetched or parsed.
    Broad exception handler is intentional — trafilatura and network
    layers raise many different exception types at this boundary.
    """
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception:
        return None
