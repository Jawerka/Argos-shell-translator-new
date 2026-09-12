"""Точка входа: python -m sidecar"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import tempfile
from pathlib import Path


def _ensure_src_on_path() -> None:
    root = Path(__file__).resolve().parent.parent
    src = root / "src"
    if src.is_dir() and str(src) not in sys.path:
        sys.path.insert(0, str(src))


def ready_json_line(port: int) -> str:
    """Первая строка stdout для Flutter: {"ok":true,"port":N}."""
    return json.dumps({"ok": True, "port": int(port)}, ensure_ascii=False) + "\n"


def ready_file_path(pid: int | None = None) -> Path:
    """Fallback, если у frozen EXE нет stdout (console=False)."""
    ident = os.getpid() if pid is None else int(pid)
    return Path(tempfile.gettempdir()) / f"argos-sidecar-ready-{ident}.json"


def cleanup_ready_file(pid: int | None = None) -> None:
    try:
        ready_file_path(pid).unlink(missing_ok=True)
    except OSError:
        pass


def _ensure_stdout() -> None:
    stdout = getattr(sys, "stdout", None)
    closed = True if stdout is None else bool(getattr(stdout, "closed", False))
    if stdout is not None and not closed:
        return
    try:
        sys.stdout = os.fdopen(1, "w", encoding="utf-8", buffering=1)
    except OSError:
        pass


def _ready(port: int) -> None:
    """Сообщить родителю порт: stdout (pipe) и файл %TEMP%/argos-sidecar-ready-<pid>.json."""
    line = ready_json_line(port)
    try:
        ready_file_path().write_text(line, encoding="utf-8")
    except OSError:
        pass
    _ensure_stdout()
    stdout = getattr(sys, "stdout", None)
    if stdout is not None and not getattr(stdout, "closed", False):
        try:
            stdout.write(line)
            stdout.flush()
        except OSError:
            pass


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sidecar",
        description="Локальный HTTP API вокруг Argos (только 127.0.0.1).",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Адрес (только loopback)")
    parser.add_argument("--port", type=int, default=0, help="Порт, 0 = свободный")
    parser.add_argument("--token", default="", help="Токен X-Sidecar-Token")
    parser.add_argument(
        "--packages-dir",
        default="",
        help="Папка packages Argos (иначе путь по умолчанию)",
    )
    parser.add_argument(
        "--parent-pid",
        type=int,
        default=0,
        help="PID родителя: sidecar выходит, когда процесс завершился",
    )
    return parser


def _install_signal_handlers() -> None:
    def _handle(_signum: int, _frame: object | None) -> None:
        cleanup_ready_file()
        os._exit(0)

    signal.signal(signal.SIGTERM, _handle)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, _handle)
    sigbreak = getattr(signal, "SIGBREAK", None)
    if sigbreak is not None:
        signal.signal(sigbreak, _handle)


def main(argv: list[str] | None = None) -> int:
    _ensure_src_on_path()
    from sidecar.logging_setup import setup_sidecar_file_log
    from sidecar.server import run_server
    from sidecar.watchdog import start_parent_watch

    args = build_parser().parse_args(argv)
    host = args.host.strip() or "127.0.0.1"
    if host not in {"127.0.0.1", "localhost", "::1"}:
        print("sidecar слушает только 127.0.0.1 / localhost / ::1", file=sys.stderr)
        return 2

    token = (args.token or os.environ.get("ARGOS_SIDECAR_TOKEN") or "").strip()
    if not token:
        print("нужен --token или ARGOS_SIDECAR_TOKEN", file=sys.stderr)
        return 2

    setup_sidecar_file_log()
    _install_signal_handlers()
    parent_pid = int(args.parent_pid or 0)
    if parent_pid > 0:
        start_parent_watch(parent_pid)

    server = run_server(
        host=host,
        port=int(args.port),
        token=token,
        packages_dir=args.packages_dir or None,
        ready_callback=_ready,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        cleanup_ready_file()
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
