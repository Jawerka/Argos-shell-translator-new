"""Настройка логирования."""

from __future__ import annotations

import logging
import sys
import tempfile
from pathlib import Path

from argos_translator.config.paths import get_log_dir


class LoggingConfig:
    def __init__(self) -> None:
        self.log_dir = get_log_dir()
        self.log_file = self.log_dir / "app_debug.log"

    def setup(self) -> logging.Logger:
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            try:
                self.log_dir = Path.home() / ".argos_translate" / "log"
                self.log_dir.mkdir(parents=True, exist_ok=True)
                self.log_file = self.log_dir / "app_debug.log"
            except Exception:
                self.log_dir = Path(tempfile.gettempdir()) / "argos_translate_log"
                self.log_dir.mkdir(parents=True, exist_ok=True)
                self.log_file = self.log_dir / "app_debug.log"

        fmt = "%(asctime)s - %(levelname)s - %(message)s"
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)

        logging.basicConfig(
            level=logging.DEBUG,
            format=fmt,
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[
                logging.FileHandler(self.log_file, encoding="utf-8", mode="a"),
                logging.StreamHandler(sys.stdout),
            ],
            force=True,
        )

        log = logging.getLogger("ArgosStreaming")
        logging.getLogger("PIL").setLevel(logging.WARNING)
        return log
