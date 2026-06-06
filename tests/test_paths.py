"""Тесты get_argos_packages_dir и связанных путей."""

from __future__ import annotations

import sys
from pathlib import Path

from argos_translator.config.paths import get_argos_packages_dir, get_log_dir, get_resource_path, get_settings_path


def test_custom_packages_dir() -> None:
    custom = "/tmp/my-argos-packages"
    assert get_argos_packages_dir(custom) == Path(custom).expanduser()


def test_custom_dir_whitespace_ignored() -> None:
    fallback = get_argos_packages_dir("   ")
    assert fallback.name == "packages"


def test_settings_path_under_home() -> None:
    path = get_settings_path()
    assert path.name == "settings.json"
    assert path.parent.name == ".argos_translate"


def test_frozen_uses_exe_dir_packages(monkeypatch, tmp_path: Path) -> None:
    exe = tmp_path / "ArgosTranslator.exe"
    exe.touch()
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(exe))
    result = get_argos_packages_dir(None)
    assert result == exe.parent / "packages"


def test_log_dir_dev_uses_project_log(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    monkeypatch.setattr(
        "argos_translator.config.paths.get_project_root",
        lambda: tmp_path,
    )
    assert get_log_dir() == tmp_path / "log"


def test_resource_path_prefers_assets(tmp_path: Path, monkeypatch) -> None:
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "icon.ico").write_bytes(b"x")
    monkeypatch.setattr(
        "argos_translator.config.paths.get_project_root",
        lambda: tmp_path,
    )
    assert get_resource_path("icon.ico") == assets / "icon.ico"
