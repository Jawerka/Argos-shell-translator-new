#!/usr/bin/env python3
"""Проверка staged Flutter + sidecar layout (dist/ArgosTranslate)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "dist" / "ArgosTranslate"


def main() -> int:
    errors: list[str] = []
    exe = STAGE / "translator.exe"
    if not exe.is_file():
        errors.append("Missing translator.exe")

    sidecar = STAGE / "sidecar" / "argos_sidecar.exe"
    if not sidecar.is_file():
        errors.append("Missing sidecar/argos_sidecar.exe")

    sidecar_internal = STAGE / "sidecar" / "_internal"
    if not sidecar_internal.is_dir():
        errors.append("Missing sidecar/_internal/ (PyInstaller onedir)")

    if (STAGE / "_internal").is_dir():
        errors.append(
            "PyInstaller _internal at Flutter root (DLL clash) — sidecar must live under sidecar/"
        )

    if errors:
        print("Flutter dist smoke FAILED:")
        for item in errors:
            print(f"  - {item}")
        return 1

    size_mb = exe.stat().st_size / (1024 * 1024)
    sidecar_mb = sidecar.stat().st_size / (1024 * 1024)
    print("Flutter dist smoke OK")
    print(f"  exe: {exe} ({size_mb:.1f} MB)")
    print(f"  sidecar: {sidecar} ({sidecar_mb:.1f} MB)")
    print(f"  sidecar/_internal entries: {len(list(sidecar_internal.iterdir()))}")
    models = STAGE / "argos_models"
    print(f"  argos_models: {models.is_dir()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
