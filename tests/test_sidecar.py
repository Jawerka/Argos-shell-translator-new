"""HTTP sidecar: health, detect, models, decode, translate NDJSON, cancel."""

from __future__ import annotations

import json
import sys
import threading
import time
import types
from pathlib import Path
from typing import Any, Iterator
from unittest.mock import MagicMock

import httpx
import pytest

from sidecar import __version__ as SIDECAR_VERSION
from sidecar.__main__ import build_parser, main as sidecar_main
from sidecar.jobs import ArgosJobRunner
from sidecar.server import TOKEN_HEADER, create_server
from argos_translator.services.translation_cache import TranslationCache
from argos_translator.services.translation_coordinator import TranslationCoordinator

REPO_ROOT = Path(__file__).resolve().parent.parent
TOKEN = "test-sidecar-token"


class FakeEngine:
    def __init__(self, prefer_api: bool = True) -> None:
        self.prefer_api = prefer_api
        self.calls: list[tuple[str, str, str]] = []

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        self.calls.append((text, from_code, to_code))
        return f"{from_code}->{to_code}:{text}"


class SlowEngine:
    def __init__(self, prefer_api: bool = True, delay: float = 0.4) -> None:
        self.prefer_api = prefer_api
        self.started = threading.Event()
        self.delay = delay

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        self.started.set()
        time.sleep(self.delay)
        return f"slow:{text}"


@pytest.fixture
def sidecar_http(monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[str, str]]:
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    server = create_server(host="127.0.0.1", port=0, token=TOKEN)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"
    deadline = time.time() + 3
    while time.time() < deadline:
        try:
            ping = httpx.get(f"{base}/health", timeout=0.4)
            if ping.status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    try:
        yield base, TOKEN
    finally:
        server.shutdown()
        server.server_close()


def _headers(token: str | None = TOKEN) -> dict[str, str]:
    if not token:
        return {}
    return {TOKEN_HEADER: token}


def _ndjson_events(response: httpx.Response) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in response.iter_lines():
        if not line:
            continue
        events.append(json.loads(line))
    return events


def test_ready_json_parses_and_writes_temp_file(capsys: pytest.CaptureFixture[str]) -> None:
    from sidecar.__main__ import _ready, ready_file_path

    path = ready_file_path()
    try:
        _ready(4242)
        out = capsys.readouterr().out
        line = out.strip().splitlines()[-1]
        payload = json.loads(line)
        assert payload == {"ok": True, "port": 4242}
        assert json.loads(path.read_text(encoding="utf-8")) == payload
    finally:
        if path.exists():
            path.unlink()


def test_ready_when_stdout_none_still_writes_file(monkeypatch: pytest.MonkeyPatch) -> None:
    import sidecar.__main__ as sidecar_main_mod
    from sidecar.__main__ import _ready, ready_file_path

    path = ready_file_path()
    monkeypatch.setattr(sidecar_main_mod.sys, "stdout", None)

    def _fdopen_fail(*_args: object, **_kwargs: object) -> object:
        raise OSError("no fd")

    monkeypatch.setattr(sidecar_main_mod.os, "fdopen", _fdopen_fail)
    try:
        _ready(99)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["ok"] is True
        assert payload["port"] == 99
    finally:
        if path.exists():
            path.unlink()


def test_help_exits_zero() -> None:
    parser = build_parser()
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])
    assert exc.value.code == 0


def test_module_help_subprocess() -> None:
    import subprocess

    result = subprocess.run(
        [sys.executable, "-m", "sidecar", "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "127.0.0.1" in (result.stdout + result.stderr)


def test_main_requires_token_and_loopback() -> None:
    assert sidecar_main(["--host", "127.0.0.1"]) == 2
    assert sidecar_main(["--host", "0.0.0.0", "--token", "abc"]) == 2


def test_health_without_token(sidecar_http: tuple[str, str]) -> None:
    base, _ = sidecar_http
    with httpx.Client(timeout=5) as client:
        res = client.get(f"{base}/health")
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["version"] == SIDECAR_VERSION


def test_protected_routes_need_token(sidecar_http: tuple[str, str]) -> None:
    base, _ = sidecar_http
    with httpx.Client(timeout=5) as client:
        denied = client.get(f"{base}/v1/health")
        ok = client.get(f"{base}/v1/health", headers=_headers())
        bearer = client.get(
            f"{base}/v1/languages",
            headers={"Authorization": f"Bearer {TOKEN}"},
        )
    assert denied.status_code == 401
    assert ok.status_code == 200
    assert ok.json()["ok"] is True
    assert bearer.status_code == 200
    assert "en" in bearer.json()["languages"]


def test_languages_and_models(sidecar_http: tuple[str, str]) -> None:
    base, token = sidecar_http
    with httpx.Client(timeout=5) as client:
        langs = client.get(f"{base}/v1/languages", headers=_headers(token))
        models = client.get(f"{base}/v1/models", headers=_headers(token))
    assert langs.status_code == 200
    assert langs.json()["languages"]["ru"]
    assert models.status_code == 200
    assert "pairs" in models.json()
    assert "packages_dir" in models.json()


def test_detect_auto(sidecar_http: tuple[str, str]) -> None:
    base, token = sidecar_http
    with httpx.Client(timeout=30) as client:
        empty = client.post(f"{base}/v1/detect", headers=_headers(token), json={"text": ""})
        ru = client.post(
            f"{base}/v1/detect",
            headers=_headers(token),
            json={"text": "Привет"},
        )
    assert empty.json()["code"] == "en"
    assert empty.json()["lang"] == "en"
    assert ru.json()["code"] == "ru"
    assert ru.json()["lang"] == "ru"


def test_files_decode(sidecar_http: tuple[str, str], tmp_path: Path) -> None:
    base, token = sidecar_http
    path = tmp_path / "note.txt"
    path.write_text("Привет, мир", encoding="utf-8")
    with httpx.Client(timeout=5) as client:
        missing = client.post(
            f"{base}/v1/files/decode",
            headers=_headers(token),
            json={},
        )
        ok = client.post(
            f"{base}/v1/files/decode",
            headers=_headers(token),
            json={"path": str(path), "max_size_mb": 1},
        )
    assert missing.status_code == 400
    assert ok.status_code == 200
    body = ok.json()
    assert body["text"] == "Привет, мир"
    assert body["encoding"]
    assert body["file_type"]


def test_models_install_requires_path_or_bundle(sidecar_http: tuple[str, str]) -> None:
    base, token = sidecar_http
    with httpx.Client(timeout=5) as client:
        res = client.post(
            f"{base}/v1/models/install",
            headers=_headers(token),
            json={},
        )
    assert res.status_code == 400


def test_models_install_bundle(sidecar_http: tuple[str, str]) -> None:
    base, token = sidecar_http
    with httpx.Client(timeout=5) as client:
        res = client.post(
            f"{base}/v1/models/install",
            headers=_headers(token),
            json={"bundle": True},
        )
    assert res.status_code == 200
    body = res.json()
    assert "installed" in body
    assert "pairs" in body
    assert isinstance(body["installed"], int)


def test_models_install_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    model = tmp_path / "en_ru.argosmodel"
    model.write_bytes(b"fake")
    fake_models = MagicMock()
    fake_models.install_from_path.return_value = True
    fake_models.list_installed_pairs.return_value = ["en->ru"]
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: FakeEngine())
    server = create_server(host="127.0.0.1", port=0, token=TOKEN)
    server.state.models = fake_models  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    try:
        with httpx.Client(timeout=5) as client:
            res = client.post(
                f"http://127.0.0.1:{port}/v1/models/install",
                headers=_headers(),
                json={"path": str(model)},
            )
        assert res.status_code == 200
        assert res.json()["installed"] == 1
        fake_models.install_from_path.assert_called_once()
    finally:
        server.shutdown()
        server.server_close()


def test_translate_applies_packages_dir_from_body(
    sidecar_http: tuple[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, token = sidecar_http
    applied: list[str] = []

    def _fake_apply(packages_dir: str | None) -> None:
        if packages_dir:
            applied.append(packages_dir)

    monkeypatch.setattr("sidecar.server._apply_packages_dir", _fake_apply)
    packages = tmp_path / "custom_packages"
    with httpx.Client(timeout=10) as client:
        with client.stream(
            "POST",
            f"{base}/v1/translate",
            headers=_headers(token),
            json={
                "text": "Hello.",
                "from": "en",
                "to": "ru",
                "packages_dir": str(packages),
            },
        ) as res:
            assert res.status_code == 200
            events = _ndjson_events(res)
    assert events[-1]["type"] == "done"
    assert applied and applied[-1] == str(packages)


def test_cancel_then_translate_completes(
    sidecar_http: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Flutter шлёт POST /v1/cancel перед каждым /v1/translate — новое задание должно завершиться."""
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    base, token = sidecar_http
    with httpx.Client(timeout=10) as client:
        cancel = client.post(f"{base}/v1/cancel", headers=_headers(token), json={})
        assert cancel.status_code == 200
        with client.stream(
            "POST",
            f"{base}/v1/translate",
            headers=_headers(token),
            json={"text": "Hello.", "from": "en", "to": "ru"},
        ) as res:
            assert res.status_code == 200
            events = _ndjson_events(res)
    assert events[-1]["type"] == "done"
    assert engine.calls


def test_translate_ndjson_stream(sidecar_http: tuple[str, str]) -> None:
    base, token = sidecar_http
    with httpx.Client(timeout=10) as client:
        with client.stream(
            "POST",
            f"{base}/v1/translate",
            headers=_headers(token),
            json={"text": "Hello world.", "from": "en", "to": "ru"},
        ) as res:
            assert res.status_code == 200
            events = _ndjson_events(res)
    types = [e["type"] for e in events]
    assert types[0] == "start"
    assert "chunk" in types
    assert types[-1] == "done"
    start = events[0]
    assert start["from"] == "en"
    assert start["to"] == "ru"
    assert start["job_id"]
    chunks = [e for e in events if e["type"] == "chunk"]
    assert chunks[0]["text"].startswith("en->ru:")


def test_translate_empty_is_done(sidecar_http: tuple[str, str]) -> None:
    base, token = sidecar_http
    with httpx.Client(timeout=5) as client:
        with client.stream(
            "POST",
            f"{base}/v1/translate",
            headers=_headers(token),
            json={"text": "   ", "from": "en", "to": "ru"},
        ) as res:
            events = _ndjson_events(res)
    assert [e["type"] for e in events] == ["start", "done"]


def test_translate_unknown_path_404(sidecar_http: tuple[str, str]) -> None:
    base, token = sidecar_http
    with httpx.Client(timeout=5) as client:
        res = client.get(f"{base}/v1/nope", headers=_headers(token))
    assert res.status_code == 404


def test_cancel_stops_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    slow = SlowEngine(delay=0.5)
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: slow)
    server = create_server(host="127.0.0.1", port=0, token=TOKEN)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    text = "First paragraph here.\n\nSecond paragraph there."
    events: list[dict[str, Any]] = []
    error: list[BaseException] = []

    def _run_translate() -> None:
        try:
            with httpx.Client(timeout=10) as client:
                with client.stream(
                    "POST",
                    f"{base}/v1/translate",
                    headers=_headers(),
                    json={"text": text, "from": "en", "to": "ru"},
                ) as res:
                    events.extend(_ndjson_events(res))
        except BaseException as exc:  # noqa: BLE001
            error.append(exc)

    worker = threading.Thread(target=_run_translate)
    worker.start()
    assert slow.started.wait(timeout=5)
    with httpx.Client(timeout=5) as client:
        cancel = client.post(f"{base}/v1/cancel", headers=_headers(), json={})
    assert cancel.status_code == 200
    worker.join(timeout=8)
    server.shutdown()
    server.server_close()
    assert not error
    assert any(e["type"] == "cancelled" for e in events)


def test_cancel_before_run_translate_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    runner = ArgosJobRunner(
        coordinator=TranslationCoordinator(),
        cache=TranslationCache(),
    )
    runner.coord.cancel()
    events: list[dict[str, Any]] = []
    status = runner.run_translate(
        text="Hello.",
        from_code="en",
        to_code="ru",
        emit=events.append,
    )
    assert status == "done"
    assert events[-1]["type"] == "done"
    assert engine.calls


def test_job_runner_detect_and_passthrough_code(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    runner = ArgosJobRunner(
        coordinator=TranslationCoordinator(),
        cache=TranslationCache(),
    )
    assert runner.detect("Привет") == "ru"
    events: list[dict[str, Any]] = []
    status = runner.run_translate(
        text="Hello.\n\n```\ncode\n```",
        from_code="en",
        to_code="ru",
        translate_code_blocks=False,
        emit=events.append,
    )
    assert status == "done"
    assert events[0]["type"] == "start"
    texts = [e["text"] for e in events if e["type"] == "chunk"]
    assert any("code" in t for t in texts)
    assert any(t.startswith("en->ru:") for t in texts)


def test_translate_applies_cache_size(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    server = create_server(host="127.0.0.1", port=0, token=TOKEN)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"
    try:
        with httpx.Client(timeout=10) as client:
            with client.stream(
                "POST",
                f"{base}/v1/translate",
                headers=_headers(),
                json={
                    "text": "Hello.",
                    "from": "en",
                    "to": "ru",
                    "cache": True,
                    "cache_size": 12,
                },
            ) as res:
                assert res.status_code == 200
                _ndjson_events(res)
        assert server.state.cache.max_size == 12  # type: ignore[attr-defined]
    finally:
        server.shutdown()
        server.server_close()


def test_translate_auto_start_uses_actual_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    runner = ArgosJobRunner(
        coordinator=TranslationCoordinator(),
        cache=TranslationCache(),
    )
    monkeypatch.setattr(runner.model_manager, "list_installed_pairs", lambda: [])
    events: list[dict[str, Any]] = []
    runner.run_translate(
        text="Привет, это достаточно длинный русский текст для детекта.",
        from_code="auto",
        to_code="ru",
        emit=events.append,
    )
    start = events[0]
    assert start["type"] == "start"
    assert start["from"] == "ru"
    assert start["to"] == "en"
    assert engine.calls
    assert engine.calls[0][1:] == ("ru", "en")


def test_translate_auto_snaps_nl_to_en_when_only_en_ru(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)

    class _FakeIso:
        name = "nl"

    class _FakeLang:
        iso_code_639_1 = _FakeIso()

    class _FakeConf:
        language = _FakeLang()
        value = 0.99

    fake_detector = types.SimpleNamespace(
        compute_language_confidence_values=lambda text: [_FakeConf()]
    )
    monkeypatch.setattr(
        "argos_translator.utils.text_utils._get_lingua_detector",
        lambda codes: fake_detector,
    )
    runner = ArgosJobRunner(
        coordinator=TranslationCoordinator(),
        cache=TranslationCache(),
    )
    monkeypatch.setattr(
        runner.model_manager,
        "list_installed_pairs",
        lambda: ["en->ru", "ru->en"],
    )
    events: list[dict[str, Any]] = []
    text = "This is a reasonably long English sentence used for language detection."
    status = runner.run_translate(
        text=text,
        from_code="auto",
        to_code="ru",
        emit=events.append,
    )
    assert status == "done"
    start = events[0]
    assert start["type"] == "start"
    assert start["from"] == "en"
    assert start["to"] == "ru"
    assert engine.calls
    assert engine.calls[0][1:] == ("en", "ru")


def test_snap_missing_pair_german_with_one_russian_word(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = ArgosJobRunner(
        coordinator=TranslationCoordinator(),
        cache=TranslationCache(),
    )
    pairs = ["en->ru", "ru->en"]
    monkeypatch.setattr(runner.model_manager, "list_installed_pairs", lambda: list(pairs))
    monkeypatch.setattr(
        runner.model_manager,
        "has_pair",
        lambda from_code, to_code: f"{from_code}->{to_code}" in pairs,
    )
    text = "Das Wetter heute ist wirklich sehr kalt und grau, слово"
    resolved = runner._snap_missing_pair(text, "de", "ru", "ru")
    assert resolved == ("en", "ru")


def test_second_translate_supersedes_first(monkeypatch: pytest.MonkeyPatch) -> None:
    started = threading.Event()
    release = threading.Event()

    class BlockingEngine:
        def __init__(self, prefer_api: bool = True) -> None:
            self.prefer_api = prefer_api
            self.calls = 0

        def translate(self, text: str, from_code: str, to_code: str) -> str:
            self.calls += 1
            started.set()
            release.wait(timeout=5)
            return f"ok:{text}"

    engine = BlockingEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    server = create_server(host="127.0.0.1", port=0, token=TOKEN)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address[:2]
    base = f"http://{host}:{port}"
    first_events: list[dict[str, Any]] = []
    second_events: list[dict[str, Any]] = []

    def _first() -> None:
        with httpx.Client(timeout=10) as client:
            with client.stream(
                "POST",
                f"{base}/v1/translate",
                headers=_headers(),
                json={
                    "text": "First paragraph here.\n\nSecond paragraph there.",
                    "from": "en",
                    "to": "ru",
                },
            ) as res:
                first_events.extend(_ndjson_events(res))

    def _second() -> None:
        with httpx.Client(timeout=10) as client:
            with client.stream(
                "POST",
                f"{base}/v1/translate",
                headers=_headers(),
                json={"text": "Hello.", "from": "en", "to": "ru"},
            ) as res:
                second_events.extend(_ndjson_events(res))

    worker = threading.Thread(target=_first)
    worker.start()
    assert started.wait(timeout=5)
    second_worker = threading.Thread(target=_second)
    second_worker.start()
    deadline = time.time() + 5
    while time.time() < deadline and not any(e.get("type") == "start" for e in second_events):
        time.sleep(0.02)
    release.set()
    worker.join(timeout=8)
    second_worker.join(timeout=8)
    server.shutdown()
    server.server_close()
    assert any(e["type"] == "cancelled" for e in first_events)
    assert second_events and second_events[-1]["type"] == "done"


def test_cancelled_job_does_not_call_engine_again(monkeypatch: pytest.MonkeyPatch) -> None:
    coord = TranslationCoordinator()

    class CancelOnFirst:
        def __init__(self, prefer_api: bool = True) -> None:
            self.prefer_api = prefer_api
            self.calls: list[str] = []

        def translate(self, text: str, from_code: str, to_code: str) -> str:
            self.calls.append(text)
            coord.cancel()
            return "x"

    engine = CancelOnFirst()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    runner = ArgosJobRunner(coordinator=coord, cache=TranslationCache())
    events: list[dict[str, Any]] = []
    status = runner.run_translate(
        text="First paragraph here.\n\nSecond paragraph there.",
        from_code="en",
        to_code="ru",
        emit=events.append,
    )
    assert status == "cancelled"
    assert len(engine.calls) == 1
    assert any(e["type"] == "cancelled" for e in events)


def test_missing_pair_emits_error_before_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    engine = FakeEngine()
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: engine)
    runner = ArgosJobRunner(
        coordinator=TranslationCoordinator(),
        cache=TranslationCache(),
    )
    monkeypatch.setattr(runner.model_manager, "list_installed_pairs", lambda: ["de->fr"])
    events: list[dict[str, Any]] = []
    status = runner.run_translate(
        text="Hello.",
        from_code="en",
        to_code="ru",
        emit=events.append,
    )
    assert status == "error"
    assert engine.calls == []
    assert events[0]["type"] == "start"
    assert events[1]["type"] == "error"
    assert events[1]["job_id"] == events[0]["job_id"]
    assert "en→ru" in events[1]["message"]


def test_cancel_respects_job_id(monkeypatch: pytest.MonkeyPatch) -> None:
    slow = SlowEngine(delay=0.5)
    monkeypatch.setattr("sidecar.jobs.TranslateEngine", lambda prefer_api=True: slow)
    server = create_server(host="127.0.0.1", port=0, token=TOKEN)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    events: list[dict[str, Any]] = []

    def _run_translate() -> None:
        with httpx.Client(timeout=10) as client:
            with client.stream(
                "POST",
                f"{base}/v1/translate",
                headers=_headers(),
                json={
                    "text": "First paragraph here.\n\nSecond paragraph there.",
                    "from": "en",
                    "to": "ru",
                },
            ) as res:
                for line in res.iter_lines():
                    if line:
                        events.append(json.loads(line))

    worker = threading.Thread(target=_run_translate)
    worker.start()
    assert slow.started.wait(timeout=5)
    start = None
    deadline = time.time() + 2
    while start is None and time.time() < deadline:
        start = next((e for e in events if e.get("type") == "start"), None)
        time.sleep(0.02)
    assert start is not None
    with httpx.Client(timeout=5) as client:
        other = client.post(
            f"{base}/v1/cancel",
            headers=_headers(),
            json={"job_id": start["job_id"] + 99},
        )
        assert other.status_code == 200
        cancel = client.post(
            f"{base}/v1/cancel",
            headers=_headers(),
            json={"job_id": start["job_id"]},
        )
        assert cancel.status_code == 200
    worker.join(timeout=8)
    server.shutdown()
    server.server_close()
    assert any(e["type"] == "cancelled" for e in events)


def test_token_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ARGOS_SIDECAR_TOKEN", "env-token")
    assert sidecar_main(["--host", "0.0.0.0"]) == 2
    # loopback still required; missing token without env:
    monkeypatch.delenv("ARGOS_SIDECAR_TOKEN", raising=False)
    assert sidecar_main(["--host", "127.0.0.1"]) == 2

