"""Главное приложение TranslatorApp."""

from __future__ import annotations

import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox

from argos_translator.config.constants import (
    DefaultLanguages,
    TranslationConstants,
    UIConfig,
)
from argos_translator.config.paths import get_resource_path, get_settings_path
from argos_translator.config.settings import AppSettings, load_settings, save_settings
from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.engines.llm_engine import llm_config_error, translate_stream
from argos_translator.logging_setup import LoggingConfig
from argos_translator.services.clipboard import capture_selection_text
from argos_translator.services.document_io import (
    DocumentIOError,
    SUPPORTED_EXTENSIONS,
    file_type_hint,
    read_text_file,
    resolve_output_encoding,
    suggest_output_path,
    write_text_file,
)
from argos_translator.services.hotkeys import register_global_hotkey
from argos_translator.services.llm_health import LLMHealthService, LLMStatus
from argos_translator.services.model_manager import ModelManager
from argos_translator.services.tray import TrayManager
from argos_translator.services.translation_cache import TranslationCache
from argos_translator.services.translation_coordinator import TranslationCoordinator
from argos_translator.ui.main_window import (
    MainWindowCallbacks,
    apply_editor_font_scale,
    build_main_window,
    set_editor_layout,
)
from argos_translator.ui.editor_layout import (
    EditorLayout,
    normalize_editor_layout,
    toggle_layout_for_panel,
)
from argos_translator.ui.settings_dialog import SettingsDialog
from argos_translator.ui.file_drop import setup_file_drop
from argos_translator.ui.themes import apply_theme, get_status_color, setup_theme
from argos_translator.ui.window_state import WindowStateManager
from argos_translator.utils.imports import (
    AT_PACKAGE_MODULE,
)
from argos_translator.utils.text_utils import TextUtils

logger = logging.getLogger("ArgosStreaming")


def _log_text_preview(text: str, max_len: int = 50) -> str:
    """Короткий превью текста для логов (без переносов)."""
    compact = " ".join((text or "").split())
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 1] + "…"


class TranslatorApp:
    """Главное приложение для потокового перевода."""

    def __init__(self, root: ctk.CTk, settings: Optional[AppSettings] = None) -> None:
        """Инициализация приложения."""
        self.root = root
        self.cfg = UIConfig()
        self.settings = settings or load_settings(self.cfg)
        self._settings_file_exists = get_settings_path().exists()
        self.engine = TranslateEngine(prefer_api=self.settings.argos.prefer_api_over_cli)
        self._translation_cache = TranslationCache(
            max_size=self.settings.behavior.translation_cache_size
        )
        self.languages = self._get_available_languages()

        # Поток перевода Argos
        self.translate_queue: queue.Queue = queue.Queue()
        self.translate_thread: Optional[threading.Thread] = None
        self.coord = TranslationCoordinator()

        # Поток перевода LLM
        self.llm_translate_thread: Optional[threading.Thread] = None
        self.llm_status_text = ""
        self.llm_health = LLMHealthService(lambda: self.settings.llm)

        # Управление заданиями — см. self.coord

        # Документ
        self._document_path: Optional[Path] = None
        self._document_encoding: str = "utf-8"
        self._document_file_type: Optional[str] = None
        self._document_dirty: bool = False
        self._document_paragraph_count: int = 0

        # Режимы
        self.streaming_enabled = tk.BooleanVar(value=self.settings.streaming)
        self.scroll_sync_enabled = tk.BooleanVar(value=self.settings.scroll_sync)
        self._editor_layout: EditorLayout = normalize_editor_layout(self.settings.editor_layout)

        self.debounce_job: Optional[Any] = None
        self.llm_debounce_job: Optional[Any] = None
        self._suppress_src_modified: bool = False
        self._window_save_job: Optional[Any] = None
        self._skip_geometry_save: bool = False
        self._window_geometry_restored: bool = False
        self._tray_unmap_guard: bool = False

        # Прокрутка
        self.src_offsets: List[int] = []
        self.dst_offsets: List[int] = []
        self.last_src_pos: Optional[float] = None
        self.last_dst_pos: Optional[float] = None
        self.src_total_chars: int = 1
        self.dst_total_chars: int = 1

        # Флаги программной прокрутки
        self._is_programmatic_src_scroll: bool = False
        self._is_programmatic_dst_scroll: bool = False
        self._clear_src_timer: Optional[Any] = None
        self._clear_dst_timer: Optional[Any] = None

        # Tray
        self.tray = TrayManager(
            lambda fn: self.root.after(0, fn),
            lambda ms, fn: self.root.after(ms, fn),
            on_show=self._show_window,
            on_settings=self._open_settings,
            on_exit=self._quit_app,
        )

        # Идентификатор задачи синхронизации прокрутки
        self._sync_scroll_job: Optional[str] = None

        setup_theme(self.settings.theme)
        self._setup_window()
        self._build_main_window()
        apply_theme(self.root, self.settings.theme)
        self._apply_opacity()
        self._bind_events()
        setup_file_drop(self.root, self._open_file_path)
        self._apply_language_settings()
        self._start_background_tasks()

        register_global_hotkey(
            self.settings.behavior.global_hotkey or "ctrl+shift+c",
            self._handle_global_hotkey,
        )

        if self.tray.enabled:
            self.tray.create()

        if self.settings.llm.enabled:
            self.root.after(500, self._check_llm_health_startup)

    def _get_available_languages(self) -> Dict[str, str]:
        """Получить доступные языки для перевода."""
        languages = DefaultLanguages.get_defaults()

        if AT_PACKAGE_MODULE is not None:
            try:
                packages = getattr(AT_PACKAGE_MODULE, "get_installed_packages", lambda: [])()
                for package in packages:
                    for attr in ("from_code", "to_code"):
                        if hasattr(package, attr):
                            code = getattr(package, attr)
                            if code and code not in languages:
                                languages[code] = code.upper()
            except Exception as exc:
                logger.warning("Failed to query packages: %s", exc)

        return dict(sorted(languages.items()))

    def _setup_window(self) -> None:
        """Настройка главного окна."""
        self.root.title(self.cfg.title)
        self.root.geometry(f"{self.cfg.width}x{self.cfg.height}")
        self.root.minsize(self.cfg.min_width, self.cfg.min_height)

        try:
            self.root.overrideredirect(False)
        except Exception:
            pass

        # Установка иконки окна
        try:
            icon_path = get_resource_path("argos_translate.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
                logger.debug("Window icon set from: %s", icon_path)
        except Exception as exc:
            logger.debug("Failed to set window icon: %s", exc)

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

    def _restore_window_geometry(self) -> None:
        first_run = not self._settings_file_exists
        self._skip_geometry_save = True
        try:
            WindowStateManager.restore(
                self.root,
                self.settings.window_state,
                self.cfg,
                first_run=first_run,
            )
            self._window_geometry_restored = True
        finally:
            self.root.after(
                TranslationConstants.WINDOW_SAVE_DEBOUNCE_MS + 100,
                self._clear_geometry_restore_lock,
            )

    def _clear_geometry_restore_lock(self) -> None:
        self._skip_geometry_save = False

    def _apply_opacity(self) -> None:
        opacity = self.settings.opacity
        if opacity >= 1.0:
            return
        try:
            self.root.attributes("-alpha", opacity)
        except Exception as exc:
            logger.debug("Window opacity not supported: %s", exc)

    def _build_main_window(self) -> None:
        callbacks = MainWindowCallbacks(
            on_file_open=self._file_open,
            on_file_save_translation=self._file_save_translation,
            on_file_save_both=self._file_save_both,
            on_quit=self._quit_app,
            on_translate=self.translate,
            on_cancel=self._cancel_translation,
            on_open_settings=self._open_settings,
            on_stream_toggle=self._on_stream_toggle,
            on_scroll_sync_toggle=self._on_scroll_sync_toggle,
            on_copy_and_hide=self._copy_and_hide,
            on_tab_changed=self._on_translation_tab_changed,
            on_src_modified=self._on_src_modified,
            on_llm_stream_append=self._update_paragraph_offsets,
            on_editor_layout_changed=self._on_editor_layout_changed,
            on_llm_enabled_changed=self._apply_llm_enabled,
        )
        view = build_main_window(
            self.root, self.cfg, self.settings, self.languages, callbacks
        )
        self.lang_widget = view.lang_widget
        self.src_panel = view.src_panel
        self.translation_tabs = view.translation_tabs
        self.streaming_enabled = view.streaming_enabled
        self.scroll_sync_enabled = view.scroll_sync_enabled
        self.translate_status_var = view.translate_status_var
        self.status_var = view.status_var
        self.llm_indicator_var = view.llm_indicator_var
        self.llm_indicator = view.llm_indicator
        self.file_progress_frame = view.file_progress_frame
        self.file_progress_var = view.file_progress_var
        self.file_progress_label = view.file_progress_label
        self._main_view = view
        self._editor_layout: EditorLayout = normalize_editor_layout(self.settings.editor_layout)
        self._update_llm_indicator()
        apply_editor_font_scale(view, self.settings.font_scale)

    def _update_window_title(self) -> None:
        if self._document_path:
            name = self._document_path.name
            modified = " *" if getattr(self, "_document_dirty", False) else ""
            self.root.title(f"{name}{modified} — {self.cfg.title}")
        else:
            self.root.title(self.cfg.title)

    def _bind_events(self) -> None:
        """Привязка обработчиков событий."""
        self.root.bind("<Control-Return>", lambda e: self.translate())
        self.root.bind("<Control-o>", lambda e: self._file_open())
        self.root.bind("<Control-O>", lambda e: self._file_open())
        self.root.bind("<Control-Shift-S>", lambda e: self._file_save_translation())
        self.root.bind("<Control-comma>", lambda e: self._open_settings())
        self.root.bind("<Control-s>", lambda e: self.lang_widget.swap_languages())
        self.root.protocol("WM_DELETE_WINDOW", self._on_window_close)
        self.root.bind("<Configure>", self._on_window_configure)
        # При сворачивании в трей
        try:
            self.root.bind("<Unmap>", self._on_window_unmap)
        except Exception:
            pass

    def _start_background_tasks(self) -> None:
        """Запуск фоновых задач."""
        self.root.after(100, self._poll_translate_queue)
        if self.scroll_sync_enabled.get():
            self._start_scroll_sync()

    def _start_scroll_sync(self) -> None:
        """Запуск синхронизации прокрутки."""
        if self._sync_scroll_job is not None:
            return
        logger.debug("Starting scroll sync")
        self._sync_scroll_job = self.root.after(
            TranslationConstants.SCROLL_SYNC_INTERVAL_MS,
            self._sync_scroll
        )

    def _stop_scroll_sync(self) -> None:
        """Остановка синхронизации прокрутки."""
        if self._sync_scroll_job is not None:
            try:
                self.root.after_cancel(self._sync_scroll_job)
                logger.debug("Stopping scroll sync")
            except Exception:
                pass
            self._sync_scroll_job = None

    def _on_scroll_sync_toggle(self) -> None:
        """Обработчик переключения синхронизации прокрутки."""
        if self.scroll_sync_enabled.get():
            self._start_scroll_sync()
        else:
            self._stop_scroll_sync()
        logger.info("Scroll sync toggle: %s", self.scroll_sync_enabled.get())

    @property
    def tray_enabled(self) -> bool:
        return self.tray.enabled

    def _cancel_pending_translate_jobs(self) -> None:
        for attr in ("debounce_job", "llm_debounce_job"):
            job = getattr(self, attr, None)
            if not job:
                continue
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
            setattr(self, attr, None)

    def _on_src_modified(self, event: Optional[tk.Event] = None) -> None:
        """Обработчик изменения исходного текста."""
        try:
            self.src_panel.text.edit_modified(False)
        except Exception:
            pass

        if self._suppress_src_modified:
            return

        if self._document_path is not None:
            self._document_dirty = True
            self._update_window_title()
            self._update_document_status()

        if self.streaming_enabled.get():
            debounce_ms = self.settings.debounce_ms or TranslationConstants.DEBOUNCE_MS
            llm_debounce_ms = self.settings.llm_debounce_ms or 1200

            if self.debounce_job:
                try:
                    self.root.after_cancel(self.debounce_job)
                except Exception:
                    pass

            self.debounce_job = self.root.after(
                debounce_ms, lambda: self.translate(streaming=True)
            )

            if self.settings.llm.enabled:
                cfg_err = llm_config_error(self.settings.llm)
                if cfg_err:
                    self.llm_status_text = (
                        "LLM не настроена — укажите сервер в Настройках"
                    )
                    self._update_combined_status()
                else:
                    if self.llm_debounce_job:
                        try:
                            self.root.after_cancel(self.llm_debounce_job)
                        except Exception:
                            pass
                    self.llm_debounce_job = self.root.after(
                        llm_debounce_ms, self._run_llm_only
                    )

    def _on_stream_toggle(self) -> None:
        """Обработчик переключения потокового режима."""
        logger.info("Stream toggle: %s", self.streaming_enabled.get())

    def translate(self, event: Optional[tk.Event] = None, streaming: bool = False) -> None:
        """Запустить перевод текста."""
        self._cancel_pending_translate_jobs()

        text = self.src_panel.get_text()
        if not text or len(text.strip()) < 2:
            return

        if self._document_path and not self._confirm_large_text(len(text)):
            return

        if not self._document_path:
            self._hide_file_progress()

        self.coord.signal_argos_restart()
        if self.translate_thread and self.translate_thread.is_alive():
            time.sleep(0.05)
        self.coord.clear_argos_restart()

        units = TextUtils.build_argos_units(
            text,
            translate_code_blocks=self.settings.files.translate_code_blocks,
        )
        if not units:
            return

        from_code = self.lang_widget.get_from_code()
        to_code = self.lang_widget.get_to_code()

        if from_code == "auto":
            detected = TextUtils.detect_language(text)
            from_code = detected
            auto_target = self.settings.auto_target_lang or "ru"
            to_code = auto_target if detected != auto_target else ("en" if detected == "ru" else "ru")

            try:
                from_name = self.languages.get(from_code, from_code)
                to_name = self.languages.get(to_code, to_code)
                try:
                    self.lang_widget.combo_from.set(f"{from_code.upper()} - {from_name}")
                    self.lang_widget.combo_to.set(f"{to_code.upper()} - {to_name}")
                except Exception:
                    pass
            except Exception:
                pass

        job_id = self.coord.allocate_job()
        model_mgr = ModelManager(self.settings.argos.packages_dir)
        argos_pair_available = model_mgr.has_pair(from_code, to_code)

        if not argos_pair_available:
            logger.warning("Argos preflight: no model for %s→%s", from_code, to_code)
            self.translation_tabs.clear_argos()
            self.translation_tabs.set_argos_text(
                f"[Argos: нет модели {from_code}→{to_code}]"
            )
            self.translation_tabs.set_tab_status("argos", "error")
            self.translate_status_var.set(f"Argos: нет модели {from_code}→{to_code}")
            self._update_combined_status()
            if self._document_path:
                self._hide_file_progress()
            if not streaming:
                self._start_llm_translation(
                    job_id, text, from_code, to_code, self._document_file_type
                )
            logger.info(
                "Translation started (LLM only): job=%d %s→%s, %d chars, streaming=%s",
                job_id,
                from_code,
                to_code,
                len(text),
                streaming,
            )
            return

        self.coord.start_argos(job_id, len(units))

        self.translation_tabs.clear_argos()

        # Установка статуса перевода
        self.translate_status_var.set(f"Argos: 0/{len(units)} чанков")
        self._update_combined_status()
        if self._document_path:
            self._show_file_progress(0, len(units))

        self.translate_thread = threading.Thread(
            target=self._translate_worker,
            args=(job_id, units, from_code, to_code),
            daemon=True,
        )
        self.translate_thread.start()

        if not streaming:
            self._start_llm_translation(
                job_id, text, from_code, to_code, self._document_file_type
            )

        logger.info(
            "Translation started: job=%d %s→%s, %d chars, %d units, streaming=%s",
            job_id,
            from_code,
            to_code,
            len(text),
            len(units),
            streaming,
        )

    def _translate_worker(
        self,
        job_id: int,
        units: List[Tuple[str, int, bool]],
        from_code: str,
        to_code: str,
    ) -> None:
        """Воркер для выполнения перевода в отдельном потоке."""
        logger.info(
            "Argos worker %d: start %s→%s (%d units)",
            job_id,
            from_code,
            to_code,
            len(units),
        )

        for i, unit in enumerate(units):
            chunk_text, para_idx, translatable = (
                unit if len(unit) == 3 else (unit[0], unit[1], True)
            )
            if self.coord.argos_should_stop(job_id):
                logger.info("Argos worker %d: stopped at chunk %d/%d", job_id, i, len(units))
                return

            try:
                if not translatable:
                    output = chunk_text
                    logger.debug(
                        "Argos worker %d: chunk %d/%d skipped (non-translatable, para %d)",
                        job_id,
                        i + 1,
                        len(units),
                        para_idx,
                    )
                else:
                    cached = None
                    if self.settings.behavior.translation_cache_enabled:
                        cached = self._translation_cache.get(chunk_text, from_code, to_code)
                    if cached is not None:
                        output = cached
                        logger.debug(
                            "Argos worker %d: chunk %d/%d cache hit (%d chars)",
                            job_id,
                            i + 1,
                            len(units),
                            len(chunk_text),
                        )
                    else:
                        logger.info(
                            "Argos worker %d: chunk %d/%d translating (%d chars): %r",
                            job_id,
                            i + 1,
                            len(units),
                            len(chunk_text),
                            _log_text_preview(chunk_text),
                        )
                        output = self.engine.translate(chunk_text, from_code, to_code)
                        logger.debug(
                            "Argos worker %d: chunk %d/%d done (%d chars out)",
                            job_id,
                            i + 1,
                            len(units),
                            len(output),
                        )
                        if self.settings.behavior.translation_cache_enabled:
                            self._translation_cache.put(chunk_text, from_code, to_code, output)
                self.translate_queue.put((job_id, i, output, para_idx))
            except Exception as exc:
                logger.error(
                    "Argos worker %d: chunk %d/%d error: %s",
                    job_id,
                    i + 1,
                    len(units),
                    exc,
                )
                self.translate_queue.put((job_id, i, f"[Error: {str(exc)[:50]}]", para_idx))

        logger.info("Argos worker %d: finished (%d units)", job_id, len(units))

    def _poll_translate_queue(self) -> None:
        """Опрос очереди переводов для обновления интерфейса."""
        try:
            items: List[Tuple[int, int, str, int]] = []
            while True:
                try:
                    item = self.translate_queue.get_nowait()
                    items.append(item)
                except queue.Empty:
                    break

            if items:
                logger.debug("Translate poll: %d chunk result(s)", len(items))
                self._handle_translate_results(items)
        except Exception as exc:
            logger.error("Poll error: %s", exc)
        finally:
            self.root.after(TranslationConstants.QUEUE_POLL_INTERVAL_MS, self._poll_translate_queue)

    def _handle_translate_results(self, results: List[Tuple[int, int, str, int]]) -> None:
        """Обработка результатов перевода."""
        need_update = False

        for job_id, idx, text, para_idx in results:
            if self.coord.record_argos_chunk(job_id, idx, text, para_idx):
                need_update = True

        if need_update and self.coord.active_job is not None:
            self._update_translated_text(self.coord.active_job)

            done, total = self.coord.argos_progress()
            if total > 0:
                progress = (done / total) * 100
                self.translate_status_var.set(
                    f"Argos: {done}/{total} чанков ({progress:.0f}%)"
                )
                if self._document_path:
                    self._show_file_progress(done, total)
                self._update_combined_status()

    def _update_translated_text(self, job_id: int) -> None:
        """Обновление текста перевода в интерфейсе."""
        partials = self.coord.partial_translations.get(job_id, {})
        total = self.coord.total_units.get(job_id, 0)

        if total == 0:
            return

        para_blocks: Dict[int, List[str]] = {}
        last_para = 0

        for i in range(total):
            entry = partials.get(i)
            if entry:
                text, para_idx = entry
                para_blocks.setdefault(para_idx, []).append(text)
                last_para = para_idx
            else:
                para_blocks.setdefault(last_para, []).append("")

        max_idx = max(para_blocks.keys()) if para_blocks else -1
        out_paras: List[str] = []

        for para_idx in range(max_idx + 1):
            sents = para_blocks.get(para_idx, [])
            non_empty = [x for x in sents if x]
            if non_empty:
                out_paras.append(" ".join(non_empty))

        final = "\n\n".join(out_paras)
        self.translation_tabs.set_argos_text(final)
        self._update_paragraph_offsets()
        is_complete = len(partials) >= total
        self.translation_tabs.set_tab_status("argos", "streaming" if not is_complete else "done")

        # Проверка завершения перевода
        if is_complete:
            logger.info(
                "Argos job %d complete: %d/%d chunks, %d chars output",
                job_id,
                len(partials),
                total,
                len(final),
            )
            self.translate_status_var.set("Argos: ✓ готово")
            if self._document_path:
                total = self.coord.total_units.get(job_id, 0)
                self._show_file_progress(total, total)
            self._update_combined_status()

    def _update_paragraph_offsets(self) -> None:
        """Обновление оффсетов параграфов для синхронизации прокрутки."""
        try:
            src = self.src_panel.text.get("1.0", tk.END)
            if (
                self.translation_tabs.get_active_engine() == "llm"
                and self.translation_tabs.llm_text is not None
            ):
                dst_widget = self.translation_tabs.llm_text
            else:
                dst_widget = self.translation_tabs.argos_text
            dst = dst_widget.get("1.0", tk.END)

            src_paras = re.split(r"\n{2,}", src)
            dst_paras = re.split(r"\n{2,}", dst)

            self.src_offsets = self._compute_offsets(src_paras)
            self.dst_offsets = self._compute_offsets(dst_paras)

            self.src_total_chars = max(1, len(src) - 1)
            self.dst_total_chars = max(1, len(dst) - 1)
        except Exception as exc:
            logger.debug("Offset update error: %s", exc)
            self.src_total_chars = 1
            self.dst_total_chars = 1

    def _compute_offsets(self, paras: List[str]) -> List[int]:
        """Вычисление оффсетов для параграфов."""
        offsets: List[int] = []
        cumulative = 0
        for para in paras:
            offsets.append(cumulative)
            cumulative += len(para) + 2
        return offsets

    def _lock_programmatic_src(self) -> None:
        """Блокировка программной прокрутки исходного текста."""
        self._is_programmatic_src_scroll = True
        if self._clear_src_timer:
            try:
                self.root.after_cancel(self._clear_src_timer)
            except Exception:
                pass
        self._clear_src_timer = self.root.after(
            TranslationConstants.PROGRAMMATIC_SCROLL_LOCK_MS, self._clear_programmatic_src
        )

    def _lock_programmatic_dst(self) -> None:
        """Блокировка программной прокрутки перевода."""
        self._is_programmatic_dst_scroll = True
        if self._clear_dst_timer:
            try:
                self.root.after_cancel(self._clear_dst_timer)
            except Exception:
                pass
        self._clear_dst_timer = self.root.after(
            TranslationConstants.PROGRAMMATIC_SCROLL_LOCK_MS, self._clear_programmatic_dst
        )

    def _clear_programmatic_src(self) -> None:
        """Снятие блокировки программной прокрутки исходного текста."""
        self._is_programmatic_src_scroll = False
        self._clear_src_timer = None

    def _clear_programmatic_dst(self) -> None:
        """Снятие блокировки программной прокрутки перевода."""
        self._is_programmatic_dst_scroll = False
        self._clear_dst_timer = None

    def _sync_scroll(self) -> None:
        """Синхронизация прокрутки между панелями."""
        if not self.scroll_sync_enabled.get() or self._editor_layout != "split":
            self._sync_scroll_job = None
            return

        try:
            try:
                src_frac = self.src_panel.text.yview()[0]
            except Exception:
                src_frac = None

            try:
                dst_frac = self.translation_tabs.get_active_text_widget().yview()[0]
            except Exception:
                dst_frac = None

            if (
                src_frac is not None
                and (self.last_src_pos is None or abs(src_frac - self.last_src_pos) > TranslationConstants.SCROLL_EPSILON)
                and not self._is_programmatic_src_scroll
            ):
                if self.dst_total_chars <= 1:
                    self.last_src_pos = src_frac
                    self.last_dst_pos = None
                else:
                    self._lock_programmatic_dst()
                    try:
                        src_chars = max(1, self.src_total_chars)
                        dst_chars = max(1, self.dst_total_chars)
                        src_pos = int(src_frac * (src_chars - 1)) if src_chars > 1 else 0
                        dst_frac_calc = src_pos / (dst_chars - 1) if dst_chars > 1 else 0.0
                        dst_frac_calc = max(0.0, min(1.0, dst_frac_calc))

                        try:
                            dst_insert = self.translation_tabs.get_active_text_widget().index(tk.INSERT)
                        except Exception:
                            dst_insert = "1.0"

                        try:
                            self.translation_tabs.get_active_text_widget().yview_moveto(dst_frac_calc)
                        except Exception:
                            pass

                        try:
                            self.translation_tabs.get_active_text_widget().mark_set(tk.INSERT, dst_insert)
                        except Exception:
                            pass
                    except Exception as exc:
                        logger.debug("Sync map left->right error: %s", exc)

                    self.last_src_pos = src_frac
                    self.last_dst_pos = dst_frac_calc

            elif (
                dst_frac is not None
                and (self.last_dst_pos is None or abs(dst_frac - self.last_dst_pos) > TranslationConstants.SCROLL_EPSILON)
                and not self._is_programmatic_dst_scroll
            ):
                if self.src_total_chars <= 1:
                    self.last_dst_pos = dst_frac
                    self.last_src_pos = None
                else:
                    self._lock_programmatic_src()
                    try:
                        dst_chars = max(1, self.dst_total_chars)
                        src_chars = max(1, self.src_total_chars)
                        dst_pos = int(dst_frac * (dst_chars - 1)) if dst_chars > 1 else 0
                        src_frac_calc = dst_pos / (src_chars - 1) if src_chars > 1 else 0.0
                        src_frac_calc = max(0.0, min(1.0, src_frac_calc))

                        try:
                            src_insert = self.src_panel.text.index(tk.INSERT)
                        except Exception:
                            src_insert = "1.0"

                        try:
                            self.src_panel.text.yview_moveto(src_frac_calc)
                        except Exception:
                            pass

                        try:
                            self.src_panel.text.mark_set(tk.INSERT, src_insert)
                        except Exception:
                            pass
                    except Exception as exc:
                        logger.debug("Sync map right->left error: %s", exc)

                    self.last_dst_pos = dst_frac
                    self.last_src_pos = src_frac_calc

        except Exception as exc:
            logger.debug("Scroll sync error: %s", exc)

        if self.scroll_sync_enabled.get():
            self._sync_scroll_job = self.root.after(
                TranslationConstants.SCROLL_SYNC_INTERVAL_MS,
                self._sync_scroll
            )

    def _handle_global_hotkey(self) -> None:
        """Обработчик глобальной горячей клавиши Ctrl+Shift+C."""
        text = capture_selection_text(
            restore_original=self.settings.behavior.restore_clipboard_after_capture
        )
        if text:
            self.root.after(0, lambda: self._handle_copied_text(text))

    def _handle_copied_text(self, text: str) -> None:
        """Обработка скопированного текста: показать окно, вставить текст, начать перевод."""
        self._show_window()
        self.src_panel.set_text(text)

        max_chars = self.settings.files.hotkey_auto_translate_max_chars
        if max_chars <= 0 or len(text) <= max_chars:
            self.translate()

    def _show_window(self) -> None:
        """Показать окно приложения (из трея или из свёрнутого состояния)."""
        try:
            self.root.deiconify()
            self.root.update_idletasks()
            if not self._window_geometry_restored:
                self._restore_window_geometry()
            self.root.lift()
            self.root.focus_force()
            try:
                self.root.attributes("-topmost", True)
                self.root.after(200, lambda: self.root.attributes("-topmost", False))
            except Exception:
                pass
        except Exception:
            pass

    def _copy_and_hide(self) -> None:
        """Копировать перевод в буфер обмена и опционально скрыть окно в трей."""
        self.translation_tabs.copy_active()
        if self.settings.behavior.minimize_to_tray_on_copy_hide:
            self._hide_to_tray()

    def _on_window_close(self) -> None:
        """Обработчик крестика окна — трей или выход по настройке."""
        if self.settings.behavior.close_action == "exit":
            self._quit_app()
        else:
            self._hide_to_tray()

    def _hide_to_tray(self) -> None:
        """Скрыть окно в трей."""
        try:
            self._persist_window_state()
            self.root.withdraw()
            self.tray.ensure()
            logger.info("Window hidden to tray")
        except Exception as exc:
            logger.exception("Hide to tray failed: %s", exc)

    def _on_window_configure(self, event: Optional[tk.Event] = None) -> None:
        if event is not None and event.widget is not self.root:
            return
        self._schedule_window_geometry_save()

    def _schedule_window_geometry_save(self) -> None:
        if self._skip_geometry_save:
            return
        if self._window_save_job:
            try:
                self.root.after_cancel(self._window_save_job)
            except Exception:
                pass
        self._window_save_job = self.root.after(
            TranslationConstants.WINDOW_SAVE_DEBOUNCE_MS,
            self._persist_window_state,
        )

    def _persist_window_state(self) -> None:
        if self._skip_geometry_save:
            return
        if not self._window_geometry_restored:
            return
        try:
            if str(self.root.state()) == "withdrawn":
                return
            self.settings.window_state = WindowStateManager.capture(self.root)
            self.settings.streaming = self.streaming_enabled.get()
            self.settings.scroll_sync = self.scroll_sync_enabled.get()
            if hasattr(self, "lang_widget"):
                self.settings.lang_from = self.lang_widget.get_from_code()
                self.settings.lang_to = self.lang_widget.get_to_code()
            if hasattr(self, "translation_tabs"):
                self.settings.active_translation_tab = self.translation_tabs.get_active_engine()
            self.settings.editor_layout = self._editor_layout
            save_settings(self.settings)
        except Exception as exc:
            logger.debug("Persist window state failed: %s", exc)

    def _quit_app(self) -> None:
        """Полный выход из приложения (меню трея)."""
        if self._clear_src_timer:
            try:
                self.root.after_cancel(self._clear_src_timer)
            except Exception:
                pass

        if self._clear_dst_timer:
            try:
                self.root.after_cancel(self._clear_dst_timer)
            except Exception:
                pass

        self._stop_scroll_sync()
        self._persist_window_state()
        self.coord.cancel()
        self.tray.stop()
        try:
            self.root.destroy()
        except Exception:
            pass

    def _apply_language_settings(self) -> None:
        from_code = self.settings.lang_from
        to_code = self.settings.lang_to
        try:
            if str(from_code).lower() == "auto":
                self.lang_widget.combo_from.set("AUTO")
            else:
                from_name = self.languages.get(from_code, from_code)
                self.lang_widget.combo_from.set(f"{str(from_code).upper()} - {from_name}")
            to_name = self.languages.get(to_code, to_code)
            self.lang_widget.combo_to.set(f"{str(to_code).upper()} - {to_name}")
        except Exception as exc:
            logger.debug("Apply language settings failed: %s", exc)

    def _apply_llm_enabled(self, enabled: bool) -> None:
        """Включить/выключить LLM (шапка или настройки)."""
        old = self.settings.llm.enabled
        self.settings.llm.enabled = enabled
        if hasattr(self, "translation_tabs"):
            self.translation_tabs.set_llm_enabled(enabled)
            if not enabled and self.settings.active_translation_tab == "llm":
                self.settings.active_translation_tab = "argos"
                self.translation_tabs.set_active_tab("argos")

        if not enabled:
            self.coord.signal_llm_restart()
            self.coord.llm_active_job = None
            self.llm_status_text = "LLM: отключена"
            self._update_combined_status()
        else:
            cfg_err = llm_config_error(self.settings.llm)
            if cfg_err:
                self.llm_status_text = (
                    "LLM не настроена — укажите сервер в Настройках"
                )
                if hasattr(self, "translation_tabs"):
                    self.translation_tabs.set_tab_status("llm", "offline")
                self._update_combined_status()
            else:
                self.llm_status_text = ""
                self._update_combined_status()

        self.llm_health.invalidate()
        self._update_llm_indicator()
        save_settings(self.settings)

        if enabled and not old:
            self.root.after(500, self._check_llm_health_startup)

        logger.info("LLM enabled toggle: %s", enabled)

    def _open_settings(self) -> None:
        """Открыть диалог настроек."""

        def on_apply(new_settings: AppSettings) -> None:
            old_llm = self.settings.llm.enabled
            self.settings = new_settings
            save_settings(self.settings)
            apply_theme(self.root, self.settings.theme)
            self._apply_opacity()
            apply_editor_font_scale(self._main_view, self.settings.font_scale)
            layout = normalize_editor_layout(self.settings.editor_layout)
            self._apply_editor_layout(layout)
            self.streaming_enabled.set(self.settings.streaming)
            self.scroll_sync_enabled.set(self.settings.scroll_sync)
            if self.settings.scroll_sync:
                self._start_scroll_sync()
            else:
                self._stop_scroll_sync()
            if hasattr(self, "translation_tabs"):
                self.translation_tabs.set_llm_enabled(self.settings.llm.enabled)
                self.translation_tabs.set_active_tab(self.settings.active_translation_tab)
            self.llm_health.invalidate()
            self._update_llm_indicator()
            if self.settings.llm.enabled != old_llm:
                if not self.settings.llm.enabled:
                    self.coord.signal_llm_restart()
                    self.coord.llm_active_job = None
                    self.llm_status_text = "LLM: отключена"
                    self._update_combined_status()
                elif llm_config_error(self.settings.llm):
                    self.llm_status_text = (
                        "LLM не настроена — укажите сервер в Настройках"
                    )
                    self._update_combined_status()
            if self.settings.llm.enabled and not old_llm:
                self.root.after(500, self._check_llm_health_startup)
            self._translation_cache = TranslationCache(
                max_size=new_settings.behavior.translation_cache_size
            )
            self.engine = TranslateEngine(prefer_api=new_settings.argos.prefer_api_over_cli)

        def on_geometry_save(partial: AppSettings) -> None:
            self.settings.settings_dialog_state = partial.settings_dialog_state
            save_settings(self.settings)

        SettingsDialog(
            self.root,
            self.settings,
            on_apply,
            self.cfg,
            on_geometry_save=on_geometry_save,
        )

    def _on_translation_tab_changed(self, tab_id: str) -> None:
        self.settings.active_translation_tab = tab_id
        self._update_paragraph_offsets()
        self._schedule_window_geometry_save()

    def _on_editor_layout_changed(self, panel: str) -> None:
        new_mode = toggle_layout_for_panel(self._editor_layout, panel)  # type: ignore[arg-type]
        self._apply_editor_layout(new_mode)

    def _apply_editor_layout(self, mode: EditorLayout) -> None:
        self._editor_layout = mode
        self.settings.editor_layout = mode
        if hasattr(self, "_main_view"):
            set_editor_layout(self._main_view, mode)
        self._schedule_window_geometry_save()
        if mode != "split":
            self._stop_scroll_sync()
        elif self.scroll_sync_enabled.get():
            self._start_scroll_sync()

    def _check_llm_health_startup(self) -> None:
        if not self.settings.llm.enabled:
            return

        def worker() -> None:
            status = self.llm_health.check()
            self.root.after(0, lambda: self._apply_llm_health_status(status))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_llm_health_status(self, status: LLMStatus) -> None:
        theme = self.settings.theme
        labels = {
            LLMStatus.AVAILABLE: ("● LLM", get_status_color(theme, "available")),
            LLMStatus.BUSY: ("● LLM", get_status_color(theme, "busy")),
            LLMStatus.OFFLINE: ("○ LLM", get_status_color(theme, "offline")),
            LLMStatus.DISABLED: ("", get_status_color(theme, "disabled")),
        }
        text, color = labels.get(status, ("○ LLM", get_status_color(theme, "offline")))
        self.llm_indicator_var.set(text if self.settings.llm.enabled else "")
        try:
            self.llm_indicator.configure(text_color=color)
        except Exception:
            pass

    def _update_llm_indicator(self) -> None:
        if not self.settings.llm.enabled:
            self.llm_indicator_var.set("")
            return
        self._apply_llm_health_status(self.llm_health.cached_status())

    def _update_combined_status(self) -> None:
        argos = self.translate_status_var.get()
        if self.settings.llm.enabled and self.llm_status_text:
            self.status_var.set(f"{argos} · {self.llm_status_text}" if argos else self.llm_status_text)
        elif argos:
            self.status_var.set(argos)
        else:
            self.status_var.set("Готов к работе")

    def _run_llm_only(self) -> None:
        self.llm_debounce_job = None
        text = self.src_panel.get_text()
        if not text or not text.strip() or len(text.strip()) < 2:
            return
        from_code = self.lang_widget.get_from_code()
        to_code = self.lang_widget.get_to_code()
        if from_code == "auto":
            detected = TextUtils.detect_language(text)
            from_code = detected
            auto_target = self.settings.auto_target_lang or "ru"
            to_code = auto_target if detected != auto_target else ("en" if detected == "ru" else "ru")
        llm_job = self.coord.active_job or self.coord.allocate_job()
        self._start_llm_translation(
            llm_job, text, from_code, to_code, self._document_file_type
        )

    def _cancel_translation(self) -> None:
        """Отменить текущий перевод Argos и LLM."""
        self.coord.cancel()
        self.translate_status_var.set("")
        self.llm_status_text = ""
        self._hide_file_progress()
        self._update_document_status()
        logger.info("Translation cancelled")

    def _confirm_large_text(self, char_count: int) -> bool:
        limit = self.settings.files.large_file_warn_chars
        if char_count <= limit:
            return True
        return messagebox.askyesno(
            "Большой файл",
            f"Текст содержит {char_count:,} символов (порог {limit:,}).\n"
            "Перевод может занять много времени. Продолжить?",
        )

    def _show_file_progress(self, done: int, total: int) -> None:
        if not self._document_path or total <= 0:
            self._hide_file_progress()
            return
        percent = min(100.0, (done / total) * 100)
        self.file_progress_var.set(f"{percent:.0f}%")
        self.file_progress_frame.pack(side="right", before=self.llm_indicator)

    def _hide_file_progress(self) -> None:
        self.file_progress_frame.pack_forget()
        self.file_progress_var.set("")

    def _file_dialog_types(self) -> List[Tuple[str, str]]:
        ext_pattern = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTENSIONS))
        return [("Text files", ext_pattern), ("All files", "*.*")]

    def _open_file_path(self, path_str: str) -> None:
        """Открыть текстовый файл по пути (меню, DnD)."""
        path = Path(path_str)
        try:
            decoded = read_text_file(path, max_size_mb=self.settings.files.max_file_size_mb)
        except DocumentIOError as exc:
            messagebox.showerror("Файл", str(exc))
            return

        self._document_path = decoded.path
        self._document_encoding = decoded.encoding
        self._document_file_type = file_type_hint(decoded.path)
        self._document_dirty = False
        self._document_paragraph_count = len(TextUtils.split_into_paragraphs(decoded.text))
        self._cancel_pending_translate_jobs()
        self._suppress_src_modified = True
        try:
            self.src_panel.set_text(decoded.text)
        finally:
            self.root.after(0, lambda: setattr(self, "_suppress_src_modified", False))
        self._update_window_title()
        self._update_document_status()
        self.translate()
        logger.info("Opened file: %s", decoded.path.name)

    def _file_open(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Открыть файл",
            filetypes=self._file_dialog_types(),
        )
        if not path_str:
            return
        self._open_file_path(path_str)

    def _file_save_translation(self) -> None:
        if not self._document_path and not self.translation_tabs.get_active_text():
            messagebox.showinfo("Сохранение", "Нет перевода для сохранения")
            return

        engine = self.translation_tabs.get_active_engine()
        text = self.translation_tabs.get_active_text()
        if not text:
            messagebox.showinfo("Сохранение", "Нет перевода для сохранения")
            return

        if self._document_path:
            default = suggest_output_path(
                self._document_path,
                self.settings.files.output_suffix,
                engine,
            )
        else:
            default = Path("translation.txt")

        path_str = filedialog.asksaveasfilename(
            title="Сохранить перевод",
            initialfile=default.name,
            initialdir=str(default.parent) if default.parent.exists() else None,
            defaultextension=default.suffix or ".txt",
            filetypes=self._file_dialog_types(),
        )
        if not path_str:
            return

        out_enc = resolve_output_encoding(
            self._document_encoding,
            self.settings.files.output_encoding,
        )
        try:
            write_text_file(Path(path_str), text, out_enc)
            messagebox.showinfo("Сохранение", f"Сохранено: {path_str}")
        except Exception as exc:
            messagebox.showerror("Сохранение", str(exc))

    def _file_save_both(self) -> None:
        if not self._document_path:
            messagebox.showinfo("Сохранение", "Сначала откройте исходный файл")
            return

        argos_text = self.translation_tabs.get_argos_text()
        llm_text = self.translation_tabs.get_llm_text()
        if not argos_text and not llm_text:
            messagebox.showinfo("Сохранение", "Нет перевода для сохранения")
            return

        out_enc = resolve_output_encoding(
            self._document_encoding,
            self.settings.files.output_encoding,
        )
        suffix = self.settings.files.output_suffix
        saved: List[str] = []

        try:
            if argos_text:
                argos_path = suggest_output_path(self._document_path, suffix, "argos")
                write_text_file(argos_path, argos_text, out_enc)
                saved.append(str(argos_path))
            if llm_text and self.settings.llm.enabled:
                llm_path = suggest_output_path(self._document_path, suffix, "llm")
                write_text_file(llm_path, llm_text, out_enc)
                saved.append(str(llm_path))
            messagebox.showinfo("Сохранение", "Сохранено:\n" + "\n".join(saved))
        except Exception as exc:
            messagebox.showerror("Сохранение", str(exc))

    def _update_document_status(self) -> None:
        if self.translate_status_var.get() or self.llm_status_text:
            return
        if self._document_path:
            mod = " · изменён" if self._document_dirty else ""
            self.status_var.set(f"{self._document_path.name}{mod}")
        else:
            self.status_var.set("Готов к работе")

    def _start_llm_translation(
        self,
        llm_job: int,
        text: str,
        from_code: str,
        to_code: str,
        file_type: Optional[str] = None,
    ) -> None:
        if not self.settings.llm.enabled:
            return

        cfg_err = llm_config_error(self.settings.llm)
        if cfg_err:
            msg = "[LLM не настроена]"
            logger.info("LLM job %d: skipped (not configured: %s)", llm_job, cfg_err)
            self.translation_tabs.set_llm_text(msg)
            self.translation_tabs.set_tab_status("llm", "offline")
            self.llm_status_text = "LLM не настроена — укажите сервер в Настройках"
            self._update_combined_status()
            self._update_llm_indicator()
            return

        status = self.llm_health.cached_status()
        if status != LLMStatus.AVAILABLE:
            messages = {
                LLMStatus.OFFLINE: "[LLM недоступна]",
                LLMStatus.BUSY: "[LLM занята, повторите позже…]",
            }
            msg = messages.get(status, "[LLM отключена]")
            logger.info("LLM job %d: skipped (%s)", llm_job, status)
            self.translation_tabs.set_llm_text(msg)
            self.translation_tabs.set_tab_status("llm", "offline")
            self.llm_status_text = f"LLM: {msg.strip('[]')}"
            self._update_combined_status()
            self._update_llm_indicator()
            return

        self.coord.signal_llm_restart()
        if self.llm_translate_thread and self.llm_translate_thread.is_alive():
            time.sleep(0.05)
        self.coord.clear_llm_restart()
        self.coord.start_llm(llm_job)
        self.translation_tabs.begin_llm_stream()
        self.translation_tabs.set_tab_status("llm", "streaming")
        self.llm_status_text = "LLM: streaming…"
        self._update_combined_status()

        logger.info(
            "LLM job %d: started %s→%s, %d chars%s",
            llm_job,
            from_code,
            to_code,
            len(text),
            f", file_type={file_type}" if file_type else "",
        )

        self.llm_translate_thread = threading.Thread(
            target=self._llm_worker,
            args=(llm_job, text, from_code, to_code, file_type),
            daemon=True,
        )
        self.llm_translate_thread.start()

    def _llm_worker(
        self,
        llm_job: int,
        text: str,
        from_code: str,
        to_code: str,
        file_type: Optional[str] = None,
    ) -> None:
        pending_text = [""]
        ui_scheduled = [False]
        token_log_counter = [0]

        def schedule_ui_update() -> None:
            if ui_scheduled[0]:
                return
            ui_scheduled[0] = True

            def flush() -> None:
                ui_scheduled[0] = False
                if self.coord.llm_is_stale(llm_job):
                    return
                self.translation_tabs.append_llm_stream_text(pending_text[0])
                self.llm_status_text = "LLM: streaming…"
                self._update_combined_status()

            self.root.after(50, flush)

        def on_token(partial: str) -> None:
            if self.coord.llm_is_stale(llm_job):
                return
            pending_text[0] = partial
            token_log_counter[0] += 1
            if token_log_counter[0] == 1 or token_log_counter[0] % 20 == 0:
                logger.debug(
                    "LLM worker %d: streaming… %d chars received",
                    llm_job,
                    len(partial),
                )
            schedule_ui_update()

        def on_done(full_text: str) -> None:
            if self.coord.llm_is_stale(llm_job):
                logger.info("LLM worker %d: done (stale job, ignored)", llm_job)
                return
            logger.info(
                "LLM worker %d: finished, %d chars output",
                llm_job,
                len(full_text),
            )

            def finish() -> None:
                partial = "[LLM Error:" in full_text
                self.translation_tabs.end_llm_stream(final_text=full_text)
                self.translation_tabs.set_tab_status("llm", "partial" if partial else "done")
                if partial:
                    self.llm_status_text = "LLM: частично (есть ошибки)"
                else:
                    self.llm_status_text = "LLM: ✓ готово"
                    self.llm_health.invalidate()
                self._update_combined_status()

            self.root.after(0, finish)

        def on_error(message: str) -> None:
            if self.coord.llm_is_stale(llm_job):
                logger.info("LLM worker %d: error on stale job: %s", llm_job, message)
                return
            logger.warning("LLM worker %d: error: %s", llm_job, message)
            if "429" in message:
                self.llm_health.mark_busy()

            def show_error() -> None:
                if pending_text[0] and "[LLM Error:" in pending_text[0]:
                    self.translation_tabs.end_llm_stream(final_text=pending_text[0])
                    self.translation_tabs.set_tab_status("llm", "partial")
                    self.llm_status_text = "LLM: частично (есть ошибки)"
                else:
                    self.translation_tabs.end_llm_stream(final_text=message)
                    self.translation_tabs.set_tab_status("llm", "error")
                    self.llm_status_text = f"LLM: {message}"
                self._update_combined_status()
                self._update_llm_indicator()

            self.root.after(0, show_error)

        def on_chunk_progress(done: int, total: int) -> None:
            if not file_type:
                return

            def update_progress() -> None:
                if self.coord.llm_is_stale(llm_job):
                    return
                self._show_file_progress(done, total)
                self.llm_status_text = f"LLM: блок {done}/{total}…"
                self._update_combined_status()

            self.root.after(0, update_progress)

        try:
            logger.info("LLM worker %d: calling translate_stream", llm_job)
            translate_stream(
                self.settings.llm,
                text,
                from_code,
                to_code,
                self.languages,
                on_token,
                on_done,
                on_error,
                self.coord.llm_stop,
                file_type=file_type,
                on_chunk_progress=on_chunk_progress,
            )
        except Exception as exc:
            logger.error("LLM worker %d: exception: %s", llm_job, exc)
            on_error(str(exc)[:80])

    def _on_window_unmap(self, event: Optional[tk.Event] = None) -> None:
        """При сворачивании окна — показать иконку в трее (без повторного withdraw)."""
        if event is not None and event.widget is not self.root:
            return
        if self._tray_unmap_guard:
            return
        try:
            state = str(self.root.state()).lower()
            if state not in ("iconic", "withdrawn"):
                return
            self._tray_unmap_guard = True
            self.tray.ensure()
        except Exception as exc:
            logger.debug("On window unmap: %s", exc)
        finally:
            self.root.after(200, lambda: setattr(self, "_tray_unmap_guard", False))
