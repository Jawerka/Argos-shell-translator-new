"""Тесты llm_engine (промпт, чанки, SSE)."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

from argos_translator.config.settings import LLMSettings
from argos_translator.engines.llm_engine import (
    LLMDisabledError,
    LLMConfigError,
    _parse_sse_token,
    _should_fallback_to_completions,
    _split_paragraph_chunks,
    build_request_context,
    build_system_prompt,
    fetch_models,
    translate_stream,
)


def test_build_system_prompt_substitution() -> None:
    llm = LLMSettings(system_prompt="From {source_code} to {target_code}")
    result = build_system_prompt(llm, "en", "ru", {"en": "English", "ru": "Russian"})
    assert "From en to ru" in result


def test_split_paragraph_chunks_single() -> None:
    assert _split_paragraph_chunks("short text") == ["short text"]


def test_split_paragraph_chunks_multiple() -> None:
    para = "word " * 2000
    text = f"{para}\n\n{para}"
    chunks = _split_paragraph_chunks(text, max_chars=3000)
    assert len(chunks) >= 2
    assert "".join(chunks).replace("\n\n", "")  # non-empty


def test_split_paragraph_chunks_overlap() -> None:
    p1 = "A" * 4000
    p2 = "B" * 4000
    p3 = "C" * 4000
    text = f"{p1}\n\n{p2}\n\n{p3}"
    chunks = _split_paragraph_chunks(text, max_chars=5000)
    assert len(chunks) >= 2
    assert p2[:20] in chunks[1]


def test_parse_sse_completions_token() -> None:
    line = 'data: {"choices":[{"text":"Hi"}]}'
    assert _parse_sse_token(line) == "Hi"


def test_should_fallback_to_completions() -> None:
    assert _should_fallback_to_completions(404, "chat/completions not found") is True
    assert _should_fallback_to_completions(404, "model not found") is False


def test_build_request_context_disabled() -> None:
    llm = LLMSettings(enabled=False)
    try:
        build_request_context(llm)
        assert False
    except LLMDisabledError:
        pass


def test_translate_stream_timeout_retries(monkeypatch) -> None:
    import httpx

    llm = LLMSettings(
        enabled=True,
        provider="local",
        base_url="http://127.0.0.1:8080/v1",
        model="test",
        stream=False,
        timeout_sec=5,
    )
    calls = {"n": 0}
    done: list[str] = []
    errors: list[str] = []

    class FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": "OK"}}]}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            calls["n"] += 1
            if calls["n"] == 1:
                raise httpx.TimeoutException("timeout")
            return FakeResp()

    monkeypatch.setattr("httpx.Client", FakeClient)

    translate_stream(
        llm,
        "Hello",
        "en",
        "ru",
        {},
        lambda _t: None,
        lambda t: done.append(t),
        lambda e: errors.append(e),
        threading.Event(),
    )
    assert calls["n"] == 2
    assert done == ["OK"]
    assert not errors


def test_translate_stream_completions_fallback(monkeypatch) -> None:
    llm = LLMSettings(
        enabled=True,
        provider="local",
        base_url="http://127.0.0.1:8080/v1",
        model="test",
        stream=False,
    )
    done: list[str] = []
    posts: list[str] = []

    class FakeResp:
        status_code = 404
        text = "chat/completions not found"
        request = MagicMock()

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"text": "Legacy"}]}

    class FakeRespOk:
        status_code = 200
        text = ""
        request = MagicMock()

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"text": "Legacy"}]}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            posts.append(url)
            if "chat/completions" in url:
                return FakeResp()
            return FakeRespOk()

    monkeypatch.setattr("httpx.Client", FakeClient)

    translate_stream(
        llm,
        "Hello",
        "en",
        "ru",
        {},
        lambda _t: None,
        lambda t: done.append(t),
        lambda _e: None,
        threading.Event(),
    )
    assert any("completions" in u for u in posts)
    assert done == ["Legacy"]


def test_parse_sse_token_delta() -> None:
    line = 'data: {"choices":[{"delta":{"content":"Hi"}}]}'
    assert _parse_sse_token(line) == "Hi"


def test_parse_sse_token_done() -> None:
    assert _parse_sse_token("data: [DONE]") is None


def test_fetch_models_disabled() -> None:
    llm = LLMSettings(enabled=False)
    try:
        fetch_models(llm)
        assert False, "expected LLMDisabledError"
    except LLMDisabledError:
        pass


def test_fetch_models_success(monkeypatch) -> None:
    llm = LLMSettings(enabled=True, provider="local", base_url="http://127.0.0.1:8080/v1")

    class FakeResp:
        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"data": [{"id": "model-a"}, {"id": "model-b"}]}

    class FakeClient:
        def __init__(self, timeout=10.0):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def get(self, url, headers=None):
            return FakeResp()

    monkeypatch.setattr("httpx.Client", FakeClient)
    models = fetch_models(llm, timeout=1.0)
    assert models == ["model-a", "model-b"]


def test_translate_stream_non_stream(monkeypatch) -> None:
    llm = LLMSettings(
        enabled=True,
        provider="local",
        base_url="http://127.0.0.1:8080/v1",
        model="test",
        stream=False,
    )
    tokens: list[str] = []
    done: list[str] = []
    errors: list[str] = []
    cancel = threading.Event()

    class FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Привет"}}]}

    class FakeClient:
        def __init__(self, timeout=None):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            return FakeResp()

    monkeypatch.setattr("httpx.Client", FakeClient)

    translate_stream(
        llm,
        "Hello",
        "en",
        "ru",
        {"en": "English", "ru": "Russian"},
        on_token=lambda t: tokens.append(t),
        on_done=lambda t: done.append(t),
        on_error=lambda e: errors.append(e),
        cancel_event=cancel,
    )
    assert not errors
    assert done == ["Привет"]
