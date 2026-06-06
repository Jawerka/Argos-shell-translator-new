"""Тесты clipboard capture."""

from __future__ import annotations

from argos_translator.services import clipboard
from argos_translator.utils.imports import ImportStatus


def test_clipboard_available_false_when_missing(monkeypatch) -> None:
    monkeypatch.setattr(clipboard, "PYPERCLIP_STATUS", ImportStatus.MISSING)
    assert clipboard.clipboard_available() is False


def test_capture_returns_none_when_unavailable(monkeypatch) -> None:
    monkeypatch.setattr(clipboard, "clipboard_available", lambda: False)
    assert clipboard.capture_selection_text() is None
