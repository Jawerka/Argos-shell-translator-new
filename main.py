#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Argos Translate Streaming — графический редактор для потокового перевода текста.

НАЗНАЧЕНИЕ:
    Приложение обеспечивает мгновенный перевод текста между языками с использованием
    движка Argos Translate. Поддерживает автоматическое определение языка,
    потоковый режим перевода при наборе текста, синхронизацию прокрутки и работу в трее.

ОСНОВНОЙ ФУНКЦИОНАЛ:
    • Потоковый перевод (streaming) — перевод обновляется автоматически при изменении текста
    • Поддержка API Argos Translate и CLI (argos-translate)
    • Автоматическое определение языка исходного текста (langdetect или эвристика)
    • Синхронизация прокрутки между исходным текстом и переводом
    • Работа в системном трее с горячими клавишами (Ctrl+Shift+C для захвата текста)
    • Сохранение настроек (размер окна, выбранные языки, режимы)
    • Установка моделей перевода из локальной папки argos_models
    • Многоязычный интерфейс (поддержка 14+ языков)

ТРЕБУЕМЫЕ МОДУЛИ (устанавливаются через pip):
    • argostranslate   — основной движок перевода (API + CLI)
    • pyperclip        — работа с буфером обмена
    • keyboard         — глобальные горячие клавиши (опционально)
    • langdetect       — точное определение языка (опционально)
    • pystray          — иконка в трее (опционально)
    • Pillow/PIL       — обработка иконок (опционально)

СТАНДАРТНЫЕ МОДУЛИ Python:
    • tkinter          — графический интерфейс
    • threading        — многопоточность для фонового перевода
    • queue            — очередь результатов перевода
    • logging          — система логирования
    • json             — сохранение настроек
    • pathlib          — работа с путями
    • re               — регулярные выражения для разбивки текста
    • subprocess       — запуск CLI утилиты
    • time             — задержки и таймеры
    • dataclasses      — конфигурационные структуры
    • enum             — перечисления статусов

АРХИТЕКТУРА:
    • TranslateEngine — движок перевода (API или CLI с фолбэком)
    • TextUtils      — утилиты для разбивки текста и определения языка
    • TextPanel      — компонент текстовой панели с буфером обмена
    • CompactLanguageSelector — компактный селектор языков
    • TranslatorApp   — главное приложение с UI и логикой
    • LoggingConfig   — конфигурация логирования в ~/.argos_transtranslate/app_streaming.log

КОНФИГУРАЦИЯ:
    Настройки сохраняются в ~/.argos_translate/settings.json
    Логи пишутся в ~/.argos_translate/app_streaming.log
    Модели устанавливаются в ~/.local/share/argos-translate/packages/

ГОРЯЧИЕ КЛАВИШИ:
    Ctrl+Enter        — запустить перевод
    Ctrl+S            — поменять языки местами
    Ctrl+Shift+C      — захватить текст из буфера обмена (глобально)

ПРИМЕЧАНИЕ:
    Все опциональные модули обрабатываются безопасно — при их отсутствии
    соответствующие функции отключаются с выводом предупреждения в лог.
"""
from __future__ import annotations

import importlib
import json
import logging
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox


# -------------------------------------------------------------------------
# Утилиты для портативной сборки (PyInstaller)
# -------------------------------------------------------------------------


def get_resource_path(relative_path: str) -> Path:
    """
    Получить путь к ресурсу в портативной сборке или при обычной работе.
    
    Для PyInstaller: использует _MEIPASS если доступен.
    Для обычной работы: использует директорию скрипта.
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Запуск из PyInstaller сборки
        bundle_dir = Path(sys._MEIPASS)
        return bundle_dir / relative_path
    else:
        # Обычный запуск из исходников
        try:
            script_dir = Path(__file__).resolve().parent
        except Exception:
            script_dir = Path.cwd()
        return script_dir / relative_path


# -------------------------------------------------------------------------
# Опциональные библиотеки: безопасный импорт через importlib
# -------------------------------------------------------------------------


class ImportStatus(Enum):
    SUCCESS = "success"
    MISSING = "missing"
    ERROR = "error"


def safe_import(module_name: str) -> Tuple[ImportStatus, Optional[Any]]:
    """Попытка импортировать модуль по имени. Возвращает (status, module|None)."""
    try:
        mod = importlib.import_module(module_name)
        return ImportStatus.SUCCESS, mod
    except ImportError:
        return ImportStatus.MISSING, None
    except Exception as exc:
        return ImportStatus.ERROR, exc


# Попытка импортировать необходимые внешние модули и сохранить объекты
ARGOS_MODULE_STATUS, argostranslate_module = safe_import("argostranslate")
AT_TRANSLATE_MODULE: Optional[Any] = None
AT_PACKAGE_MODULE: Optional[Any] = None
if ARGOS_MODULE_STATUS == ImportStatus.SUCCESS and argostranslate_module is not None:
    _, AT_TRANSLATE_MODULE = safe_import("argostranslate.translate")
    _, AT_PACKAGE_MODULE = safe_import("argostranslate.package")

PYPERCLIP_STATUS, PYPERCLIP_MODULE = safe_import("pyperclip")
KEYBOARD_STATUS, KEYBOARD_MODULE = safe_import("keyboard")
LANGDETECT_STATUS, LANGDETECT_MODULE = safe_import("langdetect")

# Tray libs (опционально)
PYSTRAY_STATUS, PYSTRAY_MODULE = safe_import("pystray")
PIL_STATUS, PIL_MODULE = safe_import("PIL")
TRAY_AVAILABLE = PYSTRAY_STATUS == ImportStatus.SUCCESS and PIL_STATUS == ImportStatus.SUCCESS

# -------------------------------------------------------------------------
# Логирование
# -------------------------------------------------------------------------


class LoggingConfig:
    """Конфигурация логирования приложения."""

    def __init__(self) -> None:
        self.config_dir = Path.home() / ".argos_translate"
        self.log_file = self.config_dir / "app_streaming.log"

    def setup(self) -> logging.Logger:
        """Настройка логирования."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

        fmt = "%(asctime)s - %(levelname)s - %(message)s"
        datefmt = "%Y-%m-%d %H:%M:%S"

        logging.basicConfig(
            level=logging.INFO,
            format=fmt,
            datefmt=datefmt,
            handlers=[
                logging.FileHandler(self.log_file, encoding="utf-8"),
                logging.StreamHandler(sys.stdout),
            ],
        )

        logger = logging.getLogger("ArgosStreaming")
        logging.getLogger("PIL").setLevel(logging.WARNING)

        logger.info("=" * 60)
        logger.info("Запуск Argos Translate Streaming GUI")
        logger.info("=" * 60)

        return logger


logging_cfg = LoggingConfig()
logger = logging_cfg.setup()

# -------------------------------------------------------------------------
# Константы
# -------------------------------------------------------------------------


class TranslationConstants:
    """Константы для настройки перевода."""
    MAX_CHARS_PER_CHUNK = 4000
    SENTENCE_WINDOW = 1
    DEBOUNCE_MS = 700
    TRANSLATE_CLI_TIMEOUT = 60
    HOTKEY_DELAY = 0.16
    QUEUE_POLL_INTERVAL_MS = 120
    SCROLL_SYNC_INTERVAL_MS = 120
    SCROLL_EPSILON = 0.003
    PROGRAMMATIC_SCROLL_LOCK_MS = 50


class DefaultLanguages:
    """Стандартные языки для перевода."""
    LANGUAGES: Dict[str, str] = {
        "en": "English",
        "ru": "Русский",
        "de": "Deutsch",
        "fr": "Français",
        "es": "Español",
        "it": "Italiano",
        "pt": "Português",
        "uk": "Українська",
        "zh": "中文",
        "ja": "日本語",
        "ko": "한국어",
        "ar": "العربية",
        "hi": "हिन्दी",
        "tr": "Türkçe",
    }

    @classmethod
    def get_defaults(cls) -> Dict[str, str]:
        """Получить словарь языков по умолчанию."""
        return cls.LANGUAGES.copy()


# -------------------------------------------------------------------------
# Текстовые утилиты
# -------------------------------------------------------------------------


class TextUtils:
    """Вспомогательные функции для разбивки/определения языка."""

    SENTENCE_REGEX = re.compile(r"(?<=\S[.!?…])\s+(?=[A-ZА-ЯЁ0-9\"'«\"])")

    @staticmethod
    def detect_language(text: str) -> str:
        """Определить язык текста."""
        text = (text or "").strip()
        if not text:
            return "en"

        if LANGDETECT_STATUS == ImportStatus.SUCCESS and LANGDETECT_MODULE is not None:
            try:
                detect_fn = getattr(LANGDETECT_MODULE, "detect_langs", None)
                if callable(detect_fn):
                    results = detect_fn(text)
                    if results:
                        code = getattr(results[0], "lang", None)
                        if code:
                            logger.debug("langdetect -> %s", code)
                            return code.lower()
            except Exception as exc:
                logger.debug("langdetect failed: %s", exc)

        if re.search(r"[А-Яа-яЁё]", text):
            return "ru"
        return "en"

    @staticmethod
    def split_into_paragraphs(text: str) -> List[str]:
        """Разбить текст на параграфы."""
        if not text or not text.strip():
            return []
        parts = re.split(r"\n{2,}", text)
        return [p.strip() for p in parts if p.strip()]

    @staticmethod
    def split_paragraph_into_sentences(paragraph: str) -> List[str]:
        """Разбить параграф на предложения."""
        paragraph = (paragraph or "").strip()
        if not paragraph:
            return []
        try:
            sentences = TextUtils.SENTENCE_REGEX.split(paragraph)
        except Exception:
            sentences = [paragraph]

        if len(sentences) == 1 and len(paragraph) > TranslationConstants.MAX_CHARS_PER_CHUNK:
            return TextUtils._fallback_split_by_words(paragraph)

        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def _fallback_split_by_words(text: str) -> List[str]:
        """Фолбэк разбивка по словам для очень длинных предложений."""
        words = text.split()
        chunks: List[str] = []
        current: List[str] = []
        current_len = 0

        for word in words:
            current.append(word)
            current_len += len(word) + 1
            if current_len >= TranslationConstants.MAX_CHARS_PER_CHUNK:
                chunks.append(" ".join(current))
                current = []
                current_len = 0

        if current:
            chunks.append(" ".join(current))

        return chunks

    @staticmethod
    def make_sentence_chunks(
        sentences: List[str],
        max_chars: int = TranslationConstants.MAX_CHARS_PER_CHUNK,
        overlap: int = TranslationConstants.SENTENCE_WINDOW,
    ) -> List[Tuple[int, int]]:
        """Создать чанки предложений для перевода."""
        if not sentences:
            return []

        ranges: List[Tuple[int, int]] = []
        n = len(sentences)
        i = 0

        while i < n:
            cur_len = 0
            j = i
            while j < n and (cur_len + len(sentences[j]) + 1) <= max_chars:
                cur_len += len(sentences[j]) + 1
                j += 1

            if j == i:
                j = i + 1

            ranges.append((i, j))
            if j >= n:
                break

            i = max(j - overlap, j)

        return ranges


# -------------------------------------------------------------------------
# Бэкенд перевода
# -------------------------------------------------------------------------


class TranslateEngine:
    """Движок перевода: сначала пытается API, затем CLI."""

    def __init__(self) -> None:
        """Инициализация движка перевода."""
        self.use_api = ARGOS_MODULE_STATUS == ImportStatus.SUCCESS and AT_TRANSLATE_MODULE is not None
        self.cli_path: Optional[Path] = None

        if not self.use_api:
            self.cli_path = self._find_cli_executable()
            if self.cli_path:
                logger.info("Using CLI: %s", self.cli_path)
            else:
                logger.warning("No translation backend found")
        else:
            logger.info("Using Argos Python API")

    @staticmethod
    def _find_cli_executable() -> Optional[Path]:
        """Найти исполняемый файл CLI."""
        exe = "argos-translate.exe" if os.name == "nt" else "argos-translate"

        found = shutil.which(exe)
        if found:
            return Path(found)

        common_paths = [
            Path(sys.prefix) / ("Scripts" if os.name == "nt" else "bin") / exe,
            Path.home() / ".local" / "bin" / exe,
            Path("/usr/local/bin") / exe,
            Path("/usr/bin") / exe,
        ]

        for path in common_paths:
            if path.exists():
                return path

        return None

    def translate(self, text: str, from_code: str, to_code: str) -> str:
        """Выполнить перевод текста."""
        text = (text or "").strip()
        if not text:
            return ""

        if self.use_api and AT_TRANSLATE_MODULE is not None:
            try:
                translate_fn = getattr(AT_TRANSLATE_MODULE, "translate", None)
                if callable(translate_fn):
                    return translate_fn(text, from_code, to_code)
            except Exception as exc:
                logger.warning("API error, fallback to CLI: %s", exc)

        if not self.cli_path:
            raise RuntimeError("No translation backend available")

        return self._translate_cli(text, from_code, to_code)

    def _translate_cli(self, text: str, from_code: str, to_code: str) -> str:
        """Выполнить перевод через CLI."""
        cmd = [str(self.cli_path), "--from", from_code, "--to", to_code, text]
        logger.debug("CLI command: %s", cmd[:6])

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=TranslationConstants.TRANSLATE_CLI_TIMEOUT,
            )

            if proc.returncode != 0:
                err = proc.stderr.strip() if proc.stderr else "Unknown error"
                logger.error("CLI error: %s", err)
                raise RuntimeError(f"Translate CLI error: {err}")

            return proc.stdout.strip()

        except subprocess.TimeoutExpired:
            logger.error("Translate timeout")
            raise RuntimeError("Translate timeout")
        except Exception as exc:
            logger.exception("CLI translate failed: %s", exc)
            raise RuntimeError(str(exc))


# -------------------------------------------------------------------------
# UI: конфиг и компоненты
# -------------------------------------------------------------------------


@dataclass
class UIConfig:
    """Конфигурация пользовательского интерфейса."""
    title: str = "Argos Translate"
    width: int = 1000
    height: int = 700
    min_width: int = 800
    min_height: int = 600
    padding: int = 10
    font_main: Tuple[str, int] = ("Segoe UI", 10)
    font_text: Tuple[str, int] = ("Consolas", 13)
    font_title: Tuple[str, int, str] = ("Segoe UI", 12, "bold")


class CompactLanguageSelector(ttk.Frame):
    """Компактный селектор языков."""

    def __init__(self, parent: ttk.Frame, languages: Dict[str, str], **kwargs) -> None:
        """Инициализация селектора языков."""
        super().__init__(parent, **kwargs)
        self.languages = languages
        self.font_cfg = ("Segoe UI", 10)
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Создание виджетов селектора."""
        for i in range(6):
            self.grid_columnconfigure(i, weight=1 if i in (2, 4) else 0)

        ttk.Label(self, text="Из:", font=self.font_cfg).grid(
            row=0, column=0, padx=(0, 5), sticky=tk.W
        )

        self.var_from = tk.StringVar(value="AUTO")
        self.combo_from = ttk.Combobox(
            self,
            textvariable=self.var_from,
            values=["AUTO"] + self._get_language_options(),
            state="readonly",
            font=self.font_cfg,
            width=18,
        )
        self.combo_from.grid(row=0, column=1, padx=(0, 10), sticky=tk.W)

        self.btn_swap = ttk.Button(self, text="↔", command=self.swap_languages, width=3)
        self.btn_swap.grid(row=0, column=2, padx=5, sticky=tk.W)

        ttk.Label(self, text="В:", font=self.font_cfg).grid(
            row=0, column=3, padx=(10, 5), sticky=tk.W
        )

        options = self._get_language_options()
        default_to = "RU - Русский" if "ru" in self.languages else (options[0] if options else "EN - English")
        self.var_to = tk.StringVar(value=default_to)
        self.combo_to = ttk.Combobox(
            self,
            textvariable=self.var_to,
            values=options,
            state="readonly",
            font=self.font_cfg,
            width=18,
        )
        self.combo_to.grid(row=0, column=4, padx=(0, 10), sticky=tk.W)

    def _get_language_options(self) -> List[str]:
        """Получить список опций языков для комбобокса."""
        return [f"{code.upper()} - {name}" for code, name in sorted(self.languages.items())]

    def swap_languages(self) -> None:
        """Поменять выбранные языки местами."""
        from_val = self.var_from.get()
        to_val = self.var_to.get()
        self.var_from.set(to_val)
        self.var_to.set(from_val)

    def get_from_code(self) -> str:
        """Получить код исходного языка."""
        value = self.var_from.get()
        if value.upper().startswith("AUTO"):
            return "auto"
        if " - " in value:
            return value.split(" - ", 1)[0].strip().lower()
        return value.strip().lower()

    def get_to_code(self) -> str:
        """Получить код целевого языка."""
        value = self.var_to.get()
        if " - " in value:
            return value.split(" - ", 1)[0].strip().lower()
        return value.strip().lower()


class TextPanel(ttk.LabelFrame):
    """Панель с текстом (источник/перевод)."""

    def __init__(
        self,
        parent: ttk.Frame,
        title: str,
        editable: bool = True,
        extra_buttons: Optional[List[Tuple[str, Callable[..., Any]]]] = None,
        **kwargs
    ) -> None:
        """Инициализация текстовой панели."""
        super().__init__(parent, text=title, padding=5, **kwargs)
        self.editable = editable
        self.extra_buttons = extra_buttons or []
        self._create_widgets()

    def _create_widgets(self) -> None:
        """Создание виджетов панели."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=0)

        self.text = scrolledtext.ScrolledText(
            self,
            wrap=tk.WORD,
            font=("Consolas", 13),
            relief=tk.FLAT,
            borderwidth=1,
            padx=8,
            pady=8,
        )
        self.text.grid(row=0, column=0, sticky=tk.NSEW)

        if not self.editable:
            self.text.config(state=tk.DISABLED)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=1, column=0, sticky=tk.W, pady=(5, 0))

        if self.editable:
            ttk.Button(btn_frame, text="Paste", command=self.paste_from_clipboard, width=8).pack(
                side=tk.LEFT
            )
            ttk.Button(btn_frame, text="Clear", command=self.clear, width=8).pack(side=tk.LEFT, padx=(5, 0))
        else:
            self.copy_btn = ttk.Button(btn_frame, text="Copy", command=self.copy_to_clipboard, width=8)
            self.copy_btn.pack(side=tk.LEFT)
            ttk.Button(btn_frame, text="Clear", command=self.clear, width=8).pack(side=tk.LEFT, padx=(5, 0))
            
            # Добавление дополнительных кнопок
            for btn_text, btn_command in self.extra_buttons:
                try:
                    ttk.Button(btn_frame, text=btn_text, command=btn_command, width=12).pack(side=tk.LEFT, padx=(5, 0))
                except Exception:
                    logger.debug("Failed to add extra button %s", btn_text)

    def get_text(self) -> str:
        """Получить текст из панели."""
        if self.editable:
            return self.text.get("1.0", tk.END).strip()

        # Временно снимаем блокировку для чтения
        self.text.config(state=tk.NORMAL)
        text = self.text.get("1.0", tk.END).strip()
        self.text.config(state=tk.DISABLED)
        return text

    def set_text(self, text: str) -> None:
        """Установить текст в панель."""
        try:
            try:
                cur_frac = float(self.text.yview()[0])
            except Exception:
                cur_frac = 0.0

            try:
                insert_index = self.text.index(tk.INSERT)
            except Exception:
                insert_index = "1.0"

            try:
                old_text = self.text.get("1.0", tk.END)
                old_len = max(1, len(old_text) - 1)
            except Exception:
                old_len = 1

            old_pos_chars = int(cur_frac * (old_len - 1)) if old_len > 1 else 0

            if self.editable:
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", text)
            else:
                self.text.config(state=tk.NORMAL)
                self.text.delete("1.0", tk.END)
                self.text.insert("1.0", text)
                self.text.config(state=tk.DISABLED)

            try:
                new_text = self.text.get("1.0", tk.END)
                new_len = max(1, len(new_text) - 1)
            except Exception:
                new_len = 1

            if new_len > 1:
                new_frac = old_pos_chars / (new_len - 1)
            else:
                new_frac = 0.0

            new_frac = max(0.0, min(1.0, new_frac))

            try:
                self.text.mark_set(tk.INSERT, insert_index)
            except Exception:
                pass

            try:
                self.text.yview_moveto(new_frac)
            except Exception:
                pass

        except Exception as exc:
            logger.debug("set_text error: %s", exc)

    def paste_from_clipboard(self) -> None:
        """Вставить текст из буфера обмена."""
        if PYPERCLIP_STATUS != ImportStatus.SUCCESS or PYPERCLIP_MODULE is None:
            messagebox.showwarning(
                "Clipboard missing",
                "Install pyperclip to use clipboard functions",
            )
            return

        try:
            text = PYPERCLIP_MODULE.paste()
            if text:
                self.text.insert(tk.INSERT, text)
        except Exception as exc:
            logger.error("Paste error: %s", exc)
            messagebox.showerror("Error", f"Paste failed: {exc}")

    def copy_to_clipboard(self) -> None:
        """Скопировать текст в буфер обмена."""
        if PYPERCLIP_STATUS != ImportStatus.SUCCESS or PYPERCLIP_MODULE is None:
            messagebox.showwarning(
                "Clipboard missing",
                "Install pyperclip to use clipboard functions",
            )
            return

        text = self.get_text()
        if not text:
            return

        try:
            PYPERCLIP_MODULE.copy(text)
            if hasattr(self, "copy_btn"):
                original_text = self.copy_btn.cget("text")
                self.copy_btn.config(text="Copied!")
                self.after(1000, lambda: self.copy_btn.config(text=original_text))
        except Exception as exc:
            logger.error("Copy error: %s", exc)
            messagebox.showerror("Error", f"Copy failed: {exc}")

    def clear(self) -> None:
        """Очистить текстовую панель."""
        if self.editable:
            self.text.delete("1.0", tk.END)
        else:
            self.text.config(state=tk.NORMAL)
            self.text.delete("1.0", tk.END)
            self.text.config(state=tk.DISABLED)


# -------------------------------------------------------------------------
# Главное приложение
# -------------------------------------------------------------------------


class TranslatorApp:
    """Главное приложение для потокового перевода."""

    def __init__(self, root: tk.Tk) -> None:
        """Инициализация приложения."""
        self.root = root
        self.cfg = UIConfig()
        self.engine = TranslateEngine()
        self.languages = self._get_available_languages()

        # Поток перевода
        self.translate_queue: queue.Queue = queue.Queue()
        self.translate_thread: Optional[threading.Thread] = None
        self.stop_flag = threading.Event()

        # Управление заданиями
        self.job_counter = 0
        self.active_job: Optional[int] = None
        self.partial_translations: Dict[int, Dict[int, Tuple[str, int]]] = {}
        self.total_sentences: Dict[int, int] = {}

        # Режимы
        self.streaming_enabled = tk.BooleanVar(value=True)
        self.scroll_sync_enabled = tk.BooleanVar(value=True)

        self.debounce_job: Optional[Any] = None

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
        self.tray_icon = None
        self.tray_thread: Optional[threading.Thread] = None
        self.tray_lock = threading.Lock()
        self.tray_enabled = TRAY_AVAILABLE

        # retry counters to avoid log spam for tray creation
        self._tray_create_attempts = 0
        self._tray_create_max_attempts = 6

        # Идентификатор задачи синхронизации прокрутки
        self._sync_scroll_job: Optional[str] = None

        self._setup_window()
        self._build_ui()
        self._bind_events()
        self._load_settings()
        self._start_background_tasks()

        if KEYBOARD_STATUS == ImportStatus.SUCCESS and KEYBOARD_MODULE is not None:
            self._setup_global_hotkeys()

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

        # Центрирование окна
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() - width) // 2
        y = (self.root.winfo_screenheight() - height) // 2
        try:
            self.root.geometry(f"{width}x{height}+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self) -> None:
        """Построение пользовательского интерфейса."""
        main = ttk.Frame(self.root, padding=self.cfg.padding)
        main.grid(row=0, column=0, sticky=tk.NSEW)

        main.columnconfigure(0, weight=1)
        main.rowconfigure(0, weight=0)
        main.rowconfigure(1, weight=1)
        main.rowconfigure(2, weight=0)

        control_frame = ttk.Frame(main)
        control_frame.grid(row=0, column=0, sticky=tk.EW, pady=(0, 8))
        control_frame.columnconfigure(0, weight=1)

        self.lang_widget = CompactLanguageSelector(control_frame, self.languages)
        self.lang_widget.grid(row=0, column=0, sticky=tk.W)

        ttk.Checkbutton(
            control_frame,
            text="Stream",
            variable=self.streaming_enabled,
            command=self._on_stream_toggle,
            width=8,
        ).grid(row=0, column=1, padx=(10, 5), sticky=tk.E)

        ttk.Checkbutton(
            control_frame,
            text="Sync scroll",
            variable=self.scroll_sync_enabled,
            command=self._on_scroll_sync_toggle,
            width=12,
        ).grid(row=0, column=2, padx=(0, 5), sticky=tk.E)

        ttk.Button(control_frame, text="Translate", command=self.translate, width=12).grid(
            row=0, column=3, padx=(5, 0), sticky=tk.E
        )

        panels = ttk.Frame(main)
        panels.grid(row=1, column=0, sticky=tk.NSEW)
        panels.columnconfigure(0, weight=1)
        panels.columnconfigure(1, weight=1)
        panels.rowconfigure(0, weight=1, minsize=150)

        self.src_panel = TextPanel(panels, "Source text", editable=True)
        self.src_panel.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 5), pady=(0, 0))
        try:
            self.src_panel.text.edit_modified(False)
        except Exception:
            pass
        self.src_panel.text.bind("<<Modified>>", self._on_src_modified)

        # Добавляем кнопку "Copy & Hide" в панель перевода
        self.dst_panel = TextPanel(
            panels,
            "Translation",
            editable=False,
            extra_buttons=[("Copy & Hide", self._copy_and_hide)]
        )
        self.dst_panel.grid(row=0, column=1, sticky=tk.NSEW, padx=(5, 0), pady=(0, 0))
        
        # Индикатор прогресса перевода внутри панели перевода
        self.translate_status_frame = ttk.Frame(panels)
        self.translate_status_frame.grid(row=1, column=1, sticky=tk.EW, pady=(5, 0))
        self.translate_status_frame.columnconfigure(0, weight=1)
        
        self.translate_status_var = tk.StringVar(value="")
        ttk.Label(
            self.translate_status_frame,
            textvariable=self.translate_status_var,
            font=("Segoe UI", 9),
            foreground="gray"
        ).grid(row=0, column=0, sticky=tk.W)

        status_frame = ttk.Frame(main, height=28)
        status_frame.grid(row=2, column=0, sticky=tk.EW, pady=(8, 0))
        status_frame.columnconfigure(0, weight=1)

        self.status_var = tk.StringVar(value="Готов к работе")
        ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 9)).grid(
            row=0, column=0, sticky=tk.W
        )

        hints = "Ctrl+Enter: Translate    Ctrl+Shift+C: Capture    Ctrl+S: Swap languages"
        ttk.Label(status_frame, text=hints, font=("Segoe UI", 9)).grid(row=0, column=1, sticky=tk.E)

    def _bind_events(self) -> None:
        """Привязка обработчиков событий."""
        self.root.bind("<Control-Return>", lambda e: self.translate())
        self.root.bind("<Control-s>", lambda e: self.lang_widget.swap_languages())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
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

    def _setup_global_hotkeys(self) -> None:
        """Настройка глобальных горячих клавиш."""
        if KEYBOARD_MODULE is None:
            return
        try:
            add_hotkey = getattr(KEYBOARD_MODULE, "add_hotkey", None)
            if callable(add_hotkey):
                add_hotkey("ctrl+shift+c", self._handle_global_hotkey, suppress=True)
                logger.info("Global hotkey registered")
        except Exception as exc:
            logger.warning("Failed to register hotkey: %s", exc)

    def _on_src_modified(self, event: Optional[tk.Event] = None) -> None:
        """Обработчик изменения исходного текста."""
        try:
            self.src_panel.text.edit_modified(False)
        except Exception:
            pass

        if self.streaming_enabled.get():
            if self.debounce_job:
                try:
                    self.root.after_cancel(self.debounce_job)
                except Exception:
                    pass

            self.debounce_job = self.root.after(
                TranslationConstants.DEBOUNCE_MS, lambda: self.translate(streaming=True)
            )

    def _on_stream_toggle(self) -> None:
        """Обработчик переключения потокового режима."""
        logger.info("Stream toggle: %s", self.streaming_enabled.get())

    def translate(self, event: Optional[tk.Event] = None, streaming: bool = False) -> None:
        """Запустить перевод текста."""
        if self.debounce_job:
            try:
                self.root.after_cancel(self.debounce_job)
            except Exception:
                pass
            self.debounce_job = None

        text = self.src_panel.get_text()
        if not text or not text.strip():
            return

        self.stop_flag.set()
        if self.translate_thread and self.translate_thread.is_alive():
            time.sleep(0.05)
        self.stop_flag.clear()

        self.job_counter += 1
        job_id = self.job_counter
        self.active_job = job_id
        self.partial_translations[job_id] = {}

        paragraphs = TextUtils.split_into_paragraphs(text)
        sentences: List[str] = []
        para_indices: List[int] = []

        for para_idx, paragraph in enumerate(paragraphs):
            sents = TextUtils.split_paragraph_into_sentences(paragraph)
            for sent in sents:
                sentences.append(sent)
                para_indices.append(para_idx)

        if not sentences:
            return

        self.total_sentences[job_id] = len(sentences)

        from_code = self.lang_widget.get_from_code()
        to_code = self.lang_widget.get_to_code()

        if from_code == "auto":
            detected = TextUtils.detect_language(text)
            from_code = detected
            to_code = "en" if detected == "ru" else "ru"

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

        self.dst_panel.clear()
        
        # Установка статуса перевода
        self.translate_status_var.set(f"Перевод: 0/{len(sentences)} предл.")

        self.translate_thread = threading.Thread(
            target=self._translate_worker,
            args=(job_id, sentences, para_indices, from_code, to_code),
            daemon=True,
        )
        self.translate_thread.start()

        logger.info("Started job %d (%d sentences)", job_id, len(sentences))

    def _translate_worker(
        self,
        job_id: int,
        sentences: List[str],
        para_indices: List[int],
        from_code: str,
        to_code: str,
    ) -> None:
        """Воркер для выполнения перевода в отдельном потоке."""
        logger.info("Worker %d: start", job_id)

        for i, sentence in enumerate(sentences):
            if self.stop_flag.is_set() and job_id != self.active_job:
                logger.info("Worker %d: stopped", job_id)
                return

            try:
                output = self.engine.translate(sentence, from_code, to_code)
                self.translate_queue.put((job_id, i, output, para_indices[i]))
            except Exception as exc:
                logger.error("Worker %d: translate error: %s", job_id, exc)
                self.translate_queue.put((job_id, i, f"[Error: {str(exc)[:50]}]", para_indices[i]))

        logger.info("Worker %d: finished", job_id)

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
                self._handle_translate_results(items)
        except Exception as exc:
            logger.error("Poll error: %s", exc)
        finally:
            self.root.after(TranslationConstants.QUEUE_POLL_INTERVAL_MS, self._poll_translate_queue)

    def _handle_translate_results(self, results: List[Tuple[int, int, str, int]]) -> None:
        """Обработка результатов перевода."""
        need_update = False

        for job_id, idx, text, para_idx in results:
            if job_id not in self.partial_translations:
                self.partial_translations[job_id] = {}

            self.partial_translations[job_id][idx] = (text, para_idx)

            if job_id == self.active_job:
                need_update = True

        if need_update and self.active_job is not None:
            self._update_translated_text(self.active_job)
            
            # Обновление статуса перевода
            total = self.total_sentences.get(self.active_job, 0)
            if total > 0:
                translated_count = len(self.partial_translations[self.active_job])
                progress = (translated_count / total) * 100
                self.translate_status_var.set(f"Перевод: {translated_count}/{total} предл. ({progress:.0f}%)")

    def _update_translated_text(self, job_id: int) -> None:
        """Обновление текста перевода в интерфейсе."""
        partials = self.partial_translations.get(job_id, {})
        total = self.total_sentences.get(job_id, 0)

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
        self.dst_panel.set_text(final)
        self._update_paragraph_offsets()
        
        # Проверка завершения перевода
        if len(partials) >= total:
            self.translate_status_var.set("✓ Перевод завершён")
            self.status_var.set("Готов к работе")

    def _update_paragraph_offsets(self) -> None:
        """Обновление оффсетов параграфов для синхронизации прокрутки."""
        try:
            src = self.src_panel.text.get("1.0", tk.END)
            dst = self.dst_panel.text.get("1.0", tk.END)

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
        if not self.scroll_sync_enabled.get():
            self._sync_scroll_job = None
            return

        try:
            try:
                src_frac = self.src_panel.text.yview()[0]
            except Exception:
                src_frac = None

            try:
                dst_frac = self.dst_panel.text.yview()[0]
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
                            dst_insert = self.dst_panel.text.index(tk.INSERT)
                        except Exception:
                            dst_insert = "1.0"

                        try:
                            self.dst_panel.text.yview_moveto(dst_frac_calc)
                        except Exception:
                            pass

                        try:
                            self.dst_panel.text.mark_set(tk.INSERT, dst_insert)
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
        if PYPERCLIP_STATUS != ImportStatus.SUCCESS or PYPERCLIP_MODULE is None or KEYBOARD_STATUS != ImportStatus.SUCCESS or KEYBOARD_MODULE is None:
            logger.warning("Hotkey unavailable: requires pyperclip and keyboard")
            return

        old_text: Optional[str] = None
        try:
            old_text = PYPERCLIP_MODULE.paste()
        except Exception:
            pass

        try:
            send_fn = getattr(KEYBOARD_MODULE, "send", None)
            if callable(send_fn):
                send_fn("ctrl+c")
        except Exception:
            logger.debug("keyboard.send failed")

        time.sleep(TranslationConstants.HOTKEY_DELAY)

        try:
            text = PYPERCLIP_MODULE.paste()
        except Exception:
            text = ""

        # Восстанавливаем оригинальное содержимое буфера обмена
        if old_text is not None and text != old_text:
            try:
                PYPERCLIP_MODULE.copy(old_text)
            except Exception:
                pass

        if text and text.strip():
            # Если окно скрыто в трее — покажем и вставим текст
            self.root.after(0, lambda: self._handle_copied_text(text))

    def _handle_copied_text(self, text: str) -> None:
        """Обработка скопированного текста: показать окно, вставить текст, начать перевод."""
        self._show_window()
        self.src_panel.set_text(text)

        if len(text) < 500:
            self.translate()

    def _show_window(self) -> None:
        """Показать окно приложения (из трея или из свёрнутого состояния)."""
        try:
            # Если скрыто из трея, удаляем иконку
            self._stop_tray()
            self.root.deiconify()
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
        """Копировать перевод в буфер обмена и скрыть окно в трей."""
        self.dst_panel.copy_to_clipboard()
        self._hide_to_tray()

    def _hide_to_tray(self) -> None:
        """Скрыть окно в трей."""
        try:
            self.root.withdraw()
            self._create_tray()
            logger.info("Window hidden to tray")
        except Exception as exc:
            logger.exception("Hide to tray failed: %s", exc)

    def _on_close(self) -> None:
        """Обработчик закрытия приложения."""
        # При закрытии — корректно завершить
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
        self._save_settings()
        self.stop_flag.set()
        self._stop_tray()
        try:
            self.root.destroy()
        except Exception:
            pass
        # Завершение процесса
        try:
            sys.exit(0)
        except Exception:
            pass

    def _settings_path(self) -> Path:
        """Получить путь к файлу настроек."""
        return Path.home() / ".argos_translate" / "settings.json"

    def _load_settings(self) -> None:
        """Загрузить настройки из файла."""
        cfg_file = self._settings_path()
        if not cfg_file.exists():
            return

        try:
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            window = data.get("window", {})

            geometry = window.get("geometry")
            if geometry:
                try:
                    self.root.geometry(geometry)
                except Exception:
                    pass

            streaming = window.get("streaming")
            if isinstance(streaming, bool):
                try:
                    self.streaming_enabled.set(streaming)
                except Exception:
                    pass

            scroll_sync = window.get("scroll_sync")
            if isinstance(scroll_sync, bool):
                try:
                    self.scroll_sync_enabled.set(scroll_sync)
                except Exception:
                    pass

            languages = data.get("languages", {})
            from_code = languages.get("from")
            to_code = languages.get("to")

            if from_code:
                try:
                    if str(from_code).lower() == "auto":
                        self.lang_widget.combo_from.set("AUTO")
                    else:
                        from_name = self.languages.get(from_code, from_code)
                        self.lang_widget.combo_from.set(f"{str(from_code).upper()} - {from_name}")
                except Exception:
                    pass

            if to_code:
                try:
                    to_name = self.languages.get(to_code, to_code)
                    self.lang_widget.combo_to.set(f"{str(to_code).upper()} - {to_name}")
                except Exception:
                    pass

        except Exception as exc:
            logger.debug("Load settings failed: %s", exc)

    def _save_settings(self) -> None:
        """Сохранить настройки в файл."""
        try:
            data = {
                "window": {
                    "geometry": self.root.geometry(),
                    "streaming": self.streaming_enabled.get(),
                    "scroll_sync": self.scroll_sync_enabled.get(),
                },
                "languages": {
                    "from": self.lang_widget.get_from_code(),
                    "to": self.lang_widget.get_to_code(),
                },
            }

            cfg_file = self._settings_path()
            cfg_file.parent.mkdir(parents=True, exist_ok=True)

            with open(cfg_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            logger.info("Settings saved")
        except Exception as exc:
            logger.error("Save settings failed: %s", exc)

    # ---------------------------------------------------------------------
    # Tray-related
    # ---------------------------------------------------------------------

    def _create_tray(self) -> None:
        """Создать иконку в трее."""
        if not self.tray_enabled:
            logger.debug("Tray not available (PYSTRAY or PIL missing).")
            return

        with self.tray_lock:
            if self.tray_icon is not None:
                logger.debug("Tray already created")
                return

            if self._tray_create_attempts >= self._tray_create_max_attempts:
                logger.warning("Tray creation attempts exhausted (%d). Skipping further retries.", self._tray_create_attempts)
                return

            try:
                # Надёжно импортируем подпакеты PIL (вдруг PIL.__init__ пустой)
                Image = getattr(PIL_MODULE, "Image", None)
                ImageDraw = getattr(PIL_MODULE, "ImageDraw", None)
                ImageFont = getattr(PIL_MODULE, "ImageFont", None)

                if Image is None or ImageDraw is None:
                    try:
                        Image = importlib.import_module("PIL.Image")
                        ImageDraw = importlib.import_module("PIL.ImageDraw")
                    except Exception as exc:
                        logger.debug("Import PIL.Image / ImageDraw failed: %s", exc)
                        # Последняя попытка прямого импорта через from PIL import ...
                        try:
                            from PIL import Image as _Image, ImageDraw as _ImageDraw  # type: ignore
                            Image = _Image
                            ImageDraw = _ImageDraw
                        except Exception as exc2:
                            logger.exception("Pillow import failed completely: %s", exc2)
                            raise

                if ImageFont is None:
                    try:
                        ImageFont = importlib.import_module("PIL.ImageFont")
                    except Exception:
                        try:
                            from PIL import ImageFont as _ImageFont  # type: ignore
                            ImageFont = _ImageFont
                        except Exception:
                            ImageFont = None

                # Попытаться загрузить .ico рядом со скриптом или по известному абсолютному пути
                icon_img = None
                icon_path = get_resource_path("argos_translate.ico")
                
                try:
                    if icon_path.exists():
                        logger.debug("Loading tray icon from: %s", str(icon_path))
                        img = Image.open(str(icon_path))
                        try:
                            img = img.convert("RGBA")
                            img = img.copy()
                            # выберем корректный ресемплинг
                            resample = None
                            if hasattr(Image, "Resampling"):
                                resample = getattr(Image.Resampling, "LANCZOS", None)
                            if resample is None:
                                resample = getattr(Image, "LANCZOS", None)
                            if resample is None:
                                resample = getattr(Image, "ANTIALIAS", None)
                            try:
                                if resample is not None:
                                    img.thumbnail((64, 64), resample)
                                else:
                                    img.thumbnail((64, 64))
                            except Exception:
                                try:
                                    img.thumbnail((64, 64))
                                except Exception:
                                    pass
                        except Exception:
                            try:
                                img = img.convert("RGBA")
                            except Exception:
                                pass
                        icon_img = img
                except Exception as exc:
                    logger.debug("Failed to load icon %s: %s", icon_path, exc)

                # Если не загрузили файл — создаём серую заглушку
                if icon_img is None:
                    try:
                        img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
                        draw = None
                        try:
                            draw = ImageDraw.Draw(img)
                        except Exception:
                            draw = None
                        if draw is not None:
                            draw.ellipse([(0, 0), (63, 63)], fill=(120, 120, 120, 255))
                            try:
                                if ImageFont is not None:
                                    font = ImageFont.load_default()
                                    draw.text((18, 14), "A", fill=(255, 255, 255, 255), font=font)
                            except Exception:
                                pass
                        icon_img = img
                    except Exception as exc:
                        logger.exception("Creating fallback tray image failed: %s", exc)
                        icon_img = None

                if icon_img is None:
                    logger.warning("No tray icon image available, aborting tray creation.")
                    return

                icon_name = "Argos Translate"

                def on_show(icon=None, item=None):
                    """Обработчик показа окна из трея."""
                    logger.debug("Tray -> Show clicked/double-clicked")
                    try:
                        self.root.after(0, self._show_window)
                    except Exception:
                        try:
                            self._show_window()
                        except Exception:
                            pass

                def on_exit(icon=None, item=None):
                    """Обработчик выхода из трея."""
                    logger.debug("Tray -> Exit clicked")
                    self.root.after(0, self._on_close)

                # Создаём меню для иконки в трее
                try:
                    menu = PYSTRAY_MODULE.Menu(
                        PYSTRAY_MODULE.MenuItem("Show", on_show),
                        PYSTRAY_MODULE.MenuItem("Exit", on_exit),
                    )
                except Exception:
                    menu = None

                # Создаём иконку в трее
                try:
                    # pystray.Icon обычно принимает (name, image, title, menu)
                    # пробуем несколько сигнатур
                    try:
                        self.tray_icon = PYSTRAY_MODULE.Icon("argos_translate", icon_img, icon_name, menu)
                    except Exception:
                        self.tray_icon = PYSTRAY_MODULE.Icon("argos_translate", icon_img)
                except Exception as exc:
                    logger.exception("Failed to construct pystray.Icon: %s", exc)
                    raise

                # Назначаем обработчик двойного клика/клика (попытки по разным вариантам API)
                try:
                    if hasattr(self.tray_icon, 'on_double_click'):
                        try:
                            setattr(self.tray_icon, 'on_double_click', on_show)
                            logger.debug("Attached on_double_click handler to tray icon")
                        except Exception:
                            logger.debug("Setting on_double_click attribute failed")
                    elif hasattr(self.tray_icon, 'on_click'):
                        try:
                            setattr(self.tray_icon, 'on_click', on_show)
                            logger.debug("Attached on_click handler to tray icon")
                        except Exception:
                            logger.debug("Setting on_click attribute failed")
                    else:
                        # запасной вариант — установить on_clicked
                        try:
                            setattr(self.tray_icon, 'on_clicked', on_show)
                            logger.debug("Attached on_clicked handler to tray icon (fallback)")
                        except Exception:
                            logger.debug("No attribute available for click handlers on tray icon")
                except Exception:
                    logger.debug("Attaching click/double-click handler failed (non-fatal)")

                # Запуск иконки
                run_detached = getattr(self.tray_icon, "run_detached", None)
                if callable(run_detached):
                    try:
                        self.tray_icon.run_detached()
                        logger.info("Tray icon started via run_detached()")
                    except Exception as exc:
                        logger.exception("run_detached failed: %s", exc)
                        self.tray_icon = None
                        raise
                else:
                    # Запускаем в отдельном потоке
                    def _run_icon():
                        try:
                            logger.debug("Starting tray icon thread")
                            self.tray_icon.run()
                        except Exception as exc:
                            logger.exception("Tray thread crashed: %s", exc)
                            with self.tray_lock:
                                try:
                                    self.tray_icon = None
                                except Exception:
                                    pass

                    self.tray_thread = threading.Thread(target=_run_icon, daemon=False)
                    self.tray_thread.start()
                    logger.info("Tray icon thread started")

                self._tray_create_attempts = 0

            except Exception as exc:
                self._tray_create_attempts += 1
                logger.exception("Tray creation failed: %s", exc)
                delay_ms = min(60_000, 1000 * (2 ** (self._tray_create_attempts - 1)))
                try:
                    self.root.after(delay_ms, self._create_tray)
                except Exception:
                    logger.debug("Failed to schedule tray retry")

    def _stop_tray(self) -> None:
        """Остановить иконку в трее."""
        with self.tray_lock:
            try:
                if self.tray_icon is not None:
                    try:
                        stop_fn = getattr(self.tray_icon, "stop", None)
                        if callable(stop_fn):
                            try:
                                stop_fn()
                            except Exception as exc:
                                logger.debug("tray_icon.stop() raised: %s", exc)
                        else:
                            try:
                                setattr(self.tray_icon, "visible", False)
                            except Exception:
                                pass
                    except Exception as exc:
                        logger.debug("Error stopping tray icon: %s", exc)
                    finally:
                        self.tray_icon = None
            except Exception:
                pass

            try:
                if self.tray_thread is not None:
                    try:
                        if self.tray_thread.is_alive():
                            self.tray_thread.join(timeout=1.0)
                    except Exception:
                        pass
                    finally:
                        self.tray_thread = None
            except Exception:
                pass

    def _on_window_unmap(self, event: Optional[tk.Event] = None) -> None:
        """Обработчик сворачивания окна - прячем в трей."""
        try:
            state = str(self.root.state()).lower()
            logger.debug("_on_window_unmap: state=%s, event=%s", state, getattr(event, "type", None))
            if state in ("iconic", "withdrawn"):
                try:
                    self.root.withdraw()
                    logger.debug("Window withdrawn, creating tray")
                    self._create_tray()
                    logger.info("Window hidden to tray")
                except Exception as exc:
                    logger.exception("Hide to tray failed: %s", exc)
            else:
                logger.debug("Unmap ignored (state not iconic/withdrawn)")
        except Exception as exc:
            logger.exception("On window unmap error: %s", exc)


# -------------------------------------------------------------------------
# Запуск приложения
# -------------------------------------------------------------------------


def attempt_relaunch_without_console() -> bool:
    """
    На Windows: попытаться перезапустить через pythonw.exe чтобы убрать консоль.
    Возвращает True если перезапуск успешен.
    """
    if os.name != "nt":
        return False

    exe = sys.executable or ""
    exe_l = exe.lower()
    if "pythonw.exe" in exe_l:
        return False

    candidate_paths = []

    try:
        cwd = os.getcwd()
        candidate_paths.append(os.path.join(cwd, "venv", "Scripts", "pythonw.exe"))
    except Exception:
        pass

    try:
        if exe.lower().endswith("python.exe"):
            candidate_paths.append(exe[:-len("python.exe")] + "pythonw.exe")
    except Exception:
        pass

    found = shutil.which("pythonw.exe")
    if found:
        candidate_paths.insert(0, found)

    for p in candidate_paths:
        if p and os.path.exists(p):
            try:
                args = [p, os.path.abspath(sys.argv[0])] + sys.argv[1:]
                DETACHED_PROCESS = 0x00000008
                subprocess.Popen(args, close_fds=True, creationflags=DETACHED_PROCESS)
                logger.info("Relaunched via pythonw: %s", p)
                return True
            except Exception as exc:
                logger.debug("Relaunch attempt failed (%s): %s", p, exc)
                continue
    return False


def check_translation_models() -> Tuple[bool, List[str]]:
    """
    Проверить наличие установленных моделей перевода.
    Возвращает (есть_ли_модели, список_доступных_пар).
    """
    if AT_PACKAGE_MODULE is None:
        return False, []

    try:
        get_packages = getattr(AT_PACKAGE_MODULE, "get_installed_packages", None)
        if not callable(get_packages):
            return False, []

        packages = get_packages()
        if not packages:
            return False, []

        # Собираем доступные пары языков
        available_pairs = set()
        for pkg in packages:
            from_code = getattr(pkg, "from_code", None)
            to_code = getattr(pkg, "to_code", None)
            if from_code and to_code:
                available_pairs.add(f"{from_code}->{to_code}")

        return len(available_pairs) > 0, list(available_pairs)

    except Exception as exc:
        logger.debug("Failed to check models: %s", exc)
        return False, []


def get_script_dir() -> Path:
    """Получить директорию скрипта (или сборки PyInstaller)."""
    return get_resource_path("")


def install_models_from_bundle() -> bool:
    """
    Попытаться установить модели из локальной папки argos_models.
    Возвращает True если модели были успешно установлены.
    """
    script_dir = get_script_dir()
    models_dir = script_dir / "argos_models"
    packages_dir = Path.home() / ".local" / "share" / "argos-translate" / "packages"

    if not models_dir.exists():
        logger.debug("Bundle models directory not found: %s", models_dir)
        return False

    try:
        packages_dir.mkdir(parents=True, exist_ok=True)
        installed = 0

        for model_file in models_dir.glob("*.argosmodel"):
            dest = packages_dir / model_file.name
            if not dest.exists():
                shutil.copy2(model_file, dest)
                logger.info("Installed model: %s", model_file.name)
                installed += 1

        if installed > 0:
            logger.info("Installed %d model(s) from bundle", installed)
            return True

        return True  # Модели уже были установлены

    except Exception as exc:
        logger.error("Failed to install bundle models: %s", exc)
        return False


def main() -> None:
    """Главная функция запуска приложения."""
    logger.info("Starting Argos Translate app")

    try:
        if attempt_relaunch_without_console():
            return
    except Exception as exc:
        logger.debug("Relaunch check failed: %s", exc)

    try:
        cli_available = shutil.which("argos-translate") is not None

        if ARGOS_MODULE_STATUS != ImportStatus.SUCCESS and not cli_available:
            root_tmp = tk.Tk()
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
                    messagebox.showerror("Install failed", f"Failed to install: {exc}")
            return
    except Exception as exc:
        logger.error("Backend check failed: %s", exc)

    # Проверка наличия моделей перевода
    has_models, available_pairs = check_translation_models()

    if not has_models and ARGOS_MODULE_STATUS == ImportStatus.SUCCESS:
        logger.info("No translation models found, attempting to install from bundle...")

        # Пытаемся установить модели из локальной папки
        if install_models_from_bundle():
            # Проверяем снова после установки
            has_models, available_pairs = check_translation_models()

        if not has_models:
            root_tmp = tk.Tk()
            root_tmp.withdraw()

            models_dir = get_script_dir() / "argos_models"
            has_bundle = models_dir.exists() and any(models_dir.glob("*.argosmodel"))

            if has_bundle:
                msg = (
                    "Translation models found in the bundle, but failed to install them.\n\n"
                    f"Please run the installer manually:\npython install_models.py\n\n"
                    "Or download models from:\nhttps://www.argosopentech.com/argospm/"
                )
            else:
                msg = (
                    "No translation models found.\n\n"
                    "Please download models from:\n"
                    "https://www.argosopentech.com/argospm/\n\n"
                    "Or place .argosmodel files in the 'argos_models' folder\n"
                    "and run: python install_models.py"
                )

            messagebox.showwarning("Translation models missing", msg)
            root_tmp.destroy()
            return

        logger.info("Models installed successfully: %s", available_pairs)

    if has_models:
        logger.info("Available translation pairs: %s", available_pairs)

    try:
        root = tk.Tk()
        app = TranslatorApp(root)
        root.mainloop()
    except Exception as exc:
        logger.critical("Fatal error: %s", exc)
        try:
            tk.Tk().withdraw()
            messagebox.showerror("Fatal error", f"Application crashed:\n{exc}")
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    main()