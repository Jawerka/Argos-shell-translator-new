"""Тесты темы CustomTkinter."""

from __future__ import annotations

import customtkinter as ctk
import pytest

from argos_translator.ui.themes import DARK_COLORS, LIGHT_COLORS, apply_theme, get_status_color, setup_theme


def test_setup_theme_dark() -> None:
    setup_theme("dark")
    assert ctk.get_appearance_mode() == "Dark"


def test_apply_theme_dark(ctk_root: ctk.CTk) -> None:
    colors = apply_theme(ctk_root, "dark")
    assert colors is not None
    assert ctk_root.cget("fg_color") == DARK_COLORS["bg"]


def test_apply_theme_light(ctk_root: ctk.CTk) -> None:
    apply_theme(ctk_root, "light")
    setup_theme("light")
    assert ctk.get_appearance_mode() == "Light"


def test_dark_palette_matches_ytdlp_baseline() -> None:
    assert DARK_COLORS["bg"] == "#0f1115"
    assert DARK_COLORS["accent"] == "#16a6ff"


def test_get_status_color() -> None:
    assert get_status_color("dark", "available") == DARK_COLORS["success"]
    assert get_status_color("dark", "offline") == DARK_COLORS["fg_muted"]
    assert get_status_color("light", "busy") == LIGHT_COLORS["warning"]
