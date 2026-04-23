import sqlite3
import hashlib
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

# Use the app directory (next to main.py) so the path is writable on Android
# where Path.home() resolves to /data and PermissionError is raised.
DB_PATH = Path(__file__).parent / ".daily-news" / "news.db"


def _conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with closing(_conn()) as conn:
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


# Upsert with first-write-wins for source and category: these fields are intentionally
# omitted from the ON CONFLICT UPDATE clause to preserve the original feed provenance.
def upsert_articles(articles: List[Dict]):
    with closing(_conn()) as conn:
        with conn:
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
    with closing(_conn()) as conn:
        with conn:
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
    with closing(_conn()) as conn:
        with conn:
            row = conn.execute(
                "SELECT * FROM articles WHERE id=?", (article_id,)
            ).fetchone()
    return dict(row) if row else None


def add_bookmark(article_id: str):
    with closing(_conn()) as conn:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO bookmarks (article_id, saved_at) VALUES (?, ?)",
                (article_id, datetime.now(timezone.utc).isoformat()),
            )


def remove_bookmark(article_id: str):
    with closing(_conn()) as conn:
        with conn:
            conn.execute("DELETE FROM bookmarks WHERE article_id=?", (article_id,))


def is_bookmarked(article_id: str) -> bool:
    with closing(_conn()) as conn:
        with conn:
            row = conn.execute(
                "SELECT 1 FROM bookmarks WHERE article_id=?", (article_id,)
            ).fetchone()
    return row is not None


def get_bookmarks() -> List[Dict]:
    with closing(_conn()) as conn:
        with conn:
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
    with closing(_conn()) as conn:
        with conn:
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
