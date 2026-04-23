# main.py
import sys
import traceback
from pathlib import Path

# Vendor pure-Python deps for mobile builds (certifi, feedparser, sgmllib)
_vendor = Path(__file__).parent / "vendor"
if str(_vendor) not in sys.path:
    sys.path.insert(0, str(_vendor))

import flet as ft

import theme
from storage import init_db
from ui.home import HomeView
from ui.article import ArticleView
from ui.bookmarks import BookmarksView


def main(page: ft.Page):
    try:
        page.title = "Daily News"
        page.theme_mode = ft.ThemeMode.DARK
        page.bgcolor = theme.color("page_bg")
        page.padding = 0

        init_db()

        # Root container that hosts the current view content.
        # We avoid page.views because ft.View stacks are known to render
        # as blank screens in flet build apk (issue #2363).
        content = ft.Container(expand=True, bgcolor=theme.color("page_bg"))

        # Track current article for theme-toggle rebuilds
        _current_article_id: str = ""

        def show_view(view):
            if content.content is view:
                return
            content.content = view
            page.update()
            if hasattr(view, "did_mount"):
                view.did_mount()

        def on_nav_change(e):
            if e.control.selected_index == 0:
                show_view(home)
            elif e.control.selected_index == 1:
                show_view(bookmarks_view)

        # Single static navigation bar – never replaced, only updated.
        # Dynamic replacement of page.navigation_bar inside event handlers
        # caused taps to be swallowed on Android.
        nav_bar = ft.NavigationBar(
            bgcolor=theme.color("nav_bg"),
            indicator_color="#e63946",
            destinations=[
                ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
                ft.NavigationBarDestination(
                    icon=ft.Icons.BOOKMARK_OUTLINED, label="Saved"
                ),
            ],
            selected_index=0,
            on_change=on_nav_change,
        )
        page.navigation_bar = nav_bar

        def push_article(article: dict):
            nonlocal _current_article_id
            _current_article_id = article["id"]
            show_view(ArticleView(article_id=article["id"], on_back=_go_home))

        def _go_home():
            nav_bar.selected_index = 0
            show_view(home)

        def _go_bookmarks():
            nav_bar.visible = True
            nav_bar.selected_index = 1
            show_view(bookmarks_view)

        def toggle_theme():
            new_mode = theme.toggle()
            page.theme_mode = (
                ft.ThemeMode.LIGHT if new_mode == "light" else ft.ThemeMode.DARK
            )
            page.bgcolor = theme.color("page_bg")
            content.bgcolor = theme.color("page_bg")
            nav_bar.bgcolor = theme.color("nav_bg")

            # Rebuild the current view so it picks up new theme colors
            current = content.content
            content.content = None
            page.update()

            if isinstance(current, HomeView):
                new_view = HomeView(
                    on_article_tap=push_article, on_theme_toggle=toggle_theme
                )
            elif isinstance(current, BookmarksView):
                new_view = BookmarksView(
                    on_article_tap=push_article, on_go_home=_go_home
                )
            elif isinstance(current, ArticleView) and _current_article_id:
                new_view = ArticleView(
                    article_id=_current_article_id, on_back=_go_home
                )
            else:
                new_view = home

            content.content = new_view
            page.update()
            if hasattr(new_view, "did_mount"):
                new_view.did_mount()

        home = HomeView(on_article_tap=push_article, on_theme_toggle=toggle_theme)
        bookmarks_view = BookmarksView(
            on_article_tap=push_article,
            on_go_home=_go_home,
        )

        page.controls.append(content)
        page.update()
        show_view(home)

    except Exception as exc:
        page.controls.clear()
        page.add(
            ft.Column(
                [
                    ft.Text(
                        "Startup error",
                        size=18,
                        color="#e63946",
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Text(str(exc), color=theme.color("text_primary"), selectable=True),
                    ft.Text(
                        traceback.format_exc(),
                        color=theme.color("text_muted"),
                        size=10,
                        selectable=True,
                    ),
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        page.update()


ft.run(main)
