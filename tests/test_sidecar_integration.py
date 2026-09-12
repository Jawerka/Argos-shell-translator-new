"""Интеграция: реальный Argos через HTTP sidecar (нужны установленные модели)."""

from __future__ import annotations

import json
import threading
from typing import Any

import httpx
import pytest

from sidecar.server import TOKEN_HEADER, create_server

pytestmark = pytest.mark.integration

TOKEN = "integration-sidecar-token"


def _headers() -> dict[str, str]:
    return {TOKEN_HEADER: TOKEN}


def _ndjson(response: httpx.Response) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in response.iter_lines():
        if line:
            events.append(json.loads(line))
    return events


@pytest.fixture
def sidecar_base() -> str:
    server = create_server(host="127.0.0.1", port=0, token=TOKEN)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    try:
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()


def _require_pair(base: str, pair: str) -> None:
    with httpx.Client(timeout=10) as client:
        models = client.get(f"{base}/v1/models", headers=_headers()).json()
    pairs = [str(p) for p in models.get("pairs") or []]
    if pair not in pairs:
        pytest.skip(f"нет модели {pair}")


def test_real_argos_en_ru(sidecar_base: str) -> None:
    _require_pair(sidecar_base, "en->ru")
    with httpx.Client(timeout=60) as client:
        with client.stream(
            "POST",
            f"{sidecar_base}/v1/translate",
            headers=_headers(),
            json={"text": "Hello world.", "from": "en", "to": "ru"},
        ) as res:
            events = _ndjson(res)
    assert events[0]["type"] == "start"
    assert events[-1]["type"] == "done"
    chunks = [e["text"] for e in events if e["type"] == "chunk"]
    assert chunks
    assert any("Привет" in t or t != "Hello world." for t in chunks)


def test_real_argos_ru_en(sidecar_base: str) -> None:
    _require_pair(sidecar_base, "ru->en")
    with httpx.Client(timeout=60) as client:
        with client.stream(
            "POST",
            f"{sidecar_base}/v1/translate",
            headers=_headers(),
            json={
                "text": "Привет мир.",
                "from": "auto",
                "to": "ru",
            },
        ) as res:
            events = _ndjson(res)
    start = events[0]
    assert start["type"] == "start"
    assert start["from"] == "ru"
    assert start["to"] == "en"
    assert events[-1]["type"] == "done"
