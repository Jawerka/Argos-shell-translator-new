#!/usr/bin/env python3
"""Проверка готовности к сборке HTTP sidecar (без запуска PyInstaller)."""

from __future__ import annotations

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
        ROOT / "ArgosSidecar.spec",
        ROOT / "sidecar_entry.py",
        ROOT / "sidecar" / "__main__.py",
        ROOT / "assets" / "version_info_sidecar.txt",
        ROOT / "hooks" / "hook-argostranslate.py",
        ROOT / "hooks" / "hook-ctranslate2.py",
        ROOT / "hooks" / "hook-numpy.py",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"Missing: {path.relative_to(ROOT)}")

    for optional in (
        ROOT / "scripts" / "build-windows.ps1",
        ROOT / "scripts" / "windows" / "argos-translate.iss",
        ROOT / "scripts" / "smoke_flutter_dist.py",
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

    if errors:
        print("Spec verification FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("Spec verification OK")
    print(f"  icon: {icon}")
    print(f"  argos_models: {(ROOT / 'argos_models').exists()}")
    print("  spec: ArgosSidecar.spec")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
