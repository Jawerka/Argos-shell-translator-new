# -*- coding: utf-8 -*-
"""
PyInstaller hook для argostranslate.
Явно указываем все подмодули для включения в сборку.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Собираем все подмодули
hiddenimports = collect_submodules('argostranslate')

# Собираем все данные
datas = collect_data_files('argostranslate')

# Явно добавляем критичные подмодули которые могут не обнаружиться
hiddenimports += [
    'argostranslate.translate',
    'argostranslate.apis',
    'argostranslate.cli',
    'argostranslate.package',
    'argostranslate.tags',
    'argostranslate.apply_bpe',
    'argostranslate.argospm',
    'argostranslate.utils',
    'argostranslate.__main__',
]
