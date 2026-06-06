"""Пресеты LLM-провайдеров (D10) и шаблон системного промпта."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class LLMProviderPreset:
    id: str
    label: str
    default_base_url: str
    api_key_required: bool
    auth_header: str = "Bearer"
    cloud_warning: bool = False


PROVIDERS: Dict[str, LLMProviderPreset] = {
    "local": LLMProviderPreset(
        "local",
        "LOCAL",
        "http://192.168.88.41:8989/v1",
        False,
    ),
    "openrouter": LLMProviderPreset(
        "openrouter",
        "OpenRouter",
        "https://openrouter.ai/api/v1",
        True,
        cloud_warning=True,
    ),
    "custom": LLMProviderPreset(
        "custom",
        "Custom",
        "",
        False,
    ),
}

DEFAULT_SYSTEM_PROMPT = """Ты — профессиональный переводчик.

Задача: переведи текст пользователя с языка «{source_lang}» ({source_code}) на язык «{target_lang}» ({target_code}).

Правила:
1. Выводи ТОЛЬКО перевод — без пояснений, примечаний и метаданных.
2. Сохраняй структуру оригинала: абзацы, переносы строк, списки, нумерацию.
3. Для Markdown (заголовки #, код ```, ссылки) сохраняй разметку; переводи только видимый текст.
4. Имена собственные, бренды, URL — оставляй как в оригинале, если нет устоявшегося перевода.
5. Сохраняй тон и стиль оригинала (нейтральный / формальный / разговорный).
6. Не добавляй контент, которого нет в исходном тексте.
7. Если текст уже на целевом языке — верни его без изменений.

Языки заданы настройками приложения. Следуй им строго."""


def get_provider(provider_id: str) -> LLMProviderPreset:
    return PROVIDERS.get(provider_id, PROVIDERS["custom"])


def get_provider_labels() -> list[str]:
    return [p.label for p in PROVIDERS.values()]


def provider_id_from_label(label: str) -> str:
    for pid, preset in PROVIDERS.items():
        if preset.label == label:
            return pid
    return "custom"


def resolve_base_url(provider_id: str, base_url: str, provider_urls: Dict[str, str]) -> str:
    if base_url.strip():
        return base_url.strip().rstrip("/")
    preset = get_provider(provider_id)
    if preset.default_base_url:
        return preset.default_base_url.rstrip("/")
    return (provider_urls.get(provider_id) or "").strip().rstrip("/")


def get_default_system_prompt() -> str:
    return DEFAULT_SYSTEM_PROMPT
