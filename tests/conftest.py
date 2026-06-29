"""Shared pytest fixtures."""

from __future__ import annotations

from unittest.mock import MagicMock

import customtkinter as ctk
import pytest

from argos_translator.app import TranslatorApp
from argos_translator.config.constants import UIConfig
from argos_translator.config.settings import AppSettings
from argos_translator.services.translation_cache import TranslationCache
from argos_translator.services.translation_coordinator import TranslationCoordinator


@pytest.fixture
def ctk_root():
    try:
        root = ctk.CTk()
    except Exception:
        pytest.skip("CustomTkinter unavailable (no display)")
    root.withdraw()
    yield root
    root.destroy()


def make_mock_translator_app(
    *,
    settings: AppSettings | None = None,
    root: ctk.CTk | None = None,
) -> TranslatorApp:
    """Минимальный TranslatorApp без полной инициализации GUI."""
    app = object.__new__(TranslatorApp)
    app.settings = settings or AppSettings()
    app.cfg = UIConfig()
    app.coord = TranslationCoordinator()
    app.engine = MagicMock()
    app._translation_cache = TranslationCache(
        max_size=app.settings.behavior.translation_cache_size
    )
    app.translate_queue = __import__("queue").Queue()
    app.translate_thread = None
    app.llm_translate_thread = None
    app.llm_health = MagicMock()
    app.translation_tabs = MagicMock()
    app.src_panel = MagicMock()
    app.lang_widget = MagicMock()
    app.languages = {"en": "English", "ru": "Russian"}
    app.translate_status_var = MagicMock()
    app.status_var = MagicMock()
    app.llm_status_text = ""
    app.llm_indicator_var = MagicMock()
    app._update_llm_indicator = MagicMock()
    app._update_combined_status = MagicMock()
    app._hide_file_progress = MagicMock()
    app._show_file_progress = MagicMock()
    app.translate = MagicMock()
    app._cancel_pending_translate_jobs = MagicMock()
    app._update_window_title = MagicMock()
    app._update_document_status = MagicMock()
    app._suppress_src_modified = False
    app._document_path = None
    app._document_file_type = None
    app._document_encoding = "utf-8"
    app._confirm_large_text = MagicMock(return_value=True)
    app.streaming_enabled = MagicMock()
    app.streaming_enabled.get.return_value = True
    app.root = root or MagicMock()
    app.root.after = MagicMock(side_effect=lambda _ms, fn: fn())
    return app


@pytest.fixture
def mock_translator_app() -> TranslatorApp:
    return make_mock_translator_app()
