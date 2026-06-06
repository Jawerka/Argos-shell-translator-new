#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Установка моделей argos-translate из папки argos_models/."""

from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parent / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from argos_translator.config.paths import get_resource_path
from argos_translator.services.model_manager import ModelManager


def main() -> int:
    bundle = get_resource_path("argos_models")
    if not bundle.exists():
        print(f"Директория с моделями не найдена: {bundle}")
        return 1

    mgr = ModelManager()
    print(f"Пакеты: {mgr.packages_dir}")
    installed = mgr.install_from_bundle(bundle)
    pairs = mgr.list_installed_pairs()
    print(f"\nГотово! Установлено из bundle: {installed}")
    print(f"Доступные пары: {', '.join(pairs) if pairs else 'нет'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
