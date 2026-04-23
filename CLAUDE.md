# Daily News — Project Documentation

Cross-platform news reader built with **Python + Flet 0.84.0**. Runs on desktop (`flet run`) and Android (`flet build apk`).

**Repo:** https://github.com/Vish150988/daily-news  
**CI:** GitHub Actions `.github/workflows/build-apk.yml` builds APK on every push to `master`.

---

## Quick Start

### Local desktop dev
```bash
cd daily-news
flet run main.py
```

### Build Android APK (CI does this automatically)
```bash
flet build apk \
  --project "Daily News" \
  --org com.dailynews \
  --build-number 1 \
  --verbose \
  --yes
```

---

## Architecture

```
main.py          → Entry point. Theme toggle, nav bar, view routing.
├── ui/home.py   → HomeView (ft.Column). Hero card, category chips, article list.
├── ui/article.py→ ArticleView (ft.Column). Inline header, paragraph rendering.
├── ui/bookmarks.py → BookmarksView (ft.Column). Saved articles list.
├── ui/components.py → NewsCard, CategoryChip factories.
├── rss.py       → Feed fetching. 27 feeds, ThreadPoolExecutor(max_workers=10).
├── reader.py    → Article text extraction (4-tier fallback).
├── storage.py   → SQLite persistence. articles + bookmarks tables.
└── theme.py     → Dark/light theme color definitions.
```

### Why `ft.Column` instead of `ft.View`?

`ft.View` + `page.views` stack causes **blank screens** in `flet build apk` (flet-dev/flet#2363). We bypass the routing system entirely and swap a root `ft.Container(content=...)` directly.

### Navigation model

- **Single static `page.navigation_bar`** — never replaced, only `selected_index` updated.
- Dynamic replacement of `page.navigation_bar` inside event handlers caused taps to be swallowed on Android.
- `page.appbar` is also avoided; each view uses an **inline header row** instead.

---

## Key Design Decisions

### Article Extraction (4-tier fallback)

| Tier | Method | When |
|------|--------|------|
| 1 | `trafilatura` | Desktop only (requires `lxml`) |
| 2 | **boilerpy3** | Mobile primary — pure Python, no API dependency, vendored in `vendor/boilerpy3/` |
| 3 | Jina AI Reader API | Fallback if boilerpy3 fails |
| 4 | stdlib regex | Final offline fallback |

**boilerpy3** is a pure-Python port of Boilerpipe. It analyzes HTML DOM structure to find the main content block — far more accurate than regex stripping. Vendored to avoid pip resolution failures on ARM64.

### Dependency Vendoring Strategy

Some packages fail to install during `flet build apk` because pip can't resolve them for ARM64 or they have C extensions. We vendor pure-Python packages into `vendor/`:

| Package | Vendored? | Reason |
|---------|-----------|--------|
| `feedparser` | ✅ `vendor/feedparser/` | Complex deps, pip resolution failure |
| `sgmllib3k` | ✅ `vendor/sgmllib.py` | feedparser dependency |
| `boilerpy3` | ✅ `vendor/boilerpy3/` | No deps, but vendored for safety |
| `certifi` | ✅ project root | Flet Android bootstrap imports `certifi` before `main.py` runs |
| `flet` | ❌ `requirements.txt` | Build environment handles mobile mapping automatically |
| `trafilatura` | ❌ (optional) | Requires `lxml` — no ARM64 wheels |

### SQLite DB Path

```python
# storage.py
DB_PATH = Path(__file__).parent / ".daily-news" / "news.db"
```

`Path.home()` returns `/data` on Android (not writable). Using `__file__` puts the DB in the app's private files directory.

### Theme System

- `theme.py` defines color palettes for **dark** and **light** modes.
- All views call `theme.color("key")` instead of hardcoded hex values.
- Toggling theme rebuilds the current view so colors update immediately.

### Refresh Throttle

Background RSS fetch has a **5-minute throttle** (`_last_refresh`) to prevent unbounded thread accumulation. **Manual refresh bypasses the throttle** by resetting `_last_refresh = 0`.

---

## File Structure

```
daily-news/
├── main.py                      # App entry point
├── theme.py                     # Dark/light color definitions
├── requirements.txt             # Runtime deps (only flet==0.84.0)
├── storage.py                   # SQLite layer
├── rss.py                       # RSS feed fetching
├── reader.py                    # Article text extraction
├── certifi/                     # CA bundle (must be at project root)
├── vendor/
│   ├── feedparser/              # Vendored feedparser 6.0.12
│   ├── sgmllib.py               # feedparser dependency
│   └── boilerpy3/               # Vendored boilerpy3 1.0.7
├── ui/
│   ├── __init__.py
│   ├── components.py            # NewsCard, CategoryChip
│   ├── home.py                  # HomeView
│   ├── article.py               # ArticleView
│   └── bookmarks.py             # BookmarksView
├── tests/
│   ├── test_reader.py
│   ├── test_rss.py
│   └── test_storage.py
├── .github/
│   └── workflows/
│       └── build-apk.yml        # CI workflow
└── CLAUDE.md                    # This file
```

---

## CI / Build Notes

### Workflow file
- **Runner:** `ubuntu-latest`
- **Java:** 17 (temurin)
- **Python:** 3.12
- **Flet version:** 0.84.0
- **Critical flag:** `--yes` (auto-confirms Flutter SDK installation in non-interactive runner)
- **Cache:** `~/.flet` for Flutter SDK

### Known build pitfalls

1. **Do NOT pre-install Flutter** via `subosito/flutter-action`. Flet 0.84.0 manages its own Flutter version internally. Pre-installing a different Flutter causes version incompatibility.
2. **Do NOT put `trafilatura` or `lxml` in `requirements.txt`** — no ARM64 wheels exist.
3. **`certifi` must be at project root** — Flet's Android bootstrap imports `certifi` before `main.py` executes.
4. **PowerShell `>>` appends UTF-16LE** — never use `echo "..." >> file` on workflow files. It corrupts YAML encoding and GitHub Actions fails with "workflow file issue".

---

## Flet 0.84.0 Gotchas

| Issue | Solution |
|-------|----------|
| `ft.app(target=main)` deprecated | Use `ft.run(main)` |
| `page.go()` doesn't trigger `on_route_change` | Bypass routing; manage views manually |
| `ft.alignment.center` doesn't exist | Use `ft.Alignment(0, 0)` |
| `ft.padding.symmetric()` deprecated | Use `ft.Padding.symmetric(...)` |
| `page.views` blank in packaged builds | Use `page.controls` + root `Container` instead |
| `page.appbar` dynamic updates unreliable on mobile | Use inline header rows inside views |
| `page.navigation_bar` replacement swallows taps | Use single static nav bar, update `selected_index` |
| `SafeArea` can hide children on some devices | Use plain `Container` with explicit top padding instead |

---

## Known Issues & Future Work

### Open
- **Performance:** Home screen still re-renders all 30 cards on every category switch. Could virtualize with lazy loading.
- **Images:** No thumbnail images in article cards. RSS feeds provide `media_content` — could extract and display.
- **Offline mode:** If RSS fetch fails, only cached articles are shown. Could show a "last updated" timestamp.
- **Search:** No search functionality across articles.
- **Push notifications:** No background refresh when app is closed.

### Resolved
- ✅ Blank screen on APK launch — fixed by avoiding `page.views`
- ✅ `PermissionError` on Android — fixed by using `Path(__file__).parent` for DB
- ✅ Back button not working — fixed by using inline header instead of `page.appbar`
- ✅ Bookmarks nav not working — fixed by using static `page.navigation_bar`
- ✅ Article extraction quality — fixed by adding boilerpy3
- ✅ `<p>` tags in extracted text — fixed by stripping HTML tags in post-processing
- ✅ Refresh button not working — fixed by bypassing throttle on manual refresh

---

## Testing

```bash
python -m pytest tests/ -v
```

17 tests covering reader extraction, RSS fetching, and SQLite storage.

---

*Last updated: 2026-04-23*
