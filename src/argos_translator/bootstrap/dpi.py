"""DPI awareness для Windows — вызывать до tk.Tk()."""

from __future__ import annotations

import logging
import sys

logger = logging.getLogger("ArgosStreaming")


def enable_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        logger.debug("DPI awareness: Per-Monitor V2")
    except Exception:
        try:
            import ctypes

            ctypes.windll.user32.SetProcessDPIAware()
            logger.debug("DPI awareness: SetProcessDPIAware fallback")
        except Exception as exc:
            logger.debug("DPI awareness not set: %s", exc)


def log_dpi_info(root) -> None:
    """Логировать DPI/scaling после создания Tk (Windows)."""
    if sys.platform != "win32":
        return
    try:
        scaling = float(root.tk.call("tk", "scaling"))
        logger.info("Tk scaling: %.2f", scaling)
    except Exception as exc:
        logger.debug("Tk scaling unavailable: %s", exc)
    try:
        from argos_translator.ui.window_state import WindowStateManager

        ratio_x, ratio_y = WindowStateManager._measure_winfo_geometry_ratio(root)
        if ratio_x > 1.01 or ratio_y > 1.01:
            logger.info(
                "Window size units: geometry uses logical px, winfo/geometry ratio %.2f x %.2f",
                ratio_x,
                ratio_y,
            )
    except Exception as exc:
        logger.debug("Geometry ratio unavailable: %s", exc)
    try:
        import ctypes

        hwnd = root.winfo_id()
        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
        logger.info("Window DPI: %s", dpi)
    except Exception as exc:
        logger.debug("GetDpiForWindow unavailable: %s", exc)
    logger.info("Windows version: %s", sys.getwindowsversion())
