# ui/bookmarks.py
import flet as ft
from typing import Callable

import theme
from storage import get_bookmarks, remove_bookmark
from ui.components import NewsCard


class BookmarksView(ft.Column):
    def __init__(
        self, on_article_tap: Callable, on_go_home: Callable = None
    ):
        self._on_article_tap = on_article_tap
        self._on_go_home = on_go_home
        self._list = ft.ListView(
            expand=True,
            spacing=8,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

        # Inline header instead of page.appbar
        header = ft.Container(
            content=ft.Text(
                "Saved", color=theme.color("text_primary"), weight=ft.FontWeight.BOLD, size=20
            ),
            padding=ft.Padding.symmetric(horizontal=16, vertical=16),
            bgcolor=theme.color("header_bg"),
        )

        super().__init__(
            expand=True,
            controls=[header, self._list],
        )

    def did_mount(self):
        self._load()

    def _load(self):
        bookmarks = get_bookmarks()
        if not bookmarks:
            self._list.controls = [
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(
                                ft.Icons.BOOKMARK_BORDER,
                                size=52,
                                color=theme.color("text_muted"),
                            ),
                            ft.Text(
                                "No saved articles yet.",
                                color=theme.color("text_muted"),
                                size=14,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                    ),
                    alignment=ft.Alignment(0, 0),
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
        return ft.Stack(
            controls=[
                NewsCard(
                    article,
                    on_tap=lambda e: self._on_article_tap(e.control.data),
                ),
                ft.Container(
                    content=ft.IconButton(
                        icon=ft.Icons.CLOSE,
                        icon_color="#e63946",
                        icon_size=16,
                        tooltip="Remove bookmark",
                        on_click=lambda e, aid=article["id"]: self._remove(
                            aid
                        ),
                    ),
                    right=4,
                    top=4,
                ),
            ]
        )

    def _remove(self, article_id: str):
        remove_bookmark(article_id)
        self._load()
