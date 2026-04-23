# main.py
import sys
from pathlib import Path

# Vendor pure-Python deps for mobile builds (certifi, feedparser, sgmllib)
_vendor = Path(__file__).parent / "vendor"
if str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))

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

    init_db()

    def push_view(view: ft.View):
        page.views.append(view)
        page.update()
        view.did_mount()

    def push_article(article: dict):
        push_view(ArticleView(article_id=article["id"]))

    def push_bookmarks():
        push_view(BookmarksView(
            on_article_tap=push_article,
            on_go_home=pop_view,
        ))

    def pop_view():
        if len(page.views) > 1:
            page.views.pop()
            page.update()

    def view_pop(e):
        pop_view()

    page.on_view_pop = view_pop

    home = HomeView(
        on_article_tap=push_article,
        on_bookmarks_tap=push_bookmarks,
    )
    page.views.append(home)
    page.update()
    home.did_mount()


ft.run(main)
