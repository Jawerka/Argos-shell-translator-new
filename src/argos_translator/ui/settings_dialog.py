"""Диалог настроек приложения (CustomTkinter)."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
import webbrowser
import tkinter as tk
from copy import deepcopy
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from argos_translator import __version__
from argos_translator.config.constants import DefaultLanguages, UIConfig
from argos_translator.config.llm_providers import (
    PROVIDERS,
    get_default_system_prompt,
    get_provider,
    provider_id_from_label,
)
from argos_translator.config.paths import get_settings_path
from argos_translator.config.settings import AppSettings
from argos_translator.engines.llm_engine import fetch_models
from argos_translator.logging_setup import LoggingConfig
from argos_translator.services.model_manager import ModelManager
from argos_translator.ui.font_scale import FONT_SCALE_MAX, FONT_SCALE_MIN, clamp_font_scale, ui_font
from argos_translator.ui.layout_config import (
    CARD_PADX,
    INPUT_HEIGHT,
    RADIUS_CONTROL,
    SECTION_GAP,
    SETTINGS_ACTION_BTN_WIDTH,
    SETTINGS_DIALOG_HEIGHT,
    SETTINGS_DIALOG_MIN_HEIGHT,
    SETTINGS_DIALOG_MIN_WIDTH,
    SETTINGS_DIALOG_WIDTH,
    SETTINGS_FOOTER_BTN_WIDTH,
    SETTINGS_FORM_LABEL_WIDTH,
    SETTINGS_HR_MARGIN_BOTTOM,
    SETTINGS_INTRO_FONT_SIZE,
    SETTINGS_SIDEBAR_WIDTH,
    SETTINGS_TITLE_FONT_SIZE,
)
from argos_translator.ui.themes import ThemeName, apply_theme, get_color_theme, setup_theme
from argos_translator.ui.window_state import WindowStateManager
from argos_translator.ui.widgets import (
    accent_button,
    card_frame,
    ghost_button,
    muted_label,
    primary_button,
    separator,
    transparent_frame,
)
from argos_translator.utils.imports import ARGOS_MODULE_STATUS, ImportStatus

logger = logging.getLogger("ArgosStreaming")

_SETTINGS_SECTIONS: list[tuple[str, str, str]] = [
    ("appearance", "Внешний вид", "Тема, масштаб текста и прозрачность окна."),
    ("translation", "Перевод", "Streaming, задержки debounce и кэш Argos."),
    ("llm", "LLM", "OpenAI-compatible API: LOCAL, OpenRouter или Custom."),
    ("files", "Файлы", "Кодировка, суффиксы и лимиты файлов."),
    ("argos", "Argos", "Офлайн-модели Argos, установка из bundle и папка packages."),
    ("behavior", "Поведение", "Трей, горячие клавиши и clipboard."),
    ("about", "О программе", "Версия, статус движков и пути к конфигурации."),
]


def _opacity_supported() -> bool:
    return sys.platform in ("win32", "darwin")


class SettingsDialog(ctk.CTkToplevel):
    """Модальный диалог настроек."""

    def __init__(
        self,
        parent: ctk.CTk,
        settings: AppSettings,
        on_apply: Callable[[AppSettings], None],
        cfg: Optional[UIConfig] = None,
        on_geometry_save: Optional[Callable[[AppSettings], None]] = None,
    ) -> None:
        self.parent = parent
        self.cfg = cfg or UIConfig()
        self._live_settings = settings
        self.settings = deepcopy(settings)
        self.on_apply = on_apply
        self.on_geometry_save = on_geometry_save
        self.result: Optional[AppSettings] = None
        self.theme: ThemeName = self.settings.theme if self.settings.theme in ("dark", "light") else "dark"
        self._colors = get_color_theme(self.theme)
        self._dialog_cfg = UIConfig(
            width=SETTINGS_DIALOG_WIDTH,
            height=SETTINGS_DIALOG_HEIGHT,
            min_width=SETTINGS_DIALOG_MIN_WIDTH,
            min_height=SETTINGS_DIALOG_MIN_HEIGHT,
        )
        self._skip_geometry_save = True

        setup_theme(self.theme)
        super().__init__(parent)

        self.title("Настройки")
        self.transient(parent)
        self.grab_set()
        self.minsize(SETTINGS_DIALOG_MIN_WIDTH, SETTINGS_DIALOG_MIN_HEIGHT)
        self.configure(fg_color=self._colors["bg_primary"])

        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build_ui()
        self._sync_provider_ui()
        self._sync_llm_enabled_ui()
        self._restore_dialog_geometry()

    def _restore_dialog_geometry(self) -> None:
        self._skip_geometry_save = True
        self.update_idletasks()
        saved = self.settings.settings_dialog_state
        if (
            saved
            and saved.width >= SETTINGS_DIALOG_MIN_WIDTH
            and saved.height >= SETTINGS_DIALOG_MIN_HEIGHT
        ):
            WindowStateManager.restore(self, saved, self._dialog_cfg)
        else:
            self._center_on_parent()
        self.after(50, self._clear_geometry_restore_lock)

    def _clear_geometry_restore_lock(self) -> None:
        self._skip_geometry_save = False

    def _capture_dialog_geometry(self) -> None:
        if self._skip_geometry_save:
            return
        try:
            self.settings.settings_dialog_state = WindowStateManager.capture(self)
        except Exception as exc:
            logger.debug("settings dialog geometry capture failed: %s", exc)

    def _persist_dialog_geometry(self) -> None:
        self._capture_dialog_geometry()
        if self.on_geometry_save and self.settings.settings_dialog_state:
            patch = deepcopy(self._live_settings)
            patch.settings_dialog_state = self.settings.settings_dialog_state
            self.on_geometry_save(patch)

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        pw, ph = self.parent.winfo_width(), self.parent.winfo_height()
        px, py = self.parent.winfo_x(), self.parent.winfo_y()
        w, h = SETTINGS_DIALOG_WIDTH, SETTINGS_DIALOG_HEIGHT
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        main = transparent_frame(self)
        main.pack(fill="both", expand=True, padx=10, pady=10)

        self._title_label = ctk.CTkLabel(
            main,
            text="Настройки",
            font=ui_font(size=SETTINGS_TITLE_FONT_SIZE),
            text_color=self._colors["text_primary"],
            anchor="w",
        )
        self._title_label.pack(anchor="w", pady=(0, SECTION_GAP))

        card = card_frame(main, theme=self.theme)
        card.pack(fill="both", expand=True)

        body = transparent_frame(card)
        body.pack(fill="both", expand=True, padx=CARD_PADX, pady=CARD_PADX)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(
            body,
            width=SETTINGS_SIDEBAR_WIDTH,
            fg_color=self._colors["bg_secondary"],
            corner_radius=RADIUS_CONTROL,
            border_width=1,
            border_color=self._colors["border"],
        )
        sidebar.grid(row=0, column=0, sticky="ns", padx=(0, SECTION_GAP))
        sidebar.grid_propagate(False)

        self._content_area = transparent_frame(body)
        self._content_area.grid(row=0, column=1, sticky="nsew")
        self._content_area.grid_rowconfigure(0, weight=1)
        self._content_area.grid_columnconfigure(0, weight=1)

        self._section_hosts: dict[str, ctk.CTkFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}

        for key, _label, _desc in _SETTINGS_SECTIONS:
            host = transparent_frame(self._content_area)
            host.grid(row=0, column=0, sticky="nsew")
            self._section_hosts[key] = host

        nav_inner = transparent_frame(sidebar)
        nav_inner.pack(fill="both", expand=True, padx=6, pady=6)

        for key, label, _desc in _SETTINGS_SECTIONS:
            btn = ghost_button(
                nav_inner,
                label,
                command=lambda k=key: self._select_section(k),
                theme=self.theme,
                width=SETTINGS_SIDEBAR_WIDTH - 20,
                anchor="w",
            )
            btn.pack(fill="x", pady=2)
            self._nav_buttons[key] = btn

        self._build_appearance_tab()
        self._build_translation_tab()
        self._build_llm_tab()
        self._build_files_tab()
        self._build_argos_tab()
        self._build_behavior_tab()
        self._build_about_tab()

        self._select_section("appearance")

        btn_frame = transparent_frame(main)
        btn_frame.pack(fill="x", pady=(10, 0))
        footer_w = SETTINGS_FOOTER_BTN_WIDTH
        self._footer_cancel = accent_button(
            btn_frame, "Отмена", self._cancel, theme=self.theme, width=footer_w,
        )
        self._footer_cancel.pack(side="right")
        self._footer_apply = accent_button(
            btn_frame, "Применить", self._apply, theme=self.theme, width=footer_w,
        )
        self._footer_apply.pack(side="right", padx=(10, 0))
        self._footer_ok = primary_button(
            btn_frame, "ОК", self._ok, theme=self.theme, width=footer_w,
        )
        self._footer_ok.pack(side="right", padx=(10, 0))

    def _select_section(self, key: str) -> None:
        colors = self._colors
        for section_key, host in self._section_hosts.items():
            if section_key == key:
                host.grid(row=0, column=0, sticky="nsew")
            else:
                host.grid_remove()
        for section_key, btn in self._nav_buttons.items():
            if section_key == key:
                btn.configure(
                    fg_color=colors["primary"],
                    hover_color=colors["primary_hover"],
                    text_color=colors["primary_foreground"],
                )
            else:
                btn.configure(
                    fg_color="transparent",
                    hover_color=colors["accent"],
                    text_color=colors["text_primary"],
                )

    def _wrap_content(self, parent: ctk.CTkFrame, *, scroll: bool = False) -> ctk.CTkFrame:
        if scroll:
            outer = ctk.CTkScrollableFrame(
                parent,
                fg_color="transparent",
                scrollbar_button_color=self._colors["accent"],
                scrollbar_button_hover_color=self._colors["accent_hover"],
            )
            outer.pack(fill="both", expand=True, padx=SECTION_GAP, pady=SECTION_GAP)
            inner = transparent_frame(outer)
            inner.pack(fill="both", expand=True)
            return inner
        inner = transparent_frame(parent)
        inner.pack(fill="both", expand=True, padx=SECTION_GAP, pady=SECTION_GAP)
        return inner

    def _section_intro(self, parent: ctk.CTkFrame, text: str, row: int = 0) -> int:
        self._make_intro_label(parent, text).grid(
            row=row, column=0, columnspan=2, sticky="ew",
        )
        separator(parent, theme=self.theme).grid(
            row=row + 1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(SECTION_GAP, SETTINGS_HR_MARGIN_BOTTOM),
        )
        return row + 2

    def _section_intro_pack(self, parent: ctk.CTkFrame, text: str) -> None:
        self._make_intro_label(parent, text).pack(anchor="w", fill="x")
        separator(parent, theme=self.theme).pack(
            fill="x", pady=(SECTION_GAP, SETTINGS_HR_MARGIN_BOTTOM),
        )

    def _make_intro_label(self, parent: ctk.CTkFrame, text: str) -> ctk.CTkLabel:
        return ctk.CTkLabel(
            parent,
            text=text,
            font=ui_font(size=SETTINGS_INTRO_FONT_SIZE),
            text_color=self._colors["text_muted"],
            wraplength=460,
            anchor="w",
            justify="left",
        )

    def _form_row(self, parent, label: str, widget, row: int) -> None:
        parent.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        ctk.CTkLabel(
            parent,
            text=label,
            font=ui_font(),
            text_color=self._colors["text_primary"],
            anchor="w",
            width=SETTINGS_FORM_LABEL_WIDTH,
        ).grid(row=row, column=0, sticky="w", pady=6, padx=(0, 12))
        widget.grid(row=row, column=1, sticky="ew", pady=6)

    def _entry(self, parent, width: int = 280, show: str = "") -> ctk.CTkEntry:
        kw = {
            "width": width,
            "height": INPUT_HEIGHT,
            "fg_color": self._colors["input"],
            "border_color": self._colors["border"],
            "text_color": self._colors["text_primary"],
        }
        if show:
            kw["show"] = show
        return ctk.CTkEntry(parent, **kw)

    def _combo(self, parent, values: list, variable: tk.StringVar, width: int = 280) -> ctk.CTkComboBox:
        return ctk.CTkComboBox(
            parent,
            variable=variable,
            values=values,
            width=width,
            height=INPUT_HEIGHT,
            state="readonly",
            fg_color=self._colors["input"],
            border_color=self._colors["border"],
            button_color=self._colors["accent"],
            button_hover_color=self._colors["accent_hover"],
            dropdown_fg_color=self._colors["bg_card"],
            dropdown_hover_color=self._colors["accent_hover"],
            text_color=self._colors["text_primary"],
        )

    def _build_appearance_tab(self) -> None:
        frame = self._wrap_content(self._section_hosts["appearance"])
        frame.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        frame.grid_columnconfigure(1, weight=1)
        row = self._section_intro(frame, "Тема, масштаб текста и прозрачность окна.")

        self.var_theme = tk.StringVar(value=self.settings.theme)
        theme_combo = self._combo(frame, ["dark", "light"], self.var_theme)
        self._form_row(frame, "Тема:", theme_combo, row)
        self.var_theme.trace_add("write", lambda *_: self._on_theme_preview())
        row += 1

        self.var_font_scale = tk.DoubleVar(value=self.settings.font_scale)
        font_row = transparent_frame(frame)
        self.font_scale_slider = ctk.CTkSlider(
            font_row,
            from_=FONT_SCALE_MIN,
            to=FONT_SCALE_MAX,
            variable=self.var_font_scale,
            command=self._on_font_scale_preview,
            fg_color=self._colors["progress_bg"],
            progress_color=self._colors["primary"],
            button_color=self._colors["primary"],
            button_hover_color=self._colors["primary_hover"],
        )
        self.font_scale_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.font_scale_label = ctk.CTkLabel(
            font_row,
            text=f"{int(self.settings.font_scale * 100)}%",
            text_color=self._colors["text_muted"],
            width=48,
        )
        self.font_scale_label.pack(side="right")
        self._form_row(frame, "Размер текста в полях:", font_row, row)
        row += 1

        self.var_opacity = tk.DoubleVar(value=self.settings.opacity)
        opacity_row = transparent_frame(frame)
        self.opacity_slider = ctk.CTkSlider(
            opacity_row,
            from_=0.3,
            to=1.0,
            variable=self.var_opacity,
            command=self._on_opacity_preview,
            fg_color=self._colors["progress_bg"],
            progress_color=self._colors["primary"],
            button_color=self._colors["primary"],
            button_hover_color=self._colors["primary_hover"],
        )
        self.opacity_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.opacity_label = ctk.CTkLabel(
            opacity_row,
            text=f"{self.settings.opacity:.0%}",
            text_color=self._colors["text_muted"],
            width=40,
        )
        self.opacity_label.pack(side="right")
        self._form_row(frame, "Прозрачность:", opacity_row, row)

        if not _opacity_supported():
            self.opacity_slider.configure(state="disabled")
            muted_label(
                frame,
                "Прозрачность не поддерживается на этой платформе",
                theme=self.theme,
            ).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_translation_tab(self) -> None:
        frame = self._wrap_content(self._section_hosts["translation"])
        frame.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        frame.grid_columnconfigure(1, weight=1)
        row = self._section_intro(frame, "Streaming, задержки debounce и кэш Argos.")

        self.var_streaming = tk.BooleanVar(value=self.settings.streaming)
        ctk.CTkCheckBox(
            frame,
            text="Потоковый перевод",
            variable=self.var_streaming,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        self.var_scroll_sync = tk.BooleanVar(value=self.settings.scroll_sync)
        ctk.CTkCheckBox(
            frame,
            text="Синхронизация прокрутки",
            variable=self.var_scroll_sync,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        self.var_debounce = tk.StringVar(value=str(self.settings.debounce_ms))
        deb_entry = self._entry(frame, width=120)
        deb_entry.configure(textvariable=self.var_debounce)
        self._form_row(frame, "Задержка Argos (мс):", deb_entry, row)
        row += 1

        self.var_llm_debounce = tk.StringVar(value=str(self.settings.llm_debounce_ms))
        llm_deb_entry = self._entry(frame, width=120)
        llm_deb_entry.configure(textvariable=self.var_llm_debounce)
        self._form_row(frame, "Задержка LLM (мс):", llm_deb_entry, row)
        row += 1

        langs = sorted(DefaultLanguages.get_defaults().items())
        lang_values = [f"{c} — {n}" for c, n in langs]
        current = self.settings.auto_target_lang
        default_val = next((v for c, v in langs if c == current), lang_values[0] if lang_values else "ru")
        self.var_auto_target = tk.StringVar(value=default_val)
        self._form_row(frame, "Целевой язык (AUTO):", self._combo(frame, lang_values, self.var_auto_target), row)
        row += 1

        self.var_cache_enabled = tk.BooleanVar(value=self.settings.behavior.translation_cache_enabled)
        ctk.CTkCheckBox(
            frame,
            text="Кэш переводов Argos (LRU, сессия)",
            variable=self.var_cache_enabled,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        self.var_cache_size = tk.StringVar(value=str(self.settings.behavior.translation_cache_size))
        cache_entry = self._entry(frame, width=120)
        self._form_row(frame, "Размер кэша:", cache_entry, row)
        cache_entry.configure(textvariable=self.var_cache_size)

    def _build_behavior_tab(self) -> None:
        frame = self._wrap_content(self._section_hosts["behavior"])
        frame.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        frame.grid_columnconfigure(1, weight=1)
        row = self._section_intro(frame, "Трей, горячие клавиши и clipboard.")

        self.var_close_action = tk.StringVar(value=self.settings.behavior.close_action)
        self._form_row(frame, "При закрытии:", self._combo(frame, ["tray", "exit"], self.var_close_action), row)
        row += 1

        self.var_start_minimized = tk.BooleanVar(value=self.settings.behavior.start_minimized_to_tray)
        ctk.CTkCheckBox(
            frame, text="Запускать свёрнутым в трей", variable=self.var_start_minimized,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        self.var_restore_clipboard = tk.BooleanVar(value=self.settings.behavior.restore_clipboard_after_capture)
        ctk.CTkCheckBox(
            frame, text="Восстанавливать clipboard после захвата", variable=self.var_restore_clipboard,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        self.var_copy_hide_tray = tk.BooleanVar(value=self.settings.behavior.minimize_to_tray_on_copy_hide)
        ctk.CTkCheckBox(
            frame, text="Copy & Hide — сворачивать в трей", variable=self.var_copy_hide_tray,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=4)
        row += 1

        self.var_global_hotkey = tk.StringVar(value=self.settings.behavior.global_hotkey)
        hotkey_entry = self._entry(frame, width=200)
        self._form_row(frame, "Глобальный хоткей:", hotkey_entry, row)
        hotkey_entry.configure(textvariable=self.var_global_hotkey)

        muted_label(
            frame,
            "Полный выход — ПКМ по иконке трея → Выход. DnD: pip install windnd (Windows).",
            theme=self.theme,
            wraplength=420,
        ).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _build_files_tab(self) -> None:
        frame = self._wrap_content(self._section_hosts["files"])
        frame.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        frame.grid_columnconfigure(1, weight=1)
        row = self._section_intro(frame, "Кодировка, суффиксы и лимиты файлов.")

        self.var_output_encoding = tk.StringVar(value=self.settings.files.output_encoding)
        self._form_row(
            frame, "Кодировка выхода:",
            self._combo(frame, ["same", "utf-8", "utf-8-sig"], self.var_output_encoding), row,
        )
        row += 1

        self.var_output_suffix = tk.StringVar(value=self.settings.files.output_suffix)
        suffix_entry = self._entry(frame)
        self._form_row(frame, "Суффикс файла:", suffix_entry, row)
        suffix_entry.configure(textvariable=self.var_output_suffix)
        row += 1

        self.var_max_file_mb = tk.StringVar(value=str(self.settings.files.max_file_size_mb))
        mb_entry = self._entry(frame, width=120)
        self._form_row(frame, "Макс. размер (МБ):", mb_entry, row)
        mb_entry.configure(textvariable=self.var_max_file_mb)
        row += 1

        self.var_hotkey_max = tk.StringVar(value=str(self.settings.files.hotkey_auto_translate_max_chars))
        hotkey_entry = self._entry(frame, width=120)
        self._form_row(frame, "Автоперевод при захвате до (симв.):", hotkey_entry, row)
        hotkey_entry.configure(textvariable=self.var_hotkey_max)
        row += 1

        self.var_large_warn = tk.StringVar(value=str(self.settings.files.large_file_warn_chars))
        warn_entry = self._entry(frame, width=120)
        self._form_row(frame, "Предупреждение при переводе от (симв.):", warn_entry, row)
        warn_entry.configure(textvariable=self.var_large_warn)

        muted_label(
            frame, "Кодировка при чтении определяется автоматически.", theme=self.theme, wraplength=400,
        ).grid(row=row + 1, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self.var_translate_code = tk.BooleanVar(value=self.settings.files.translate_code_blocks)
        ctk.CTkCheckBox(
            frame, text="Переводить блоки кода", variable=self.var_translate_code,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row + 2, column=0, columnspan=2, sticky="w", pady=4)

    def _build_argos_tab(self) -> None:
        frame = self._wrap_content(self._section_hosts["argos"])
        self._section_intro_pack(frame, "Офлайн-модели Argos, установка из bundle и папка packages.")

        self.var_bundle_on_start = tk.BooleanVar(value=self.settings.argos.bundle_models_on_start)
        ctk.CTkCheckBox(
            frame, text="Устанавливать модели из bundle при старте", variable=self.var_bundle_on_start,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).pack(anchor="w", pady=4)

        self.var_prefer_api = tk.BooleanVar(value=self.settings.argos.prefer_api_over_cli)
        ctk.CTkCheckBox(
            frame, text="Предпочитать Python API (иначе CLI)", variable=self.var_prefer_api,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).pack(anchor="w", pady=4)

        mgr = ModelManager(self.settings.argos.packages_dir or None)
        self._packages_dir_label = ctk.CTkLabel(
            frame,
            text=f"Папка моделей:\n{mgr.packages_dir}",
            font=ui_font(),
            text_color=self._colors["text_primary"],
            anchor="w",
            justify="left",
        )
        self._packages_dir_label.pack(anchor="w", pady=8)

        btn_col = transparent_frame(frame)
        btn_col.pack(anchor="w", pady=4)
        action_w = SETTINGS_ACTION_BTN_WIDTH
        accent_button(btn_col, "Открыть packages", self._open_packages_dir, theme=self.theme, width=action_w).pack(
            anchor="w", pady=(0, 8)
        )
        accent_button(btn_col, "Установить bundle", self._install_bundle, theme=self.theme, width=action_w).pack(
            anchor="w", pady=(0, 8)
        )
        accent_button(btn_col, "Установить .argosmodel", self._install_model_file, theme=self.theme, width=action_w).pack(
            anchor="w", pady=(0, 8)
        )
        accent_button(btn_col, "Список пар", self._show_model_pairs, theme=self.theme, width=action_w).pack(anchor="w")

        link = ctk.CTkLabel(
            frame,
            text="Дополнительные модели: argosopentech.com/argospm/",
            font=ui_font(),
            text_color=self._colors["text_muted"],
            cursor="hand2",
        )
        link.pack(anchor="w", pady=(12, 0))
        link.bind("<Button-1>", lambda _e: webbrowser.open("https://www.argosopentech.com/argospm/"))

        muted_label(
            frame, "CLI: argos-translate mo-install en ru", theme=self.theme, wraplength=420,
        ).pack(anchor="w", pady=(4, 0))
        muted_label(
            frame, "Базовый bundle: en↔ru; остальные языки — докачка.", theme=self.theme, wraplength=420,
        ).pack(anchor="w", pady=(4, 0))

    def _build_about_tab(self) -> None:
        frame = self._wrap_content(self._section_hosts["about"])
        log_cfg = LoggingConfig()
        argos_ok = ARGOS_MODULE_STATUS == ImportStatus.SUCCESS
        llm_state = "включён" if self.settings.llm.enabled else "выключен"

        self._section_intro_pack(frame, "Версия, статус движков и пути к конфигурации.")

        ctk.CTkLabel(
            frame,
            text=f"Argos Translate Streaming v{__version__}",
            font=ui_font(weight="bold"),
            text_color=self._colors["text_primary"],
            anchor="w",
        ).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(frame, text=f"Argos: {'доступен' if argos_ok else 'не найден'}", anchor="w",
                     text_color=self._colors["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(frame, text=f"LLM: {llm_state}", anchor="w",
                     text_color=self._colors["text_primary"]).pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(frame, text=f"Настройки: {get_settings_path()}", anchor="w", justify="left",
                     text_color=self._colors["text_muted"], wraplength=480).pack(anchor="w")
        ctk.CTkLabel(frame, text=f"Лог: {log_cfg.log_file}", anchor="w", justify="left",
                     text_color=self._colors["text_muted"], wraplength=480).pack(anchor="w", pady=(0, 8))
        accent_button(
            frame, "Открыть лог", self._open_log_file, theme=self.theme, width=SETTINGS_ACTION_BTN_WIDTH,
        ).pack(anchor="w")

    def _build_llm_tab(self) -> None:
        frame = self._wrap_content(self._section_hosts["llm"], scroll=True)
        frame.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        frame.grid_columnconfigure(1, weight=1)
        row = self._section_intro(frame, "OpenAI-compatible API: LOCAL, OpenRouter или Custom.")

        self.var_llm_enabled = tk.BooleanVar(value=self.settings.llm.enabled)
        ctk.CTkCheckBox(
            frame, text="Использовать LLM-перевод", variable=self.var_llm_enabled,
            command=self._sync_llm_enabled_ui,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
        row += 1

        self.llm_fields_frame = transparent_frame(frame)
        self.llm_fields_frame.grid(row=row, column=0, columnspan=2, sticky="nsew")
        self.llm_fields_frame.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        self.llm_fields_frame.grid_columnconfigure(1, weight=1)
        lf = self.llm_fields_frame
        lf_row = 0

        provider_labels = [p.label for p in PROVIDERS.values()]
        self.var_provider = tk.StringVar(value=get_provider(self.settings.llm.provider).label)
        provider_combo = self._combo(lf, provider_labels, self.var_provider)
        provider_combo.configure(command=lambda _v: self._on_provider_changed())
        self._form_row(lf, "Провайдер:", provider_combo, lf_row)
        lf_row += 1

        self.entry_url = self._entry(lf, width=320)
        self.entry_url.insert(0, self.settings.llm.base_url)
        self._form_row(lf, "Base URL:", self.entry_url, lf_row)
        lf_row += 1

        self.entry_api_key = self._entry(lf, width=320, show="•")
        key = self.settings.llm.api_keys.get(self.settings.llm.provider, "")
        if key:
            self.entry_api_key.insert(0, key)
        self._form_row(lf, "API key:", self.entry_api_key, lf_row)
        lf_row += 1

        self.api_key_hint = muted_label(lf, "", theme=self.theme)
        self.api_key_hint.grid(row=lf_row, column=1, sticky="w")
        lf_row += 1

        self.cloud_warning = ctk.CTkLabel(
            lf, text="", font=ui_font(), text_color=self._colors["text_warning"], anchor="w",
        )
        self.cloud_warning.grid(row=lf_row, column=0, columnspan=2, sticky="w")
        lf_row += 1

        self.entry_model = self._entry(lf, width=320)
        self.entry_model.insert(0, self.settings.llm.model)
        self._form_row(lf, "Модель:", self.entry_model, lf_row)
        lf_row += 1

        btn_col = transparent_frame(lf)
        btn_col.grid(row=lf_row, column=0, columnspan=2, sticky="w", pady=8)
        accent_button(
            btn_col, "Проверить", self._test_connection, theme=self.theme, width=SETTINGS_ACTION_BTN_WIDTH,
        ).pack(anchor="w", pady=(0, 8))
        accent_button(
            btn_col, "Загрузить модели", self._load_models, theme=self.theme, width=SETTINGS_ACTION_BTN_WIDTH,
        ).pack(anchor="w")
        lf_row += 1

        self.var_llm_advanced = tk.BooleanVar(value=False)
        ctk.CTkCheckBox(
            lf,
            text="Дополнительные параметры (temperature, промпт)",
            variable=self.var_llm_advanced,
            command=self._toggle_llm_advanced,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=lf_row, column=0, columnspan=2, sticky="w", pady=(4, 4))
        lf_row += 1

        self.llm_advanced_frame = transparent_frame(lf)
        self.llm_advanced_frame.grid(row=lf_row, column=0, columnspan=2, sticky="ew")
        self.llm_advanced_frame.grid_columnconfigure(0, minsize=SETTINGS_FORM_LABEL_WIDTH)
        self.llm_advanced_frame.grid_columnconfigure(1, weight=1)
        self.llm_advanced_frame.grid_remove()

        self.var_temperature = tk.StringVar(value=str(self.settings.llm.temperature))
        temp_entry = self._entry(self.llm_advanced_frame, width=120)
        temp_entry.configure(textvariable=self.var_temperature)
        self._form_row(self.llm_advanced_frame, "Temperature:", temp_entry, 0)

        ctk.CTkLabel(
            self.llm_advanced_frame, text="Системный промпт:", font=ui_font(),
            text_color=self._colors["text_primary"], anchor="nw",
        ).grid(row=1, column=0, sticky="nw", pady=4)

        self.prompt_text = ctk.CTkTextbox(
            self.llm_advanced_frame, height=120, width=320,
            fg_color=self._colors["input"], text_color=self._colors["text_primary"],
            border_color=self._colors["border"], corner_radius=RADIUS_CONTROL,
        )
        self.prompt_text.grid(row=1, column=1, sticky="nsew", pady=4)
        prompt = self.settings.llm.system_prompt or get_default_system_prompt()
        self.prompt_text.insert("1.0", prompt)

        accent_button(
            self.llm_advanced_frame, "Сбросить промпт", self._reset_prompt, theme=self.theme, width=140,
        ).grid(row=2, column=1, sticky="w", pady=4)

        ctk.CTkLabel(
            self.llm_advanced_frame, text="Файлы (LLM):", font=ui_font(weight="bold"),
            text_color=self._colors["text_primary"], anchor="w",
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(12, 4))

        self.var_file_chunk_max = tk.StringVar(value=str(self.settings.llm.file_chunk_max_chars))
        file_chunk_entry = self._entry(self.llm_advanced_frame, width=120)
        file_chunk_entry.configure(textvariable=self.var_file_chunk_max)
        self._form_row(self.llm_advanced_frame, "Размер блока (файл):", file_chunk_entry, 4)

        self.var_file_chunk_context = tk.BooleanVar(value=self.settings.llm.file_chunk_context)
        ctk.CTkCheckBox(
            self.llm_advanced_frame,
            text="Контекст между блоками при переводе файлов",
            variable=self.var_file_chunk_context,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=4)

    def _toggle_llm_advanced(self) -> None:
        if self.var_llm_advanced.get():
            self.llm_advanced_frame.grid()
        else:
            self.llm_advanced_frame.grid_remove()

    @property
    def dialog(self):
        """Совместимость: self как диалог."""
        return self

    def _on_theme_preview(self) -> None:
        self.theme = self.var_theme.get() if self.var_theme.get() in ("dark", "light") else "dark"
        self._colors = get_color_theme(self.theme)
        apply_theme(self, self.theme)
        apply_theme(self.parent, self.theme)

    def _on_font_scale_preview(self, _value: str = "") -> None:
        val = clamp_font_scale(self.var_font_scale.get())
        self.font_scale_label.configure(text=f"{int(val * 100)}%")

    def _on_opacity_preview(self, _value: str = "") -> None:
        val = self.var_opacity.get()
        self.opacity_label.configure(text=f"{val:.0%}")
        if _opacity_supported():
            try:
                self.parent.attributes("-alpha", val)
            except Exception:
                pass

    def _on_provider_changed(self) -> None:
        pid = provider_id_from_label(self.var_provider.get())
        preset = get_provider(pid)
        if preset.default_base_url:
            self.entry_url.delete(0, "end")
            self.entry_url.insert(0, preset.default_base_url)
        stored_key = self.settings.llm.api_keys.get(pid, "")
        self.entry_api_key.delete(0, "end")
        if stored_key:
            self.entry_api_key.insert(0, stored_key)
        self._sync_provider_ui()

    def _sync_provider_ui(self) -> None:
        pid = provider_id_from_label(self.var_provider.get())
        preset = get_provider(pid)
        if preset.api_key_required:
            self.entry_api_key.configure(state="normal")
            self.api_key_hint.configure(text="Обязателен для OpenRouter")
        elif pid == "local":
            self.entry_api_key.configure(state="disabled")
            self.api_key_hint.configure(text="Не требуется для LOCAL")
        else:
            self.entry_api_key.configure(state="normal")
            self.api_key_hint.configure(text="Опционально для Custom")

        if preset.cloud_warning:
            self.cloud_warning.configure(text="⚠ Текст отправляется в облако OpenRouter")
        else:
            self.cloud_warning.configure(text="")

    def _sync_llm_enabled_ui(self) -> None:
        enabled = self.var_llm_enabled.get()
        state = "normal" if enabled else "disabled"
        for child in self.llm_fields_frame.winfo_children():
            try:
                if hasattr(child, "configure"):
                    child.configure(state=state)
            except Exception:
                pass
        if enabled:
            self._sync_provider_ui()
            self.prompt_text.configure(state="normal")
        else:
            self.prompt_text.configure(state="disabled")

    def _collect_settings(self) -> AppSettings:
        s = deepcopy(self.settings)
        s.theme = self.var_theme.get()
        s.font_scale = clamp_font_scale(float(self.var_font_scale.get()))
        s.opacity = float(self.var_opacity.get())
        s.streaming = self.var_streaming.get()
        s.scroll_sync = self.var_scroll_sync.get()
        s.debounce_ms = int(self.var_debounce.get())
        s.llm_debounce_ms = int(self.var_llm_debounce.get())

        auto_val = self.var_auto_target.get()
        s.auto_target_lang = auto_val.split(" — ", 1)[0].strip().lower()

        pid = provider_id_from_label(self.var_provider.get())
        s.llm.enabled = self.var_llm_enabled.get()
        s.llm.provider = pid
        s.llm.base_url = self.entry_url.get().strip()
        s.llm.provider_urls[pid] = s.llm.base_url
        s.llm.api_keys[pid] = self.entry_api_key.get().strip()
        s.llm.model = self.entry_model.get().strip()
        s.llm.temperature = float(self.var_temperature.get())
        s.llm.system_prompt = self.prompt_text.get("1.0", "end-1c").strip()
        s.llm.file_chunk_max_chars = int(self.var_file_chunk_max.get())
        s.llm.file_chunk_context = self.var_file_chunk_context.get()
        s.files.output_encoding = self.var_output_encoding.get()
        s.files.output_suffix = self.var_output_suffix.get().strip() or "_translated"
        s.files.max_file_size_mb = int(self.var_max_file_mb.get())
        s.files.hotkey_auto_translate_max_chars = int(self.var_hotkey_max.get())
        s.files.large_file_warn_chars = int(self.var_large_warn.get())
        s.files.translate_code_blocks = self.var_translate_code.get()
        s.argos.bundle_models_on_start = self.var_bundle_on_start.get()
        s.argos.prefer_api_over_cli = self.var_prefer_api.get()
        s.behavior.close_action = self.var_close_action.get()
        s.behavior.start_minimized_to_tray = self.var_start_minimized.get()
        s.behavior.restore_clipboard_after_capture = self.var_restore_clipboard.get()
        s.behavior.minimize_to_tray_on_copy_hide = self.var_copy_hide_tray.get()
        s.behavior.global_hotkey = self.var_global_hotkey.get().strip() or "ctrl+shift+c"
        s.behavior.translation_cache_enabled = self.var_cache_enabled.get()
        s.behavior.translation_cache_size = int(self.var_cache_size.get())
        self._capture_dialog_geometry()
        s.settings_dialog_state = self.settings.settings_dialog_state
        return s

    def _validate(self, s: AppSettings) -> bool:
        if s.llm.enabled:
            preset = get_provider(s.llm.provider)
            if preset.api_key_required and not s.llm.api_keys.get(s.llm.provider, "").strip():
                if not self.entry_api_key.get().strip():
                    messagebox.showerror("Настройки", "API key обязателен для OpenRouter", parent=self)
                    return False
            if not s.llm.base_url.strip() and not preset.default_base_url:
                messagebox.showerror("Настройки", "Укажите Base URL", parent=self)
                return False
        return True

    def _open_packages_dir(self) -> None:
        mgr = ModelManager(self.settings.argos.packages_dir or None)
        path = mgr.packages_dir
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # noqa: S606
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=False)
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as exc:
            messagebox.showerror("Argos", str(exc), parent=self)

    def _install_bundle(self) -> None:
        mgr = ModelManager(self.settings.argos.packages_dir or None)
        count = mgr.install_from_bundle()
        messagebox.showinfo("Argos", f"Установлено моделей: {count}", parent=self)
        self._refresh_packages_label()

    def _install_model_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Выберите .argosmodel",
            filetypes=[("Argos models", "*.argosmodel"), ("All", "*.*")],
            parent=self,
        )
        if not path_str:
            return
        mgr = ModelManager(self.settings.argos.packages_dir or None)
        ok = mgr.install_from_path(Path(path_str))
        messagebox.showinfo(
            "Argos", "Модель установлена" if ok else "Не удалось установить модель", parent=self,
        )
        self._refresh_packages_label()

    def _show_model_pairs(self) -> None:
        mgr = ModelManager(self.settings.argos.packages_dir or None)
        pairs = mgr.list_installed_pairs()
        text = "\n".join(pairs) if pairs else "Нет установленных пар"
        messagebox.showinfo("Argos — установленные пары", text, parent=self)

    def _refresh_packages_label(self) -> None:
        mgr = ModelManager(self.settings.argos.packages_dir or None)
        self._packages_dir_label.configure(text=f"Папка моделей:\n{mgr.packages_dir}")

    def _open_log_file(self) -> None:
        log_cfg = LoggingConfig()
        path = log_cfg.log_file
        if not path.exists():
            messagebox.showinfo("Лог", "Файл лога ещё не создан", parent=self)
            return
        try:
            if sys.platform == "win32":
                os.startfile(str(path))  # noqa: S606
            else:
                webbrowser.open(path.as_uri())
        except Exception as exc:
            messagebox.showerror("Log", str(exc), parent=self)

    def _test_connection(self) -> None:
        s = self._collect_settings()
        if not self._validate(s):
            return
        try:
            models = fetch_models(s.llm, timeout=5.0)
            messagebox.showinfo("LLM", f"Соединение OK. Моделей: {len(models)}", parent=self)
        except Exception as exc:
            messagebox.showerror("LLM", f"Ошибка: {exc}", parent=self)

    def _load_models(self) -> None:
        s = self._collect_settings()
        if not self._validate(s):
            return
        try:
            models = fetch_models(s.llm, timeout=10.0)
            if not models:
                messagebox.showwarning("LLM", "Список моделей пуст", parent=self)
                return
            picker = ctk.CTkToplevel(self)
            picker.title("Выберите модель")
            picker.transient(self)
            picker.grab_set()
            picker.configure(fg_color=self._colors["bg_primary"])
            picker.geometry("440x140")
            picker.minsize(360, 120)
            picker.resizable(True, False)

            body = transparent_frame(picker)
            body.pack(fill="both", expand=True, padx=10, pady=10)

            var = tk.StringVar(value=models[0])
            self._combo(body, models, var, width=400).pack(fill="x")

            actions = transparent_frame(body)
            actions.pack(fill="x", pady=(10, 0))

            def pick() -> None:
                self.entry_model.delete(0, "end")
                self.entry_model.insert(0, var.get())
                picker.destroy()

            primary_button(actions, "Выбрать", pick, theme=self.theme, width=100).pack(side="right")
        except Exception as exc:
            messagebox.showerror("LLM", f"Ошибка: {exc}", parent=self)

    def _reset_prompt(self) -> None:
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", get_default_system_prompt())

    def _apply(self) -> None:
        s = self._collect_settings()
        if not self._validate(s):
            return
        self.settings = s
        self.on_apply(s)

    def _ok(self) -> None:
        s = self._collect_settings()
        if not self._validate(s):
            return
        self.result = s
        self.on_apply(s)
        self.destroy()

    def _cancel(self) -> None:
        if _opacity_supported():
            try:
                self.parent.attributes("-alpha", self.settings.opacity)
            except Exception:
                pass
        self._persist_dialog_geometry()
        self.destroy()
