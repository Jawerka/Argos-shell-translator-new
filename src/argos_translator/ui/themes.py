"""Тема CustomTkinter (дизайн-система UI-for-ytdlp)."""

from __future__ import annotations

from typing import Dict, Literal

import customtkinter as ctk
import tkinter as tk

ThemeName = Literal["dark", "light"]

# Палитра UI-for-ytdlp → CustomTkinter
COLOR_THEME_DARK: Dict[str, str | int] = {
    "bg_primary": "#0f1115",
    "bg_secondary": "#0b0c10",
    "bg_card": "#1b2230",
    "primary": "#3890b5",
    "primary_hover": "#0f92e6",
    "primary_foreground": "#0b0c10",
    "accent": "#2f3542",
    "accent_hover": "#3f4a63",
    "accent_foreground": "#e6eef8",
    "muted": "#535b6d",
    "muted_foreground": "#8f98ab",
    "border": "#202a38",
    "border_width": 1,
    "border_color_focus": "#3890b5",
    "input": "#101216",
    "text_primary": "#e6eef8",
    "text_editor": "#b8c4d4",
    "text_muted": "#9aa3bf",
    "text_success": "#7bd389",
    "text_warning": "#f0c674",
    "text_error": "#ff7b95",
    "progress_bg": "#0b0d10",
    "progress_fill": "#3890b5",
    "radius_sm": 6,
    "radius_md": 10,
    "radius_lg": 14,
}

COLOR_THEME_LIGHT: Dict[str, str | int] = {
    "bg_primary": "#f0f2f5",
    "bg_secondary": "#e4e6eb",
    "bg_card": "#ffffff",
    "primary": "#0f92e6",
    "primary_hover": "#0878c7",
    "primary_foreground": "#ffffff",
    "accent": "#e4e6eb",
    "accent_hover": "#d0d3d9",
    "accent_foreground": "#1a1d21",
    "muted": "#c5c9d0",
    "muted_foreground": "#5c6370",
    "border": "#d0d3d9",
    "border_width": 1,
    "border_color_focus": "#0f92e6",
    "input": "#ffffff",
    "text_primary": "#1a1d21",
    "text_editor": "#3d4554",
    "text_muted": "#5c6370",
    "text_success": "#2e7d32",
    "text_warning": "#b8860b",
    "text_error": "#c62828",
    "progress_bg": "#e4e6eb",
    "progress_fill": "#0f92e6",
    "radius_sm": 6,
    "radius_md": 10,
    "radius_lg": 14,
}

# Алиасы для тестов и обратной совместимости
DARK_COLORS: Dict[str, str] = {
    "bg": str(COLOR_THEME_DARK["bg_primary"]),
    "panel": str(COLOR_THEME_DARK["bg_card"]),
    "fg": str(COLOR_THEME_DARK["text_primary"]),
    "fg_muted": str(COLOR_THEME_DARK["text_muted"]),
    "accent": str(COLOR_THEME_DARK["primary"]),
    "success": str(COLOR_THEME_DARK["text_success"]),
    "warning": str(COLOR_THEME_DARK["text_warning"]),
    "error": str(COLOR_THEME_DARK["text_error"]),
}

LIGHT_COLORS: Dict[str, str] = {
    "bg": str(COLOR_THEME_LIGHT["bg_primary"]),
    "panel": str(COLOR_THEME_LIGHT["bg_card"]),
    "fg": str(COLOR_THEME_LIGHT["text_primary"]),
    "fg_muted": str(COLOR_THEME_LIGHT["text_muted"]),
    "accent": str(COLOR_THEME_LIGHT["primary"]),
    "success": str(COLOR_THEME_LIGHT["text_success"]),
    "warning": str(COLOR_THEME_LIGHT["text_warning"]),
    "error": str(COLOR_THEME_LIGHT["text_error"]),
}


class Spacing:
    XS = 4
    SM = 8
    MD = 12
    LG = 16
    XL = 24
    XXL = 32


def get_color_theme(theme: ThemeName = "dark") -> Dict[str, str | int]:
    return COLOR_THEME_DARK if theme == "dark" else COLOR_THEME_LIGHT


def get_colors(theme: ThemeName = "dark") -> Dict[str, str]:
    """Словарь цветов (legacy API для тестов)."""
    return DARK_COLORS if theme == "dark" else LIGHT_COLORS


def get_status_color(theme: ThemeName, status: str) -> str:
    colors = get_color_theme(theme)
    mapping = {
        "available": str(colors["text_success"]),
        "busy": str(colors["text_warning"]),
        "offline": str(colors["text_muted"]),
        "disabled": str(colors["text_muted"]),
        "error": str(colors["text_error"]),
    }
    return mapping.get(status, str(colors["text_muted"]))


def setup_theme(theme: ThemeName = "dark") -> None:
    """Инициализация CustomTkinter."""
    ctk.set_appearance_mode("dark" if theme == "dark" else "light")
    try:
        ctk.set_default_color_theme("dark-blue")
    except Exception:
        pass


def apply_theme(root: ctk.CTk | ctk.CTkToplevel, theme: ThemeName = "dark") -> Dict[str, str | int]:
    """Применить тему к окну CTk."""
    setup_theme(theme)
    colors = get_color_theme(theme)
    try:
        root.configure(fg_color=str(colors["bg_primary"]))
    except Exception:
        pass
    apply_menu_theme(root, theme)
    return colors


def apply_menu_theme(root: tk.Misc, theme: ThemeName = "dark") -> None:
    """Тёмная (или светлая) тема для нативного tk.Menu / menubar."""
    colors = get_color_theme(theme)
    bg = str(colors["bg_card"])
    fg = str(colors["text_primary"])
    active_bg = str(colors["primary"])
    active_fg = str(colors["primary_foreground"])

    try:
        root.option_add("*Menu.background", bg)
        root.option_add("*Menu.foreground", fg)
        root.option_add("*Menu.activeBackground", active_bg)
        root.option_add("*Menu.activeForeground", active_fg)
        root.option_add("*Menu.disabledForeground", str(colors["text_muted"]))
        root.option_add("*Menu.borderWidth", 0)
        root.option_add("*Menu.relief", "flat")
    except Exception:
        pass

    try:
        menu_name = root.cget("menu")
        if menu_name:
            _style_menu_tree(root.nametowidget(menu_name), theme)
    except Exception:
        pass


def style_menu(menu: tk.Menu, theme: ThemeName = "dark") -> None:
    """Применить палитру к одному tk.Menu."""
    colors = get_color_theme(theme)
    try:
        menu.configure(
            background=str(colors["bg_card"]),
            foreground=str(colors["text_primary"]),
            activebackground=str(colors["primary"]),
            activeforeground=str(colors["primary_foreground"]),
            disabledforeground=str(colors["text_muted"]),
            borderwidth=0,
            relief="flat",
        )
    except Exception:
        pass


def _style_menu_tree(menu: tk.Menu, theme: ThemeName = "dark") -> None:
    style_menu(menu, theme)
    try:
        last = menu.index("end")
    except tk.TclError:
        return
    if last is None:
        return
    for i in range(last + 1):
        try:
            if menu.type(i) == "cascade":
                submenu = menu.nametowidget(menu.entrycget(i, "menu"))
                _style_menu_tree(submenu, theme)
        except Exception:
            continue
