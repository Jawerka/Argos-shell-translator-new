"""Тесты точки входа translate() в TranslatorApp."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from argos_translator.app import TranslatorApp


def test_translate_skips_short_text(mock_translator_app) -> None:
    app = mock_translator_app
    app.src_panel.get_text.return_value = " "
    app._cancel_pending_translate_jobs = MagicMock()

    with patch.object(app.coord, "allocate_job") as alloc:
        TranslatorApp.translate(app)
        alloc.assert_not_called()


def test_translate_auto_detect_updates_languages(mock_translator_app) -> None:
    app = mock_translator_app
    app.src_panel.get_text.return_value = "Hello world, this is English text for detection."
    app.lang_widget.get_from_code.return_value = "auto"
    app.lang_widget.get_to_code.return_value = "ru"
    app._cancel_pending_translate_jobs = MagicMock()
    app._hide_file_progress = MagicMock()
    app._update_combined_status = MagicMock()
    app.translation_tabs.clear_argos = MagicMock()
    with patch.object(app.coord, "allocate_job", return_value=1):
        with patch("argos_translator.app.ModelManager") as mm_cls:
            mm_cls.return_value.has_pair.return_value = True
            with patch("argos_translator.app.threading.Thread") as thread_cls:
                thread_cls.return_value = MagicMock()
                TranslatorApp.translate(app, streaming=False)

    app.lang_widget.combo_from.set.assert_called()


def test_translate_streaming_does_not_start_llm_immediately(mock_translator_app) -> None:
    app = mock_translator_app
    app.src_panel.get_text.return_value = "Hello world"
    app.lang_widget.get_from_code.return_value = "en"
    app.lang_widget.get_to_code.return_value = "ru"
    app._cancel_pending_translate_jobs = MagicMock()
    app.translation_tabs.clear_argos = MagicMock()
    app._start_llm_translation = MagicMock()

    with patch.object(app.coord, "allocate_job", return_value=1):
        with patch("argos_translator.app.ModelManager") as mm_cls:
            mm_cls.return_value.has_pair.return_value = True
            with patch("argos_translator.app.threading.Thread") as thread_cls:
                thread_cls.return_value = MagicMock()
                TranslatorApp.translate(app, streaming=True)

    app._start_llm_translation.assert_not_called()


def test_translate_non_streaming_starts_llm(mock_translator_app) -> None:
    app = mock_translator_app
    app.src_panel.get_text.return_value = "Hello world"
    app.lang_widget.get_from_code.return_value = "en"
    app.lang_widget.get_to_code.return_value = "ru"
    app._cancel_pending_translate_jobs = MagicMock()
    app.translation_tabs.clear_argos = MagicMock()
    app._start_llm_translation = MagicMock()

    with patch.object(app.coord, "allocate_job", return_value=7):
        with patch("argos_translator.app.ModelManager") as mm_cls:
            mm_cls.return_value.has_pair.return_value = True
            with patch("argos_translator.app.threading.Thread") as thread_cls:
                thread_cls.return_value = MagicMock()
                TranslatorApp.translate(app, streaming=False)

    app._start_llm_translation.assert_called_once()
    args = app._start_llm_translation.call_args[0]
    assert args[0] == 7


def test_translate_skips_argos_when_no_model_pair(mock_translator_app) -> None:
    app = mock_translator_app
    app.src_panel.get_text.return_value = "Hello world"
    app.lang_widget.get_from_code.return_value = "en"
    app.lang_widget.get_to_code.return_value = "ru"
    app._cancel_pending_translate_jobs = MagicMock()
    app.translation_tabs.clear_argos = MagicMock()
    app._start_llm_translation = MagicMock()

    with patch.object(app.coord, "allocate_job", return_value=3):
        with patch.object(app.coord, "start_argos") as start_argos:
            with patch("argos_translator.app.ModelManager") as mm_cls:
                mm_cls.return_value.has_pair.return_value = False
                with patch("argos_translator.app.threading.Thread") as thread_cls:
                    TranslatorApp.translate(app, streaming=False)

    thread_cls.assert_not_called()
    start_argos.assert_not_called()
    app.translation_tabs.set_argos_text.assert_called()
    assert "нет модели" in app.translation_tabs.set_argos_text.call_args[0][0]
    app._start_llm_translation.assert_called_once()
