"""LLM disabled: вкладка скрыта, worker не стартует."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from argos_translator.app import TranslatorApp
from argos_translator.config.constants import UIConfig
from argos_translator.config.settings import AppSettings, LLMSettings
from argos_translator.engines.factory import create_engine, is_llm_available
from argos_translator.engines.llm_engine import LLMDisabledError, translate_stream
from argos_translator.ui.translation_tabs import TranslationTabs


@pytest.fixture
def ctk_root():
    try:
        root = ctk.CTk()
    except Exception:
        pytest.skip("CustomTkinter unavailable (no display)")
    root.withdraw()
    yield root
    root.destroy()


def test_is_llm_available_respects_setting() -> None:
    settings = AppSettings()
    settings.llm.enabled = True
    assert is_llm_available(settings) is True
    settings.llm.enabled = False
    assert is_llm_available(settings) is False


def test_create_engine_llm_raises_when_disabled() -> None:
    settings = AppSettings()
    settings.llm.enabled = False
    with pytest.raises(LLMDisabledError):
        create_engine("llm", settings)


def test_translate_stream_raises_when_disabled() -> None:
    llm = LLMSettings(enabled=False)
    with pytest.raises(LLMDisabledError):
        translate_stream(
            llm,
            "hello",
            "en",
            "ru",
            {},
            lambda _t: None,
            lambda _f: None,
            lambda _e: None,
            threading.Event(),
        )


def test_translation_tabs_hides_llm_tab(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(frame, cfg=UIConfig(), llm_enabled=False)
    assert len(tabs.notebook.tabs()) == 1
    assert tabs.get_active_engine() == "argos"


def test_start_llm_translation_skips_worker_when_disabled() -> None:
    settings = AppSettings()
    settings.llm.enabled = False

    app = object.__new__(TranslatorApp)
    app.settings = settings
    app.coord = MagicMock()
    app.llm_health = MagicMock()
    app.translation_tabs = MagicMock()
    app.llm_translate_thread = None
    app.llm_status_text = ""

    TranslatorApp._start_llm_translation(app, 1, "text", "en", "ru")

    app.coord.start_llm.assert_not_called()
    app.translation_tabs.set_llm_text.assert_not_called()
