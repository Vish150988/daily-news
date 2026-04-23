import logging
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Dict
from storage import upsert_articles, make_article_id, prune_articles

_MAX_ENTRIES_PER_FEED = 30  # cap per fetch to avoid DB bloat

FEEDS: Dict[str, List[tuple]] = {
    "world": [
        ("Reuters Top News",      "https://feeds.reuters.com/reuters/topNews"),
        ("BBC News",              "https://feeds.bbci.co.uk/news/rss.xml"),
        ("New York Times",        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
        ("The Guardian",          "https://www.theguardian.com/world/rss"),
        ("Al Jazeera",            "https://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "tech": [
        ("TechCrunch",            "https://techcrunch.com/feed/"),
        ("Wired",                 "https://www.wired.com/feed/rss"),
        ("The Verge",             "https://www.theverge.com/rss/index.xml"),
        ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ],
    "data-ai": [
        ("Hacker News",           "https://hnrss.org/frontpage"),
        ("Ars Technica",          "https://feeds.arstechnica.com/arstechnica/index"),
        ("KDnuggets",             "https://www.kdnuggets.com/feed"),
        ("VentureBeat",           "https://venturebeat.com/feed/"),
        ("The New Stack",         "https://thenewstack.io/feed/"),
    ],
    "business": [
        ("Wall Street Journal",   "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
        ("CNBC",                  "https://search.cnbc.com/rs/search/combinedcms/view.xml?id=100003114"),
        ("Fortune",               "https://fortune.com/feed/"),
    ],
    "florida": [
        ("Palm Beach Post",       "https://www.palmbeachpost.com/news/feed/"),
        ("Sun Sentinel",          "https://www.sun-sentinel.com/arc/outboundfeeds/rss/"),
        ("CBS News Miami",        "https://www.cbsnews.com/miami/rss/"),
    ],
    "us-politics": [
        ("NPR",                   "https://feeds.npr.org/1001/rss.xml"),
        ("Politico",              "https://rss.politico.com/politics-news.xml"),
        ("ProPublica",            "https://www.propublica.org/feeds/propublica/main"),
        ("AP News",               "https://news.yahoo.com/rss/world"),
    ],
    "long-form": [
        ("The Atlantic",          "https://www.theatlantic.com/feed/all/"),
        ("Longreads",             "https://longreads.com/feed/"),
        ("Smithsonian Magazine",  "https://www.smithsonianmag.com/rss/latest_articles/"),
    ],
}


def _fetch_feed(category: str, source: str, url: str) -> List[Dict]:
    try:
        feed = feedparser.parse(url)
        now = datetime.now(timezone.utc).isoformat()
        articles = []
        for entry in feed.entries[:_MAX_ENTRIES_PER_FEED]:
            link = entry.get("link", "")
            if not link:
                continue
            articles.append({
                "id":           make_article_id(link),
                "title":        entry.get("title", "").strip(),
                "url":          link,
                "source":       source,
                "category":     category,
                "excerpt":      entry.get("summary", "")[:500].strip(),
                "published_at": entry.get("published", now),
                "fetched_at":   now,
            })
        return articles
    except Exception as exc:
        logging.warning("_fetch_feed failed for %s (%s): %s", source, url, exc)
        return []


def fetch_all_feeds() -> int:
    """Fetch all 27 feeds in parallel and return the total article count."""
    tasks = [
        (cat, src, url)
        for cat, feeds in FEEDS.items()
        for src, url in feeds
    ]
    all_articles: List[Dict] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_feed, cat, src, url): (cat, src) for cat, src, url in tasks}
        for future in as_completed(futures):
            try:
                all_articles.extend(future.result())
            except Exception as exc:
                logging.warning("Feed fetch task failed: %s", exc)
    if all_articles:
        upsert_articles(all_articles)
        prune_articles()  # keep cache bounded to 200 articles per category
    return len(all_articles)
