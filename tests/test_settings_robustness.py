"""Тесты устойчивости загрузки настроек."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from argos_translator.config.constants import UIConfig
from argos_translator.config.settings import (
    AppSettings,
    clamp_settings,
    load_settings,
    migrate_settings,
)


def test_load_settings_missing_file(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    cfg = UIConfig()
    loaded = load_settings(cfg, path)
    assert loaded.debounce_ms == 700
    assert loaded.llm.enabled is True


def test_load_settings_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    path.write_text("{not json", encoding="utf-8")
    loaded = load_settings(UIConfig(), path)
    assert isinstance(loaded, AppSettings)


def test_clamp_settings_negative_values() -> None:
    settings = AppSettings()
    settings.debounce_ms = -100
    settings.llm.timeout_sec = 0
    settings.llm.max_tokens = -50
    settings.files.max_file_size_mb = 0
    clamped = clamp_settings(settings)
    assert clamped.debounce_ms >= 100
    assert clamped.llm.timeout_sec >= 5
    assert clamped.llm.max_tokens >= 64
    assert clamped.files.max_file_size_mb >= 1


def test_load_settings_clamps_hand_edited_json(tmp_path: Path) -> None:
    path = tmp_path / "settings.json"
    data = {
        "version": 8,
        "translation": {"debounce_ms": -999, "llm_debounce_ms": 99999},
        "llm": {"timeout_sec": 1, "max_tokens": 10},
        "files": {"max_file_size_mb": 0},
    }
    path.write_text(json.dumps(data), encoding="utf-8")
    loaded = load_settings(UIConfig(), path)
    assert loaded.debounce_ms == 100
    assert loaded.llm_debounce_ms == 10000
    assert loaded.llm.timeout_sec == 5
    assert loaded.llm.max_tokens == 64


def test_migrate_api_keys_legacy() -> None:
    data = migrate_settings({"version": 3, "llm": {"api_key": "secret", "provider": "openrouter"}})
    assert data["llm"]["api_keys"]["openrouter"] == "secret"


def test_migrate_v1_geometry() -> None:
    data = migrate_settings(
        {
            "version": 1,
            "window": {"geometry": "800x600+10+20", "streaming": True},
        }
    )
    assert data["version"] >= 2
    assert "translation" in data
