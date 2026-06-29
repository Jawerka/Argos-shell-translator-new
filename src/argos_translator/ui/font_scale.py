"""Масштаб шрифтов UI и полей редактора."""

from __future__ import annotations

import customtkinter as ctk

from argos_translator.ui.layout_config import TEXT_FONT_FAMILY, TEXT_FONT_SIZE, UI_FONT_FAMILY

FONT_SCALE_MIN = 0.85
FONT_SCALE_MAX = 2.0
FONT_SCALE_DEFAULT = 1.0
UI_FONT_SIZE = 14


def clamp_font_scale(value: float) -> float:
    return max(FONT_SCALE_MIN, min(FONT_SCALE_MAX, float(value)))


def ui_font(size: int = UI_FONT_SIZE, weight: str = "normal") -> ctk.CTkFont:
    if weight == "bold":
        return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight="bold")
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size)


def scaled_text_font(scale: float = 1.0) -> ctk.CTkFont:
    size = max(8, round(TEXT_FONT_SIZE * clamp_font_scale(scale)))
    return ctk.CTkFont(family=TEXT_FONT_FAMILY, size=size)
