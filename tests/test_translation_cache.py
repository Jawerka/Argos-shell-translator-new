"""Тесты LRU-кэша переводов."""

from __future__ import annotations

from argos_translator.services.translation_cache import TranslationCache


def test_cache_hit_and_miss() -> None:
    cache = TranslationCache(max_size=10)
    assert cache.get("hello", "en", "ru") is None
    cache.put("hello", "en", "ru", "привет")
    assert cache.get("hello", "en", "ru") == "привет"


def test_cache_lru_eviction() -> None:
    cache = TranslationCache(max_size=2)
    cache.put("a", "en", "ru", "A")
    cache.put("b", "en", "ru", "B")
    cache.put("c", "en", "ru", "C")
    assert cache.get("a", "en", "ru") is None
    assert cache.get("b", "en", "ru") == "B"
    assert cache.get("c", "en", "ru") == "C"


def test_cache_key_includes_language_pair() -> None:
    cache = TranslationCache(max_size=10)
    cache.put("text", "en", "ru", "RU")
    assert cache.get("text", "en", "de") is None
    assert cache.get("text", "en", "ru") == "RU"
