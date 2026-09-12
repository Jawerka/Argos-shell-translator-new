"""Тесты LLM pipeline в TranslatorApp."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock, patch

from argos_translator.app import TranslatorApp
from argos_translator.services.llm_health import LLMStatus


def _enable_configured_llm(app: TranslatorApp) -> None:
    app.settings.llm.enabled = True
    app.settings.llm.provider = "local"
    app.settings.llm.base_url = "http://127.0.0.1:8080/v1"
    app.settings.llm.provider_urls = {"local": "http://127.0.0.1:8080/v1"}


def test_start_llm_translation_skips_when_offline(mock_translator_app) -> None:
    app = mock_translator_app
    _enable_configured_llm(app)
    app.llm_health.cached_status.return_value = LLMStatus.OFFLINE

    with patch.object(app.coord, "start_llm") as start_llm:
        TranslatorApp._start_llm_translation(app, 1, "text", "en", "ru")
        start_llm.assert_not_called()


def test_start_llm_translation_skips_when_not_configured(mock_translator_app) -> None:
    app = mock_translator_app
    app.settings.llm.enabled = True
    app.settings.llm.provider = "custom"
    app.settings.llm.base_url = ""
    app.settings.llm.provider_urls = {"custom": ""}

    with patch.object(app.coord, "start_llm") as start_llm:
        TranslatorApp._start_llm_translation(app, 1, "text", "en", "ru")
        start_llm.assert_not_called()

    msg = app.translation_tabs.set_llm_text.call_args[0][0]
    assert "не настроена" in msg.lower()
    assert "не настроена" in app.llm_status_text.lower()
    app.llm_health.cached_status.assert_not_called()


def test_start_llm_translation_skips_when_busy(mock_translator_app) -> None:
    app = mock_translator_app
    _enable_configured_llm(app)
    app.llm_health.cached_status.return_value = LLMStatus.BUSY

    with patch.object(app.coord, "start_llm") as start_llm:
        TranslatorApp._start_llm_translation(app, 1, "text", "en", "ru")
        start_llm.assert_not_called()

    assert "занята" in app.translation_tabs.set_llm_text.call_args[0][0].lower()


def test_start_llm_translation_starts_worker_when_available(mock_translator_app) -> None:
    app = mock_translator_app
    _enable_configured_llm(app)
    app.llm_health.cached_status.return_value = LLMStatus.AVAILABLE
    app.llm_translate_thread = None
    started = threading.Event()

    def fake_worker(*_args, **_kwargs):
        started.set()

    with patch.object(app.coord, "start_llm") as start_llm:
        with patch("argos_translator.app.threading.Thread") as thread_cls:
            thread_inst = MagicMock()

            def start():
                fake_worker()

            thread_inst.start = start
            thread_cls.return_value = thread_inst

            TranslatorApp._start_llm_translation(app, 1, "hello", "en", "ru")

        start_llm.assert_called_once_with(1)
    app.translation_tabs.begin_llm_stream.assert_called_once()
    assert started.is_set()


def test_llm_worker_on_done_partial_status(mock_translator_app) -> None:
    app = mock_translator_app
    app.coord.start_llm(1)

    def fake_translate_stream(_llm, _text, _fc, _tc, _langs, on_token, on_done, on_error, _cancel, **kwargs):
        on_token("Part one")
        on_done("Part one\n\n[LLM Error: таймаут запроса]")

    with patch("argos_translator.app.translate_stream", side_effect=fake_translate_stream):
        TranslatorApp._llm_worker(app, 1, "long text", "en", "ru")

    app.translation_tabs.end_llm_stream.assert_called_once()
    app.translation_tabs.set_tab_status.assert_called_with("llm", "partial")


def test_translate_stream_partial_chunk_error(monkeypatch) -> None:
    import httpx

    from argos_translator.config.settings import LLMSettings
    from argos_translator.engines.llm_engine import LlmChunk, translate_stream

    llm = LLMSettings(
        enabled=True,
        provider="local",
        base_url="http://127.0.0.1:8080/v1",
        model="test",
        stream=False,
    )
    text = "AAAA" * 200 + "\n\n" + "BBBB" * 200
    done: list[str] = []
    errors: list[str] = []
    call_count = {"n": 0}

    def fake_split(_text: str, _max_chars: int) -> list[LlmChunk]:
        return [
            LlmChunk(translate_text="part-one", split_level="test"),
            LlmChunk(translate_text="part-two", split_level="test"),
        ]

    monkeypatch.setattr(
        "argos_translator.engines.llm_engine._split_llm_chunks",
        fake_split,
    )

    class FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Chunk OK"}}]}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return FakeResp()
            raise httpx.ConnectError("refused")

    monkeypatch.setattr("httpx.Client", FakeClient)

    translate_stream(
        llm,
        text,
        "en",
        "ru",
        {},
        lambda _t: None,
        lambda t: done.append(t),
        lambda e: errors.append(e),
        threading.Event(),
        file_type="txt",
    )

    assert done
    assert "[LLM Error:" in done[0]
    assert "Chunk OK" in done[0]
    assert not errors
