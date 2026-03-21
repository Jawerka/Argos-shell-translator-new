# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec-файл для сборки Argos Translate Streaming.

Использование:
    pyinstaller ArgosTranslator.spec

После сборки исполняемый файл находится в dist/ArgosTranslator.exe
"""

import os
from pathlib import Path

# Директория проекта
project_dir = Path(__file__).parent.resolve()

# Анализ проекта
a = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        # Иконки
        (str(project_dir / 'argos_translate.ico'), '.'),
        (str(project_dir / 'argos_translate.png'), '.'),
        # Папка с моделями (если существует)
        (str(project_dir / 'argos_models'), 'argos_models') if (project_dir / 'argos_models').exists() else None,
    ],
    # Скрытые импорты для корректной работы всех компонентов
    hiddenimports=[
        # Pystray (работа в трее)
        'pystray._win32',
        'pystray._darwin',
        'pystray._xorg',
        # Argos Translate
        'argostranslate.package',
        'argostranslate.translate',
        # Опциональные зависимости
        'pyperclip',
        'keyboard',
        'langdetect',
        # PIL/Pillow для иконок
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        # Tkinter (может потребоваться явное указание)
        'tkinter',
        'tkinter.scrolledtext',
        'tkinter.ttk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'pytest',
        'setuptools',
        'distutils',
    ],
    noarchive=False,
    optimize=0,
)

# Создание PYZ-архива
pyz = PYZ(a.pure)

# Создание исполняемого файла
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ArgosTranslator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Без консольного окна (GUI приложение)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(project_dir / 'argos_translate.ico')],
)
