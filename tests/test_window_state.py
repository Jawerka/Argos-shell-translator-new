"""Тесты WindowState и clamp."""

from __future__ import annotations

import customtkinter as ctk
import pytest

from argos_translator.config.constants import UIConfig
from argos_translator.ui.window_state import WindowState, WindowStateManager


def test_from_geometry_string() -> None:
    cfg = UIConfig()
    ws = WindowState.from_geometry_string("800x600+50+100", cfg)
    assert ws.width == 800
    assert ws.height == 600
    assert ws.x == 50
    assert ws.y == 100


def test_from_geometry_invalid_uses_defaults() -> None:
    cfg = UIConfig()
    ws = WindowState.from_geometry_string("invalid", cfg)
    assert ws.width == cfg.width
    assert ws.height == cfg.height


def test_clamp_keeps_window_on_screen() -> None:
    cfg = UIConfig(min_width=400, min_height=300)
    state = WindowState(x=5000, y=5000, width=1000, height=700)
    clamped = WindowStateManager.clamp_to_visible_area(state, cfg)
    assert clamped.x >= 0
    assert clamped.y >= 0
    assert clamped.width >= cfg.min_width
    assert clamped.height >= cfg.min_height


def test_clamp_shrinks_oversized_window() -> None:
    cfg = UIConfig(min_width=400, min_height=300)
    state = WindowState(x=0, y=0, width=10000, height=10000)
    clamped = WindowStateManager.clamp_to_visible_area(state, cfg)
    assert clamped.width <= 10000
    assert clamped.height <= 10000


@pytest.fixture
def ctk_root():
    try:
        root = ctk.CTk()
    except Exception:
        pytest.skip("CustomTkinter unavailable (no display)")
    root.withdraw()
    yield root
    root.destroy()


def test_capture_uses_geometry_not_winfo(ctk_root: ctk.CTk) -> None:
    ctk_root.geometry("1000x700+100+100")
    ctk_root.deiconify()
    ctk_root.update_idletasks()

    captured = WindowStateManager.capture(ctk_root)
    parsed = WindowStateManager._parse_geometry(ctk_root.geometry())

    assert parsed is not None
    assert captured.width == parsed[0]
    assert captured.height == parsed[1]
    assert captured.geometry_units == "tk_geometry"


def test_geometry_roundtrip_stable(ctk_root: ctk.CTk) -> None:
    cfg = UIConfig()
    ctk_root.geometry("1000x700+100+100")
    ctk_root.deiconify()
    ctk_root.update_idletasks()

    for _ in range(3):
        state = WindowStateManager.capture(ctk_root)
        WindowStateManager.restore(ctk_root, state, cfg)
        ctk_root.update_idletasks()

    final = WindowStateManager.capture(ctk_root)
    assert final.width == 1000
    assert final.height == 700


def test_migrate_legacy_winfo_dimensions(ctk_root: ctk.CTk) -> None:
    ctk_root.geometry("1000x700+100+100")
    ctk_root.deiconify()
    ctk_root.update_idletasks()

    ratio_x, _ = WindowStateManager._measure_winfo_geometry_ratio(ctk_root)
    if ratio_x <= 1.01:
        pytest.skip("No DPI scaling on this display")

    legacy = WindowState(
        x=100,
        y=100,
        width=round(1000 * ratio_x),
        height=round(700 * ratio_x),
        geometry_units="legacy",
    )
    migrated = WindowStateManager._migrate_legacy_dimensions(ctk_root, legacy)
    assert migrated.width == 1000
    assert migrated.height == pytest.approx(700, abs=2)
    assert migrated.geometry_units == "tk_geometry"
