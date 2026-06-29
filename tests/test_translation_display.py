"""Проверка отображения текста в CTkTextbox (TranslationTabs)."""

from __future__ import annotations

import customtkinter as ctk
import pytest

from argos_translator.config.constants import UIConfig
from argos_translator.ui.translation_tabs import TranslationTabs


def test_set_argos_text_visible_in_ctk_widget(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(frame, cfg=UIConfig(), llm_enabled=False)
    tabs.update_idletasks()
    tabs.set_argos_text("Hello translated")
    assert tabs.get_argos_text() == "Hello translated"
    assert tabs._argos_box.get("1.0", "end-1c") == "Hello translated"


def test_tab_status_preserves_argos_text(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(frame, cfg=UIConfig(), llm_enabled=True)
    tabs.update_idletasks()
    tabs.set_argos_text("Argos result")
    tabs.set_tab_status("argos", "done")
    tabs.set_tab_status("llm", "streaming")
    tabs.update_idletasks()
    tabs.set_active_tab("argos")
    tabs.update_idletasks()
    assert tabs.get_argos_text() == "Argos result"
    assert tabs._argos_box.get("1.0", "end-1c") == "Argos result"
