# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec — onedir HTTP sidecar.

Использование:
    venv\\Scripts\\python.exe -m PyInstaller ArgosSidecar.spec --clean --noconfirm

Результат: dist/argos_sidecar/argos_sidecar.exe
Не смешивать _internal с Flutter Release — копировать в {app}/sidecar/.
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

project_dir = Path(SPEC).parent.resolve() if "SPEC" in globals() else Path.cwd().resolve()
src_dir = project_dir / "src"
hooks_dir = project_dir / "hooks"

argos_modules = collect_submodules("argostranslate")
argos_datas = collect_data_files("argostranslate")
sidecar_modules = collect_submodules("sidecar")

try:
    ctranslate2_binaries = collect_dynamic_libs("ctranslate2")
except Exception:
    ctranslate2_binaries = []

try:
    numpy_binaries = collect_dynamic_libs("numpy")
except Exception:
    numpy_binaries = []

_icon_path = project_dir / "assets" / "argos_translate.ico"
if not _icon_path.exists():
    _icon_path = project_dir / "argos_translate.ico"

_version_file = project_dir / "assets" / "version_info_sidecar.txt"

a = Analysis(
    ["sidecar_entry.py"],
    pathex=[str(project_dir), str(src_dir)],
    binaries=[*ctranslate2_binaries, *numpy_binaries],
    datas=[*argos_datas],
    hiddenimports=[
        *argos_modules,
        *sidecar_modules,
        "sidecar",
        "sidecar.__main__",
        "sidecar.server",
        "sidecar.jobs",
        "argostranslate.translate",
        "argostranslate.package",
        "ctranslate2",
        "numpy",
        "charset_normalizer",
        "charset_normalizer.md",
        "langdetect",
        "argos_translator",
        "argos_translator.config.constants",
        "argos_translator.config.paths",
        "argos_translator.engines.argos_engine",
        "argos_translator.services.document_io",
        "argos_translator.services.model_manager",
        "argos_translator.services.translation_cache",
        "argos_translator.services.translation_coordinator",
        "argos_translator.utils.text_utils",
        "argos_translator.utils.imports",
    ],
    hookspath=[str(hooks_dir)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "pandas",
        "pytest",
        "IPython",
        "jupyter",
        "notebook",
        "sphinx",
        "torch",
        "tensorflow",
        "customtkinter",
        "darkdetect",
        "pystray",
        "keyboard",
        "tkinter",
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="argos_sidecar",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=["*.dll", "vcruntime*.dll", "python*.dll"],
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    icon=str(_icon_path) if _icon_path.exists() else None,
    version=str(_version_file) if _version_file.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=["*.dll"],
    name="argos_sidecar",
)
