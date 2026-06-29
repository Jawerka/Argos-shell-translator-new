"""Тесты раскладки редактора."""

from __future__ import annotations

from unittest.mock import MagicMock

from argos_translator.ui.editor_layout import (
    apply_editor_layout,
    normalize_editor_layout,
    toggle_layout_for_panel,
)


def test_normalize_editor_layout_invalid() -> None:
    assert normalize_editor_layout("unknown") == "split"


def test_toggle_layout_for_panel_source() -> None:
    assert toggle_layout_for_panel("split", "source") == "source"
    assert toggle_layout_for_panel("source", "source") == "split"
    assert toggle_layout_for_panel("translation", "source") == "source"


def test_toggle_layout_for_panel_translation() -> None:
    assert toggle_layout_for_panel("split", "translation") == "translation"
    assert toggle_layout_for_panel("translation", "translation") == "split"
    assert toggle_layout_for_panel("source", "translation") == "translation"


def test_apply_editor_layout_split() -> None:
    panels = MagicMock()
    src = MagicMock()
    dst = MagicMock()
    apply_editor_layout(panels, src, dst, "split", gap=8)
    src.grid.assert_called_once()
    dst.grid.assert_called_once()
    src.grid_remove.assert_not_called()
    dst.grid_remove.assert_not_called()


def test_apply_editor_layout_source_only() -> None:
    panels = MagicMock()
    src = MagicMock()
    dst = MagicMock()
    apply_editor_layout(panels, src, dst, "source", gap=8)
    dst.grid_remove.assert_called_once()
    src.grid.assert_called_once_with(row=0, column=0, columnspan=2, sticky="nsew", padx=0)


def test_apply_editor_layout_translation_only() -> None:
    panels = MagicMock()
    src = MagicMock()
    dst = MagicMock()
    apply_editor_layout(panels, src, dst, "translation", gap=8)
    src.grid_remove.assert_called_once()
    dst.grid.assert_called_once_with(row=0, column=0, columnspan=2, sticky="nsew", padx=0)
