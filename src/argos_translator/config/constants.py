"""Константы приложения."""

from __future__ import annotations

from typing import Dict


class TranslationConstants:
    MAX_CHARS_PER_CHUNK = 4000
    SENTENCE_WINDOW = 1
    TRANSLATE_CLI_TIMEOUT = 60


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
        "nl": "Nederlands",
        "pl": "Polski",
        "cs": "Čeština",
        "sv": "Svenska",
        "el": "Ελληνικά",
        "he": "עברית",
        "th": "ไทย",
    }

    @classmethod
    def get_defaults(cls) -> Dict[str, str]:
        return cls.LANGUAGES.copy()
