"""Тесты TranslateEngine (API / CLI)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from argos_translator.engines import argos_engine
from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.utils.imports import ImportStatus


def test_api_translate(monkeypatch) -> None:
    fake = SimpleNamespace(translate=lambda text, fc, tc: f"{fc}>{tc}:{text}")
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", fake)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.SUCCESS)

    engine = TranslateEngine()
    assert engine.use_api is True
    assert engine.translate("hello", "en", "ru") == "en>ru:hello"


def test_api_empty_text(monkeypatch) -> None:
    fake = SimpleNamespace(translate=lambda text, fc, tc: "should not run")
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", fake)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.SUCCESS)

    engine = TranslateEngine()
    assert engine.translate("   ", "en", "ru") == ""


def test_cli_fallback(monkeypatch) -> None:
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", None)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.MISSING)

    engine = TranslateEngine()
    engine.cli_path = __import__("pathlib").Path("/fake/argos-translate")
    engine.use_api = False

    mock_run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="translated", stderr=""))
    monkeypatch.setattr(argos_engine.subprocess, "run", mock_run)

    result = engine.translate("text", "en", "ru")
    assert result == "translated"
    mock_run.assert_called_once()


def test_no_backend_raises(monkeypatch) -> None:
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", None)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.MISSING)

    engine = TranslateEngine()
    engine.cli_path = None
    engine.use_api = False

    with pytest.raises(RuntimeError, match="No translation backend"):
        engine.translate("hello", "en", "ru")
