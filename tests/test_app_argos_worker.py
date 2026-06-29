"""Тесты Argos worker в TranslatorApp."""

from __future__ import annotations

from unittest.mock import MagicMock

from argos_translator.app import TranslatorApp


def test_translate_worker_cache_hit(mock_translator_app) -> None:
    app = mock_translator_app
    app.settings.behavior.translation_cache_enabled = True
    app._translation_cache.put("hello", "en", "ru", "привет")
    app.engine.translate = MagicMock(return_value="should not be called")

    TranslatorApp._translate_worker(app, 1, [("hello", 0, True)], "en", "ru")

    job_id, idx, output, para_idx = app.translate_queue.get_nowait()
    assert job_id == 1
    assert output == "привет"
    app.engine.translate.assert_not_called()


def test_translate_worker_cache_miss(mock_translator_app) -> None:
    app = mock_translator_app
    app.settings.behavior.translation_cache_enabled = True
    app.engine.translate = MagicMock(return_value="translated")

    TranslatorApp._translate_worker(app, 1, [("hello", 0, True)], "en", "ru")

    _, _, output, _ = app.translate_queue.get_nowait()
    assert output == "translated"
    app.engine.translate.assert_called_once_with("hello", "en", "ru")


def test_translate_worker_non_translatable_passthrough(mock_translator_app) -> None:
    app = mock_translator_app
    code = "```python\nprint(1)\n```"
    app.engine.translate = MagicMock()

    TranslatorApp._translate_worker(app, 1, [(code, 0, False)], "en", "ru")

    _, _, output, _ = app.translate_queue.get_nowait()
    assert output == code
    app.engine.translate.assert_not_called()


def test_translate_worker_stops_when_superseded(mock_translator_app) -> None:
    app = mock_translator_app
    app.coord.start_argos(1, 3)
    app.coord.signal_argos_restart()
    app.coord.start_argos(2, 3)
    app.engine.translate = MagicMock(return_value="x")

    TranslatorApp._translate_worker(
        app,
        1,
        [("one", 0, True), ("two", 1, True)],
        "en",
        "ru",
    )

    assert app.translate_queue.empty()


def test_translate_worker_chunk_error_queued(mock_translator_app) -> None:
    app = mock_translator_app
    app.engine.translate = MagicMock(side_effect=RuntimeError("backend down"))

    TranslatorApp._translate_worker(app, 1, [("hello", 0, True)], "en", "ru")

    _, _, output, _ = app.translate_queue.get_nowait()
    assert output.startswith("[Error:")
    assert "backend down" in output
