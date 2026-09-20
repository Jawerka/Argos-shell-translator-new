"""Диагностический лог детекции языка (logger ArgosDetect → detect.log)."""

from __future__ import annotations

import logging
import re
from typing import Optional

detect_logger = logging.getLogger("ArgosDetect")

_WORD_RE = re.compile(r"\S+")
_MAX_WORD_LEN = 24


def peek_words(text: str, n: int = 3) -> str:
    """Первые n слов для лога (длинные слова обрезаются), без полного текста."""
    if not text or not str(text).strip():
        return ""
    words: list[str] = []
    for match in _WORD_RE.finditer(str(text).strip()):
        raw = match.group(0)
        if len(raw) > _MAX_WORD_LEN:
            raw = raw[:_MAX_WORD_LEN] + "…"
        words.append(raw)
        if len(words) >= n:
            break
    return " ".join(words)


def detect_info(message: str, *args: object) -> None:
    """INFO в ArgosDetect (если хендлер не настроен — silently no-op через root)."""
    detect_logger.info(message, *args)


def detect_path_hint() -> Optional[str]:
    """Путь к detect.log из первого FileHandler, если есть."""
    for handler in detect_logger.handlers:
        base = getattr(handler, "baseFilename", None)
        if base:
            return str(base)
    return None
