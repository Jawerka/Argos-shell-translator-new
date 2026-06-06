"""Константы приложения."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple


class TranslationConstants:
    MAX_CHARS_PER_CHUNK = 4000
    SENTENCE_WINDOW = 1
    DEBOUNCE_MS = 700
    TRANSLATE_CLI_TIMEOUT = 60
    HOTKEY_DELAY = 0.16
    QUEUE_POLL_INTERVAL_MS = 120
    SCROLL_SYNC_INTERVAL_MS = 120
    SCROLL_EPSILON = 0.003
    PROGRAMMATIC_SCROLL_LOCK_MS = 50
    WINDOW_SAVE_DEBOUNCE_MS = 500


class DefaultLanguages:
    LANGUAGES: Dict[str, str] = {
        "en": "English",
        "ru": "Русский",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "it": "Italiano",
        "pt": "Português",
        "uk": "Українська",
        "zh": "中文",
        "ja": "日本語",
        "ko": "한국어",
        "ar": "العربية",
        "hi": "हिन्दी",
        "tr": "Türkçe",
    }

    @classmethod
    def get_defaults(cls) -> Dict[str, str]:
        return cls.LANGUAGES.copy()


@dataclass
class UIConfig:
    title: str = "Argos Translate"
    width: int = 1000
    height: int = 700
    min_width: int = 800
    min_height: int = 600
    padding: int = 0
    font_main: Tuple[str, int] = ("Segoe UI", 11)
    font_text: Tuple[str, int] = ("Consolas", 12)
    font_small: Tuple[str, int] = ("Segoe UI", 9)
    font_title: Tuple[str, int, str] = ("Segoe UI", 11, "bold")
