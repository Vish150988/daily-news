# Daily News App — Design Spec

**Date:** 2026-04-22  
**Framework:** Flet (Python + Flutter rendering)  
**Platforms:** Android & iOS  

---

## Overview

A cross-platform mobile news reader built with Python and Flet. Aggregates RSS feeds across three categories (World, Tech, Business), displays them in a bold dark-themed UI with colorful category accents, and lets users read articles in a clean in-app reader and bookmark them locally.

---

## Features

| Feature | Description |
|---|---|
| Browse headlines | Home screen with hero top story + article list |
| Category filter | Filter by All / World / Tech / Business |
| In-app reader | Strips article to clean text via trafilatura |
| Bookmarks | Save/remove articles, persisted in SQLite |
| Background refresh | RSS feeds refresh in background on launch |
| Offline support | Cached articles shown when network is unavailable |

---

## RSS Feed Sources

### World News
- Reuters Top News: `http://feeds.reuters.com/reuters/topNews`
- BBC News: `http://feeds.bbci.co.uk/news/rss.xml`
- New York Times: `https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml`
- The Guardian: `https://www.theguardian.com/world/rss`
- Al Jazeera: `http://www.aljazeera.com/xml/rss/all.xml`

### Technology & Science
- TechCrunch: `https://techcrunch.com/feed/`
- Wired: `https://www.wired.com/feed/rss`
- The Verge: `https://www.theverge.com/rss/index.xml`
- MIT Technology Review: `https://www.technologyreview.com/feed/`

### Business & Finance
- Wall Street Journal Markets: `https://feeds.a.dj.com/rss/RSSMarketsMain.xml`
- CNBC Top News: `https://search.cnbc.com/rs/search/combinedcms/view.xml?id=100003114`
- Fortune: `https://fortune.com/feed/`

---

## Project Structure

```
daily-news/
  main.py           # Flet entry point, wires up navigation
  rss.py            # Fetch + parse RSS feeds (feedparser)
  storage.py        # SQLite: articles cache + bookmarks
  reader.py         # Fetch full article text (trafilatura)
  ui/
    home.py         # Home screen (hero card + category chips + article list)
    article.py      # Reader screen (clean text view)
    bookmarks.py    # Bookmarks screen (saved articles list)
    components.py   # Shared: NewsCard, CategoryChip
  requirements.txt
```

---

## Screens

### Home Screen
- Top section: hero card showing the latest top story (gradient red→orange)
- Category chips row: All / World / Tech / Business (filters the list below)
- Article list: `NewsCard` components showing category color, source, headline, time
- Bottom nav: Home | Saved

### Article Reader Screen
- Back button (top left) + Bookmark button (top right)
- Category label + source + timestamp
- Full article text stripped to clean prose via `trafilatura`
- Fallback: RSS excerpt + "Open in Browser" button if extraction fails

### Bookmarks Screen
- List of saved articles using the same `NewsCard` style
- Remove button per article
- Empty state message when no bookmarks saved
- Bottom nav: Home | Saved

---

## Visual Design

**Theme:** Bold & Vibrant — dark base (`#18181b`) with colorful per-category accents

| Category | Accent color |
|---|---|
| World | `#e63946` (red) |
| Tech | `#f4a261` (orange) |
| Business | `#4ade80` (green) |

- Hero card: gradient from World red → Tech orange
- Article cards: dark card (`#27272a`) with category-colored label
- Typography: bold white headlines, muted gray metadata

---

## Data Flow

1. **App launch** → `storage.py` reads cached articles from SQLite → Home renders immediately
2. **Background thread** → `rss.py` fetches all 12 feeds in parallel (ThreadPoolExecutor) → deduplicates by URL → upserts into SQLite → triggers UI refresh
3. **Article tap** → `reader.py` calls `trafilatura.fetch_url()` + `trafilatura.extract()` → Reader screen renders clean text
4. **Bookmark tap** → `storage.py` inserts or deletes from `bookmarks` table → Bookmarks screen refreshes

---

## Storage (SQLite)

### `articles` table
| Column | Type | Notes |
|---|---|---|
| id | TEXT PRIMARY KEY | MD5 of URL |
| title | TEXT | |
| url | TEXT UNIQUE | |
| source | TEXT | e.g. "BBC News" |
| category | TEXT | world / tech / business |
| excerpt | TEXT | From RSS description |
| published_at | TEXT | ISO 8601 |
| fetched_at | TEXT | ISO 8601 |

### `bookmarks` table
| Column | Type | Notes |
|---|---|---|
| article_id | TEXT | FK → articles.id |
| saved_at | TEXT | ISO 8601 |

Articles cache is pruned to the 200 most recent per category on each refresh.

---

## Error Handling

| Scenario | Behavior |
|---|---|
| RSS fetch fails | Show cached articles, display subtle "Offline" chip in header |
| All feeds fail, no cache | Empty state with "No articles" message + Retry button |
| Article text extraction fails | Show RSS excerpt, display "Open in Browser" button |
| SQLite error | Log error, degrade gracefully (no crash) |

---

## Dependencies

```
flet>=0.25.0
feedparser>=6.0.0
trafilatura>=1.9.0
```

`sqlite3` is built into Python — no install needed.

---

## Testing Approach

- **Unit tests** for `rss.py` (parse known feed XML) and `storage.py` (insert/query/delete)
- **Manual testing** on Android emulator (via `flet run --android`) and iOS simulator (`flet run --ios`)
- Verify offline behavior by toggling airplane mode after first load
- Verify reader mode on articles from each source

---

## Out of Scope (v1)

- User accounts or cloud sync
- Push notifications
- Search
- Dark/light mode toggle (dark only)
- Article sharing
