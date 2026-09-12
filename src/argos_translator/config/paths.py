"""Пути к ресурсам, моделям и настройкам."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_exe_dir() -> Path:
    """Каталог exe (portable) или корень проекта в dev."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent.parent


def get_frozen_app_dir() -> Path:
    """Корень установленного приложения.

    Frozen sidecar лежит в ``{app}/sidecar/argos_sidecar.exe`` — пакеты и лог
    держим рядом с Flutter EXE, не внутри onedir sidecar.
    """
    exe_dir = get_exe_dir()
    if exe_dir.name.lower() == "sidecar":
        return exe_dir.parent
    return exe_dir


def get_project_root() -> Path:
    """Корень проекта или PyInstaller bundle (_MEIPASS)."""
    if is_frozen() and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent.parent


def get_log_dir() -> Path:
    """Каталог логов: `{app}/log` (frozen) или `log/` в проекте."""
    if is_frozen():
        return get_frozen_app_dir() / "log"
    return get_project_root() / "log"


def get_resource_path(relative_path: str) -> Path:
    """Путь к ресурсу (ico, argos_models). Ищет assets/, _MEIPASS и exe_dir."""
    candidates: list[Path] = []
    roots = [get_project_root(), get_exe_dir()]
    if is_frozen():
        app_dir = get_frozen_app_dir()
        if app_dir not in roots:
            roots.append(app_dir)
    for root in roots:
        if relative_path.startswith("assets/"):
            candidates.append(root / relative_path)
        else:
            candidates.extend([root / "assets" / relative_path, root / relative_path])

    for path in candidates:
        if path.exists():
            return path
    return candidates[0] if candidates else get_project_root() / relative_path


def get_argos_packages_dir(custom_dir: Optional[str] = None) -> Path:
    """
    Директория пакетов argos-translate.

    Приоритет:
    1. custom_dir из настроек
    2. {app}/packages/ (frozen portable; Flutter: рядом с translator.exe)
    3. ~/.local/share/argos-translate/packages/
    4. %LOCALAPPDATA%/argos-translate/packages/ (Windows)
    5. ~/.argos-translate/packages/
    """
    if custom_dir and str(custom_dir).strip():
        return Path(custom_dir).expanduser()

    if getattr(sys, "frozen", False):
        return get_frozen_app_dir() / "packages"

    linux_path = Path.home() / ".local" / "share" / "argos-translate" / "packages"
    if linux_path.exists():
        return linux_path

    if os.name == "nt":
        local_app = os.environ.get("LOCALAPPDATA")
        if local_app:
            win_path = Path(local_app) / "argos-translate" / "packages"
            if win_path.exists():
                return win_path

    if linux_path.parent.exists() or os.name != "nt":
        return linux_path

    return Path.home() / ".argos-translate" / "packages"


def get_settings_path() -> Path:
    return Path.home() / ".argos_translate" / "settings.json"
