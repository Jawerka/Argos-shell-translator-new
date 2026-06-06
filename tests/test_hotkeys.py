"""Тесты hotkeys service."""

from __future__ import annotations

from argos_translator.services import hotkeys
from argos_translator.utils.imports import ImportStatus


def test_register_fails_when_keyboard_missing(monkeypatch) -> None:
    monkeypatch.setattr(hotkeys, "KEYBOARD_STATUS", ImportStatus.MISSING)
    assert hotkeys.register_global_hotkey("ctrl+c", lambda: None) is False
