"""Безопасный импорт опциональных зависимостей и инициализация Argos."""

from __future__ import annotations

import importlib
import logging
import types
from enum import Enum
from typing import Any, Optional, Tuple

logger = logging.getLogger("ArgosStreaming")


class ImportStatus(Enum):
    SUCCESS = "success"
    MISSING = "missing"
    ERROR = "error"


def safe_import(module_name: str) -> Tuple[ImportStatus, Optional[Any]]:
    try:
        mod = importlib.import_module(module_name)
        return ImportStatus.SUCCESS, mod
    except ImportError:
        return ImportStatus.MISSING, None
    except Exception as exc:
        return ImportStatus.ERROR, exc


def _init_argos_translate() -> Tuple[Optional[Any], Optional[Any]]:
    package_module: Optional[Any] = None
    translate_module: Optional[Any] = None

    try:
        package_module = importlib.import_module("argostranslate.package")
        logger.debug("argostranslate.package imported")
    except Exception as exc:
        logger.debug("argostranslate.package import failed: %s", exc)

    try:
        translate_module = importlib.import_module("argostranslate.translate")
        translate_fn = getattr(translate_module, "translate", None)
        if not callable(translate_fn):
            translate_module = None
        else:
            logger.debug("argostranslate.translate imported")
    except Exception as exc:
        logger.debug("argostranslate.translate import failed: %s", exc)
        translate_module = None

    if translate_module is None and package_module is not None:
        translate_module = _try_ctranslate2_fallback(package_module)

    return package_module, translate_module


def _try_ctranslate2_fallback(package_module: Any) -> Optional[Any]:
    try:
        ctranslate2_module = importlib.import_module("ctranslate2")

        def custom_translate(text: str, from_code: str, to_code: str) -> str:
            get_installed_packages = getattr(package_module, "get_installed_packages", None)
            if not callable(get_installed_packages):
                raise RuntimeError("get_installed_packages not available")

            pkg = None
            for p in get_installed_packages():
                if p.from_code == from_code and p.to_code == to_code:
                    pkg = p
                    break
            if pkg is None:
                raise RuntimeError(f"No package for {from_code}->{to_code}")

            tokenizer = pkg.tokenizer
            if tokenizer is None:
                raise RuntimeError(f"No tokenizer for package {pkg.code}")

            model_path = str(pkg.package_path / "model")
            translator = ctranslate2_module.Translator(model_path, device="cpu")
            tokens = tokenizer.encode(text)
            result = translator.translate_batch([tokens])
            translated_tokens = result[0].hypotheses[0]
            return tokenizer.decode(translated_tokens).strip()

        mod = types.ModuleType("argostranslate.translate")
        mod.translate = custom_translate
        logger.info("ctranslate2 fallback enabled for argostranslate.translate")
        return mod
    except Exception as exc:
        logger.debug("ctranslate2 fallback failed: %s", exc)
        return None


ARGOS_MODULE_STATUS, argostranslate_module = safe_import("argostranslate")
AT_PACKAGE_MODULE: Optional[Any] = None
AT_TRANSLATE_MODULE: Optional[Any] = None

if ARGOS_MODULE_STATUS == ImportStatus.SUCCESS and argostranslate_module is not None:
    AT_PACKAGE_MODULE, AT_TRANSLATE_MODULE = _init_argos_translate()

PYPERCLIP_STATUS, PYPERCLIP_MODULE = safe_import("pyperclip")
KEYBOARD_STATUS, KEYBOARD_MODULE = safe_import("keyboard")
LANGDETECT_STATUS, LANGDETECT_MODULE = safe_import("langdetect")
PYSTRAY_STATUS, PYSTRAY_MODULE = safe_import("pystray")
PIL_STATUS, PIL_MODULE = safe_import("PIL")
TRAY_AVAILABLE = PYSTRAY_STATUS == ImportStatus.SUCCESS and PIL_STATUS == ImportStatus.SUCCESS
