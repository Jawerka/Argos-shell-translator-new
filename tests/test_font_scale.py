"""Тесты масштаба шрифта полей редактора."""

from __future__ import annotations

import customtkinter as ctk

from argos_translator.ui.font_scale import (
    FONT_SCALE_MAX,
    clamp_font_scale,
    scaled_text_font,
    ui_font,
)


def test_clamp_font_scale_max_200_percent() -> None:
    assert FONT_SCALE_MAX == 2.0
    assert clamp_font_scale(2.0) == 2.0
    assert clamp_font_scale(2.5) == 2.0


def test_scaled_text_font_grows_with_scale(ctk_root: ctk.CTk) -> None:
    base = scaled_text_font(1.0)
    large = scaled_text_font(2.0)
    assert large.cget("size") > base.cget("size")


def test_ui_font_fixed_size(ctk_root: ctk.CTk) -> None:
    font = ui_font()
    assert font.cget("size") == 13
