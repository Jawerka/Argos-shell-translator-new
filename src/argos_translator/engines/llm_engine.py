"""LLM-движок перевода (OpenAI-compatible API)."""

from __future__ import annotations

import json
import logging
import re
import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from argos_translator.config.llm_providers import (
    get_default_system_prompt,
    get_provider,
    resolve_base_url,
)
from argos_translator.config.settings import LLMSettings

logger = logging.getLogger("ArgosStreaming")

LLM_MAX_CHARS = 6000
UI_UPDATE_THROTTLE_MS = 50


class LLMDisabledError(Exception):
    pass


class LLMConfigError(Exception):
    pass


def current_api_key(llm: LLMSettings) -> str:
    return (llm.api_keys.get(llm.provider) or "").strip()


def build_system_prompt(
    llm: LLMSettings,
    from_code: str,
    to_code: str,
    languages: Dict[str, str],
) -> str:
    template = (llm.system_prompt or "").strip() or get_default_system_prompt()
    source_lang = languages.get(from_code, from_code.upper())
    target_lang = languages.get(to_code, to_code.upper())
    return template.format(
        source_lang=source_lang,
        target_lang=target_lang,
        source_code=from_code,
        target_code=to_code,
        formality="neutral",
    )


def _build_headers(llm: LLMSettings) -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    preset = get_provider(llm.provider)
    key = current_api_key(llm)
    auth_mode = llm.auth_header

    if auth_mode == "auto":
        send_auth = bool(key) and llm.provider != "local"
    elif auth_mode in ("Bearer", "api-key"):
        send_auth = bool(key)
    else:
        send_auth = bool(key)

    if send_auth and key:
        if auth_mode == "api-key":
            headers["api-key"] = key
        else:
            headers["Authorization"] = f"Bearer {key}"

    if llm.provider == "openrouter":
        headers.setdefault("HTTP-Referer", "https://argos-translator.local")
        headers.setdefault("X-Title", "Argos Translate")

    return headers


def _completions_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/completions"
    return f"{base}/v1/completions"


@dataclass
class LLMRequestContext:
    """Подготовленный контекст HTTP-запроса к OpenAI-compatible API."""

    base_url: str
    headers: Dict[str, str]
    chat_url: str
    completions_url: str
    model: str


def build_request_context(llm: LLMSettings) -> LLMRequestContext:
    """Собрать URL, заголовки и модель для LLM-запросов (PLAN §10.1)."""
    if not llm.enabled:
        raise LLMDisabledError()

    preset = get_provider(llm.provider)
    base_url = resolve_base_url(llm.provider, llm.base_url, llm.provider_urls)
    if not base_url:
        raise LLMConfigError("Base URL не задан")

    if preset.api_key_required and not current_api_key(llm):
        raise LLMConfigError("API key обязателен для OpenRouter")

    return LLMRequestContext(
        base_url=base_url,
        headers=_build_headers(llm),
        chat_url=_chat_url(base_url),
        completions_url=_completions_url(base_url),
        model=llm.model or "default",
    )


def _chat_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/chat/completions"
    return f"{base}/v1/chat/completions"


def _models_url(base_url: str) -> str:
    base = base_url.rstrip("/")
    if base.endswith("/v1"):
        return f"{base}/models"
    return f"{base}/v1/models"


def fetch_models(llm: LLMSettings, timeout: float = 10.0) -> List[str]:
    if not llm.enabled:
        raise LLMDisabledError()

    preset = get_provider(llm.provider)
    base_url = resolve_base_url(llm.provider, llm.base_url, llm.provider_urls)
    if not base_url:
        raise LLMConfigError("Base URL не задан")

    if preset.api_key_required and not current_api_key(llm):
        raise LLMConfigError("API key обязателен для OpenRouter")

    import httpx

    headers = _build_headers(llm)
    url = _models_url(base_url)
    with httpx.Client(timeout=timeout) as client:
        resp = client.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    models: List[str] = []
    for item in data.get("data", []):
        mid = item.get("id") if isinstance(item, dict) else None
        if mid:
            models.append(str(mid))
    return models


def check_connection(llm: LLMSettings, timeout: float = 3.0) -> bool:
    try:
        fetch_models(llm, timeout=timeout)
        return True
    except Exception as exc:
        logger.debug("LLM connection check failed: %s", exc)
        return False


def _split_paragraph_chunks(text: str, max_chars: int = LLM_MAX_CHARS) -> List[str]:
    if len(text) <= max_chars:
        return [text]

    paragraphs = re.split(r"\n{2,}", text)
    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for para in paragraphs:
        part = para if not current else "\n\n" + para
        if current_len + len(part) > max_chars and current:
            chunks.append("\n\n".join(current))
            overlap = current[-1] if current else ""
            current = [overlap, para] if overlap else [para]
            current_len = sum(len(p) + 2 for p in current)
        else:
            current.append(para)
            current_len += len(part)

    if current:
        chunks.append("\n\n".join(current))
    return chunks


def _parse_sse_token(line: str) -> Optional[str]:
    if not line.startswith("data:"):
        return None
    payload = line[5:].strip()
    if payload == "[DONE]":
        return None
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return None

    choices = data.get("choices") or []
    if not choices:
        return None
    choice = choices[0]
    delta = choice.get("delta") or {}
    content = delta.get("content")
    if content:
        return str(content)
    delta_text = delta.get("text")
    if delta_text:
        return str(delta_text)
    text = choice.get("text")
    if text:
        return str(text)
    message = choice.get("message") or {}
    msg_content = message.get("content")
    if msg_content:
        return str(msg_content)
    return None


def _should_fallback_to_completions(status_code: int, response_text: str) -> bool:
    """Chat endpoint недоступен — пробуем legacy /v1/completions."""
    if status_code not in (404, 405):
        return False
    lower = (response_text or "").lower()
    if "model" in lower and "not found" in lower and "chat" not in lower:
        return False
    return True


def _completions_prompt(system_prompt: str, user_content: str) -> str:
    return f"{system_prompt}\n\n### User:\n{user_content}\n\n### Assistant:\n"


def _extract_non_stream_content(data: Dict[str, Any]) -> str:
    choices = data.get("choices") or []
    if not choices:
        return ""
    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content")
    if content:
        return str(content)
    text = choice.get("text")
    return str(text) if text else ""


def _request_chunk(
    client: Any,
    ctx: LLMRequestContext,
    llm: LLMSettings,
    system_prompt: str,
    user_content: str,
    cancel_event: threading.Event,
    on_token: Callable[[str], None],
    prefix: str,
    *,
    use_completions: bool = False,
) -> str:
    import httpx

    if use_completions:
        url = ctx.completions_url
        body: Dict[str, Any] = {
            "model": ctx.model,
            "prompt": _completions_prompt(system_prompt, user_content),
            "temperature": llm.temperature,
            "max_tokens": llm.max_tokens,
            "stream": llm.stream,
        }
    else:
        url = ctx.chat_url
        body = {
            "model": ctx.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": llm.temperature,
            "max_tokens": llm.max_tokens,
            "stream": llm.stream,
        }

    chunk_result = ""
    if llm.stream:
        with client.stream("POST", url, headers=ctx.headers, json=body) as resp:
            if resp.status_code == 429:
                raise httpx.HTTPStatusError(
                    "429 Too Many Requests",
                    request=resp.request,
                    response=resp,
                )
            if resp.status_code >= 400:
                resp.read()
                if not use_completions and _should_fallback_to_completions(
                    resp.status_code, resp.text
                ):
                    return _request_chunk(
                        client,
                        ctx,
                        llm,
                        system_prompt,
                        user_content,
                        cancel_event,
                        on_token,
                        prefix,
                        use_completions=True,
                    )
                resp.raise_for_status()
            for line in resp.iter_lines():
                if cancel_event.is_set():
                    return chunk_result
                if not line:
                    continue
                token = _parse_sse_token(line)
                if token:
                    chunk_result += token
                    on_token(prefix + chunk_result)
    else:
        resp = client.post(url, headers=ctx.headers, json={**body, "stream": False})
        if resp.status_code == 429:
            raise httpx.HTTPStatusError(
                "429 Too Many Requests",
                request=resp.request,
                response=resp,
            )
        if resp.status_code >= 400:
            if not use_completions and _should_fallback_to_completions(
                resp.status_code, resp.text
            ):
                return _request_chunk(
                    client,
                    ctx,
                    llm,
                    system_prompt,
                    user_content,
                    cancel_event,
                    on_token,
                    prefix,
                    use_completions=True,
                )
            resp.raise_for_status()
        chunk_result = _extract_non_stream_content(resp.json())
        if chunk_result:
            on_token(prefix + chunk_result)
    return chunk_result


def _request_chunk_with_retry(
    ctx: LLMRequestContext,
    llm: LLMSettings,
    system_prompt: str,
    user_content: str,
    cancel_event: threading.Event,
    on_token: Callable[[str], None],
    prefix: str,
) -> str:
    import httpx

    timeout = httpx.Timeout(llm.timeout_sec, connect=10.0)
    last_timeout: Optional[httpx.TimeoutException] = None
    for attempt in range(2):
        try:
            with httpx.Client(timeout=timeout) as client:
                return _request_chunk(
                    client,
                    ctx,
                    llm,
                    system_prompt,
                    user_content,
                    cancel_event,
                    on_token,
                    prefix,
                )
        except httpx.TimeoutException as exc:
            last_timeout = exc
            if attempt == 0:
                logger.debug("LLM timeout, retrying once")
                continue
            raise last_timeout
    raise RuntimeError("unreachable")


def translate_stream(
    llm: LLMSettings,
    text: str,
    from_code: str,
    to_code: str,
    languages: Dict[str, str],
    on_token: Callable[[str], None],
    on_done: Callable[[str], None],
    on_error: Callable[[str], None],
    cancel_event: threading.Event,
    file_type: Optional[str] = None,
) -> None:
    if not llm.enabled:
        raise LLMDisabledError()

    try:
        ctx = build_request_context(llm)
    except LLMConfigError as exc:
        on_error(str(exc))
        return

    import httpx

    chunks = _split_paragraph_chunks(text)
    full_parts: List[str] = []
    system_prompt = build_system_prompt(llm, from_code, to_code, languages)

    logger.info(
        "LLM stream: %s→%s, %d chars, %d chunk(s)",
        from_code,
        to_code,
        len(text),
        len(chunks),
    )

    for chunk_idx, chunk in enumerate(chunks):
        if cancel_event.is_set():
            logger.info("LLM stream: cancelled at chunk %d/%d", chunk_idx + 1, len(chunks))
            return

        logger.info(
            "LLM stream: chunk %d/%d (%d chars)",
            chunk_idx + 1,
            len(chunks),
            len(chunk),
        )

        user_content = chunk
        if file_type and chunk_idx == 0:
            user_content = f"File type: {file_type}\n\n{chunk}"

        prefix = "".join(full_parts)
        try:
            chunk_result = _request_chunk_with_retry(
                ctx,
                llm,
                system_prompt,
                user_content,
                cancel_event,
                on_token,
                prefix,
            )
        except httpx.ConnectError:
            on_error("LLM недоступен: нет соединения")
            return
        except httpx.TimeoutException:
            on_error("LLM: таймаут запроса")
            return
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            if code == 429:
                on_error("LLM занята (429), повторите позже")
            elif code == 404:
                on_error("Модель не найдена — выберите модель в настройках")
            else:
                on_error(f"LLM HTTP {code}")
            return
        except Exception as exc:
            logger.debug("LLM translate error: %s", exc)
            on_error(f"LLM ошибка: {str(exc)[:80]}")
            return

        if not chunk_result.strip():
            on_error("LLM: пустой ответ")
            return
        full_parts.append(chunk_result)

    result = "".join(full_parts)
    logger.info("LLM stream: complete, %d chars total", len(result))
    on_done(result)
