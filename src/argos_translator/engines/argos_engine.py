"""Движок перевода Argos (API / CLI)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

from argos_translator.config.constants import TranslationConstants
from argos_translator.utils.imports import (
    ARGOS_MODULE_STATUS,
    AT_TRANSLATE_MODULE,
    ImportStatus,
)

logger = logging.getLogger("ArgosStreaming")


class TranslateEngine:
    def __init__(self) -> None:
        self.use_api = ARGOS_MODULE_STATUS == ImportStatus.SUCCESS and AT_TRANSLATE_MODULE is not None
        self.cli_path: Optional[Path] = None

        if not self.use_api:
            self.cli_path = self._find_cli_executable()
            if self.cli_path:
                logger.info("Using CLI: %s", self.cli_path)
            else:
                logger.warning("No translation backend found")
        else:
            logger.info("Using Argos Python API")

    @staticmethod
    def _find_cli_executable() -> Optional[Path]:
        exe = "argos-translate.exe" if os.name == "nt" else "argos-translate"
        found = shutil.which(exe)
        if found:
            return Path(found)

        for path in (
            Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin") / exe,
            Path.home() / ".local" / "bin" / exe,
            Path("/usr/local/bin") / exe,
            Path("/usr/bin") / exe,
        ):
            if path.exists():
                return path
        return None

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        text = (text or "").strip()
        if not text:
            return ""

        logger.debug(
            "Argos translate: %s→%s, %d chars: %r",
            from_code,
            to_code,
            len(text),
            text[:50] + ("…" if len(text) > 50 else ""),
        )

        if self.use_api and AT_TRANSLATE_MODULE is not None:
            try:
                translate_fn = getattr(AT_TRANSLATE_MODULE, "translate", None)
                if callable(translate_fn):
                    return translate_fn(text, from_code, to_code)
            except Exception as exc:
                logger.warning("API error, fallback to CLI: %s", exc)

        if not self.cli_path:
            raise RuntimeError("No translation backend available")
        return self._translate_cli(text, from_code, to_code)

    def _translate_cli(self, text: str, from_code: str, to_code: str) -> str:
        cmd = [str(self.cli_path), "--from", from_code, "--to", to_code, text]
        logger.debug("CLI command: %s", cmd[:6])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TranslationConstants.TRANSLATE_CLI_TIMEOUT,
            )
            if proc.returncode != 0:
                err = proc.stderr.strip() if proc.stderr else "Unknown error"
                raise RuntimeError(f"Translate CLI error: {err}")
            return proc.stdout.strip()
        except subprocess.TimeoutExpired:
            raise RuntimeError("Translate timeout") from None
        except Exception as exc:
            logger.exception("CLI translate failed: %s", exc)
            raise RuntimeError(str(exc)) from exc
