"""Первый запуск frozen EXE: модели Argos в portable packages/."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from argos_translator.config.paths import (
    get_argos_packages_dir,
    get_frozen_app_dir,
    get_resource_path,
    is_frozen,
)
from argos_translator.services.model_manager import ModelManager

if TYPE_CHECKING:
    from argos_translator.config.settings import AppSettings

logger = logging.getLogger("ArgosStreaming")

_ARGOS_PACKAGE_DIR_ENV = "ARGOS_TRANSLATE_PACKAGE_DIR"


def configure_argos_package_dir(packages_dir: Path) -> None:
    """Подсказать argostranslate каталог пакетов (если поддерживается)."""
    os.environ[_ARGOS_PACKAGE_DIR_ENV] = str(packages_dir)
    try:
        import argostranslate.package as pkg  # type: ignore[import-untyped]

        if hasattr(pkg, "PACKAGE_DIR"):
            setattr(pkg, "PACKAGE_DIR", str(packages_dir))
    except Exception as exc:
        logger.debug("Could not patch argostranslate.package.PACKAGE_DIR: %s", exc)


def bootstrap_frozen_models(settings: AppSettings) -> int:
    """
    Portable EXE: установить en↔ru из bundle в {exe_dir}/packages при первом запуске.

    Возвращает число установленных моделей из bundle.
    """
    if not is_frozen():
        return 0

    if not settings.argos.bundle_models_on_start:
        logger.debug("bundle_models_on_start=false — skip frozen bootstrap")
        return 0

    packages_dir = get_argos_packages_dir(settings.argos.packages_dir or None)
    packages_dir.mkdir(parents=True, exist_ok=True)
    configure_argos_package_dir(packages_dir)

    mgr = ModelManager(settings.argos.packages_dir or None)
    pairs = mgr.list_installed_pairs()
    if pairs:
        logger.info("Frozen: models already installed: %s", pairs)
        return 0

    bundle = _resolve_bundle_dir()
    if not bundle.exists():
        logger.warning("Frozen: bundle argos_models not found near %s", get_frozen_app_dir())
        return 0

    installed = mgr.install_from_bundle(bundle)
    if installed:
        logger.info("Frozen: installed %d model(s) from %s", installed, bundle)
    return installed


def _resolve_bundle_dir() -> Path:
    for candidate in (
        get_resource_path("argos_models"),
        get_frozen_app_dir() / "argos_models",
    ):
        if candidate.is_dir() and any(candidate.glob("*.argosmodel")):
            return candidate
    return get_resource_path("argos_models")
