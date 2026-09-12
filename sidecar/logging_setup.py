"""Файловый лог sidecar — только RotatingFileHandler, никогда stdout."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from argos_translator.config.paths import get_log_dir

_MAX_BYTES = 2 * 1024 * 1024
_BACKUP_COUNT = 3


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
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root = logging.getLogger("ArgosStreaming")
    root.setLevel(logging.DEBUG)
    root.handlers.clear()
    root.addHandler(handler)
    root.propagate = False
    return log_file
