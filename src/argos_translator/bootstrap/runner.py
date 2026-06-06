"""Запуск приложения: DPI, проверки, mainloop."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox

from argos_translator.app import TranslatorApp
from argos_translator.bootstrap.dpi import enable_dpi_awareness, log_dpi_info
from argos_translator.config.constants import UIConfig
from argos_translator.config.paths import get_exe_dir, get_project_root, get_resource_path, is_frozen
from argos_translator.config.settings import load_settings
from argos_translator.logging_setup import LoggingConfig
from argos_translator.services.frozen_bootstrap import bootstrap_frozen_models
from argos_translator.services.model_manager import ModelManager
from argos_translator.ui.themes import setup_theme
from argos_translator.utils.imports import (
    ARGOS_MODULE_STATUS,
    AT_PACKAGE_MODULE,
    AT_TRANSLATE_MODULE,
    KEYBOARD_MODULE,
    KEYBOARD_STATUS,
    LANGDETECT_MODULE,
    LANGDETECT_STATUS,
    PIL_MODULE,
    PIL_STATUS,
    PYPERCLIP_MODULE,
    PYPERCLIP_STATUS,
    PYSTRAY_MODULE,
    PYSTRAY_STATUS,
    TRAY_AVAILABLE,
    ImportStatus,
    argostranslate_module,
)

logger = logging.getLogger("ArgosStreaming")


def attempt_relaunch_without_console() -> bool:
    if getattr(sys, "frozen", False) or os.name != "nt":
        return False
    exe = sys.executable or ""
    if "pythonw.exe" in exe.lower():
        return False

    candidates: list[str] = []
    found = shutil.which("pythonw.exe")
    if found:
        candidates.append(found)
    try:
        candidates.append(os.path.join(os.getcwd(), "venv", "Scripts", "pythonw.exe"))
    except Exception:
        pass
    if exe.lower().endswith("python.exe"):
        candidates.append(exe[: -len("python.exe")] + "pythonw.exe")

    for path in candidates:
        if path and os.path.exists(path):
            try:
                args = [path, os.path.abspath(sys.argv[0])] + sys.argv[1:]
                subprocess.Popen(args, close_fds=True, creationflags=0x00000008)
                logger.info("Relaunched via pythonw: %s", path)
                return True
            except Exception as exc:
                logger.debug("Relaunch failed (%s): %s", path, exc)
    return False


def _log_startup_diagnostics(log: logging.Logger, log_cfg: LoggingConfig) -> None:
    log.info("=" * 70)
    log.info("Argos Translate Streaming - ЗАПУСК")
    log.info("Python: %s | Platform: %s | Frozen: %s", sys.executable, sys.platform, is_frozen())
    log.info("Project root: %s | Exe dir: %s", get_project_root(), get_exe_dir())
    log.info("Log file: %s", log_cfg.log_file)
    log.info(
        "Imports: argos=%s pyperclip=%s keyboard=%s tray=%s",
        ARGOS_MODULE_STATUS.value,
        PYPERCLIP_STATUS.value,
        KEYBOARD_STATUS.value,
        TRAY_AVAILABLE,
    )


def _check_backend(log: logging.Logger) -> bool:
    cli_available = shutil.which("argos-translate") is not None or shutil.which("argos-translate.exe") is not None
    if ARGOS_MODULE_STATUS == ImportStatus.SUCCESS or cli_available:
        return True

    log.warning("No translation backend found")
    root_tmp = ctk.CTk()
    root_tmp.withdraw()
    answer = messagebox.askyesno(
        "Backend missing",
        "Argos Translate API/CLI not found. Install argostranslate now?",
    )
    root_tmp.destroy()
    if answer:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "argostranslate"])
            messagebox.showinfo("Installed", "argostranslate installed. Restart the app.")
        except Exception as exc:
            log.exception("Install failed: %s", exc)
            messagebox.showerror("Install failed", f"Failed to install: {exc}")
    return False


def _check_models(log: logging.Logger, settings) -> bool:
    if ARGOS_MODULE_STATUS != ImportStatus.SUCCESS:
        return True

    if is_frozen():
        bootstrap_frozen_models(settings)

    mgr = ModelManager(settings.argos.packages_dir or None)
    has_models, pairs = mgr.has_any_model()
    if has_models:
        log.info("Translation pairs: %s", pairs)
        return True

    log.info("Installing models from bundle...")
    if settings.argos.bundle_models_on_start:
        mgr.install_from_bundle()
    has_models, pairs = mgr.has_any_model()
    if has_models:
        log.info("Models after bundle: %s", pairs)
        return True

    root_tmp = ctk.CTk()
    root_tmp.withdraw()
    models_dir = get_resource_path("argos_models")
    has_bundle = models_dir.exists() and any(models_dir.glob("*.argosmodel"))
    if has_bundle:
        msg = (
            "Translation models found in the bundle, but failed to install.\n\n"
            "Run: python install_models.py"
        )
    else:
        msg = (
            "No translation models found.\n\n"
            "Place .argosmodel files in argos_models/ and run install_models.py"
        )
    messagebox.showwarning("Translation models missing", msg)
    root_tmp.destroy()
    return False


def main() -> None:
    enable_dpi_awareness()
    log_cfg = LoggingConfig()
    log = log_cfg.setup()
    _log_startup_diagnostics(log, log_cfg)

    if attempt_relaunch_without_console():
        return
    if not _check_backend(log):
        return

    settings = load_settings(UIConfig())
    if not _check_models(log, settings):
        return

    try:
        root = ctk.CTk()
        root.withdraw()
        setup_theme(settings.theme)
        log_dpi_info(root)
        app = TranslatorApp(root, settings=settings)

        if settings.behavior.start_minimized_to_tray and app.tray_enabled:
            root.after(100, app._hide_to_tray)
        else:
            root.deiconify()
            root.update_idletasks()
            app._restore_window_geometry()

        root.mainloop()
    except Exception as exc:
        log.exception("Fatal error: %s", exc)
        try:
            tk.Tk().withdraw()
            messagebox.showerror("Fatal error", f"Application crashed:\n{exc}")
        except Exception:
            pass
        sys.exit(1)
