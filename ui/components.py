import flet as ft
from typing import Callable, Optional, Dict

import theme

CATEGORY_COLORS: Dict[str, str] = {
    "world":       "#e63946",
    "tech":        "#f4a261",
    "data-ai":     "#a78bfa",
    "business":    "#4ade80",
    "florida":     "#38bdf8",
    "us-politics": "#fb923c",
    "long-form":   "#e879f9",
}

CATEGORY_LABELS: Dict[str, str] = {
    "world":       "World",
    "tech":        "Tech",
    "data-ai":     "Data & AI",
    "business":    "Business",
    "florida":     "Florida",
    "us-politics": "US Politics",
    "long-form":   "Long-Form",
}

# Ordered list for chip display
CATEGORIES = [("All", "all")] + [(v, k) for k, v in CATEGORY_LABELS.items()]


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, "#888888")


def category_label(category: str) -> str:
    return CATEGORY_LABELS.get(category, category.title())


def NewsCard(article: Dict, on_tap: Optional[Callable] = None) -> ft.Container:
    color = category_color(article["category"])
    label = category_label(article["category"])
    pub = article.get("published_at", "")[:10]
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(
                    f"{label} · {article['source']}",
                    size=10,
                    color=color,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    article["title"],
                    size=13,
                    color=theme.color("text_primary"),
                    weight=ft.FontWeight.W_600,
                    max_lines=3,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                ft.Text(pub, size=10, color=theme.color("text_muted")),
            ],
            spacing=4,
        ),
        bgcolor=theme.color("card_bg"),
        border_radius=8,
        padding=12,
        on_click=on_tap,
        data=article,
    )


def CategoryChip(label: str, category: str, active: bool, on_tap: Optional[Callable] = None) -> ft.Container:
    color = CATEGORY_COLORS.get(category, "#e63946")
    return ft.Container(
        content=ft.Text(
            label,
            size=11,
            color=theme.color("text_primary") if active else theme.color("chip_inactive_text"),
            weight=ft.FontWeight.W_600,
        ),
        bgcolor=color if active else theme.color("chip_inactive_bg"),
        border_radius=12,
        padding=ft.Padding.symmetric(horizontal=12, vertical=4),
        on_click=on_tap,
        data=category,
    )
