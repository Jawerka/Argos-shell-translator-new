"""Тесты пресетов LLM-провайдеров."""

from __future__ import annotations

from argos_translator.config.llm_providers import (
    get_provider,
    get_provider_labels,
    provider_id_from_label,
    resolve_base_url,
)


def test_provider_labels() -> None:
    labels = get_provider_labels()
    assert "LOCAL" in labels
    assert "OpenRouter" in labels


def test_openrouter_requires_api_key() -> None:
    preset = get_provider("openrouter")
    assert preset.api_key_required is True
    assert preset.cloud_warning is True


def test_local_no_api_key_required() -> None:
    preset = get_provider("local")
    assert preset.api_key_required is False


def test_provider_id_from_label() -> None:
    assert provider_id_from_label("LOCAL") == "local"
    assert provider_id_from_label("OpenRouter") == "openrouter"


def test_resolve_base_url_prefers_explicit() -> None:
    url = resolve_base_url("local", "http://127.0.0.1:8080/v1", {})
    assert url == "http://127.0.0.1:8080/v1"


def test_resolve_base_url_fallback_to_preset() -> None:
    url = resolve_base_url("openrouter", "", {})
    assert url == "https://openrouter.ai/api/v1"
