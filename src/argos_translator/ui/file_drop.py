"""Drag & Drop файлов на окно (Windows, опционально windnd)."""

from __future__ import annotations

import logging
import sys
from typing import Callable, Optional

logger = logging.getLogger("ArgosStreaming")


def setup_file_drop(widget, on_file_path: Callable[[str], None]) -> bool:
    """Подключить DnD если доступен пакет windnd (pip install windnd)."""
    if sys.platform != "win32":
        return False
    try:
        import windnd  # type: ignore[import-untyped]
    except ImportError:
        logger.debug("windnd not installed — drag & drop disabled")
        return False

    def _handler(files) -> None:
        try:
            if not files:
                return
            raw = files[0] if isinstance(files, (list, tuple)) else files
            if isinstance(raw, bytes):
                path = raw.decode("utf-8", errors="replace").strip("\x00")
            else:
                path = str(raw).strip("\x00")
            if path:
                on_file_path(path)
        except Exception as exc:
            logger.debug("file drop handler error: %s", exc)

    try:
        windnd.hook_dropfiles(widget, func=_handler)
        logger.info("File drag & drop enabled (windnd)")
        return True
    except Exception as exc:
        logger.debug("windnd hook failed: %s", exc)
        return False
