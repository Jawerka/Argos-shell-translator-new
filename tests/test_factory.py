"""Тесты engines/factory.py."""

from __future__ import annotations

import pytest

from argos_translator.config.settings import AppSettings
from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.engines.factory import create_engine
from argos_translator.engines.llm_engine import LLMDisabledError


def test_create_engine_argos() -> None:
    engine = create_engine("argos", AppSettings())
    assert isinstance(engine, TranslateEngine)


def test_create_engine_llm_disabled() -> None:
    settings = AppSettings()
    settings.llm.enabled = False
    with pytest.raises(LLMDisabledError):
        create_engine("llm", settings)


def test_create_engine_unknown() -> None:
    with pytest.raises(ValueError, match="Unknown engine"):
        create_engine("unknown", AppSettings())  # type: ignore[arg-type]
