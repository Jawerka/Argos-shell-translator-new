"""Построение главного окна (CustomTkinter, flat layout)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import customtkinter as ctk
import tkinter as tk

from argos_translator.config.constants import UIConfig
from argos_translator.config.settings import AppSettings
from argos_translator.ui.file_menu import clear_window_menubar, create_file_popup_menu, show_popup_menu
from argos_translator.ui.language_selector import CompactLanguageSelector
from argos_translator.ui.font_scale import scaled_ui_font
from argos_translator.ui.layout_config import (
    CARD_PADX,
    CARD_PADY,
    ELEMENT_GAP,
    PROGRESS_HEIGHT,
    PROGRESS_WIDTH,
    WINDOW_PADX,
    WINDOW_PADY,
)
from argos_translator.ui.text_panel import TextPanel
from argos_translator.ui.themes import ThemeName, get_color_theme
from argos_translator.ui.tooltip import create_tooltip
from argos_translator.ui.translation_tabs import TranslationTabs
from argos_translator.ui.widgets import (
    card_frame,
    ghost_button,
    icon_button,
    primary_button,
    themed_checkbox,
    transparent_frame,
    vertical_separator,
)


@dataclass
class MainWindowCallbacks:
    on_file_open: Callable[[], None]
    on_file_save_translation: Callable[[], None]
    on_file_save_both: Callable[[], None]
    on_quit: Callable[[], None]
    on_translate: Callable[[], None]
    on_cancel: Callable[[], None]
    on_open_settings: Callable[[], None]
    on_stream_toggle: Callable[[], None]
    on_scroll_sync_toggle: Callable[[], None]
    on_copy_and_hide: Callable[[], None]
    on_tab_changed: Callable[[str], None]
    on_src_modified: Callable[[Optional[tk.Event]], None]


@dataclass
class MainWindowView:
    main_frame: ctk.CTkFrame
    lang_widget: CompactLanguageSelector
    src_panel: TextPanel
    translation_tabs: TranslationTabs
    streaming_enabled: tk.BooleanVar
    scroll_sync_enabled: tk.BooleanVar
    translate_status_var: tk.StringVar
    status_var: tk.StringVar
    llm_indicator_var: tk.StringVar
    llm_indicator: ctk.CTkLabel
    file_progress: ctk.CTkProgressBar
    file_progress_var: tk.StringVar
    file_progress_label: ctk.CTkLabel
    file_progress_frame: ctk.CTkFrame
    status_label: ctk.CTkLabel
    hints_label: ctk.CTkLabel


def apply_ui_font_scale(view: MainWindowView, scale: float) -> None:
    view.src_panel.apply_font_scale(scale)
    view.translation_tabs.apply_font_scale(scale)
    small = scaled_ui_font(scale, 11)
    for widget in (
        view.status_label,
        view.llm_indicator,
        view.hints_label,
        view.file_progress_label,
    ):
        widget.configure(font=small)


def build_main_window(
    root: ctk.CTk,
    cfg: UIConfig,
    settings: AppSettings,
    languages: Dict[str, str],
    callbacks: MainWindowCallbacks,
) -> MainWindowView:
    theme: ThemeName = settings.theme if settings.theme in ("dark", "light") else "dark"
    colors = get_color_theme(theme)
    font_scale = settings.font_scale

    clear_window_menubar(root)

    main = transparent_frame(root)
    main.grid(row=0, column=0, sticky="nsew", padx=WINDOW_PADX, pady=WINDOW_PADY)
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)

    toolbar = card_frame(main, theme=theme)
    toolbar.grid(row=0, column=0, sticky="ew", pady=(0, ELEMENT_GAP))
    toolbar_inner = transparent_frame(toolbar)
    toolbar_inner.pack(fill="x", padx=CARD_PADX, pady=CARD_PADY)

    toolbar_row = transparent_frame(toolbar_inner)
    toolbar_row.pack(fill="x")

    file_menu = create_file_popup_menu(
        root,
        on_open=callbacks.on_file_open,
        on_save_translation=callbacks.on_file_save_translation,
        on_save_both=callbacks.on_file_save_both,
        on_quit=callbacks.on_quit,
        theme=theme,
    )
    file_btn = ghost_button(
        toolbar_row,
        "Файл ▾",
        command=lambda: show_popup_menu(file_btn, file_menu),
        theme=theme,
        width=72,
    )
    file_btn.pack(side="left")
    create_tooltip(file_btn, "Открыть, сохранить, выход", theme=theme)

    vertical_separator(toolbar_row, theme=theme, height=30).pack(side="left")

    lang_widget = CompactLanguageSelector(toolbar_row, languages, cfg, theme=theme)
    lang_widget.pack(side="left", fill="x", expand=True)

    vertical_separator(toolbar_row, theme=theme, height=30).pack(side="left")

    actions = transparent_frame(toolbar_row)
    actions.pack(side="right")

    streaming_enabled = tk.BooleanVar(value=settings.streaming)
    stream_cb = themed_checkbox(
        actions,
        "Поток",
        streaming_enabled,
        command=callbacks.on_stream_toggle,
        theme=theme,
        width=72,
    )
    stream_cb.pack(side="left")
    create_tooltip(stream_cb, "Автоперевод при вводе текста", theme=theme)

    scroll_sync_enabled = tk.BooleanVar(value=settings.scroll_sync)
    sync_cb = themed_checkbox(
        actions,
        "Синхр.",
        scroll_sync_enabled,
        command=callbacks.on_scroll_sync_toggle,
        theme=theme,
        width=72,
    )
    sync_cb.pack(side="left")
    create_tooltip(sync_cb, "Синхронная прокрутка исходника и перевода", theme=theme)

    translate_btn = primary_button(actions, "Перевод", callbacks.on_translate, theme=theme, width=96)
    translate_btn.pack(side="left")
    create_tooltip(translate_btn, "Перевести (Ctrl+Enter)", theme=theme)

    cancel_btn = ghost_button(actions, "Стоп", callbacks.on_cancel, theme=theme, width=64)
    cancel_btn.pack(side="left")
    create_tooltip(cancel_btn, "Остановить текущий перевод", theme=theme)

    settings_btn = icon_button(actions, "⚙", callbacks.on_open_settings, theme=theme, width=40)
    settings_btn.pack(side="left")
    create_tooltip(settings_btn, "Настройки (Ctrl+,)", theme=theme)

    panels = transparent_frame(main)
    panels.grid(row=1, column=0, sticky="nsew")
    panels.grid_columnconfigure(0, weight=1, uniform="editor_col")
    panels.grid_columnconfigure(1, weight=1, uniform="editor_col")
    panels.grid_rowconfigure(0, weight=1)

    src_panel = TextPanel(
        panels,
        "Исходный текст",
        editable=True,
        cfg=cfg,
        theme=theme,
        font_scale=font_scale,
    )
    src_panel.grid(row=0, column=0, sticky="nsew")
    try:
        src_panel.text.edit_modified(False)
    except Exception:
        pass
    src_panel.text.bind("<<Modified>>", callbacks.on_src_modified)

    translation_tabs = TranslationTabs(
        panels,
        cfg=cfg,
        llm_enabled=settings.llm.enabled,
        active_tab=settings.active_translation_tab,
        extra_buttons=[("Копир. и скрыть", callbacks.on_copy_and_hide)],
        on_tab_changed=callbacks.on_tab_changed,
        theme=theme,
        font_scale=font_scale,
    )
    translation_tabs.grid(row=0, column=1, sticky="nsew")

    translate_status_var = tk.StringVar(value="")

    status_card = card_frame(main, theme=theme)
    status_card.grid(row=2, column=0, sticky="ew", pady=(ELEMENT_GAP, 0))
    status_inner = transparent_frame(status_card)
    status_inner.pack(fill="x", padx=CARD_PADX, pady=CARD_PADY)
    status_inner.grid_columnconfigure(0, weight=1)

    status_var = tk.StringVar(value="Готов к работе")
    status_label = ctk.CTkLabel(
        status_inner,
        textvariable=status_var,
        font=scaled_ui_font(font_scale, 11),
        text_color=colors["text_primary"],
        anchor="w",
    )
    status_label.grid(row=0, column=0, sticky="w")

    llm_indicator_var = tk.StringVar(value="")
    llm_indicator = ctk.CTkLabel(
        status_inner,
        textvariable=llm_indicator_var,
        font=scaled_ui_font(font_scale, 11),
        text_color=colors["text_muted"],
    )
    llm_indicator.grid(row=0, column=1, sticky="e")

    hints_label = ctk.CTkLabel(
        status_inner,
        text="Ctrl+Enter · Ctrl+, · Ctrl+Shift+C",
        font=scaled_ui_font(font_scale, 11),
        text_color=colors["text_muted"],
    )
    hints_label.grid(row=0, column=2, sticky="e")

    file_progress_frame = transparent_frame(status_inner)
    file_progress_frame.grid(row=0, column=3, sticky="e")
    file_progress_frame.grid_remove()

    file_progress = ctk.CTkProgressBar(
        file_progress_frame,
        width=PROGRESS_WIDTH,
        height=PROGRESS_HEIGHT,
        progress_color=colors["progress_fill"],
        fg_color=colors["progress_bg"],
        corner_radius=0,
    )
    file_progress.pack()
    file_progress.set(0)

    file_progress_var = tk.StringVar(value="")
    file_progress_label = ctk.CTkLabel(
        status_inner,
        textvariable=file_progress_var,
        font=scaled_ui_font(font_scale, 11),
        text_color=colors["text_muted"],
        anchor="w",
    )
    file_progress_label.grid(row=1, column=0, columnspan=4, sticky="w")
    file_progress_label.grid_remove()

    return MainWindowView(
        main_frame=main,
        lang_widget=lang_widget,
        src_panel=src_panel,
        translation_tabs=translation_tabs,
        streaming_enabled=streaming_enabled,
        scroll_sync_enabled=scroll_sync_enabled,
        translate_status_var=translate_status_var,
        status_var=status_var,
        llm_indicator_var=llm_indicator_var,
        llm_indicator=llm_indicator,
        file_progress=file_progress,
        file_progress_var=file_progress_var,
        file_progress_label=file_progress_label,
        file_progress_frame=file_progress_frame,
        status_label=status_label,
        hints_label=hints_label,
    )
