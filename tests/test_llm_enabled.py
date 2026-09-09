"""LLM disabled: вкладка скрыта, worker не стартует."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

import customtkinter as ctk
import pytest

from argos_translator.app import TranslatorApp
from argos_translator.config.constants import UIConfig
from argos_translator.config.settings import AppSettings, LLMSettings
from argos_translator.engines.factory import create_engine, is_llm_available
from argos_translator.engines.llm_engine import LLMDisabledError, llm_config_error, translate_stream
from argos_translator.ui.translation_tabs import TranslationTabs


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


def test_llm_config_error_missing_url() -> None:
    llm = LLMSettings(
        enabled=True,
        provider="custom",
        base_url="",
        provider_urls={"custom": ""},
    )
    assert llm_config_error(llm) is not None


def test_llm_config_error_openrouter_needs_key() -> None:
    llm = LLMSettings(
        enabled=True,
        provider="openrouter",
        base_url="https://openrouter.ai/api/v1",
        api_keys={"openrouter": ""},
    )
    err = llm_config_error(llm)
    assert err is not None
    assert "API key" in err


def test_llm_config_error_local_ok() -> None:
    llm = LLMSettings(
        enabled=True,
        provider="local",
        base_url="http://192.168.88.37:8989/v1",
    )
    assert llm_config_error(llm) is None


def test_translation_tabs_hides_llm_tab(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    tabs = TranslationTabs(frame, cfg=UIConfig(), llm_enabled=False)
    assert len(tabs.notebook.tabs()) == 1
    assert tabs.get_active_engine() == "argos"
    assert tabs._llm_enable_cb is not None
    assert tabs._llm_enable_var.get() is False


def test_translation_tabs_checkbox_toggles_llm_tab(ctk_root: ctk.CTk) -> None:
    frame = ctk.CTkFrame(ctk_root, fg_color="transparent")
    calls: list[bool] = []

    tabs = TranslationTabs(
        frame,
        cfg=UIConfig(),
        llm_enabled=True,
        on_llm_enabled_changed=calls.append,
    )
    tabs.update_idletasks()
    assert "llm" in tabs.tabs()
    assert tabs._llm_enable_var.get() is True

    tabs.set_llm_enabled(False)
    tabs.update_idletasks()
    assert "llm" not in tabs.tabs()
    assert tabs._llm_enable_var.get() is False
    assert calls == []

    tabs._llm_enable_var.set(True)
    tabs._handle_llm_enable_toggle()
    assert calls == [True]


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


def test_apply_llm_enabled_persists_and_cancels(mock_translator_app) -> None:
    app = mock_translator_app
    app.settings.llm.enabled = True
    app.settings.active_translation_tab = "llm"
    app.translation_tabs = MagicMock()
    app.coord = MagicMock()
    app.llm_health = MagicMock()
    app.root = MagicMock()

    with patch("argos_translator.app.save_settings") as save:
        TranslatorApp._apply_llm_enabled(app, False)

    assert app.settings.llm.enabled is False
    app.translation_tabs.set_llm_enabled.assert_called_with(False)
    app.coord.signal_llm_restart.assert_called()
    save.assert_called_once()
    assert "отключена" in app.llm_status_text
