"""Режимы раскладки редактора: две панели или одна на всю ширину."""

from __future__ import annotations

from typing import Literal

EditorLayout = Literal["split", "source", "translation"]
EditorPanel = Literal["source", "translation"]

_VALID_LAYOUTS = frozenset({"split", "source", "translation"})


def normalize_editor_layout(value: str) -> EditorLayout:
    if value in _VALID_LAYOUTS:
        return value  # type: ignore[return-value]
    return "split"


def toggle_layout_for_panel(current: EditorLayout, panel: EditorPanel) -> EditorLayout:
    if panel == "source":
        return "split" if current == "source" else "source"
    return "split" if current == "translation" else "translation"


def apply_editor_layout(
    panels,
    src_panel,
    translation_tabs,
    mode: EditorLayout,
    *,
    gap: int,
) -> None:
    """Показать split / только исходник / только перевод."""
    half_gap = max(0, gap // 2)
    if mode == "split":
        src_panel.grid(row=0, column=0, columnspan=1, sticky="nsew", padx=(0, half_gap))
        translation_tabs.grid(row=0, column=1, columnspan=1, sticky="nsew", padx=(half_gap, 0))
    elif mode == "source":
        translation_tabs.grid_remove()
        src_panel.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=0)
    else:
        src_panel.grid_remove()
        translation_tabs.grid(row=0, column=0, columnspan=2, sticky="nsew", padx=0)
