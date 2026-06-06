"""Тесты LLMHealthService."""

from __future__ import annotations

from argos_translator.config.settings import LLMSettings
from argos_translator.services.llm_health import LLMHealthService, LLMStatus


def _settings(**kwargs) -> LLMSettings:
    return LLMSettings(**kwargs)


def test_disabled_when_llm_off() -> None:
    svc = LLMHealthService(lambda: _settings(enabled=False))
    assert svc.check() == LLMStatus.DISABLED
    assert svc.cached_status() == LLMStatus.DISABLED


def test_mark_busy() -> None:
    svc = LLMHealthService(lambda: _settings(enabled=True, health_check_ttl_sec=60))
    svc.mark_busy(seconds=30)
    assert svc.cached_status() == LLMStatus.BUSY


def test_check_available(monkeypatch) -> None:
    svc = LLMHealthService(lambda: _settings(enabled=True, health_check_ttl_sec=60))

    monkeypatch.setattr(
        "argos_translator.services.llm_health.check_connection",
        lambda llm, timeout=3.0: True,
    )
    assert svc.check() == LLMStatus.AVAILABLE


def test_check_offline(monkeypatch) -> None:
    svc = LLMHealthService(lambda: _settings(enabled=True, health_check_ttl_sec=60))

    monkeypatch.setattr(
        "argos_translator.services.llm_health.check_connection",
        lambda llm, timeout=3.0: False,
    )
    assert svc.check() == LLMStatus.OFFLINE


def test_cache_ttl(monkeypatch) -> None:
    svc = LLMHealthService(lambda: _settings(enabled=True, health_check_ttl_sec=300))
    calls = {"n": 0}

    def fake_check(llm, timeout=3.0):
        calls["n"] += 1
        return True

    monkeypatch.setattr("argos_translator.services.llm_health.check_connection", fake_check)
    assert svc.check() == LLMStatus.AVAILABLE
    assert svc.cached_status() == LLMStatus.AVAILABLE
    assert calls["n"] == 1

    svc.invalidate()
    assert svc.cached_status() == LLMStatus.AVAILABLE
    assert calls["n"] == 2
