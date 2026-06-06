"""Проверка доступности LLM-сервера."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from argos_translator.config.settings import LLMSettings
from argos_translator.engines.llm_engine import check_connection

logger = logging.getLogger("ArgosStreaming")


class LLMStatus(str, Enum):
    AVAILABLE = "available"
    BUSY = "busy"
    OFFLINE = "offline"
    DISABLED = "disabled"


@dataclass
class _CacheEntry:
    status: LLMStatus
    checked_at: float


class LLMHealthService:
    def __init__(self, get_llm_settings: Callable[[], LLMSettings]) -> None:
        self._get_llm_settings = get_llm_settings
        self._cache: Optional[_CacheEntry] = None
        self._busy_until: float = 0.0
        self._lock = threading.Lock()

    def _llm(self) -> LLMSettings:
        return self._get_llm_settings()

    def mark_busy(self, seconds: float = 45.0) -> None:
        with self._lock:
            self._busy_until = time.monotonic() + seconds
            self._cache = _CacheEntry(LLMStatus.BUSY, time.monotonic())

    def cached_status(self) -> LLMStatus:
        llm = self._llm()
        if not llm.enabled:
            return LLMStatus.DISABLED

        with self._lock:
            if time.monotonic() < self._busy_until:
                return LLMStatus.BUSY
            if self._cache is not None:
                age = time.monotonic() - self._cache.checked_at
                if age < llm.health_check_ttl_sec:
                    return self._cache.status
        return self.check()

    def check(self) -> LLMStatus:
        llm = self._llm()
        if not llm.enabled:
            return LLMStatus.DISABLED

        with self._lock:
            if time.monotonic() < self._busy_until:
                return LLMStatus.BUSY

        try:
            ok = check_connection(llm, timeout=3.0)
            status = LLMStatus.AVAILABLE if ok else LLMStatus.OFFLINE
        except Exception as exc:
            logger.debug("LLM health check error: %s", exc)
            status = LLMStatus.OFFLINE

        with self._lock:
            self._cache = _CacheEntry(status, time.monotonic())
        return status

    def invalidate(self) -> None:
        with self._lock:
            self._cache = None
