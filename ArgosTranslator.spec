# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec-файл для сборки Argos Translate Streaming.

Использование:
    pyinstaller ArgosTranslator.spec

После сборки исполняемый файл находится в dist/ArgosTranslator.exe
Сборка полностью портативная — все зависимости встроены.
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules, collect_data_files
from PyInstaller.building.api import COLLECT

# Директория проекта (корректно работает при запуске из PyInstaller)
if 'SPEC' in globals():
    project_dir = Path(SPEC).parent.resolve()
else:
    project_dir = Path.cwd().resolve()

# Сбор всех подмодулей и данных для зависимостей
# Это обеспечивает встраивание всех необходимых компонентов в сборку
argos_modules = collect_submodules('argostranslate')
argos_datas = collect_data_files('argostranslate')

# Явно добавляем подмодули argostranslate которые могут не обнаружиться
argos_hidden_imports = [
    'argostranslate.translate',
    'argostranslate.apis',
    'argostranslate.cli',
    'argostranslate.package',
    'argostranslate.tags',
    'argostranslate.apply_bpe',
    'argostranslate.argospm',
]

pystray_modules = collect_submodules('pystray')
pystray_datas = collect_data_files('pystray')

pil_modules = collect_submodules('PIL')
pil_datas = collect_data_files('PIL')

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
        # Данные зависимостей
        *argos_datas,
        *pystray_datas,
        *pil_datas,
    ],
    # Скрытые импорты для корректной работы всех компонентов
    hiddenimports=[
        # Все подмодули argostranslate
        *argos_modules,
        # Явные импорты argostranslate
        *argos_hidden_imports,
        # Все подмодули pystray
        *pystray_modules,
        # Все подмодули PIL
        *pil_modules,
        # Опциональные зависимости
        'pyperclip',
        'keyboard',
        'langdetect',
        # Tkinter
        'tkinter',
        'tkinter.constants',
        'tkinter.scrolledtext',
        'tkinter.ttk',
        'tkinter.messagebox',
        # Системные модули
        'queue',
        'threading',
        'subprocess',
        'json',
        'logging',
        'pathlib',
        'dataclasses',
        'enum',
        'importlib',
        'shutil',
        're',
        'time',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Исключаем тяжёлые и ненужные пакеты
        'matplotlib',
        'matplotlib.*',
        'numpy',
        'numpy.*',
        'scipy',
        'scipy.*',
        'pandas',
        'pandas.*',
        'pytest',
        'pytest.*',
        'setuptools',
        'distutils',
        'IPython',
        'IPython.*',
        'jupyter',
        'jupyter.*',
        'notebook',
        'notebook.*',
        'sphinx',
        'sphinx.*',
        'docutils',
        'docutils.*',
        'Cython',
        'Cython.*',
    ],
    noarchive=False,
    optimize=0,
)

# Создание PYZ-архива
pyz = PYZ(a.pure)

# Создание исполняемого файла
# COLLECT вместо EXE - сборка в папку (проще для отладки)
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
    upx=True,  # Сжатие для уменьшения размера
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Консоль для отладки (видны ошибки)
    disable_windowed_traceback=True,  # Показывать traceback в консоли
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(project_dir / 'argos_translate.ico')],
)

# Сборка в папку вместо одного файла
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name='ArgosTranslator',
)
