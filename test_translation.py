#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Legacy-скрипт проверки Argos backend.

Рекомендуется: pytest tests/test_translation_integration.py -m integration
"""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.services.model_manager import ModelManager
from argos_translator.utils.imports import ARGOS_MODULE_STATUS, ImportStatus


def main() -> int:
    print("=" * 60)
    print("ARGOS TRANSLATE — integration check")
    print("=" * 60)
    print(f"Python: {sys.version.split()[0]} | argos import: {ARGOS_MODULE_STATUS.value}")

    if ARGOS_MODULE_STATUS != ImportStatus.SUCCESS:
        print("SKIP: argostranslate not available")
        return 0

    mgr = ModelManager()
    has_models, pairs = mgr.has_any_model()
    print(f"Models: {pairs if has_models else 'none'}")

    engine = TranslateEngine()
    print(f"Backend: API={engine.use_api} CLI={engine.cli_path}")

    if has_models and mgr.has_pair("en", "ru") and (engine.use_api or engine.cli_path):
        result = engine.translate("Hello", "en", "ru")
        print(f"Translate en->ru: {result!r}")
    else:
        print("SKIP: en->ru not available")

    return 0


if __name__ == "__main__":
    sys.exit(main())
