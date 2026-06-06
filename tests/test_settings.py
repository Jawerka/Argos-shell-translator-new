"""Тесты settings.json: load/save/migrate."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from argos_translator.config.constants import UIConfig
from argos_translator.config.settings import (
    CURRENT_SETTINGS_VERSION,
    AppSettings,
    load_settings,
    migrate_settings,
    save_settings,
)


def test_default_settings_version() -> None:
    s = AppSettings()
    assert s.version == CURRENT_SETTINGS_VERSION
    assert s.llm.enabled is True
    assert s.files.output_encoding == "same"
    assert s.argos.bundle_models_on_start is True


def test_migrate_v1_geometry(tmp_path: Path) -> None:
    legacy = {
        "version": 1,
        "window": {"geometry": "800x600+10+20", "streaming": True},
        "languages": {"from": "auto", "to": "en"},
    }
    migrated = migrate_settings(legacy)
    assert migrated["version"] == CURRENT_SETTINGS_VERSION
    assert "translation" in migrated
    assert "files" in migrated
    assert "argos" in migrated


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    cfg_path = tmp_path / "settings.json"
    original = AppSettings()
    original.theme = "light"
    original.llm.provider = "openrouter"
    original.files.max_file_size_mb = 5
    original.argos.prefer_api_over_cli = False

    save_settings(original, cfg_path)
    loaded = load_settings(UIConfig(), path=cfg_path)

    assert loaded.theme == "light"
    assert loaded.llm.provider == "openrouter"
    assert loaded.files.max_file_size_mb == 5
    assert loaded.argos.prefer_api_over_cli is False


def test_to_dict_contains_sections() -> None:
    data = AppSettings().to_dict()
    assert data["version"] == CURRENT_SETTINGS_VERSION
    assert "llm" in data
    assert "files" in data
    assert "argos" in data
    assert "behavior" in data
    assert data["translation"]["default_engine"] == "both_adaptive"
    assert data["behavior"]["close_action"] == "tray"
    assert "settings_dialog" in data["ui"]


def test_settings_dialog_state_roundtrip(tmp_path: Path) -> None:
    from argos_translator.ui.window_state import WindowState

    cfg_path = tmp_path / "settings.json"
    original = AppSettings()
    original.settings_dialog_state = WindowState(
        x=120,
        y=80,
        width=720,
        height=560,
        geometry_units="tk_geometry",
    )

    save_settings(original, cfg_path)
    loaded = load_settings(UIConfig(), path=cfg_path)

    assert loaded.settings_dialog_state is not None
    assert loaded.settings_dialog_state.width == 720
    assert loaded.settings_dialog_state.height == 560
    assert loaded.settings_dialog_state.x == 120
    assert loaded.settings_dialog_state.geometry_units == "tk_geometry"


def test_migrate_v6_adds_behavior() -> None:
    legacy = {"version": 6, "window": {}, "languages": {}, "translation": {}, "llm": {}}
    migrated = migrate_settings(legacy)
    assert migrated["version"] == CURRENT_SETTINGS_VERSION
    assert migrated["behavior"]["start_minimized_to_tray"] is False
    assert migrated["translation"]["cache_enabled"] is False
