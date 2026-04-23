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
