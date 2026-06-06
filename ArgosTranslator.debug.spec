# -*- mode: python ; coding: utf-8 -*-
# Debug-сборка с консолью для диагностики ошибок.

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

project_dir = Path(SPEC).parent.resolve() if "SPEC" in globals() else Path.cwd().resolve()
src_dir = project_dir / "src"
hooks_dir = project_dir / "hooks"

argos_modules = collect_submodules("argostranslate")
argos_datas = collect_data_files("argostranslate")
pystray_datas = collect_data_files("pystray")
pil_datas = collect_data_files("PIL")
httpx_datas = collect_data_files("httpx")
ctk_modules = collect_submodules("customtkinter")
ctk_datas = collect_data_files("customtkinter")

try:
    ctranslate2_binaries = collect_dynamic_libs("ctranslate2")
except Exception:
    ctranslate2_binaries = []

try:
    numpy_binaries = collect_dynamic_libs("numpy")
except Exception:
    numpy_binaries = []

app_datas = [
    (str(project_dir / "assets" / "argos_translate.ico"), "assets"),
    (str(project_dir / "assets" / "argos_translate.png"), "assets"),
]
for name in ("argos_translate.ico", "argos_translate.png"):
    legacy = project_dir / name
    if legacy.exists() and not (project_dir / "assets" / name).exists():
        app_datas.append((str(legacy), "."))
if (project_dir / "argos_models").is_dir():
    app_datas.append((str(project_dir / "argos_models"), "argos_models"))

_icon_path = project_dir / "assets" / "argos_translate.ico"
if not _icon_path.exists():
    _icon_path = project_dir / "argos_translate.ico"

all_datas = [*app_datas, *argos_datas, *pystray_datas, *pil_datas, *httpx_datas, *ctk_datas]

a = Analysis(
    ["main.py"],
    pathex=[str(project_dir), str(src_dir)],
    binaries=[*ctranslate2_binaries, *numpy_binaries],
    datas=all_datas,
    hiddenimports=[
        *argos_modules,
        "ctranslate2",
        "numpy",
        "httpx",
        "charset_normalizer",
        "argos_translator",
        *ctk_modules,
        "customtkinter",
        "darkdetect",
    ],
    hookspath=[str(hooks_dir)],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matplotlib", "scipy", "pandas", "pytest", "torch"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ArgosTranslator",
    debug=True,
    console=True,
    icon=str(_icon_path),
)

coll = COLLECT(exe, a.binaries, a.datas, name="ArgosTranslator")
