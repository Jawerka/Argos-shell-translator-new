"""Фабрика движков перевода."""

from __future__ import annotations

import threading
from typing import Dict, Literal, Union

from argos_translator.config.settings import AppSettings
from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.engines.llm_engine import LLMDisabledError, translate_stream

EngineName = Literal["argos", "llm"]


class LLMTranslateEngine:
    """Адаптер LLM под протокол TranslationEngine (сбор результата из stream)."""

    def __init__(self, settings: AppSettings, languages: Dict[str, str] | None = None) -> None:
        self._settings = settings
        self._languages = languages or {}

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        assert_llm_enabled(self._settings)
        result: list[str] = []
        error: list[str] = []
        done = threading.Event()
        cancel = threading.Event()

        def on_token(token: str) -> None:
            result.append(token)

        def on_done(full: str) -> None:
            if full:
                result.clear()
                result.append(full)
            done.set()

        def on_error(msg: str) -> None:
            error.append(msg)
            done.set()

        translate_stream(
            self._settings.llm,
            text,
            from_code,
            to_code,
            self._languages,
            on_token,
            on_done,
            on_error,
            cancel,
        )
        done.wait(timeout=self._settings.llm.timeout_sec + 5)
        if error:
            raise RuntimeError(error[0])
        return "".join(result)


Engine = Union[TranslateEngine, LLMTranslateEngine]


def create_argos_engine() -> TranslateEngine:
    return TranslateEngine()


def is_llm_available(settings: AppSettings) -> bool:
    return bool(settings.llm.enabled)


def assert_llm_enabled(settings: AppSettings) -> None:
    if not settings.llm.enabled:
        raise LLMDisabledError()


def create_engine(
    name: EngineName,
    settings: AppSettings,
    *,
    languages: Dict[str, str] | None = None,
) -> Engine:
    if name == "argos":
        return create_argos_engine()
    if name == "llm":
        assert_llm_enabled(settings)
        return LLMTranslateEngine(settings, languages)
    raise ValueError(f"Unknown engine: {name}")
