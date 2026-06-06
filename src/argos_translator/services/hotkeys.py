"""Глобальные горячие клавиши (keyboard)."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from argos_translator.utils.imports import KEYBOARD_MODULE, KEYBOARD_STATUS, ImportStatus

logger = logging.getLogger("ArgosStreaming")


def hotkeys_available() -> bool:
    return KEYBOARD_STATUS == ImportStatus.SUCCESS and KEYBOARD_MODULE is not None


def register_global_hotkey(
    hotkey: str,
    callback: Callable[[], None],
    *,
    suppress: bool = True,
) -> bool:
    """Зарегистрировать глобальную горячую клавишу. Возвращает True при успехе."""
    if not hotkeys_available():
        return False
    try:
        add_hotkey = getattr(KEYBOARD_MODULE, "add_hotkey", None)
        if not callable(add_hotkey):
            return False
        add_hotkey(hotkey, callback, suppress=suppress)
        logger.info("Global hotkey registered: %s", hotkey)
        return True
    except Exception as exc:
        logger.warning("Failed to register hotkey %s: %s", hotkey, exc)
        return False
