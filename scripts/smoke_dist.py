#!/usr/bin/env python3
"""Проверка структуры dist/ArgosTranslator после сборки."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist" / "ArgosTranslator"


def main() -> int:
    errors: list[str] = []
    exe = DIST / "ArgosTranslator.exe"
    if not exe.is_file():
        errors.append("Missing ArgosTranslator.exe")
    internal = DIST / "_internal"
    if not internal.is_dir():
        errors.append("Missing _internal/")

    for name in ("assets",):
        if not (DIST / name).is_dir() and not (internal / name).is_dir():
            errors.append(f"Missing {name}/ in dist or _internal")

    if not (DIST / "argos_models").is_dir() and not (internal / "argos_models").is_dir():
        errors.append("Missing argos_models/ in dist or _internal (bundle for offline en↔ru)")

    if errors:
        print("Dist smoke FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1

    size_mb = exe.stat().st_size / (1024 * 1024)
    print("Dist smoke OK")
    print(f"  exe: {exe} ({size_mb:.1f} MB)")
    print(f"  _internal entries: {len(list(internal.iterdir()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
