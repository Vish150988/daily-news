# Daily News App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cross-platform (Android & iOS) Python news reader using Flet that fetches 27 RSS feeds across 7 categories, displays them in a bold dark UI, and supports in-app reading and local bookmarks.

**Architecture:** Layered — `storage.py` handles SQLite (articles cache + bookmarks), `rss.py` fetches all feeds in parallel on launch, `reader.py` extracts clean article text via trafilatura. The `ui/` package contains one file per screen plus shared components. Flet's `page.views` stack handles navigation between Home, Article, and Bookmarks screens.

**Tech Stack:** Python 3.9+, Flet 0.25+, feedparser, trafilatura, SQLite (built-in), pytest

---

## File Map

| File | Responsibility |
|---|---|
| `main.py` | Flet entry point, route-based navigation, DB init, launch refresh |
| `storage.py` | SQLite schema, article upsert/query, bookmark add/remove/query, pruning |
| `rss.py` | FEEDS dict (27 feeds × 7 categories), parallel fetch via ThreadPoolExecutor |
| `reader.py` | Fetch + extract clean article text via trafilatura |
| `ui/__init__.py` | Empty package marker |
| `ui/components.py` | `CATEGORY_COLORS`, `CATEGORY_LABELS`, `NewsCard()`, `CategoryChip()` |
| `ui/home.py` | `HomeView` — hero card, category chips, article list, refresh |
| `ui/article.py` | `ArticleView` — clean text reader, bookmark toggle, open-in-browser fallback |
| `ui/bookmarks.py` | `BookmarksView` — saved articles list with remove, empty state |
| `tests/test_storage.py` | Unit tests for all storage functions |
| `tests/test_rss.py` | Unit tests for feed parsing (mocked feedparser) |
| `tests/test_reader.py` | Unit tests for article extraction (mocked trafilatura) |
| `requirements.txt` | Pinned runtime + dev deps |

---

## Task 1: Project Setup

**Files:**
- Create: `requirements.txt`
- Create: `ui/__init__.py`

- [ ] **Step 1: Create requirements.txt**

```
flet>=0.25.0
feedparser>=6.0.0
trafilatura>=1.9.0
pytest>=8.0.0
```

- [ ] **Step 2: Create empty package marker**

```python
# ui/__init__.py
```

- [ ] **Step 3: Install dependencies**

```bash
pip install flet feedparser trafilatura pytest
```

Expected: no errors. Verify with:
```bash
python -c "import flet, feedparser, trafilatura; print('OK')"
```
Expected output: `OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt ui/__init__.py
git commit -m "chore: project setup and dependencies"
```

---

## Task 2: Storage Layer

**Files:**
- Create: `storage.py`
- Create: `tests/test_storage.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_storage.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

SAMPLE = {
    "id": "abc123",
    "title": "Test Article",
    "url": "https://example.com/1",
    "source": "BBC News",
    "category": "world",
    "excerpt": "A short excerpt.",
    "published_at": "2026-01-01T00:00:00Z",
    "fetched_at": "2026-01-01T00:00:00Z",
}

@pytest.fixture
def db(tmp_path, monkeypatch):
    import storage
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "test.db")
    storage.init_db()
    return storage

def test_upsert_and_get_articles(db):
    db.upsert_articles([SAMPLE])
    articles = db.get_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "Test Article"

def test_get_articles_filters_by_category(db):
    db.upsert_articles([
        {**SAMPLE, "id": "1", "url": "https://ex.com/1", "category": "world"},
        {**SAMPLE, "id": "2", "url": "https://ex.com/2", "category": "tech", "source": "TechCrunch"},
    ])
    world = db.get_articles("world")
    assert len(world) == 1
    assert world[0]["category"] == "world"

def test_upsert_deduplicates_by_url(db):
    db.upsert_articles([SAMPLE])
    db.upsert_articles([{**SAMPLE, "title": "Updated Title"}])
    articles = db.get_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "Updated Title"

def test_bookmark_lifecycle(db):
    db.upsert_articles([SAMPLE])
    assert not db.is_bookmarked("abc123")
    db.add_bookmark("abc123")
    assert db.is_bookmarked("abc123")
    db.remove_bookmark("abc123")
    assert not db.is_bookmarked("abc123")

def test_get_bookmarks_returns_article_data(db):
    db.upsert_articles([SAMPLE])
    db.add_bookmark("abc123")
    bookmarks = db.get_bookmarks()
    assert len(bookmarks) == 1
    assert bookmarks[0]["title"] == "Test Article"

def test_make_article_id_is_deterministic(db):
    assert db.make_article_id("https://example.com") == db.make_article_id("https://example.com")

def test_get_article_by_id(db):
    db.upsert_articles([SAMPLE])
    article = db.get_article("abc123")
    assert article is not None
    assert article["url"] == "https://example.com/1"

def test_get_article_returns_none_for_missing(db):
    assert db.get_article("nonexistent") is None
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_storage.py -v
```
Expected: `ModuleNotFoundError` or `ImportError` (storage.py doesn't exist yet).

- [ ] **Step 3: Implement storage.py**

```python
# storage.py
import sqlite3
import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path.home() / ".daily-news" / "news.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                url TEXT UNIQUE NOT NULL,
                source TEXT NOT NULL,
                category TEXT NOT NULL,
                excerpt TEXT,
                published_at TEXT,
                fetched_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS bookmarks (
                article_id TEXT PRIMARY KEY,
                saved_at TEXT NOT NULL
            );
        """)


def make_article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def upsert_articles(articles: List[Dict]):
    with _conn() as conn:
        conn.executemany(
            """
            INSERT INTO articles (id, title, url, source, category, excerpt, published_at, fetched_at)
            VALUES (:id, :title, :url, :source, :category, :excerpt, :published_at, :fetched_at)
            ON CONFLICT(url) DO UPDATE SET
                title = excluded.title,
                excerpt = excluded.excerpt,
                published_at = excluded.published_at,
                fetched_at = excluded.fetched_at
            """,
            articles,
        )


def get_articles(category: Optional[str] = None, limit: int = 100) -> List[Dict]:
    with _conn() as conn:
        if category and category != "all":
            rows = conn.execute(
                "SELECT * FROM articles WHERE category=? ORDER BY published_at DESC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM articles ORDER BY published_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    return [dict(r) for r in rows]


def get_article(article_id: str) -> Optional[Dict]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM articles WHERE id=?", (article_id,)
        ).fetchone()
    return dict(row) if row else None


def add_bookmark(article_id: str):
    with _conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO bookmarks (article_id, saved_at) VALUES (?, ?)",
            (article_id, datetime.now(timezone.utc).isoformat()),
        )


def remove_bookmark(article_id: str):
    with _conn() as conn:
        conn.execute("DELETE FROM bookmarks WHERE article_id=?", (article_id,))


def is_bookmarked(article_id: str) -> bool:
    with _conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM bookmarks WHERE article_id=?", (article_id,)
        ).fetchone()
    return row is not None


def get_bookmarks() -> List[Dict]:
    with _conn() as conn:
        rows = conn.execute(
            """
            SELECT a.*, b.saved_at AS bookmark_saved_at
            FROM bookmarks b
            JOIN articles a ON b.article_id = a.id
            ORDER BY b.saved_at DESC
            """
        ).fetchall()
    return [dict(r) for r in rows]


def prune_articles(keep: int = 200):
    with _conn() as conn:
        categories = [r[0] for r in conn.execute(
            "SELECT DISTINCT category FROM articles"
        ).fetchall()]
        for cat in categories:
            conn.execute(
                """
                DELETE FROM articles WHERE id IN (
                    SELECT id FROM articles WHERE category=?
                    ORDER BY published_at DESC
                    LIMIT -1 OFFSET ?
                )
                """,
                (cat, keep),
            )
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_storage.py -v
```
Expected: all 8 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_storage.py
git commit -m "feat: storage layer with SQLite articles cache and bookmarks"
```

---

## Task 3: RSS Fetching Layer

**Files:**
- Create: `rss.py`
- Create: `tests/test_rss.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rss.py
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
         patch("rss.upsert_articles") as mock_upsert:
        count = fetch_all_feeds()
    assert mock_upsert.called
    assert count > 0
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_rss.py -v
```
Expected: `ModuleNotFoundError` (rss.py doesn't exist yet).

- [ ] **Step 3: Implement rss.py**

```python
# rss.py
import feedparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import List, Dict
from storage import upsert_articles, make_article_id

FEEDS: Dict[str, List[tuple]] = {
    "world": [
        ("Reuters Top News",      "http://feeds.reuters.com/reuters/topNews"),
        ("BBC News",              "http://feeds.bbci.co.uk/news/rss.xml"),
        ("New York Times",        "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),
        ("The Guardian",          "https://www.theguardian.com/world/rss"),
        ("Al Jazeera",            "http://www.aljazeera.com/xml/rss/all.xml"),
    ],
    "tech": [
        ("TechCrunch",            "https://techcrunch.com/feed/"),
        ("Wired",                 "https://www.wired.com/feed/rss"),
        ("The Verge",             "https://www.theverge.com/rss/index.xml"),
        ("MIT Technology Review", "https://www.technologyreview.com/feed/"),
    ],
    "data-ai": [
        ("Hacker News",           "https://hnrss.org/frontpage"),
        ("Ars Technica",          "http://feeds.arstechnica.com/arstechnica/index"),
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
        for entry in feed.entries[:30]:
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
    except Exception:
        return []


def fetch_all_feeds() -> int:
    tasks = [
        (cat, src, url)
        for cat, feeds in FEEDS.items()
        for src, url in feeds
    ]
    all_articles: List[Dict] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(_fetch_feed, cat, src, url): (cat, src) for cat, src, url in tasks}
        for future in as_completed(futures):
            all_articles.extend(future.result())
    if all_articles:
        upsert_articles(all_articles)
    return len(all_articles)
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_rss.py -v
```
Expected: all 5 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add rss.py tests/test_rss.py
git commit -m "feat: RSS fetching layer with 27 feeds across 7 categories"
```

---

## Task 4: Article Reader Layer

**Files:**
- Create: `reader.py`
- Create: `tests/test_reader.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_reader.py
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/test_reader.py -v
```
Expected: `ModuleNotFoundError` (reader.py doesn't exist yet).

- [ ] **Step 3: Implement reader.py**

```python
# reader.py
import trafilatura
from typing import Optional


def fetch_article_text(url: str) -> Optional[str]:
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        return trafilatura.extract(downloaded, include_comments=False, include_tables=False)
    except Exception:
        return None
```

- [ ] **Step 4: Run tests — verify they pass**

```bash
pytest tests/test_reader.py -v
```
Expected: all 4 tests PASS.

- [ ] **Step 5: Run full test suite — verify nothing broken**

```bash
pytest tests/ -v
```
Expected: all 17 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add reader.py tests/test_reader.py
git commit -m "feat: article text extraction via trafilatura"
```

---

## Task 5: Shared UI Components

**Files:**
- Create: `ui/components.py`

No unit tests — these are pure Flet UI factory functions verified by visual inspection in later tasks.

- [ ] **Step 1: Implement ui/components.py**

```python
# ui/components.py
import flet as ft
from typing import Callable, Optional, Dict

CATEGORY_COLORS: Dict[str, str] = {
    "world":       "#e63946",
    "tech":        "#f4a261",
    "data-ai":     "#a78bfa",
    "business":    "#4ade80",
    "florida":     "#38bdf8",
    "us-politics": "#fb923c",
    "long-form":   "#e879f9",
}

CATEGORY_LABELS: Dict[str, str] = {
    "world":       "World",
    "tech":        "Tech",
    "data-ai":     "Data & AI",
    "business":    "Business",
    "florida":     "Florida",
    "us-politics": "US Politics",
    "long-form":   "Long-Form",
}

# Ordered list for chip display
CATEGORIES = [("All", "all")] + [(v, k) for k, v in CATEGORY_LABELS.items()]


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#888888")


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category.title())


def NewsCard(article: Dict, on_tap: Optional[Callable] = None) -> ft.Container:
    color = category_color(article["category"])
    label = category_label(article["category"])
    pub = article.get("published_at", "")[:10]
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    f"{label} · {article['source']}",
                    size=10,
                    color=color,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    article["title"],
                    size=13,
                    color="#ffffff",
                    weight=ft.FontWeight.W_600,
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(pub, size=10, color="#888888"),
            ],
            spacing=4,
        ),
        bgcolor="#27272a",
        border_radius=8,
        padding=12,
        on_click=on_tap,
        data=article,
    )


def CategoryChip(label: str, category: str, active: bool, on_tap: Optional[Callable] = None) -> ft.Container:
    color = CATEGORY_COLORS.get(category, "#e63946")
    return ft.Container(
        content=ft.Text(
            label,
            size=11,
            color="#ffffff" if active else "#888888",
            weight=ft.FontWeight.W_600,
        ),
        bgcolor=color if active else "#27272a",
        border_radius=12,
        padding=ft.padding.symmetric(horizontal=12, vertical=4),
        on_click=on_tap,
        data=category,
    )
```

- [ ] **Step 2: Verify import is clean**

```bash
python -c "from ui.components import NewsCard, CategoryChip, CATEGORIES; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/components.py
git commit -m "feat: shared UI components (NewsCard, CategoryChip)"
```

---

## Task 6: Home Screen

**Files:**
- Create: `ui/home.py`

- [ ] **Step 1: Implement ui/home.py**

```python
# ui/home.py
import threading
import flet as ft
from typing import Callable, List, Dict

from storage import get_articles
from rss import fetch_all_feeds
from ui.components import NewsCard, CategoryChip, CATEGORIES, category_color


class HomeView(ft.View):
    def __init__(self, on_article_tap: Callable, on_bookmarks_tap: Callable):
        self._on_article_tap = on_article_tap
        self._active_category = "all"

        self._status = ft.Text("", size=10, color="#888888")
        self._hero = ft.Container()
        self._chips = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=6)
        self._list = ft.ListView(
            expand=True,
            spacing=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        self._refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color="#888888",
            icon_size=20,
            tooltip="Refresh feeds",
            on_click=lambda e: self.refresh(),
        )

        super().__init__(
            route="/",
            bgcolor="#18181b",
            padding=0,
            navigation_bar=ft.NavigationBar(
                bgcolor="#1c1c1f",
                indicator_color="#e63946",
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
                    ft.NavigationBarDestination(icon=ft.Icons.BOOKMARK_OUTLINED, label="Saved"),
                ],
                selected_index=0,
                on_change=lambda e: on_bookmarks_tap() if e.control.selected_index == 1 else None,
            ),
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Row(
                            [
                                ft.Text("Daily News", size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
                                ft.Row([self._status, self._refresh_btn], spacing=4),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        self._hero,
                        self._chips,
                    ], spacing=10),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    bgcolor="#18181b",
                ),
                self._list,
            ],
        )

    def did_mount(self):
        self._build_chips()
        self._load_cached()
        self._refresh_background()

    def _build_chips(self):
        self._chips.controls = [
            CategoryChip(label, cat, cat == self._active_category, self._on_chip_tap)
            for label, cat in CATEGORIES
        ]
        if self.page:
            self.page.update()

    def _on_chip_tap(self, e):
        self._active_category = e.control.data
        self._build_chips()
        self._load_cached()

    def _load_cached(self):
        cat = None if self._active_category == "all" else self._active_category
        articles = get_articles(cat, limit=100)
        self._render(articles)

    def _render(self, articles: List[Dict]):
        if articles:
            hero = articles[0]
            color = category_color(hero["category"])
            self._hero.content = ft.Container(
                content=ft.Column([
                    ft.Text(
                        f"TOP STORY · {hero['source'].upper()}",
                        size=9, color="rgba(255,255,255,0.75)", weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        hero["title"],
                        size=15, color="#ffffff", weight=ft.FontWeight.BOLD, max_lines=3,
                    ),
                    ft.Text(hero.get("published_at", "")[:10], size=9, color="rgba(255,255,255,0.6)"),
                ], spacing=4),
                gradient=ft.LinearGradient(
                    begin=ft.alignment.top_left,
                    end=ft.alignment.bottom_right,
                    colors=["#e63946", "#f4a261"],
                ),
                border_radius=10,
                padding=14,
                on_click=lambda e, h=hero: self._on_article_tap(h),
            )
        else:
            self._hero.content = None

        self._list.controls = [
            NewsCard(a, on_tap=lambda e: self._on_article_tap(e.control.data))
            for a in (articles[1:] if articles else [])
        ]

        if self.page:
            self.page.update()

    def _refresh_background(self):
        def _do():
            self._status.value = "↻ Refreshing"
            if self.page:
                self.page.update()
            count = fetch_all_feeds()
            self._status.value = f"{count} articles fetched" if count else "Offline"
            self._load_cached()

        threading.Thread(target=_do, daemon=True).start()

    def refresh(self):
        self._refresh_background()
```

- [ ] **Step 2: Smoke-test by running the app (desktop)**

```bash
python -c "
import flet as ft
from ui.home import HomeView
from storage import init_db
init_db()
def main(page):
    page.bgcolor = '#18181b'
    view = HomeView(on_article_tap=lambda a: print(a['title']), on_bookmarks_tap=lambda: print('bookmarks'))
    page.views.append(view)
    page.update()
ft.app(target=main)
"
```
Expected: app window opens, shows 'Daily News' header, starts fetching feeds. No Python errors in terminal.

- [ ] **Step 3: Commit**

```bash
git add ui/home.py
git commit -m "feat: home screen with hero card, category chips, and background refresh"
```

---

## Task 7: Article Reader Screen

**Files:**
- Create: `ui/article.py`

- [ ] **Step 1: Implement ui/article.py**

```python
# ui/article.py
import threading
import flet as ft

from storage import get_article, is_bookmarked, add_bookmark, remove_bookmark
from reader import fetch_article_text
from ui.components import category_color, category_label


class ArticleView(ft.View):
    def __init__(self, article_id: str):
        self._article_id = article_id
        self._content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=12,
        )

        super().__init__(
            route=f"/article/{article_id}",
            bgcolor="#18181b",
            padding=0,
            appbar=ft.AppBar(
                bgcolor="#18181b",
                color="#ffffff",
                automatically_imply_leading=True,
            ),
            controls=[
                ft.Container(
                    content=self._content,
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    expand=True,
                )
            ],
        )

    def did_mount(self):
        article = get_article(self._article_id)
        if not article:
            self._content.controls = [
                ft.Text("Article not found.", color="#888888", size=14)
            ]
            self.page.update()
            return

        color = category_color(article["category"])
        bookmarked = is_bookmarked(self._article_id)

        self.appbar.actions = [
            ft.IconButton(
                icon=ft.Icons.BOOKMARK if bookmarked else ft.Icons.BOOKMARK_BORDER,
                icon_color=color,
                tooltip="Remove bookmark" if bookmarked else "Save article",
                on_click=lambda e, a=article: self._toggle_bookmark(e, a),
            )
        ]

        self._content.controls = [
            ft.Text(
                f"{category_label(article['category'])} · {article['source']} · {article.get('published_at', '')[:10]}",
                size=11, color=color, weight=ft.FontWeight.W_600,
            ),
            ft.Text(
                article["title"],
                size=18, color="#ffffff", weight=ft.FontWeight.BOLD,
            ),
            ft.Divider(color="#333333"),
            ft.Container(
                content=ft.ProgressRing(color=color, width=24, height=24),
                alignment=ft.alignment.center,
                padding=24,
            ),
        ]
        self.page.update()

        threading.Thread(target=self._fetch_text, args=(article,), daemon=True).start()

    def _fetch_text(self, article: dict):
        text = fetch_article_text(article["url"])
        if text:
            self._content.controls[-1] = ft.Text(
                text, size=14, color="#cccccc", selectable=True,
            )
        else:
            self._content.controls[-1] = ft.Column([
                ft.Text(
                    article.get("excerpt", "No preview available."),
                    size=14, color="#cccccc",
                ),
                ft.Container(height=16),
                ft.ElevatedButton(
                    "Open in Browser ↗",
                    bgcolor="#27272a",
                    color="#ffffff",
                    on_click=lambda e: self.page.launch_url(article["url"]),
                ),
            ], spacing=0)
        self.page.update()

    def _toggle_bookmark(self, e, article: dict):
        currently = is_bookmarked(self._article_id)
        if currently:
            remove_bookmark(self._article_id)
        else:
            add_bookmark(self._article_id)
        e.control.icon = ft.Icons.BOOKMARK_BORDER if currently else ft.Icons.BOOKMARK
        self.page.update()
```

- [ ] **Step 2: Verify import is clean**

```bash
python -c "from ui.article import ArticleView; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/article.py
git commit -m "feat: article reader screen with trafilatura extraction and bookmark toggle"
```

---

## Task 8: Bookmarks Screen

**Files:**
- Create: `ui/bookmarks.py`

- [ ] **Step 1: Implement ui/bookmarks.py**

```python
# ui/bookmarks.py
import flet as ft
from typing import Callable

from storage import get_bookmarks, remove_bookmark
from ui.components import NewsCard


class BookmarksView(ft.View):
    def __init__(self, on_article_tap: Callable):
        self._on_article_tap = on_article_tap
        self._list = ft.ListView(
            expand=True,
            spacing=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        super().__init__(
            route="/bookmarks",
            bgcolor="#18181b",
            padding=0,
            appbar=ft.AppBar(
                title=ft.Text("Saved", color="#ffffff", weight=ft.FontWeight.BOLD, size=20),
                bgcolor="#18181b",
                color="#ffffff",
                automatically_imply_leading=False,
            ),
            navigation_bar=ft.NavigationBar(
                bgcolor="#1c1c1f",
                indicator_color="#e63946",
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.HOME_OUTLINED, label="Home"),
                    ft.NavigationBarDestination(icon=ft.Icons.BOOKMARK, label="Saved"),
                ],
                selected_index=1,
                on_change=lambda e: self.page.go("/") if e.control.selected_index == 0 else None,
            ),
            controls=[self._list],
        )

    def did_mount(self):
        self._load()

    def _load(self):
        bookmarks = get_bookmarks()
        if not bookmarks:
            self._list.controls = [
                ft.Container(
                    content=ft.Column([
                        ft.Icon(ft.Icons.BOOKMARK_BORDER, size=52, color="#444444"),
                        ft.Text("No saved articles yet.", color="#888888", size=14),
                    ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                    alignment=ft.alignment.center,
                    expand=True,
                    padding=60,
                )
            ]
        else:
            self._list.controls = [
                self._make_row(article) for article in bookmarks
            ]
        if self.page:
            self.page.update()

    def _make_row(self, article: dict) -> ft.Stack:
        return ft.Stack([
            NewsCard(article, on_tap=lambda e: self._on_article_tap(e.control.data)),
            ft.Container(
                content=ft.IconButton(
                    icon=ft.Icons.CLOSE,
                    icon_color="#e63946",
                    icon_size=16,
                    tooltip="Remove bookmark",
                    on_click=lambda e, aid=article["id"]: self._remove(aid),
                ),
                right=4,
                top=4,
            ),
        ])

    def _remove(self, article_id: str):
        remove_bookmark(article_id)
        self._load()
```

- [ ] **Step 2: Verify import is clean**

```bash
python -c "from ui.bookmarks import BookmarksView; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add ui/bookmarks.py
git commit -m "feat: bookmarks screen with remove and empty state"
```

---

## Task 9: Main Entry Point & Navigation

**Files:**
- Create: `main.py`

- [ ] **Step 1: Implement main.py**

```python
# main.py
import flet as ft

from storage import init_db
from ui.home import HomeView
from ui.article import ArticleView
from ui.bookmarks import BookmarksView


def main(page: ft.Page):
    page.title = "Daily News"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#18181b"
    page.padding = 0
    page.fonts = {}

    init_db()

    def route_change(e: ft.RouteChangeEvent):
        page.views.clear()

        home = HomeView(
            on_article_tap=lambda article: page.go(f"/article/{article['id']}"),
            on_bookmarks_tap=lambda: page.go("/bookmarks"),
        )
        page.views.append(home)

        route = page.route
        if route == "/bookmarks":
            page.views.append(
                BookmarksView(
                    on_article_tap=lambda article: page.go(f"/article/{article['id']}"),
                )
            )
        elif route.startswith("/article/"):
            article_id = route[len("/article/"):]
            page.views.append(ArticleView(article_id=article_id))

        page.update()

    def view_pop(e: ft.ViewPopEvent):
        page.views.pop()
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/")


ft.app(target=main)
```

- [ ] **Step 2: Run the app on desktop**

```bash
python main.py
```
Expected: app launches, shows home screen with "Daily News" title, starts loading feeds in background. Category chips appear. No errors in terminal.

- [ ] **Step 3: Manual test — browse and read**

1. Wait for feeds to finish loading (status text updates)
2. Tap a category chip — list filters to that category
3. Tap an article — reader screen opens, shows loading spinner, then article text
4. Tap bookmark icon — icon fills solid
5. Press back — returns to home

Expected: all of the above work without errors.

- [ ] **Step 4: Manual test — bookmarks**

1. Bookmark 2+ articles
2. Tap "Saved" in bottom nav — bookmarks screen shows saved articles
3. Tap × on one article — it disappears from the list
4. Tap an article in bookmarks — reader opens correctly

Expected: all of the above work without errors.

- [ ] **Step 5: Manual test — offline behavior**

1. Disable network (or unplug Wi-Fi)
2. Restart the app
3. Verify: cached articles still show, status shows "Offline"
4. Re-enable network, tap refresh (or restart app) — articles update

- [ ] **Step 6: Run full test suite one final time**

```bash
pytest tests/ -v
```
Expected: all 17 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add main.py
git commit -m "feat: main entry point with Flet routing and navigation"
```

---

## Task 10: Mobile Build (Optional — do after desktop testing passes)

- [ ] **Step 1: Install Flet CLI build tools**

```bash
pip install flet[build]
```

- [ ] **Step 2: Build Android APK**

```bash
flet build apk
```
Expected: `build/apk/app-release.apk` created. Time: 5–15 minutes on first build.

- [ ] **Step 3: Install on Android device or emulator**

```bash
adb install build/apk/app-release.apk
```

- [ ] **Step 4: Build iOS IPA (macOS only)**

```bash
flet build ipa
```
Expected: `build/ipa/` directory created. Requires Xcode installed.

- [ ] **Step 5: Commit build artifacts exclusion**

```bash
echo "build/" >> .gitignore
echo "__pycache__/" >> .gitignore
echo ".daily-news/" >> .gitignore
echo ".superpowers/" >> .gitignore
git add .gitignore
git commit -m "chore: add .gitignore for build artifacts"
```
