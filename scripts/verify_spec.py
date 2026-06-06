#!/usr/bin/env python3
"""Проверка готовности к сборке EXE (без запуска PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors: list[str] = []

    required = [
        ROOT / "main.py",
        ROOT / "ArgosTranslator.spec",
        ROOT / "hooks" / "hook-argostranslate.py",
        ROOT / "src" / "argos_translator" / "app.py",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Missing: {path.relative_to(ROOT)}")

    for optional in (
        ROOT / "assets" / "version_info.txt",
        ROOT / "assets" / "app.manifest",
        ROOT / "docs" / "UI_BASELINE.md",
    ):
        if not optional.exists():
            errors.append(f"Missing (recommended): {optional.relative_to(ROOT)}")

    icon = ROOT / "assets" / "argos_translate.ico"
    if not icon.exists():
        icon = ROOT / "argos_translate.ico"
    if not icon.exists():
        errors.append("Missing icon: assets/argos_translate.ico (or root fallback)")

    for mod in ("customtkinter", "darkdetect", "httpx"):
        try:
            __import__(mod)
        except ImportError:
            errors.append(
                f"Missing Python package: {mod} (pip install -r requirements.txt in venv)"
            )

    if errors:
        print("Spec verification FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Spec verification OK")
    print(f"  icon: {icon}")
    print(f"  argos_models: {(ROOT / 'argos_models').exists()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
