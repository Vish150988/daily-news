# ui/home.py
import threading
from datetime import datetime, timezone
import flet as ft
from typing import Callable, List, Dict

import theme
from storage import get_articles
from rss import fetch_all_feeds
from ui.components import NewsCard, CategoryChip, CATEGORIES, category_color


class HomeView(ft.Column):
    def __init__(self, on_article_tap: Callable, on_theme_toggle: Callable = None):
        self._last_refresh: float = 0.0
        self._on_article_tap = on_article_tap
        self._active_category = "all"

        self._status = ft.Text("", size=10, color=theme.color("text_muted"))
        self._hero = ft.Container()
        self._chips = ft.Row(scroll=ft.ScrollMode.AUTO, spacing=6)
        self._list = ft.ListView(
            expand=True,
            spacing=8,
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
        )

        self._refresh_btn = ft.IconButton(
            icon=ft.Icons.REFRESH,
            icon_color=theme.color("text_muted"),
            icon_size=20,
            tooltip="Refresh feeds",
            on_click=lambda e: self.refresh(),
        )

        self._theme_btn = ft.IconButton(
            icon=ft.Icons.WB_SUNNY if theme.mode() == "dark" else ft.Icons.NIGHTLIGHT_ROUND,
            icon_color=theme.color("text_primary"),
            icon_size=20,
            tooltip="Toggle theme",
            on_click=lambda e: on_theme_toggle() if on_theme_toggle else None,
        )

        super().__init__(
            expand=True,
            controls=[
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        "Daily News",
                                        size=22,
                                        weight=ft.FontWeight.BOLD,
                                        color=theme.color("text_primary"),
                                    ),
                                    ft.Row([self._status, self._refresh_btn, self._theme_btn], spacing=4),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            self._hero,
                            self._chips,
                        ],
                        spacing=10,
                    ),
                    padding=ft.Padding.symmetric(horizontal=12, vertical=10),
                    bgcolor=theme.color("page_bg"),
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
                content=ft.Column(
                    [
                        ft.Text(
                            f"TOP STORY · {hero['source'].upper()}",
                            size=9,
                            color=theme.color("hero_text"),
                            weight=ft.FontWeight.W_600,
                        ),
                        ft.Text(
                            hero["title"],
                            size=15,
                            color=theme.color("text_primary"),
                            weight=ft.FontWeight.BOLD,
                            max_lines=3,
                        ),
                        ft.Text(
                            hero.get("published_at", "")[:10],
                            size=9,
                            color=theme.color("hero_date"),
                        ),
                    ],
                    spacing=4,
                ),
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
            NewsCard(
                a, on_tap=lambda e: self._on_article_tap(e.control.data)
            )
            for a in (articles[1:] if articles else [])
        ]

        if self.page:
            self.page.update()

    def _refresh_background(self):
        now = datetime.now(timezone.utc).timestamp()
        if now - self._last_refresh < 300:  # skip if refreshed within 5 minutes
            return

        def _do():
            self._status.value = "↻ Refreshing"
            if self.page:
                self.page.update()
            count = fetch_all_feeds()
            self._last_refresh = datetime.now(timezone.utc).timestamp()
            self._status.value = f"{count} articles fetched" if count else "Offline"
            self._load_cached()

        threading.Thread(target=_do, daemon=True).start()

    def refresh(self):
        self._refresh_background()
