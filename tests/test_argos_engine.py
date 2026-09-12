"""Тесты TranslateEngine (API / CLI)."""

from __future__ import annotations

import subprocess
from pathlib import Path
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


def test_prefer_cli_over_api(monkeypatch) -> None:
    fake = SimpleNamespace(translate=lambda text, fc, tc: "api")
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", fake)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.SUCCESS)

    engine = TranslateEngine(prefer_api=False)
    engine.cli_path = __import__("pathlib").Path("/fake/argos-translate")
    mock_run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="cli", stderr=""))
    monkeypatch.setattr(argos_engine.subprocess, "run", mock_run)

    assert engine.prefer_api is False
    assert engine.translate("text", "en", "ru") == "cli"
    mock_run.assert_called_once()


def test_no_backend_raises(monkeypatch) -> None:
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", None)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.MISSING)

    engine = TranslateEngine()
    engine.cli_path = None
    engine.use_api = False

    with pytest.raises(RuntimeError, match="No translation backend"):
        engine.translate("hello", "en", "ru")


def test_init_warns_when_no_backend(monkeypatch) -> None:
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", None)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.MISSING)
    monkeypatch.setattr(TranslateEngine, "_find_cli_executable", staticmethod(lambda: None))
    engine = TranslateEngine()
    assert engine.use_api is False
    assert engine.cli_path is None


def test_api_error_falls_back_to_cli(monkeypatch) -> None:
    fake = SimpleNamespace(translate=MagicMock(side_effect=RuntimeError("api down")))
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", fake)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.SUCCESS)

    engine = TranslateEngine()
    engine.cli_path = Path("/fake/argos-translate")
    mock_run = MagicMock(return_value=SimpleNamespace(returncode=0, stdout="cli", stderr=""))
    monkeypatch.setattr(argos_engine.subprocess, "run", mock_run)

    assert engine.translate("text", "en", "ru") == "cli"
    mock_run.assert_called_once()


def test_cli_nonzero_raises(monkeypatch) -> None:
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", None)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.MISSING)

    engine = TranslateEngine()
    engine.cli_path = Path("/fake/argos-translate")
    engine.use_api = False
    mock_run = MagicMock(return_value=SimpleNamespace(returncode=1, stdout="", stderr="boom"))
    monkeypatch.setattr(argos_engine.subprocess, "run", mock_run)

    with pytest.raises(RuntimeError, match="Translate CLI error"):
        engine.translate("text", "en", "ru")


def test_cli_timeout_raises(monkeypatch) -> None:
    monkeypatch.setattr(argos_engine, "AT_TRANSLATE_MODULE", None)
    monkeypatch.setattr(argos_engine, "ARGOS_MODULE_STATUS", ImportStatus.MISSING)

    engine = TranslateEngine()
    engine.cli_path = Path("/fake/argos-translate")
    engine.use_api = False
    monkeypatch.setattr(
        argos_engine.subprocess,
        "run",
        MagicMock(side_effect=subprocess.TimeoutExpired(cmd="argos", timeout=1)),
    )

    with pytest.raises(RuntimeError, match="Translate timeout"):
        engine.translate("text", "en", "ru")

