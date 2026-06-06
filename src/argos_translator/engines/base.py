"""Протокол движка перевода."""

from __future__ import annotations

from typing import Protocol


class TranslationEngine(Protocol):
    def translate(self, text: str, from_code: str, to_code: str) -> str: ...
