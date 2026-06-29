"""Тесты файлового workflow в TranslatorApp."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from argos_translator.app import TranslatorApp
from argos_translator.services.document_io import DecodedFile, DocumentIOError


def test_open_file_path_loads_and_translates(mock_translator_app, tmp_path: Path) -> None:
    app = mock_translator_app
    src = tmp_path / "doc.txt"
    src.write_text("Hello file content here", encoding="utf-8")
    app.translate = MagicMock()
    app._update_window_title = MagicMock()
    app._update_document_status = MagicMock()

    decoded = DecodedFile(text="Hello file content here", encoding="utf-8", path=src, confidence=1.0)
    with patch("argos_translator.app.read_text_file", return_value=decoded):
        TranslatorApp._open_file_path(app, str(src))

    app.src_panel.set_text.assert_called_once_with("Hello file content here")
    app.translate.assert_called_once()
    assert app._document_path == src


def test_open_file_path_shows_error_on_io_failure(mock_translator_app) -> None:
    app = mock_translator_app
    with patch("argos_translator.app.read_text_file", side_effect=DocumentIOError("too large")):
        with patch("argos_translator.app.messagebox.showerror") as show_error:
            TranslatorApp._open_file_path(app, "/missing/file.txt")

    show_error.assert_called_once()
    app.translate.assert_not_called()


def test_file_save_translation_writes_file(mock_translator_app, tmp_path: Path) -> None:
    app = mock_translator_app
    app._document_path = tmp_path / "readme.md"
    app.translation_tabs.get_active_engine.return_value = "argos"
    app.translation_tabs.get_active_text.return_value = "Перевод"
    app._document_encoding = "utf-8"

    out_path = tmp_path / "readme_translated.md"
    with patch("argos_translator.app.filedialog.asksaveasfilename", return_value=str(out_path)):
        with patch("argos_translator.app.write_text_file") as write_fn:
            with patch("argos_translator.app.messagebox.showinfo"):
                TranslatorApp._file_save_translation(app)

    write_fn.assert_called_once()
    assert write_fn.call_args[0][0] == out_path
    assert write_fn.call_args[0][1] == "Перевод"


def test_file_save_both_writes_argos_and_llm(mock_translator_app, tmp_path: Path) -> None:
    app = mock_translator_app
    app._document_path = tmp_path / "doc.txt"
    app._document_encoding = "utf-8"
    app.translation_tabs.get_argos_text.return_value = "Argos out"
    app.translation_tabs.get_llm_text.return_value = "LLM out"
    app.settings.files.output_suffix = "_translated"

    with patch("argos_translator.app.write_text_file") as write_fn:
        with patch("argos_translator.app.messagebox.showinfo"):
            TranslatorApp._file_save_both(app)

    assert write_fn.call_count == 2
    paths = [call.args[0] for call in write_fn.call_args_list]
    assert any("translated" in p.name and "llm" not in p.name for p in paths)
    assert any("llm" in p.name for p in paths)
