"""DPI-aware сохранение и восстановление геометрии окна."""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

import tkinter as tk

from argos_translator.config.constants import UIConfig

logger = logging.getLogger("ArgosStreaming")

_GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$")


@dataclass
class WindowState:
    state: str = "normal"
    x: int = 100
    y: int = 100
    width: int = 1000
    height: int = 700
    monitor_hint: Optional[Dict[str, Any]] = None
    dpi_scale: float = 1.0
    geometry_units: str = "legacy"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any], defaults: Optional["WindowState"] = None) -> "WindowState":
        base = defaults or cls()
        return cls(
            state=str(data.get("state", base.state)),
            x=int(data.get("x", base.x)),
            y=int(data.get("y", base.y)),
            width=int(data.get("width", base.width)),
            height=int(data.get("height", base.height)),
            monitor_hint=data.get("monitor_hint"),
            dpi_scale=float(data.get("dpi_scale", base.dpi_scale)),
            geometry_units=str(data.get("geometry_units", base.geometry_units)),
        )

    @classmethod
    def from_geometry_string(cls, geometry: str, cfg: UIConfig) -> "WindowState":
        m = _GEOMETRY_RE.match(geometry.strip())
        if not m:
            return cls(width=cfg.width, height=cfg.height)
        w, h = int(m.group(1)), int(m.group(2))
        x = int(m.group(3)) if m.group(3) is not None else 100
        y = int(m.group(4)) if m.group(4) is not None else 100
        return cls(x=x, y=y, width=w, height=h)


class WindowStateManager:
    @staticmethod
    def _parse_geometry(geometry: str) -> Optional[Tuple[int, int, int, int]]:
        m = _GEOMETRY_RE.match(geometry.strip())
        if not m:
            return None
        width = int(m.group(1))
        height = int(m.group(2))
        x = int(m.group(3)) if m.group(3) is not None else 0
        y = int(m.group(4)) if m.group(4) is not None else 0
        return width, height, x, y

    @staticmethod
    def _measure_winfo_geometry_ratio(root: tk.Tk) -> Tuple[float, float]:
        """Соотношение winfo (физ.) к geometry (лог. ед. Tk) на текущем DPI."""
        try:
            parsed = WindowStateManager._parse_geometry(root.geometry())
            if parsed is None:
                return 1.0, 1.0
            geo_w, geo_h, _, _ = parsed
            if geo_w < 10 or geo_h < 10:
                return 1.0, 1.0
            root.update_idletasks()
            winfo_w = max(root.winfo_width(), 1)
            winfo_h = max(root.winfo_height(), 1)
            return winfo_w / geo_w, winfo_h / geo_h
        except Exception:
            return 1.0, 1.0

    @staticmethod
    def _migrate_legacy_dimensions(root: tk.Tk, state: WindowState) -> WindowState:
        """Старые сохранения писали winfo_width/height — переводим в единицы geometry()."""
        if state.geometry_units == "tk_geometry":
            return state
        ratio_x, ratio_y = WindowStateManager._measure_winfo_geometry_ratio(root)
        if ratio_x <= 1.01 and ratio_y <= 1.01:
            return WindowState(
                state=state.state,
                x=state.x,
                y=state.y,
                width=state.width,
                height=state.height,
                monitor_hint=state.monitor_hint,
                dpi_scale=state.dpi_scale,
                geometry_units="tk_geometry",
            )
        width = max(1, round(state.width / ratio_x))
        height = max(1, round(state.height / ratio_y))
        logger.info(
            "Window geometry migrated from legacy winfo units: %sx%s -> %sx%s (DPI ratio %.2f/%.2f)",
            state.width,
            state.height,
            width,
            height,
            ratio_x,
            ratio_y,
        )
        return WindowState(
            state=state.state,
            x=state.x,
            y=state.y,
            width=width,
            height=height,
            monitor_hint=state.monitor_hint,
            dpi_scale=WindowStateManager._get_dpi_scale(root),
            geometry_units="tk_geometry",
        )

    @staticmethod
    def capture(root: tk.Tk) -> WindowState:
        try:
            state = str(root.state())
        except Exception:
            state = "normal"
        if state == "iconic":
            state = "normal"

        try:
            root.update_idletasks()
            parsed = WindowStateManager._parse_geometry(root.geometry())
            if parsed is None:
                return WindowState()
            width, height, x, y = parsed
        except Exception:
            return WindowState()

        hint = WindowStateManager._capture_monitor_hint(root)
        dpi_scale = WindowStateManager._get_dpi_scale(root)

        return WindowState(
            state=state if state in ("normal", "zoomed") else "normal",
            x=x,
            y=y,
            width=width,
            height=height,
            monitor_hint=hint,
            dpi_scale=dpi_scale,
            geometry_units="tk_geometry",
        )

    @staticmethod
    def restore(root: tk.Tk, state: WindowState, cfg: UIConfig, *, first_run: bool = False) -> None:
        if first_run:
            WindowStateManager._center_on_primary(root, cfg)
            return

        root.update_idletasks()
        state = WindowStateManager._migrate_legacy_dimensions(root, state)
        clamped = WindowStateManager.clamp_to_visible_area(state, cfg, root)
        try:
            root.geometry(f"{clamped.width}x{clamped.height}+{clamped.x}+{clamped.y}")
            root.update_idletasks()
            if clamped.state == "zoomed":
                try:
                    root.state("zoomed")
                except Exception:
                    pass
        except Exception as exc:
            logger.debug("restore geometry failed: %s", exc)
            WindowStateManager._center_on_primary(root, cfg)

    @staticmethod
    def clamp_to_visible_area(
        state: WindowState,
        cfg: UIConfig,
        root: Optional[tk.Tk] = None,
    ) -> WindowState:
        try:
            if root is not None:
                sw = root.winfo_screenwidth()
                sh = root.winfo_screenheight()
            else:
                import tkinter as _tk

                tmp = _tk.Tk()
                tmp.withdraw()
                sw = tmp.winfo_screenwidth()
                sh = tmp.winfo_screenheight()
                tmp.destroy()
        except Exception:
            sw, sh = 1920, 1080

        width = max(cfg.min_width, min(state.width, sw))
        height = max(cfg.min_height, min(state.height, sh))

        min_visible_w = max(int(width * 0.3), cfg.min_width)
        min_visible_h = max(int(height * 0.2), 80)

        x = state.x
        y = state.y

        if x + min_visible_w > sw:
            x = max(0, sw - width)
        if y + min_visible_h > sh:
            y = max(0, sh - height)
        if x < 0:
            x = 0
        if y < 0:
            y = 0
        if x + width > sw:
            width = max(cfg.min_width, sw - x)
        if y + height > sh:
            height = max(cfg.min_height, sh - y)

        return WindowState(
            state=state.state,
            x=x,
            y=y,
            width=width,
            height=height,
            monitor_hint=state.monitor_hint,
            dpi_scale=state.dpi_scale,
            geometry_units=state.geometry_units,
        )

    @staticmethod
    def _center_on_primary(root: tk.Tk, cfg: UIConfig) -> None:
        root.update_idletasks()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        x = max(0, (sw - cfg.width) // 2)
        y = max(0, (sh - cfg.height) // 2)
        try:
            root.geometry(f"{cfg.width}x{cfg.height}+{x}+{y}")
        except Exception:
            root.geometry(f"{cfg.width}x{cfg.height}")

    @staticmethod
    def _get_dpi_scale(root: tk.Tk) -> float:
        try:
            scaling = float(root.tk.call("tk", "scaling"))
            return round(scaling / 1.0, 2)
        except Exception:
            return 1.0

    @staticmethod
    def _capture_monitor_hint(root: tk.Tk) -> Optional[Dict[str, Any]]:
        if sys.platform != "win32":
            return None
        try:
            import ctypes
            from ctypes import wintypes

            hwnd = wintypes.HWND(root.winfo_id())
            MONITOR_DEFAULTTONEAREST = 2
            monitor = ctypes.windll.user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
            if not monitor:
                return None

            class RECT(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class MONITORINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", RECT),
                    ("rcWork", RECT),
                    ("dwFlags", ctypes.c_ulong),
                ]

            info = MONITORINFO()
            info.cbSize = ctypes.sizeof(MONITORINFO)
            if not ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(info)):
                return None

            work = info.rcWork
            dpi = 96
            try:
                MDT_EFFECTIVE_DPI = 0
                dpi_x = ctypes.c_uint()
                dpi_y = ctypes.c_uint()
                if ctypes.windll.shcore.GetDpiForMonitor(
                    monitor, MDT_EFFECTIVE_DPI, ctypes.byref(dpi_x), ctypes.byref(dpi_y)
                ) == 0:
                    dpi = int(dpi_x.value)
            except Exception:
                pass
            return {
                "work_area": [work.left, work.top, work.right, work.bottom],
                "dpi": dpi,
            }
        except Exception as exc:
            logger.debug("monitor hint capture failed: %s", exc)
            return None
