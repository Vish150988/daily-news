# ui/article.py
import threading
import flet as ft
from typing import Callable, Optional

from storage import get_article, is_bookmarked, add_bookmark, remove_bookmark
from reader import fetch_article_text
from ui.components import category_color, category_label


class ArticleView(ft.Column):
    def __init__(self, article_id: str, on_back: Optional[Callable] = None):
        self._article_id = article_id
        self._on_back = on_back
        self._content = ft.Column(
            scroll=ft.ScrollMode.AUTO,
            expand=True,
            spacing=12,
        )

        self._bookmark_btn = ft.IconButton(
            icon=ft.Icons.BOOKMARK_BORDER,
            icon_color="#ffffff",
        )

        # Inline header instead of page.appbar – page.appbar dynamic updates
        # are unreliable on Android packaged builds.
        self._header = ft.Container(
            content=ft.Row(
                [
                    ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        icon_color="#ffffff",
                        on_click=lambda e: on_back() if on_back else None,
                    ),
                    ft.Container(expand=True),
                    self._bookmark_btn,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            padding=ft.padding.symmetric(horizontal=8, vertical=8),
            bgcolor="#18181b",
        )

        super().__init__(
            expand=True,
            controls=[
                self._header,
                ft.Divider(color="#333333"),
                ft.Container(
                    content=self._content,
                    padding=ft.padding.symmetric(horizontal=16, vertical=8),
                    expand=True,
                ),
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

        self._bookmark_btn.icon = (
            ft.Icons.BOOKMARK if bookmarked else ft.Icons.BOOKMARK_BORDER
        )
        self._bookmark_btn.icon_color = color
        self._bookmark_btn.tooltip = (
            "Remove bookmark" if bookmarked else "Save article"
        )
        self._bookmark_btn.on_click = lambda e: self._toggle_bookmark()

        self._content.controls = [
            ft.Text(
                f"{category_label(article['category'])} · {article['source']} · {article.get('published_at', '')[:10]}",
                size=11,
                color=color,
                weight=ft.FontWeight.W_600,
            ),
            ft.Text(
                article["title"],
                size=18,
                color="#ffffff",
                weight=ft.FontWeight.BOLD,
            ),
            ft.Divider(color="#333333"),
            ft.Container(
                content=ft.ProgressRing(color=color, width=24, height=24),
                alignment=ft.Alignment(0, 0),
                padding=24,
            ),
        ]
        self.page.update()

        threading.Thread(target=self._fetch_text, args=(article,), daemon=True).start()

    def _fetch_text(self, article: dict):
        text = fetch_article_text(article["url"])
        if not self.page:  # view was popped while fetching
            return
        if text:
            self._content.controls[-1] = ft.Text(
                text, size=14, color="#cccccc", selectable=True,
            )
        else:
            self._content.controls[-1] = ft.Column(
                [
                    ft.Text(
                        article.get("excerpt", "No preview available."),
                        size=14,
                        color="#cccccc",
                    ),
                    ft.Container(height=16),
                    ft.ElevatedButton(
                        "Open in Browser ↗",
                        bgcolor="#27272a",
                        color="#ffffff",
                        on_click=lambda e: self._open_browser(article["url"]),
                    ),
                ],
                spacing=0,
            )
        self.page.update()

    def _open_browser(self, url: str):
        """Try to open URL in browser; fallback to clipboard + snackbar."""
        try:
            self.page.launch_url(url)
        except Exception:
            pass
        try:
            self.page.set_clipboard(url)
            self.page.open(
                ft.SnackBar(
                    content=ft.Text("Opening browser… URL copied to clipboard")
                )
            )
        except Exception:
            pass

    def _toggle_bookmark(self):
        currently = is_bookmarked(self._article_id)
        if currently:
            remove_bookmark(self._article_id)
        else:
            add_bookmark(self._article_id)
        self._bookmark_btn.icon = (
            ft.Icons.BOOKMARK_BORDER if currently else ft.Icons.BOOKMARK
        )
        self.page.update()
