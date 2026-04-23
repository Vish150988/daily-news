# ui/bookmarks.py
import flet as ft
from typing import Callable

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
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        self.appbar = ft.AppBar(
            title=ft.Text(
                "Saved", color="#ffffff", weight=ft.FontWeight.BOLD, size=20
            ),
            bgcolor="#18181b",
            color="#ffffff",
            automatically_imply_leading=False,
        )

        self.navigation_bar = ft.NavigationBar(
            bgcolor="#1c1c1f",
            indicator_color="#e63946",
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.HOME_OUTLINED, label="Home"
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.BOOKMARK, label="Saved"
                ),
            ],
            selected_index=1,
            on_change=lambda e: self._on_go_home()
            if e.control.selected_index == 0 and self._on_go_home
            else None,
        )

        super().__init__(
            expand=True,
            controls=[self._list],
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
                                color="#444444",
                            ),
                            ft.Text(
                                "No saved articles yet.",
                                color="#888888",
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
