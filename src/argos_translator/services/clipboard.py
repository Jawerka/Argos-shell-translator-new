"""Захват текста из буфера обмена (Ctrl+C simulation)."""

from __future__ import annotations

import logging
import time
from typing import Callable, Optional

from argos_translator.config.constants import TranslationConstants
from argos_translator.utils.imports import (
    KEYBOARD_MODULE,
    KEYBOARD_STATUS,
    PYPERCLIP_MODULE,
    PYPERCLIP_STATUS,
    ImportStatus,
)

logger = logging.getLogger("ArgosStreaming")


def clipboard_available() -> bool:
    return (
        PYPERCLIP_STATUS == ImportStatus.SUCCESS
        and PYPERCLIP_MODULE is not None
        and KEYBOARD_STATUS == ImportStatus.SUCCESS
        and KEYBOARD_MODULE is not None
    )


def capture_selection_text(*, restore_original: bool = True) -> Optional[str]:
    """
    Симулировать Ctrl+C и прочитать буфер обмена.

    При restore_original=True восстанавливает предыдущее содержимое буфера.
    """
    if not clipboard_available():
        logger.warning("Clipboard capture unavailable: requires pyperclip and keyboard")
        return None

    old_text: Optional[str] = None
    try:
        old_text = PYPERCLIP_MODULE.paste()
    except Exception:
        pass

    try:
        send_fn = getattr(KEYBOARD_MODULE, "send", None)
        if callable(send_fn):
            send_fn("ctrl+c")
    except Exception:
        logger.debug("keyboard.send failed")

    time.sleep(TranslationConstants.HOTKEY_DELAY)

    try:
        text = PYPERCLIP_MODULE.paste()
    except Exception:
        text = ""

    if restore_original and old_text is not None and text != old_text:
        try:
            PYPERCLIP_MODULE.copy(old_text)
        except Exception:
            pass

    text = (text or "").strip()
    return text or None
