#!/usr/bin/env python3
"""Проверка готовности к сборке EXE (без запуска PyInstaller).

Проверяет и legacy CTk GUI (ArgosTranslator.spec), и Flutter sidecar (ArgosSidecar.spec).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _spec_excludes_numpy(spec_text: str) -> bool:
    idx = spec_text.find("excludes")
    if idx < 0:
        return False
    chunk = spec_text[idx : idx + 1200]
    return '"numpy"' in chunk or "'numpy'" in chunk


def main() -> int:
    errors: list[str] = []

    required = [
        ROOT / "main.py",
        ROOT / "ArgosTranslator.spec",
        ROOT / "ArgosSidecar.spec",
        ROOT / "sidecar_entry.py",
        ROOT / "sidecar" / "__main__.py",
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
        ROOT / "scripts" / "build-windows.ps1",
        ROOT / "scripts" / "windows" / "argos-translate.iss",
    ):
        if not optional.exists():
            errors.append(f"Missing (recommended): {optional.relative_to(ROOT)}")

    icon = ROOT / "assets" / "argos_translate.ico"
    if not icon.exists():
        icon = ROOT / "argos_translate.ico"
    if not icon.exists():
        errors.append("Missing icon: assets/argos_translate.ico (or root fallback)")

    sidecar_spec = ROOT / "ArgosSidecar.spec"
    if sidecar_spec.exists():
        text = sidecar_spec.read_text(encoding="utf-8")
        if "sidecar_entry.py" not in text:
            errors.append("ArgosSidecar.spec must analyze sidecar_entry.py")
        if "console=False" not in text.replace(" ", ""):
            errors.append("ArgosSidecar.spec must set console=False")
        if "argos_sidecar" not in text:
            errors.append("ArgosSidecar.spec must name output argos_sidecar")
        if _spec_excludes_numpy(text):
            errors.append("ArgosSidecar.spec must not exclude numpy")

    settings_src = (ROOT / "src" / "argos_translator" / "config" / "settings.py").read_text(
        encoding="utf-8"
    )
    if "argos_translator.ui" in settings_src:
        errors.append(
            "config/settings.py must not import argos_translator.ui "
            "(ArgosSidecar.spec excludes the CTk UI package)"
        )

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
    print("  specs: ArgosTranslator.spec (legacy CTk), ArgosSidecar.spec")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
