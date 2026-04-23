import flet as ft

_current = "dark"

_THEMES = {
    "dark": {
        "page_bg": "#18181b",
        "card_bg": "#27272a",
        "text_primary": "#ffffff",
        "text_secondary": "#cccccc",
        "text_muted": "#888888",
        "divider": "#333333",
        "nav_bg": "#1c1c1f",
        "header_bg": "#18181b",
        "chip_inactive_bg": "#27272a",
        "chip_inactive_text": "#888888",
        "button_bg": "#27272a",
        "hero_text": "rgba(255,255,255,0.75)",
        "hero_date": "rgba(255,255,255,0.6)",
    },
    "light": {
        "page_bg": "#f3f4f6",
        "card_bg": "#ffffff",
        "text_primary": "#111827",
        "text_secondary": "#374151",
        "text_muted": "#6b7280",
        "divider": "#e5e7eb",
        "nav_bg": "#ffffff",
        "header_bg": "#ffffff",
        "chip_inactive_bg": "#e5e7eb",
        "chip_inactive_text": "#6b7280",
        "button_bg": "#e5e7eb",
        "hero_text": "rgba(0,0,0,0.7)",
        "hero_date": "rgba(0,0,0,0.5)",
    },
}


def mode() -> str:
    return _current


def set_mode(m: str):
    global _current
    _current = m


def toggle() -> str:
    set_mode("light" if _current == "dark" else "dark")
    return _current


def color(key: str) -> str:
    return _THEMES[_current].get(key, "#000000")
