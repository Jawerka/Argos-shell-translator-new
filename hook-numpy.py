# -*- coding: utf-8 -*-
"""
PyInstaller hook для numpy.
Обеспечивает правильное включение numpy и его DLL в сборку.
"""

from PyInstaller.utils.hooks import collect_submodules, collect_data_files

# Собираем все подмодули numpy кроме тестов
hiddenimports = collect_submodules('numpy')

# Исключаем тестовые модули
hiddenimports = [
    m for m in hiddenimports 
    if not m.endswith('.tests') 
    and not m.endswith('.tests.test_')
    and 'f2py.tests' not in m
    and 'distutils.tests' not in m
]

# Собираем данные
datas = collect_data_files('numpy')
