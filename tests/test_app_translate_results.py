"""Тесты сборки результатов Argos из очереди."""

from __future__ import annotations

from unittest.mock import MagicMock

from argos_translator.app import TranslatorApp


def test_handle_translate_results_reassembles_paragraphs(mock_translator_app) -> None:
    app = mock_translator_app
    app.coord.start_argos(1, 3)
    app._update_paragraph_offsets = MagicMock()

    TranslatorApp._handle_translate_results(
        app,
        [(1, 0, "Hello", 0), (1, 1, "world.", 0), (1, 2, "Second para.", 1)],
    )

    app.translation_tabs.set_argos_text.assert_called()
    final_text = app.translation_tabs.set_argos_text.call_args[0][0]
    assert "Hello world." in final_text
    assert "Second para." in final_text
    assert "\n\n" in final_text


def test_handle_translate_results_ignores_stale_job(mock_translator_app) -> None:
    app = mock_translator_app
    app.coord.start_argos(2, 1)
    app._update_paragraph_offsets = MagicMock()

    TranslatorApp._handle_translate_results(app, [(1, 0, "stale", 0)])

    app.translation_tabs.set_argos_text.assert_not_called()


def test_handle_translate_results_updates_progress(mock_translator_app) -> None:
    app = mock_translator_app
    app.coord.start_argos(1, 2)
    app._update_combined_status = MagicMock()
    app._update_paragraph_offsets = MagicMock()

    TranslatorApp._handle_translate_results(app, [(1, 0, "A", 0)])

    app.translate_status_var.set.assert_called()
    status = app.translate_status_var.set.call_args[0][0]
    assert "1/2" in status
