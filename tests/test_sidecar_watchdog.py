"""Watchdog родителя и файловый лог sidecar."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from sidecar.__main__ import cleanup_ready_file, ready_file_path
from sidecar.logging_setup import setup_sidecar_file_log
from sidecar.watchdog import start_parent_watch, wait_for_parent


def test_wait_for_parent_returns_when_child_exits() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
    )
    try:
        done = threading.Event()

        def _wait() -> None:
            wait_for_parent(child.pid, poll_interval=0.05)
            done.set()

        worker = threading.Thread(target=_wait, daemon=True)
        worker.start()
        time.sleep(0.1)
        assert not done.is_set()
        child.terminate()
        child.wait(timeout=5)
        assert done.wait(timeout=5)
    finally:
        if child.poll() is None:
            child.kill()
            child.wait(timeout=3)


def test_start_parent_watch_invokes_callback() -> None:
    child = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(30)"],
    )
    called = threading.Event()
    try:
        start_parent_watch(child.pid, on_parent_gone=called.set)
        child.kill()
        child.wait(timeout=5)
        assert called.wait(timeout=5)
    finally:
        if child.poll() is None:
            child.kill()


def test_cleanup_ready_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("TMP", str(tmp_path))
    monkeypatch.setenv("TEMP", str(tmp_path))
    import sidecar.__main__ as main_mod

    monkeypatch.setattr(main_mod.tempfile, "gettempdir", lambda: str(tmp_path))
    path = ready_file_path(os.getpid())
    path.write_text("{}", encoding="utf-8")
    assert path.exists()
    cleanup_ready_file(os.getpid())
    assert not path.exists()


def test_sidecar_file_log_created(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        "sidecar.logging_setup.get_log_dir",
        lambda: tmp_path / "log",
    )
    log_file = setup_sidecar_file_log()
    logging.getLogger("ArgosStreaming").info("sidecar boot")
    for handler in logging.getLogger("ArgosStreaming").handlers:
        handler.flush()
    assert log_file.exists()
    text = log_file.read_text(encoding="utf-8")
    assert "sidecar boot" in text
    assert "DETECT path=" in text

    detect = logging.getLogger("ArgosDetect")
    detect.info("probe=ok")
    for handler in detect.handlers:
        handler.flush()
    detect_file = tmp_path / "log" / "detect.log"
    assert detect_file.exists()
    detect_text = detect_file.read_text(encoding="utf-8")
    assert "DETECT" in detect_text
    assert "probe=ok" in detect_text or "path=" in detect_text


def test_detect_log_respects_env(tmp_path: Path, monkeypatch) -> None:
    custom = tmp_path / "custom" / "detect.log"
    monkeypatch.setenv("ARGOS_DETECT_LOG", str(custom))
    from sidecar.logging_setup import resolve_detect_log_path, setup_detect_file_log

    assert resolve_detect_log_path() == custom
    path = setup_detect_file_log()
    assert path == custom
    assert custom.exists()
