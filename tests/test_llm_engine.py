"""Тесты llm_engine (промпт, чанки, SSE)."""

from __future__ import annotations

import threading
from unittest.mock import MagicMock

from argos_translator.config.settings import LLMSettings
from argos_translator.engines.llm_engine import (
    LLMDisabledError,
    LLMConfigError,
    _adaptive_chunk_timeout,
    _adaptive_max_tokens,
    _build_chunk_user_content,
    _join_chunk_outputs,
    _parse_sse_token,
    _should_fallback_to_completions,
    _split_llm_chunks,
    _split_paragraph_chunks,
    _translated_tail,
    build_request_context,
    build_system_prompt,
    fetch_models,
    llm_config_error,
    translate_stream,
)


def test_llm_config_error_none_when_ok() -> None:
    llm = LLMSettings(enabled=True, provider="local", base_url="http://127.0.0.1:8080/v1")
    assert llm_config_error(llm) is None


def test_build_system_prompt_substitution() -> None:
    llm = LLMSettings(system_prompt="From {source_code} to {target_code}")
    result = build_system_prompt(llm, "en", "ru", {"en": "English", "ru": "Russian"})
    assert "From en to ru" in result


def test_build_system_prompt_multi_part() -> None:
    llm = LLMSettings()
    result = build_system_prompt(llm, "en", "ru", {}, multi_part=True)
    assert "sequential parts" in result


def test_split_paragraph_chunks_single() -> None:
    assert _split_paragraph_chunks("short text") == ["short text"]


def test_split_paragraph_chunks_multiple() -> None:
    para = "word " * 2000
    text = f"{para}\n\n{para}"
    chunks = _split_paragraph_chunks(text, max_chars=3000)
    assert len(chunks) >= 2


def test_split_llm_chunks_disjoint_coverage() -> None:
    p1 = "A" * 4000
    p2 = "B" * 4000
    p3 = "C" * 4000
    text = f"{p1}\n\n{p2}\n\n{p3}"
    chunks = _split_llm_chunks(text, max_chars=5000)
    assert len(chunks) >= 2
    rebuilt = "".join(chunk.translate_text for chunk in chunks)
    assert rebuilt == text


def test_split_llm_chunks_single_long_paragraph() -> None:
    text = "Sentence one. " * 1200
    assert len(text) > 15000
    chunks = _split_llm_chunks(text, max_chars=3500)
    assert len(chunks) >= 4
    assert all(len(c.translate_text) <= 4000 for c in chunks)


def test_split_llm_chunks_context_on_second_chunk() -> None:
    p1 = "First paragraph here."
    p2 = "Second paragraph here."
    text = f"{p1}\n\n{p2}"
    chunks = _split_llm_chunks(p1 + "\n\n" + "x" * 4000 + "\n\n" + p2, max_chars=3500)
    assert len(chunks) >= 2
    assert chunks[1].context_text


def test_join_chunk_outputs() -> None:
    assert _join_chunk_outputs(["TA", "\n\nTB"], []) == "TA\n\nTB"


def test_adaptive_limits() -> None:
    assert _adaptive_max_tokens(1000, 4096) >= 4096
    assert _adaptive_max_tokens(3500, 4096, file_mode=True) <= 2048
    assert _adaptive_max_tokens(5000, 4096, file_mode=True) <= 2048
    assert _adaptive_chunk_timeout(6000, 120, file_mode=True) >= 750
    assert _adaptive_chunk_timeout(6000, 120) >= 200


def test_parse_sse_token_reasoning() -> None:
    line = 'data: {"choices":[{"delta":{"reasoning_content":"Перевод"}}]}'
    assert _parse_sse_token(line) == "Перевод"


def test_finalize_stream_text_prefers_content() -> None:
    from argos_translator.engines.llm_engine import _finalize_stream_text

    assert _finalize_stream_text("Answer", "Thinking") == "Answer"
    assert _finalize_stream_text("", "Fallback") == "Fallback"


def test_translated_tail() -> None:
    text = "word " * 100
    tail = _translated_tail(text, max_chars=50)
    assert len(tail) <= 50
    assert tail in text


def test_build_chunk_user_content_with_context() -> None:
    from argos_translator.engines.llm_engine import LlmChunk

    chunk = LlmChunk(translate_text="New part.", context_text="Old source.")
    content = _build_chunk_user_content(
        chunk, 1, 2, "txt", "Previous translation.", use_context=True
    )
    assert "do not translate again" in content
    assert "Previous translation ended" in content
    assert "New part." in content


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


def test_translate_stream_multi_chunk_progress(monkeypatch) -> None:
    llm = LLMSettings(
        enabled=True,
        provider="local",
        base_url="http://127.0.0.1:8080/v1",
        model="test",
        stream=False,
        file_chunk_max_chars=100,
    )
    progress: list[tuple[int, int]] = []
    text = ("Paragraph one text. " * 20) + "\n\n" + ("Paragraph two text. " * 20)

    class FakeResp:
        status_code = 200

        def raise_for_status(self) -> None:
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Translated"}}]}

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
        text,
        "en",
        "ru",
        {},
        lambda _t: None,
        lambda t: None,
        lambda _e: None,
        threading.Event(),
        file_type="txt",
        on_chunk_progress=lambda d, t: progress.append((d, t)),
    )
    assert len(progress) >= 2
    assert progress[-1][0] == progress[-1][1]


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
