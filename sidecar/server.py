"""Локальный HTTP-сервер sidecar (только loopback)."""

from __future__ import annotations

import hmac
import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Optional
from urllib.parse import urlparse

from sidecar.jobs import ArgosJobRunner

from argos_translator.config.constants import DefaultLanguages
from argos_translator.services.document_io import (
    DocumentIOError,
    file_type_hint,
    read_text_file,
)
from argos_translator.services.frozen_bootstrap import configure_argos_package_dir
from argos_translator.services.model_manager import ModelManager
from argos_translator.services.translation_cache import TranslationCache
from argos_translator.services.translation_coordinator import TranslationCoordinator
from sidecar import __version__ as SIDECAR_VERSION

logger = logging.getLogger("ArgosStreaming")

MAX_BODY_BYTES = 32 * 1024 * 1024
TOKEN_HEADER = "X-Sidecar-Token"


def _apply_packages_dir(packages_dir: Optional[str]) -> None:
    """Подсказать argostranslate каталог packages (CLI и тело /v1/translate)."""
    cleaned = (packages_dir or "").strip()
    if not cleaned:
        return
    path = Path(cleaned)
    path.mkdir(parents=True, exist_ok=True)
    configure_argos_package_dir(path)


class SidecarState:
    def __init__(self, token: str, packages_dir: Optional[str] = None) -> None:
        self.token = token
        self.packages_dir = packages_dir
        _apply_packages_dir(packages_dir)
        self.coord = TranslationCoordinator()
        self.cache = TranslationCache()
        self.lock = threading.Lock()
        self.runner = ArgosJobRunner(
            coordinator=self.coord,
            cache=self.cache,
            packages_dir=packages_dir,
            translate_lock=self.lock,
        )
        self.models = ModelManager(packages_dir)


def _json_bytes(payload: dict[str, Any], status: int = 200) -> tuple[int, bytes, str]:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    return status, body, "application/json; charset=utf-8"


def _read_json(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length") or 0)
    if length < 0 or length > MAX_BODY_BYTES:
        raise ValueError("Слишком большой запрос")
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Ожидался JSON-объект")
    return data


def _token_ok(handler: BaseHTTPRequestHandler, token: str) -> bool:
    got = handler.headers.get(TOKEN_HEADER) or ""
    if not got:
        auth = handler.headers.get("Authorization") or ""
        if auth.lower().startswith("bearer "):
            got = auth[7:].strip()
    if not token or not got:
        return False
    return hmac.compare_digest(got.encode("utf-8"), token.encode("utf-8"))


def _handle(
    state: SidecarState,
    handler: BaseHTTPRequestHandler,
    method: str,
    path: str,
) -> None:
    if path == "/health" and method == "GET":
        _send(handler, *_json_bytes({"ok": True, "version": SIDECAR_VERSION}))
        return

    if not _token_ok(handler, state.token):
        _send(handler, *_json_bytes({"error": "unauthorized"}, 401))
        return

    if path == "/v1/health" and method == "GET":
        pairs = state.models.list_installed_pairs()
        has_any, _ = state.models.has_any_model()
        _send(
            handler,
            *_json_bytes(
                {
                    "ok": True,
                    "version": SIDECAR_VERSION,
                    "argos": has_any,
                    "pairs": pairs,
                    "packages_dir": str(state.models.get_packages_dir()),
                }
            ),
        )
        return

    if path == "/v1/languages" and method == "GET":
        _send(handler, *_json_bytes({"languages": DefaultLanguages.get_defaults()}))
        return

    if path == "/v1/models" and method == "GET":
        _send(
            handler,
            *_json_bytes(
                {
                    "pairs": state.models.list_installed_pairs(),
                    "packages_dir": str(state.models.get_packages_dir()),
                }
            ),
        )
        return

    if path == "/v1/models/install" and method == "POST":
        body = _read_json(handler)
        installed = 0
        if body.get("bundle"):
            installed = state.models.install_from_bundle()
        else:
            raw_path = str(body.get("path") or "").strip()
            if not raw_path:
                _send(handler, *_json_bytes({"error": "нужен path или bundle"}, 400))
                return
            ok = state.models.install_from_path(Path(raw_path))
            installed = 1 if ok else 0
        _send(
            handler,
            *_json_bytes(
                {
                    "installed": installed,
                    "pairs": state.models.list_installed_pairs(),
                }
            ),
        )
        return

    if path == "/v1/detect" and method == "POST":
        body = _read_json(handler)
        text = str(body.get("text") or "")
        code = state.runner.detect(text)
        label = DefaultLanguages.LANGUAGES.get(code, code)
        _send(handler, *_json_bytes({"code": code, "label": label}))
        return

    if path == "/v1/files/decode" and method == "POST":
        body = _read_json(handler)
        raw_path = str(body.get("path") or "").strip()
        if not raw_path:
            _send(handler, *_json_bytes({"error": "нужен path"}, 400))
            return
        max_mb = int(body.get("max_size_mb") or 10)
        try:
            decoded = read_text_file(Path(raw_path), max_size_mb=max_mb)
        except DocumentIOError as exc:
            _send(handler, *_json_bytes({"error": str(exc)}, 400))
            return
        _send(
            handler,
            *_json_bytes(
                {
                    "text": decoded.text,
                    "encoding": decoded.encoding,
                    "confidence": decoded.confidence,
                    "file_type": file_type_hint(decoded.path),
                    "path": str(decoded.path),
                }
            ),
        )
        return

    if path == "/v1/cancel" and method == "POST":
        body = _read_json(handler)
        raw_job = body.get("job_id")
        job_id: Optional[int] = None
        if raw_job is not None and raw_job != "":
            try:
                job_id = int(raw_job)
            except (TypeError, ValueError):
                _send(handler, *_json_bytes({"error": "некорректный job_id"}, 400))
                return
        state.coord.cancel(job_id)
        _send(handler, *_json_bytes({"ok": True}))
        return

    if path == "/v1/translate" and method == "POST":
        body = _read_json(handler)
        _stream_translate(state, handler, body)
        return

    _send(handler, *_json_bytes({"error": "not found"}, 404))


def _stream_translate(
    state: SidecarState,
    handler: BaseHTTPRequestHandler,
    body: dict[str, Any],
) -> None:
    text = str(body.get("text") or "")
    from_code = str(body.get("from") or "auto")
    to_code = str(body.get("to") or "ru")
    prefer_api = bool(body.get("prefer_api", True))
    translate_code_blocks = bool(body.get("translate_code_blocks", False))
    use_cache = bool(body.get("cache", False))
    if "cache_size" in body:
        try:
            size = int(body.get("cache_size"))
        except (TypeError, ValueError):
            size = state.cache.max_size
        state.cache.set_max_size(max(10, min(10000, size)))
    request_packages = str(body.get("packages_dir") or "").strip()
    if request_packages:
        _apply_packages_dir(request_packages)

    handler.send_response(200)
    handler.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
    handler.send_header("Cache-Control", "no-cache")
    handler.send_header("Connection", "close")
    handler.end_headers()

    def emit(event: dict[str, Any]) -> None:
        line = json.dumps(event, ensure_ascii=False) + "\n"
        handler.wfile.write(line.encode("utf-8"))
        handler.wfile.flush()

    try:
        state.runner.run_translate(
            text=text,
            from_code=from_code,
            to_code=to_code,
            prefer_api=prefer_api,
            translate_code_blocks=translate_code_blocks,
            use_cache=use_cache,
            emit=emit,
        )
    except BrokenPipeError:
        logger.debug("client closed translate stream")
    except Exception as exc:
        logger.exception("translate stream failed")
        try:
            emit({"type": "error", "job_id": state.coord.active_job, "message": str(exc)})
        except Exception:
            pass


def _send(handler: BaseHTTPRequestHandler, status: int, body: bytes, content_type: str) -> None:
    handler.send_response(status)
    handler.send_header("Content-Type", content_type)
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(body)


def make_handler(state: SidecarState) -> type[BaseHTTPRequestHandler]:
    class SidecarHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt: str, *args: Any) -> None:
            logger.debug("%s - %s", self.address_string(), fmt % args)

        def do_GET(self) -> None:  # noqa: N802
            self._dispatch("GET")

        def do_POST(self) -> None:  # noqa: N802
            self._dispatch("POST")

        def _dispatch(self, method: str) -> None:
            path = urlparse(self.path).path
            try:
                _handle(state, self, method, path)
            except (ValueError, json.JSONDecodeError) as exc:
                _send(self, *_json_bytes({"error": str(exc)}, 400))
            except Exception:
                logger.exception("sidecar handler failed")
                _send(self, *_json_bytes({"error": "internal error"}, 500))

    return SidecarHandler


def create_server(
    *,
    host: str = "127.0.0.1",
    port: int = 0,
    token: str,
    packages_dir: Optional[str] = None,
) -> ThreadingHTTPServer:
    state = SidecarState(token=token, packages_dir=packages_dir)
    server = ThreadingHTTPServer((host, port), make_handler(state))
    server.state = state  # type: ignore[attr-defined]
    return server


def run_server(
    *,
    host: str,
    port: int,
    token: str,
    packages_dir: Optional[str] = None,
    ready_callback: Optional[Callable[[int], None]] = None,
) -> ThreadingHTTPServer:
    server = create_server(host=host, port=port, token=token, packages_dir=packages_dir)
    bound_port = int(server.server_address[1])
    if ready_callback is not None:
        ready_callback(bound_port)
    logger.info("sidecar listening on %s:%s", host, bound_port)
    return server
