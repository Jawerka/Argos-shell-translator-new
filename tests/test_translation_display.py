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


def test_idle_badges_show_engine_names(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(frame, cfg=UIConfig(), llm_enabled=True)
    tabs.update_idletasks()
    assert tabs._status_badges["argos"].cget("text") == "Argos"
    assert tabs._status_badges["llm"].cget("text") == "LLM"
    tabs.set_tab_status("argos", "done")
    assert tabs._status_badges["argos"].cget("text") == "Argos ✓"
    tabs.set_tab_status("argos", None)
    assert tabs._status_badges["argos"].cget("text") == "Argos"


def test_header_controls_single_row(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(
        frame,
        cfg=UIConfig(),
        llm_enabled=True,
        on_editor_layout_toggle=lambda: None,
    )
    tabs.update_idletasks()
    children = tabs._header_controls.pack_slaves()
    assert children == [
        tabs._layout_btn,
        tabs._status_badges["argos"],
        tabs._llm_enable_cb,
        tabs._status_badges["llm"],
    ]
    assert int(tabs._layout_btn.cget("width")) == 40
    assert int(tabs._llm_enable_cb.cget("width")) == 16


def test_llm_stream_incremental_append(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(frame, cfg=UIConfig(), llm_enabled=True)
    tabs.update_idletasks()
    assert tabs._llm_box is not None

    tabs.begin_llm_stream()
    tabs.append_llm_stream_text("a")
    tabs.append_llm_stream_text("ab")
    tabs.update_idletasks()

    assert tabs._llm_box.get("1.0", "end-1c") == "ab"
    assert str(tabs._llm_box._textbox.cget("state")) == "normal"

    tabs.end_llm_stream()
    assert str(tabs._llm_box._textbox.cget("state")) == "disabled"
    assert tabs.get_llm_text() == "ab"


def test_llm_stream_prefix_mismatch_fallback(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(frame, cfg=UIConfig(), llm_enabled=True)
    tabs.update_idletasks()
    assert tabs._llm_box is not None

    tabs.begin_llm_stream()
    tabs.append_llm_stream_text("reasoning text")
    tabs.append_llm_stream_text("final content")
    tabs.update_idletasks()

    assert tabs._llm_box.get("1.0", "end-1c") == "final content"
    tabs.end_llm_stream()
    assert tabs.get_llm_text() == "final content"


def test_llm_stream_append_invokes_callback(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    calls: list[str] = []

    def on_append() -> None:
        calls.append("append")

    tabs = TranslationTabs(
        frame,
        cfg=UIConfig(),
        llm_enabled=True,
        on_llm_stream_append=on_append,
    )
    tabs.update_idletasks()
    tabs.begin_llm_stream()
    tabs.append_llm_stream_text("x")
    tabs.append_llm_stream_text("x")

    assert calls == ["append"]
