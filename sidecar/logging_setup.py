"""Файловый лог sidecar — только RotatingFileHandler, никогда stdout."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

from argos_translator.config.paths import get_log_dir

_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 3

_DETECT_FORMAT = logging.Formatter(
    "%(asctime)s - %(levelname)s - DETECT %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
_SIDECAR_FORMAT = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def resolve_detect_log_path() -> Path:
    """Канонический detect.log: ARGOS_DETECT_LOG или {get_log_dir()}/detect.log."""
    raw = (os.environ.get("ARGOS_DETECT_LOG") or "").strip()
    if raw:
        return Path(raw)
    return get_log_dir() / "detect.log"


def setup_detect_file_log(log_file: Path | None = None) -> Path:
    """Отдельный logger ArgosDetect → detect.log."""
    path = log_file or resolve_detect_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        path,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(_DETECT_FORMAT)
    detect = logging.getLogger("ArgosDetect")
    detect.setLevel(logging.INFO)
    detect.handlers.clear()
    detect.addHandler(handler)
    detect.propagate = False
    detect.info("path=%s", path)
    return path


def setup_sidecar_file_log() -> Path:
    log_dir = get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "sidecar.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setFormatter(_SIDECAR_FORMAT)
    root = logging.getLogger("ArgosStreaming")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False

    detect_path = setup_detect_file_log()
    root.info("DETECT path=%s", detect_path)
    return log_file
