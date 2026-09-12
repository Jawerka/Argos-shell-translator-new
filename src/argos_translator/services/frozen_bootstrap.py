"""Подсказка argostranslate каталога пакетов (frozen sidecar)."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("ArgosStreaming")

_ARGOS_PACKAGE_DIR_ENV = "ARGOS_TRANSLATE_PACKAGE_DIR"


def configure_argos_package_dir(packages_dir: Path) -> None:
    """Подсказать argostranslate каталог пакетов (если поддерживается)."""
    os.environ[_ARGOS_PACKAGE_DIR_ENV] = str(packages_dir)
    try:
        import argostranslate.package as pkg  # type: ignore[import-untyped]

        if hasattr(pkg, "PACKAGE_DIR"):
            setattr(pkg, "PACKAGE_DIR", str(packages_dir))
    except Exception as exc:
        logger.debug("Could not patch argostranslate.package.PACKAGE_DIR: %s", exc)
