"""Масштаб шрифтов UI."""

from __future__ import annotations

import customtkinter as ctk

from argos_translator.ui.layout_config import LABEL_FONT_SIZE, TEXT_FONT_FAMILY, TEXT_FONT_SIZE, TITLE_FONT_SIZE, UI_FONT_FAMILY

FONT_SCALE_MIN = 0.85
FONT_SCALE_MAX = 1.5
FONT_SCALE_DEFAULT = 1.0


def clamp_font_scale(value: float) -> float:
    return max(FONT_SCALE_MIN, min(FONT_SCALE_MAX, float(value)))


def scaled_text_font(scale: float = 1.0) -> ctk.CTkFont:
    size = max(8, round(TEXT_FONT_SIZE * clamp_font_scale(scale)))
    return ctk.CTkFont(family=TEXT_FONT_FAMILY, size=size)


def scaled_ui_font(scale: float = 1.0, base: int = LABEL_FONT_SIZE, weight: str = "normal") -> ctk.CTkFont:
    size = max(8, round(base * clamp_font_scale(scale)))
    if weight == "bold":
        return ctk.CTkFont(family=UI_FONT_FAMILY, size=size, weight="bold")
    return ctk.CTkFont(family=UI_FONT_FAMILY, size=size)


def scaled_title_font(scale: float = 1.0) -> ctk.CTkFont:
    return scaled_ui_font(scale, TITLE_FONT_SIZE, weight="bold")
