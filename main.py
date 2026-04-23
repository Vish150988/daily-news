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

    init_db()

    def route_change(e):
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

    def view_pop(e):
        page.views.pop()
        page.update()

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    page.go("/")


ft.run(main)
