# ui/home.py
import threading
import flet as ft
from typing import Callable, List, Dict

from storage import get_articles
from rss import fetch_all_feeds
from ui.components import NewsCard, CategoryChip, CATEGORIES, category_color


class HomeView(ft.View):
    def __init__(self, on_article_tap: Callable, on_bookmarks_tap: Callable):
        self._on_article_tap = on_article_tap
        self._active_category = "all"

        self._status = ft.Text("", size=10, color="#888888")
        self._hero = ft.Container()
        self._chips = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=6)
        self._list = ft.ListView(
            expand=True,
            spacing=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=8),
        )

        self._refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color="#888888",
            icon_size=20,
            tooltip="Refresh feeds",
            on_click=lambda e: self.refresh(),
        )

        super().__init__(
            route="/",
            bgcolor="#18181b",
            padding=0,
            navigation_bar=ft.NavigationBar(
                bgcolor="#1c1c1f",
                indicator_color="#e63946",
                destinations=[
                    ft.NavigationBarDestination(icon=ft.Icons.HOME, label="Home"),
                    ft.NavigationBarDestination(icon=ft.Icons.BOOKMARK_OUTLINED, label="Saved"),
                ],
                selected_index=0,
                on_change=lambda e: on_bookmarks_tap() if e.control.selected_index == 1 else None,
            ),
            controls=[
                ft.Container(
                    content=ft.Column([
                        ft.Row(
                            [
                                ft.Text("Daily News", size=22, weight=ft.FontWeight.BOLD, color="#ffffff"),
                                ft.Row([self._status, self._refresh_btn], spacing=4),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        self._hero,
                        self._chips,
                    ], spacing=10),
                    padding=ft.padding.symmetric(horizontal=12, vertical=10),
                    bgcolor="#18181b",
                ),
                self._list,
            ],
        )

    def did_mount(self):
        self._build_chips()
        self._load_cached()
        self._refresh_background()

    def _build_chips(self):
        self._chips.controls = [
            CategoryChip(label, cat, cat == self._active_category, self._on_chip_tap)
            for label, cat in CATEGORIES
        ]
        if self.page:
            self.page.update()

    def _on_chip_tap(self, e):
        self._active_category = e.control.data
        self._build_chips()
        self._load_cached()

    def _load_cached(self):
        cat = None if self._active_category == "all" else self._active_category
        articles = get_articles(cat, limit=100)
        self._render(articles)

    def _render(self, articles: List[Dict]):
        if articles:
            hero = articles[0]
            self._hero.content = ft.Container(
                content=ft.Column([
                    ft.Text(
                        f"TOP STORY · {hero['source'].upper()}",
                        size=9, color="rgba(255,255,255,0.75)", weight=ft.FontWeight.W_600,
                    ),
                    ft.Text(
                        hero["title"],
                        size=15, color="#ffffff", weight=ft.FontWeight.BOLD, max_lines=3,
                    ),
                    ft.Text(hero.get("published_at", "")[:10], size=9, color="rgba(255,255,255,0.6)"),
                ], spacing=4),
                gradient=ft.LinearGradient(
                    begin=ft.Alignment(-1, -1),
                    end=ft.Alignment(1, 1),
                    colors=["#e63946", "#f4a261"],
                ),
                border_radius=10,
                padding=14,
                on_click=lambda e, h=hero: self._on_article_tap(h),
            )
        else:
            self._hero.content = None

        self._list.controls = [
            NewsCard(a, on_tap=lambda e: self._on_article_tap(e.control.data))
            for a in (articles[1:] if articles else [])
        ]

        if self.page:
            self.page.update()

    def _refresh_background(self):
        def _do():
            self._status.value = "↻ Refreshing"
            if self.page:
                self.page.update()
            count = fetch_all_feeds()
            self._status.value = f"{count} articles fetched" if count else "Offline"
            self._load_cached()

        threading.Thread(target=_do, daemon=True).start()

    def refresh(self):
        self._refresh_background()
