"""Интеграционные тесты Argos backend (@pytest.mark.integration)."""

from __future__ import annotations

import pytest

from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.services.model_manager import ModelManager
from argos_translator.utils.imports import ARGOS_MODULE_STATUS, ImportStatus


@pytest.mark.integration
def test_model_manager_lists_pairs() -> None:
    if ARGOS_MODULE_STATUS != ImportStatus.SUCCESS:
        pytest.skip("argostranslate not installed")
    mgr = ModelManager()
    has_models, pairs = mgr.has_any_model()
    if not has_models:
        pytest.skip("no Argos models installed")
    assert pairs


@pytest.mark.integration
def test_translate_engine_en_ru() -> None:
    if ARGOS_MODULE_STATUS != ImportStatus.SUCCESS:
        pytest.skip("argostranslate not installed")
    mgr = ModelManager()
    if not mgr.has_pair("en", "ru"):
        pytest.skip("en->ru model not installed")
    engine = TranslateEngine()
    if not engine.use_api and not engine.cli_path:
        pytest.skip("no Argos backend available")
    result = engine.translate("Hello", "en", "ru")
    assert result.strip()
