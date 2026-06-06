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
from argos_translator.ui.font_scale import FONT_SCALE_MAX, FONT_SCALE_MIN, clamp_font_scale
from argos_translator.ui.layout_config import CARD_PADX, CORNER_RADIUS, INPUT_HEIGHT, Spacing, get_tabview_kwargs
from argos_translator.ui.themes import ThemeName, apply_theme, get_color_theme, setup_theme
from argos_translator.ui.widgets import accent_button, card_frame, muted_label, primary_button, transparent_frame
from argos_translator.utils.imports import ARGOS_MODULE_STATUS, ImportStatus

logger = logging.getLogger("ArgosStreaming")


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
    ) -> None:
        self.parent = parent
        self.cfg = cfg or UIConfig()
        self.settings = deepcopy(settings)
        self.on_apply = on_apply
        self.result: Optional[AppSettings] = None
        self.theme: ThemeName = self.settings.theme if self.settings.theme in ("dark", "light") else "dark"
        self._colors = get_color_theme(self.theme)

        setup_theme(self.theme)
        super().__init__(parent)

        self.title("Настройки")
        self.transient(parent)
        self.grab_set()
        self.minsize(560, 480)
        self.geometry("640x560")
        self.configure(fg_color=self._colors["bg_primary"])

        self._center_on_parent()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build_ui()
        self._sync_provider_ui()
        self._sync_llm_enabled_ui()

    def _center_on_parent(self) -> None:
        self.update_idletasks()
        pw, ph = self.parent.winfo_width(), self.parent.winfo_height()
        px, py = self.parent.winfo_x(), self.parent.winfo_y()
        w, h = 640, 560
        x = px + max(0, (pw - w) // 2)
        y = py + max(0, (ph - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self) -> None:
        main = transparent_frame(self)
        main.pack(fill="both", expand=True, padx=Spacing.LG, pady=Spacing.LG)

        card = card_frame(main, theme=self.theme)
        card.pack(fill="both", expand=True)

        tabview_kw = get_tabview_kwargs(self.theme)
        tabview_kw["fg_color"] = self._colors["bg_card"]
        self.tabview = ctk.CTkTabview(card, **tabview_kw)
        self.tabview.pack(fill="both", expand=True, padx=CARD_PADX, pady=CARD_PADX)

        self._build_appearance_tab()
        self._build_translation_tab()
        self._build_llm_tab()
        self._build_files_tab()
        self._build_argos_tab()
        self._build_behavior_tab()
        self._build_about_tab()

        btn_frame = transparent_frame(main)
        btn_frame.pack(fill="x", pady=(Spacing.MD, 0))
        accent_button(btn_frame, "Отмена", self._cancel, theme=self.theme, width=100).pack(side="right")
        primary_button(btn_frame, "ОК", self._ok, theme=self.theme, width=100).pack(side="right", padx=(8, 0))
        accent_button(btn_frame, "Применить", self._apply, theme=self.theme, width=110).pack(
            side="right", padx=(8, 0)
        )

    def _plain_tab(self, name: str) -> ctk.CTkFrame:
        self.tabview.add(name)
        frame = self.tabview.tab(name)
        content = transparent_frame(frame)
        content.pack(fill="both", expand=True, padx=Spacing.SM, pady=Spacing.SM)
        return content

    def _scroll_tab(self, name: str) -> ctk.CTkScrollableFrame:
        self.tabview.add(name)
        frame = self.tabview.tab(name)
        scroll = ctk.CTkScrollableFrame(
            frame,
            fg_color="transparent",
            scrollbar_button_color=self._colors["accent"],
            scrollbar_button_hover_color=self._colors["accent_hover"],
        )
        scroll.pack(fill="both", expand=True, padx=4, pady=4)
        return scroll

    def _form_row(self, parent, label: str, widget, row: int) -> None:
        ctk.CTkLabel(
            parent,
            text=label,
            font=ctk.CTkFont(size=12),
            text_color=self._colors["text_primary"],
            anchor="w",
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
        frame = self._plain_tab("Внешний вид")
        frame.grid_columnconfigure(1, weight=1)

        self.var_theme = tk.StringVar(value=self.settings.theme)
        theme_combo = self._combo(frame, ["dark", "light"], self.var_theme)
        self._form_row(frame, "Тема:", theme_combo, 0)
        self.var_theme.trace_add("write", lambda *_: self._on_theme_preview())

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
        self._form_row(frame, "Размер текста:", font_row, 1)

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
        self._form_row(frame, "Прозрачность:", opacity_row, 2)

        if not _opacity_supported():
            self.opacity_slider.configure(state="disabled")
            muted_label(
                frame,
                "Прозрачность не поддерживается на этой платформе",
                theme=self.theme,
            ).grid(row=3, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def _build_translation_tab(self) -> None:
        frame = self._plain_tab("Перевод")
        frame.grid_columnconfigure(1, weight=1)

        self.var_streaming = tk.BooleanVar(value=self.settings.streaming)
        ctk.CTkCheckBox(
            frame,
            text="Потоковый перевод (streaming)",
            variable=self.var_streaming,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=4)

        self.var_scroll_sync = tk.BooleanVar(value=self.settings.scroll_sync)
        ctk.CTkCheckBox(
            frame,
            text="Синхронизация прокрутки",
            variable=self.var_scroll_sync,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        self.var_debounce = tk.StringVar(value=str(self.settings.debounce_ms))
        deb_entry = self._entry(frame, width=120)
        deb_entry.configure(textvariable=self.var_debounce)
        self._form_row(frame, "Задержка Argos (мс):", deb_entry, 2)

        self.var_llm_debounce = tk.StringVar(value=str(self.settings.llm_debounce_ms))
        llm_deb_entry = self._entry(frame, width=120)
        llm_deb_entry.configure(textvariable=self.var_llm_debounce)
        self._form_row(frame, "Задержка LLM (мс):", llm_deb_entry, 3)

        langs = sorted(DefaultLanguages.get_defaults().items())
        lang_values = [f"{c} — {n}" for c, n in langs]
        current = self.settings.auto_target_lang
        default_val = next((v for c, v in langs if c == current), lang_values[0] if lang_values else "ru")
        self.var_auto_target = tk.StringVar(value=default_val)
        self._form_row(frame, "Целевой язык (AUTO):", self._combo(frame, lang_values, self.var_auto_target), 4)

        self.var_cache_enabled = tk.BooleanVar(value=self.settings.behavior.translation_cache_enabled)
        ctk.CTkCheckBox(
            frame,
            text="Кэш переводов Argos (LRU, сессия)",
            variable=self.var_cache_enabled,
            fg_color=self._colors["primary"],
            hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=4)

        self.var_cache_size = tk.StringVar(value=str(self.settings.behavior.translation_cache_size))
        cache_entry = self._entry(frame, width=120)
        self._form_row(frame, "Размер кэша:", cache_entry, 6)
        cache_entry.configure(textvariable=self.var_cache_size)

    def _build_behavior_tab(self) -> None:
        frame = self._plain_tab("Поведение")
        frame.grid_columnconfigure(1, weight=1)

        self.var_close_action = tk.StringVar(value=self.settings.behavior.close_action)
        self._form_row(frame, "При закрытии (X):", self._combo(frame, ["tray", "exit"], self.var_close_action), 0)

        self.var_start_minimized = tk.BooleanVar(value=self.settings.behavior.start_minimized_to_tray)
        ctk.CTkCheckBox(
            frame, text="Запуск свёрнутым в трей", variable=self.var_start_minimized,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=4)

        self.var_restore_clipboard = tk.BooleanVar(value=self.settings.behavior.restore_clipboard_after_capture)
        ctk.CTkCheckBox(
            frame, text="Восстанавливать буфер после Ctrl+Shift+C", variable=self.var_restore_clipboard,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=4)

        self.var_copy_hide_tray = tk.BooleanVar(value=self.settings.behavior.minimize_to_tray_on_copy_hide)
        ctk.CTkCheckBox(
            frame, text="Copy & Hide — сворачивать в трей", variable=self.var_copy_hide_tray,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=3, column=0, columnspan=2, sticky="w", pady=4)

        self.var_global_hotkey = tk.StringVar(value=self.settings.behavior.global_hotkey)
        hotkey_entry = self._entry(frame, width=200)
        self._form_row(frame, "Глобальная горячая клавиша:", hotkey_entry, 4)
        hotkey_entry.configure(textvariable=self.var_global_hotkey)

        muted_label(
            frame,
            "Полный выход — ПКМ по иконке трея → Выход. DnD: pip install windnd (Windows).",
            theme=self.theme,
            wraplength=420,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

    def _build_files_tab(self) -> None:
        frame = self._plain_tab("Файлы")
        frame.grid_columnconfigure(1, weight=1)

        self.var_output_encoding = tk.StringVar(value=self.settings.files.output_encoding)
        self._form_row(
            frame, "Кодировка сохранения:",
            self._combo(frame, ["same", "utf-8", "utf-8-sig"], self.var_output_encoding), 0,
        )

        self.var_output_suffix = tk.StringVar(value=self.settings.files.output_suffix)
        suffix_entry = self._entry(frame)
        self._form_row(frame, "Суффикс имени файла:", suffix_entry, 1)
        suffix_entry.configure(textvariable=self.var_output_suffix)

        self.var_max_file_mb = tk.StringVar(value=str(self.settings.files.max_file_size_mb))
        mb_entry = self._entry(frame, width=120)
        self._form_row(frame, "Макс. размер файла (MB):", mb_entry, 2)
        mb_entry.configure(textvariable=self.var_max_file_mb)

        self.var_hotkey_max = tk.StringVar(value=str(self.settings.files.hotkey_auto_translate_max_chars))
        hotkey_entry = self._entry(frame, width=120)
        self._form_row(frame, "Автоперевод при захвате до (симв.):", hotkey_entry, 3)
        hotkey_entry.configure(textvariable=self.var_hotkey_max)

        self.var_large_warn = tk.StringVar(value=str(self.settings.files.large_file_warn_chars))
        warn_entry = self._entry(frame, width=120)
        self._form_row(frame, "Предупреждение при переводе от (симв.):", warn_entry, 4)
        warn_entry.configure(textvariable=self.var_large_warn)

        muted_label(
            frame, "Кодировка при чтении определяется автоматически.", theme=self.theme, wraplength=400,
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(12, 0))

        self.var_translate_code = tk.BooleanVar(value=self.settings.files.translate_code_blocks)
        ctk.CTkCheckBox(
            frame, text="Переводить блоки кода Markdown (```…```)", variable=self.var_translate_code,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=4)

    def _build_argos_tab(self) -> None:
        frame = self._plain_tab("Argos")

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
            font=ctk.CTkFont(size=12),
            text_color=self._colors["text_primary"],
            anchor="w",
            justify="left",
        )
        self._packages_dir_label.pack(anchor="w", pady=8)

        btn_row = transparent_frame(frame)
        btn_row.pack(anchor="w", pady=4)
        accent_button(btn_row, "Открыть папку", self._open_packages_dir, theme=self.theme, width=130).pack(
            side="left"
        )
        accent_button(btn_row, "Из bundle", self._install_bundle, theme=self.theme, width=100).pack(
            side="left", padx=(8, 0)
        )
        accent_button(btn_row, "Из файла…", self._install_model_file, theme=self.theme, width=100).pack(
            side="left", padx=(8, 0)
        )
        accent_button(btn_row, "Список пар", self._show_model_pairs, theme=self.theme, width=100).pack(
            side="left", padx=(8, 0)
        )

        link = ctk.CTkLabel(
            frame,
            text="Дополнительные модели: argosopentech.com/argospm/",
            font=ctk.CTkFont(size=11),
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
        frame = self._plain_tab("О программе")
        log_cfg = LoggingConfig()
        argos_ok = ARGOS_MODULE_STATUS == ImportStatus.SUCCESS
        llm_state = "включён" if self.settings.llm.enabled else "выключен"

        ctk.CTkLabel(
            frame,
            text=f"Argos Translate Streaming v{__version__}",
            font=ctk.CTkFont(size=14, weight="bold"),
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
        accent_button(frame, "Открыть лог", self._open_log_file, theme=self.theme, width=120).pack(anchor="w")

    def _build_llm_tab(self) -> None:
        frame = self._scroll_tab("LLM")
        frame.grid_columnconfigure(1, weight=1)

        self.var_llm_enabled = tk.BooleanVar(value=self.settings.llm.enabled)
        ctk.CTkCheckBox(
            frame, text="Использовать LLM-перевод", variable=self.var_llm_enabled,
            command=self._sync_llm_enabled_ui,
            fg_color=self._colors["primary"], hover_color=self._colors["primary_hover"],
            text_color=self._colors["text_primary"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        self.llm_fields_frame = transparent_frame(frame)
        self.llm_fields_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.llm_fields_frame.grid_columnconfigure(1, weight=1)
        lf = self.llm_fields_frame

        provider_labels = [p.label for p in PROVIDERS.values()]
        self.var_provider = tk.StringVar(value=get_provider(self.settings.llm.provider).label)
        provider_combo = self._combo(lf, provider_labels, self.var_provider)
        provider_combo.configure(command=lambda _v: self._on_provider_changed())
        self._form_row(lf, "Провайдер:", provider_combo, 0)

        self.entry_url = self._entry(lf, width=320)
        self.entry_url.insert(0, self.settings.llm.base_url)
        self._form_row(lf, "Base URL:", self.entry_url, 1)

        self.entry_api_key = self._entry(lf, width=320, show="•")
        key = self.settings.llm.api_keys.get(self.settings.llm.provider, "")
        if key:
            self.entry_api_key.insert(0, key)
        self._form_row(lf, "API key:", self.entry_api_key, 2)

        self.api_key_hint = muted_label(lf, "", theme=self.theme)
        self.api_key_hint.grid(row=3, column=1, sticky="w")

        self.cloud_warning = ctk.CTkLabel(
            lf, text="", font=ctk.CTkFont(size=11), text_color=self._colors["text_warning"], anchor="w",
        )
        self.cloud_warning.grid(row=4, column=0, columnspan=2, sticky="w")

        self.entry_model = self._entry(lf, width=320)
        self.entry_model.insert(0, self.settings.llm.model)
        self._form_row(lf, "Модель:", self.entry_model, 5)

        self.var_temperature = tk.StringVar(value=str(self.settings.llm.temperature))
        temp_entry = self._entry(lf, width=120)
        temp_entry.configure(textvariable=self.var_temperature)
        self._form_row(lf, "Temperature:", temp_entry, 6)

        btn_row = transparent_frame(lf)
        btn_row.grid(row=7, column=0, columnspan=2, sticky="w", pady=8)
        accent_button(btn_row, "Проверить", self._test_connection, theme=self.theme, width=110).pack(side="left")
        accent_button(btn_row, "Загрузить модели", self._load_models, theme=self.theme, width=140).pack(
            side="left", padx=(8, 0)
        )

        ctk.CTkLabel(
            lf, text="Системный промпт:", font=ctk.CTkFont(size=12),
            text_color=self._colors["text_primary"], anchor="nw",
        ).grid(row=8, column=0, sticky="nw", pady=4)

        self.prompt_text = ctk.CTkTextbox(
            lf, height=140, width=320,
            fg_color=self._colors["input"], text_color=self._colors["text_primary"],
            border_color=self._colors["border"], corner_radius=CORNER_RADIUS - 4,
        )
        self.prompt_text.grid(row=8, column=1, sticky="nsew", pady=4)
        prompt = self.settings.llm.system_prompt or get_default_system_prompt()
        self.prompt_text.insert("1.0", prompt)

        accent_button(lf, "Сбросить промпт", self._reset_prompt, theme=self.theme, width=140).grid(
            row=9, column=1, sticky="w", pady=4
        )

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
            var = tk.StringVar(value=models[0])
            self._combo(picker, models, var, width=400).pack(padx=16, pady=16)

            def pick() -> None:
                self.entry_model.delete(0, "end")
                self.entry_model.insert(0, var.get())
                picker.destroy()

            primary_button(picker, "Выбрать", pick, theme=self.theme).pack(pady=(0, 16))
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
        self.destroy()
