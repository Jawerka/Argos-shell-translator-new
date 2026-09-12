"""Геометрия окна в settings.json — без Tk/CustomTkinter (нужно sidecar)."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional

from argos_translator.config.constants import UIConfig

GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)(?:\+(-?\d+)\+(-?\d+))?$")


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
        m = GEOMETRY_RE.match(geometry.strip())
        if not m:
            return cls(width=cfg.width, height=cfg.height)
        w, h = int(m.group(1)), int(m.group(2))
        x = int(m.group(3)) if m.group(3) is not None else 100
        y = int(m.group(4)) if m.group(4) is not None else 100
        return cls(x=x, y=y, width=w, height=h)
