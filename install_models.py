#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматическая установка моделей argos-translate.
Копирует .argosmodel файлы из локальной директории в системную.
"""

import shutil
from pathlib import Path


def get_argos_packages_dir() -> Path:
    """Получить директорию пакетов argos-translate."""
    if Path.home().exists():
        return Path.home() / ".local" / "share" / "argos-translate" / "packages"
    # Fallback для Windows
    return Path.home() / ".argos-translate" / "packages"


def install_models() -> int:
    """Установить модели из локальной папки в системную."""
    script_dir = Path(__file__).parent
    models_dir = script_dir / "argos_models"
    packages_dir = get_argos_packages_dir()

    if not models_dir.exists():
        print(f"Директория с моделями не найдена: {models_dir}")
        return 1

    # Создаём целевую директорию
    packages_dir.mkdir(parents=True, exist_ok=True)

    installed = 0
    for model_file in models_dir.glob("*.argosmodel"):
        dest = packages_dir / model_file.name
        if not dest.exists():
            print(f"Установка модели: {model_file.name}")
            shutil.copy2(model_file, dest)
            installed += 1
        else:
            print(f"Модель уже установлена: {model_file.name}")

    print(f"\nГотово! Установлено моделей: {installed}")
    return 0


if __name__ == "__main__":
    exit(install_models())
