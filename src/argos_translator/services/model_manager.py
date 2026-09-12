"""Установка и проверка моделей Argos."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Set, Tuple

from argos_translator.config.paths import get_argos_packages_dir, get_resource_path
from argos_translator.utils.imports import AT_PACKAGE_MODULE

logger = logging.getLogger("ArgosStreaming")


class ModelManager:
    def __init__(self, packages_dir: Optional[str] = None) -> None:
        self.packages_dir = get_argos_packages_dir(packages_dir)

    def list_installed_pairs(self) -> List[str]:
        if AT_PACKAGE_MODULE is None:
            return []
        try:
            get_packages = getattr(AT_PACKAGE_MODULE, "get_installed_packages", None)
            if not callable(get_packages):
                return []
            pairs: Set[str] = set()
            for pkg in get_packages():
                fc = getattr(pkg, "from_code", None)
                tc = getattr(pkg, "to_code", None)
                if fc and tc:
                    pairs.add(f"{fc}->{tc}")
            return sorted(pairs)
        except Exception as exc:
            logger.debug("list_installed_pairs failed: %s", exc)
            return []

    def has_any_model(self) -> Tuple[bool, List[str]]:
        pairs = self.list_installed_pairs()
        return len(pairs) > 0, pairs

    def get_packages_dir(self) -> Path:
        return self.packages_dir

    def has_pair(self, from_code: str, to_code: str) -> bool:
        target = f"{from_code}->{to_code}"
        return target in self.list_installed_pairs()

    def install_file(self, path: Path) -> bool:
        """Установить модель из .argosmodel (алиас install_from_path)."""
        return self.install_from_path(path)

    def install_from_path(self, model_path: Path) -> bool:
        if AT_PACKAGE_MODULE is None:
            return False
        install_fn = getattr(AT_PACKAGE_MODULE, "install_from_path", None)
        if not callable(install_fn):
            logger.warning("install_from_path not available, copying file")
            return self._copy_model_file(model_path)

        try:
            install_fn(str(model_path))
            # argostranslate 1.11 вызывает package.cache_clear() внутри install_from_path.
            logger.info("Installed model via API: %s", model_path.name)
            return True
        except Exception as exc:
            logger.error("install_from_path failed for %s: %s", model_path, exc)
            return self._copy_model_file(model_path)

    def _copy_model_file(self, model_path: Path) -> bool:
        try:
            self.packages_dir.mkdir(parents=True, exist_ok=True)
            dest = self.packages_dir / model_path.name
            if dest.exists():
                return True
            import shutil

            shutil.copy2(model_path, dest)
            logger.info("Copied model file: %s", model_path.name)
            return True
        except Exception as exc:
            logger.error("Copy model failed: %s", exc)
            return False

    def install_from_bundle(self, bundle_dir: Optional[Path] = None) -> int:
        bundle = bundle_dir or get_resource_path("argos_models")
        if not bundle.exists():
            logger.debug("Bundle models directory not found: %s", bundle)
            return 0

        installed = 0
        for model_file in sorted(bundle.glob("*.argosmodel")):
            dest = self.packages_dir / model_file.name
            if dest.exists():
                continue
            if self.install_from_path(model_file):
                installed += 1
        if installed:
            logger.info("Installed %d model(s) from bundle", installed)
        return installed
