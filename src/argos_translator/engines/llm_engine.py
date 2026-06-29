"""LLM-движок перевода (OpenAI-compatible API)."""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from argos_translator.config.llm_providers import (
    get_default_system_prompt,
    get_provider,
    resolve_base_url,
)
from argos_translator.config.settings import LLMSettings
from argos_translator.utils.text_utils import TextUtils

logger = logging.getLogger("ArgosStreaming")

LLM_MAX_CHARS = 6000
LLM_MAX_CHARS_EDITOR = 6000
LLM_MAX_CHARS_FILE_DEFAULT = 3500
LLM_CONTEXT_TAIL_CHARS = 300
LLM_STRIP_PREFIX_MIN = 80
UI_UPDATE_THROTTLE_MS = 50


class LLMDisabledError(Exception):
    pass


class LLMConfigError(Exception):
    pass


LLM_CHUNK_ERROR_PREFIX = "[LLM Error: "


@dataclass
class LlmChunk:
    """Disjoint сегмент для перевода; context_text — read-only контекст в prompt."""

    translate_text: str
    join_before: str = ""
    context_text: str = ""
    split_level: str = "paragraph"
    seam_after: bool = False
    source_start: int = 0
    source_end: int = 0


@dataclass
class _Segment:
    text: str
    join_before: str
    level: str
    start: int
    end: int


def current_api_key(llm: LLMSettings) -> str:
    return (llm.api_keys.get(llm.provider) or "").strip()


def build_system_prompt(
    llm: LLMSettings,
    from_code: str,
    to_code: str,
    languages: Dict[str, str],
    *,
    multi_part: bool = False,
) -> str:
    template = (llm.system_prompt or "").strip() or get_default_system_prompt()
    source_lang = languages.get(from_code, from_code.upper())
    target_lang = languages.get(to_code, to_code.upper())
    prompt = template.format(
        source_lang=source_lang,
        target_lang=target_lang,
        source_code=from_code,
        target_code=to_code,
        formality="neutral",
    )
    if multi_part:
        prompt += (
            "\n\nThe document is split into sequential parts; translate each part once. "
            "Keep terminology consistent with any provided context."
        )
    return prompt


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


def _paragraph_ranges(text: str) -> List[Tuple[int, int]]:
    """Диапазоны абзацев в исходном тексте (разделитель — пустая строка)."""
    ranges: List[Tuple[int, int]] = []
    n = len(text)
    i = 0
    while i < n:
        while i < n and text[i] == "\n":
            i += 1
        if i >= n:
            break
        start = i
        while i < n:
            if i + 1 < n and text[i] == "\n" and text[i + 1] == "\n":
                break
            i += 1
        ranges.append((start, i))
        while i < n and text[i] == "\n":
            i += 1
    if not ranges and text:
        ranges.append((0, n))
    return ranges


def _split_oversized_text(block: str, max_chars: int) -> List[Tuple[str, str]]:
    """Разбить блок > max_chars на части. Возвращает (text, level)."""
    if len(block) <= max_chars:
        return [(block, "paragraph")]

    sentences = TextUtils.split_paragraph_into_sentences(block)
    if not sentences:
        return [(block, "word")]

    if len(sentences) == 1 and len(block) > max_chars:
        words = TextUtils._fallback_split_by_words(block)
        return [(part, "word") for part in words if part.strip()]

    parts: List[Tuple[str, str]] = []
    for start, end in TextUtils.make_sentence_chunks(sentences, max_chars=max_chars, overlap=0):
        chunk = " ".join(sentences[start:end])
        if chunk.strip():
            parts.append((chunk, "sentence"))
    return parts or [(block, "paragraph")]


def _text_to_segments(text: str, max_chars: int) -> List[_Segment]:
    """Разбить текст на disjoint-сегменты с позициями в исходнике."""
    segments: List[_Segment] = []
    ranges = _paragraph_ranges(text)
    if not ranges:
        if text:
            segments.append(_Segment(text, "", "paragraph", 0, len(text)))
        return segments

    for para_idx, (start, end) in enumerate(ranges):
        para_text = text[start:end]
        join = "\n\n" if para_idx > 0 else ""
        if len(para_text) <= max_chars:
            segments.append(_Segment(para_text, join, "paragraph", start, end))
            continue

        subparts = _split_oversized_text(para_text, max_chars)
        offset = start
        for sub_idx, (sub_text, level) in enumerate(subparts):
            sub_join = join if sub_idx == 0 else ("\n" if level == "sentence" else " ")
            sub_start = text.find(sub_text, offset, end)
            if sub_start < 0:
                sub_start = offset
            sub_end = sub_start + len(sub_text)
            segments.append(_Segment(sub_text, sub_join, level, sub_start, sub_end))
            offset = sub_end

    return segments


def _segment_packed_len(segments: List[_Segment]) -> int:
    total = 0
    for seg in segments:
        total += len(seg.join_before) + len(seg.text)
    return total


def _pack_segments(segments: List[_Segment], max_chars: int) -> List[List[_Segment]]:
    """Упаковать сегменты в чанки без overlap в translate_text."""
    if not segments:
        return []

    packs: List[List[_Segment]] = []
    current: List[_Segment] = []
    current_len = 0

    for seg in segments:
        add_len = len(seg.text) + (len(seg.join_before) if current else 0)
        if current and current_len + add_len > max_chars:
            packs.append(current)
            current = [seg]
            current_len = len(seg.text)
        else:
            current.append(seg)
            current_len += add_len

    if current:
        packs.append(current)
    return packs


def _segments_to_chunk(pack: List[_Segment]) -> LlmChunk:
    translate = ""
    for seg in pack:
        translate += seg.join_before + seg.text
    level_order = {"paragraph": 0, "sentence": 1, "word": 2}
    level = max((s.level for s in pack), key=lambda x: level_order.get(x, 0))
    seam = level != "paragraph"
    return LlmChunk(
        translate_text=translate,
        join_before="",
        split_level=level,
        seam_after=seam,
        source_start=pack[0].start if pack else 0,
        source_end=pack[-1].end if pack else 0,
    )


def _split_llm_chunks(text: str, max_chars: int) -> List[LlmChunk]:
    """Disjoint-разбиение для LLM: абзацы → предложения → слова."""
    if not text:
        return [LlmChunk(translate_text="", source_start=0, source_end=0)]
    if len(text) <= max_chars:
        return [LlmChunk(translate_text=text, source_start=0, source_end=len(text))]

    segments = _text_to_segments(text, max_chars)
    packs = _pack_segments(segments, max_chars)
    chunks = [_segments_to_chunk(p) for p in packs]

    for idx in range(1, len(chunks)):
        prev_pack = packs[idx - 1]
        context_parts = [prev_pack[-1].text]
        if len(prev_pack) > 1 and prev_pack[-2].level == "paragraph":
            context_parts.insert(0, prev_pack[-2].text)
        chunks[idx].context_text = "\n\n".join(context_parts)

    return chunks


def _split_paragraph_chunks(text: str, max_chars: int = LLM_MAX_CHARS) -> List[str]:
    """Обратная совместимость: только тексты disjoint-чанков."""
    return [c.translate_text for c in _split_llm_chunks(text, max_chars)]


def _chunk_max_chars(llm: LLMSettings, file_type: Optional[str]) -> int:
    if file_type is not None:
        return max(500, llm.file_chunk_max_chars)
    return max(500, llm.chunk_max_chars)


def _adaptive_max_tokens(text_len: int, base_max: int, *, file_mode: bool = False) -> int:
    """Оценка выхода перевода; для файлов — жёсткий потолок, не завышать base_max."""
    cap = 2048 if file_mode else 8192
    estimated = int(text_len / 2.5) + 256
    if file_mode:
        return min(cap, base_max, max(512, estimated))
    return min(cap, max(base_max, estimated))


def _adaptive_chunk_timeout(text_len: int, base_timeout: int, *, file_mode: bool = False) -> float:
    divisor = 8 if file_mode else 30
    return float(max(base_timeout, text_len // divisor))


def _translated_tail(text: str, max_chars: int = LLM_CONTEXT_TAIL_CHARS) -> str:
    text = text.rstrip()
    if len(text) <= max_chars:
        return text
    tail = text[-max_chars:]
    space = tail.find(" ")
    if space > 0:
        return tail[space + 1 :]
    return tail


def _strip_leading_context_repeat(output: str, translated_tail: str) -> str:
    """Safety net: модель повторила хвост предыдущего перевода."""
    if not translated_tail or len(output) < LLM_STRIP_PREFIX_MIN:
        return output
    check = translated_tail[-min(200, len(translated_tail)) :]
    if len(check) >= LLM_STRIP_PREFIX_MIN and output.startswith(check):
        stripped = output[len(check) :].lstrip()
        if stripped.strip():
            return stripped
        logger.warning(
            "LLM strip: prefix removal would empty output (%d chars), keeping original",
            len(output),
        )
    return output


def _build_chunk_user_content(
    chunk: LlmChunk,
    chunk_idx: int,
    total: int,
    file_type: Optional[str],
    translated_tail: str,
    use_context: bool,
) -> str:
    parts: List[str] = []
    if file_type and chunk_idx == 0:
        parts.append(f"File type: {file_type}")

    if chunk_idx > 0 and use_context:
        parts.append(f"Document part {chunk_idx + 1}/{total}.")
        if chunk.context_text:
            parts.append(
                "Context from previous source (for continuity only, do not translate again):\n---\n"
                f"{chunk.context_text}\n---"
            )
        if translated_tail:
            parts.append(
                "Previous translation ended with:\n---\n"
                f"{translated_tail}\n---"
            )
        parts.append(
            "Translate the following segment. Output ONLY the translation of the new segment:\n---\n"
            f"{chunk.translate_text}\n---"
        )
    else:
        parts.append(chunk.translate_text)

    return "\n\n".join(parts)


def _join_chunk_outputs(parts: List[str], chunks: List[LlmChunk]) -> str:
    del chunks
    return "".join(parts)


def _normalize_content_field(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: List[str] = []
        for item in value:
            if isinstance(item, dict):
                part = item.get("text") or item.get("content")
                if part:
                    parts.append(str(part))
            elif item:
                parts.append(str(item))
        return "".join(parts)
    return str(value)


def _parse_sse_parts(line: str) -> Tuple[str, str]:
    """Из SSE-строки: (content_delta, reasoning_delta)."""
    if not line.startswith("data:"):
        return "", ""
    payload = line[5:].strip()
    if payload == "[DONE]":
        return "", ""
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        return "", ""

    choices = data.get("choices") or []
    if not choices:
        return "", ""
    choice = choices[0]
    delta = choice.get("delta") or {}
    content = _normalize_content_field(delta.get("content"))
    if not content:
        content = _normalize_content_field(delta.get("text"))
    if not content:
        content = _normalize_content_field(choice.get("text"))

    reasoning = _normalize_content_field(delta.get("reasoning_content"))
    if not reasoning:
        message = choice.get("message") or {}
        if not content:
            content = _normalize_content_field(message.get("content"))
        reasoning = _normalize_content_field(message.get("reasoning_content"))
    return content, reasoning


def _parse_sse_token(line: str) -> Optional[str]:
    content, reasoning = _parse_sse_parts(line)
    piece = content or reasoning
    return piece or None


def _finalize_stream_text(content: str, reasoning: str) -> str:
    """Qwen/peg-native может отдавать весь ответ только в reasoning_content."""
    if content.strip():
        return content
    if reasoning.strip():
        logger.warning(
            "LLM: no content deltas in stream, using reasoning_content (%d chars)",
            len(reasoning),
        )
        return reasoning
    return ""


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
    content = _normalize_content_field(message.get("content"))
    if content.strip():
        return content
    reasoning = _normalize_content_field(message.get("reasoning_content"))
    if reasoning.strip():
        logger.warning(
            "LLM: non-stream response used reasoning_content (%d chars)",
            len(reasoning),
        )
        return reasoning
    text = _normalize_content_field(choice.get("text"))
    return text


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
    max_tokens: int,
    use_completions: bool = False,
    stream_override: Optional[bool] = None,
) -> str:
    import httpx

    use_stream = llm.stream if stream_override is None else stream_override

    if use_completions:
        url = ctx.completions_url
        body: Dict[str, Any] = {
            "model": ctx.model,
            "prompt": _completions_prompt(system_prompt, user_content),
            "temperature": llm.temperature,
            "max_tokens": max_tokens,
            "stream": use_stream,
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
            "max_tokens": max_tokens,
            "stream": use_stream,
            "chat_template_kwargs": {"enable_thinking": False},
        }

    chunk_result = ""
    if use_stream:
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
                        max_tokens=max_tokens,
                        use_completions=True,
                        stream_override=stream_override,
                    )
                resp.raise_for_status()
            content_acc = ""
            reasoning_acc = ""
            for line in resp.iter_lines():
                if cancel_event.is_set():
                    return _finalize_stream_text(content_acc, reasoning_acc)
                if not line:
                    continue
                content_piece, reasoning_piece = _parse_sse_parts(line)
                if content_piece:
                    content_acc += content_piece
                if reasoning_piece:
                    reasoning_acc += reasoning_piece
                display = content_acc if content_acc else reasoning_acc
                if display != chunk_result:
                    chunk_result = display
                    on_token(prefix + chunk_result)
            chunk_result = _finalize_stream_text(content_acc, reasoning_acc)
            if chunk_result:
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
                    max_tokens=max_tokens,
                    use_completions=True,
                    stream_override=stream_override,
                )
            resp.raise_for_status()
        chunk_result = _extract_non_stream_content(resp.json())
        if chunk_result:
            on_token(prefix + chunk_result)
    return chunk_result


def _chunk_error_message(exc: BaseException) -> str:
    import httpx

    if isinstance(exc, httpx.ConnectError):
        return "нет соединения"
    if isinstance(exc, httpx.TimeoutException):
        return "таймаут запроса"
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code if exc.response is not None else 0
        if code == 429:
            return "занята (429)"
        if code == 404:
            return "модель не найдена"
        return f"HTTP {code}"
    return str(exc)[:80]


def _chunk_error_marker(exc: BaseException) -> str:
    return f"{LLM_CHUNK_ERROR_PREFIX}{_chunk_error_message(exc)}]"


def _request_chunk_with_retry(
    ctx: LLMRequestContext,
    llm: LLMSettings,
    system_prompt: str,
    user_content: str,
    cancel_event: threading.Event,
    on_token: Callable[[str], None],
    prefix: str,
    *,
    text_len: int,
    file_mode: bool = False,
) -> str:
    import httpx

    chunk_timeout = _adaptive_chunk_timeout(text_len, llm.timeout_sec, file_mode=file_mode)
    max_tokens = _adaptive_max_tokens(text_len, llm.max_tokens, file_mode=file_mode)
    timeout = httpx.Timeout(connect=10.0, read=chunk_timeout, write=30.0, pool=30.0)
    last_exc: Optional[BaseException] = None
    result = ""
    for attempt in range(2):
        try:
            with httpx.Client(timeout=timeout) as client:
                result = _request_chunk(
                    client,
                    ctx,
                    llm,
                    system_prompt,
                    user_content,
                    cancel_event,
                    on_token,
                    prefix,
                    max_tokens=max_tokens,
                )
            break
        except httpx.TimeoutException as exc:
            last_exc = exc
            if attempt == 0:
                logger.debug("LLM timeout, retrying once")
                continue
            raise
        except httpx.ConnectError as exc:
            last_exc = exc
            if attempt == 0:
                logger.debug("LLM connect error, retrying once")
                time.sleep(1.0)
                continue
            raise
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code if exc.response is not None else 0
            if code >= 500 or code == 429:
                last_exc = exc
                if attempt == 0:
                    wait = 2.0 if code == 429 else 1.0
                    logger.debug("LLM HTTP %d, retrying after %.1fs", code, wait)
                    time.sleep(wait)
                    continue
            raise
    else:
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("unreachable")

    if result.strip() or not llm.stream or cancel_event.is_set():
        return result

    logger.warning("LLM: empty stream response, retrying with stream=False")
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
            max_tokens=max_tokens,
            stream_override=False,
        )


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
    on_chunk_progress: Optional[Callable[[int, int], None]] = None,
) -> None:
    if not llm.enabled:
        raise LLMDisabledError()

    try:
        ctx = build_request_context(llm)
    except LLMConfigError as exc:
        on_error(str(exc))
        return

    max_chars = _chunk_max_chars(llm, file_type)
    chunks = _split_llm_chunks(text, max_chars)
    full_parts: List[str] = []
    use_context = file_type is not None and llm.file_chunk_context
    system_prompt = build_system_prompt(
        llm, from_code, to_code, languages, multi_part=len(chunks) > 1
    )

    logger.info(
        "LLM stream: %s→%s, %d chars, %d chunk(s), max_chars=%d",
        from_code,
        to_code,
        len(text),
        len(chunks),
        max_chars,
    )

    had_partial_errors = False

    for chunk_idx, chunk in enumerate(chunks):
        if cancel_event.is_set():
            logger.info("LLM stream: cancelled at chunk %d/%d", chunk_idx + 1, len(chunks))
            return

        if on_chunk_progress:
            on_chunk_progress(chunk_idx + 1, len(chunks))

        logger.info(
            "LLM stream: chunk %d/%d (%d chars, level=%s)",
            chunk_idx + 1,
            len(chunks),
            len(chunk.translate_text),
            chunk.split_level,
        )

        translated_tail = _translated_tail(full_parts[-1]) if full_parts and use_context else ""
        user_content = _build_chunk_user_content(
            chunk,
            chunk_idx,
            len(chunks),
            file_type,
            translated_tail,
            use_context,
        )

        prefix = _join_chunk_outputs(full_parts, chunks[:chunk_idx])
        try:
            chunk_result = _request_chunk_with_retry(
                ctx,
                llm,
                system_prompt,
                user_content,
                cancel_event,
                on_token,
                prefix,
                text_len=len(chunk.translate_text),
                file_mode=file_type is not None,
            )
        except Exception as exc:
            logger.warning(
                "LLM stream: chunk %d/%d failed: %s",
                chunk_idx + 1,
                len(chunks),
                exc,
            )
            marker = _chunk_error_marker(exc)
            full_parts.append(marker)
            had_partial_errors = True
            on_token(_join_chunk_outputs(full_parts, chunks[: chunk_idx + 1]))
            continue

        if cancel_event.is_set():
            if chunk_result.strip():
                full_parts.append(_strip_leading_context_repeat(chunk_result, translated_tail))
            if full_parts:
                logger.info(
                    "LLM stream: cancelled after partial chunks, %d part(s)",
                    len(full_parts),
                )
                on_done(_join_chunk_outputs(full_parts, chunks[: len(full_parts)]))
            else:
                on_error("LLM: запрос отменён")
            return

        chunk_result = _strip_leading_context_repeat(chunk_result, translated_tail)

        if not chunk_result.strip():
            if cancel_event.is_set():
                on_error("LLM: запрос отменён")
                return
            logger.warning(
                "LLM stream: empty chunk %d/%d (raw len=%d, tail ctx=%d)",
                chunk_idx + 1,
                len(chunks),
                len(chunk_result),
                len(translated_tail),
            )
            full_parts.append(f"{LLM_CHUNK_ERROR_PREFIX}пустой ответ]")
            had_partial_errors = True
            on_token(_join_chunk_outputs(full_parts, chunks[: chunk_idx + 1]))
            continue

        full_parts.append(chunk_result)

    if not full_parts:
        on_error("LLM: не удалось перевести")
        return

    result = _join_chunk_outputs(full_parts, chunks)
    if had_partial_errors:
        logger.info("LLM stream: complete with partial errors, %d chars total", len(result))
    else:
        logger.info("LLM stream: complete, %d chars total", len(result))
    on_done(result)
