"""Тесты frozen bootstrap и portable путей."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from argos_translator.config.paths import get_exe_dir, get_log_dir
from argos_translator.config.settings import AppSettings
from argos_translator.services.frozen_bootstrap import bootstrap_frozen_models


def test_bootstrap_skips_when_not_frozen(monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert bootstrap_frozen_models(AppSettings()) == 0


def test_bootstrap_skips_when_models_present(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "ArgosTranslator.exe"
    exe.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))

    mgr = MagicMock()
    mgr.list_installed_pairs.return_value = ["en->ru"]
    monkeypatch.setattr("argos_translator.services.frozen_bootstrap.ModelManager", lambda *_: mgr)

    assert bootstrap_frozen_models(AppSettings()) == 0
    mgr.install_from_bundle.assert_not_called()


def test_bootstrap_installs_from_bundle(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "ArgosTranslator.exe"
    exe.touch()
    bundle = tmp_path / "argos_models"
    bundle.mkdir()
    (bundle / "translate-en_ru-1_0.argosmodel").write_bytes(b"fake")

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    monkeypatch.setattr(
        "argos_translator.services.frozen_bootstrap._resolve_bundle_dir",
        lambda: bundle,
    )

    mgr = MagicMock()
    mgr.list_installed_pairs.return_value = []
    mgr.install_from_bundle.return_value = 2
    monkeypatch.setattr("argos_translator.services.frozen_bootstrap.ModelManager", lambda *_: mgr)

    settings = AppSettings()
    settings.argos.bundle_models_on_start = True
    assert bootstrap_frozen_models(settings) == 2
    mgr.install_from_bundle.assert_called_once_with(bundle)


def test_log_dir_frozen_beside_exe(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "app.exe"
    exe.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    assert get_log_dir() == tmp_path / "log"
    assert get_exe_dir() == tmp_path
