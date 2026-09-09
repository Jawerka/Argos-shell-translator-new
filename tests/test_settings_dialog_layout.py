"""Вёрстка диалога настроек по HTML-макету."""

from __future__ import annotations

import customtkinter as ctk

from argos_translator.config.settings import AppSettings
from argos_translator.ui.layout_config import (
    BTN_ICON_WIDTH,
    CHECKBOX_COMPACT_SIZE,
    SETTINGS_ACTION_BTN_WIDTH,
    SETTINGS_FOOTER_BTN_WIDTH,
    SETTINGS_HR_MARGIN_BOTTOM,
    SETTINGS_INTRO_FONT_SIZE,
    SETTINGS_TITLE_FONT_SIZE,
)
from argos_translator.ui.settings_dialog import SettingsDialog


def test_mockup_layout_tokens() -> None:
    assert BTN_ICON_WIDTH == 40
    assert CHECKBOX_COMPACT_SIZE == 16
    assert SETTINGS_INTRO_FONT_SIZE == 15
    assert SETTINGS_HR_MARGIN_BOTTOM == 25
    assert SETTINGS_ACTION_BTN_WIDTH == 170
    assert SETTINGS_FOOTER_BTN_WIDTH == 100
    assert SETTINGS_TITLE_FONT_SIZE == 16


def test_settings_dialog_title_intro_and_footer(ctk_root: ctk.CTk) -> None:
    dialog = SettingsDialog(ctk_root, AppSettings(), on_apply=lambda _s: None)
    try:
        dialog.update_idletasks()
        assert dialog._title_label.cget("text") == "Настройки"
        assert int(dialog._title_label.cget("font").cget("size")) == SETTINGS_TITLE_FONT_SIZE

        assert int(dialog._footer_ok.cget("width")) == SETTINGS_FOOTER_BTN_WIDTH
        assert int(dialog._footer_apply.cget("width")) == SETTINGS_FOOTER_BTN_WIDTH
        assert int(dialog._footer_cancel.cget("width")) == SETTINGS_FOOTER_BTN_WIDTH

        packed = dialog._footer_ok.master.pack_slaves()
        assert packed == [dialog._footer_cancel, dialog._footer_apply, dialog._footer_ok]

        intro = dialog._make_intro_label(dialog, "probe")
        assert int(intro.cget("font").cget("size")) == SETTINGS_INTRO_FONT_SIZE
        intro.destroy()
    finally:
        dialog.destroy()
