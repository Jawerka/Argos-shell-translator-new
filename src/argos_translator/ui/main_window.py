"""Построение главного окна (CustomTkinter, structured flat v2.1)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

import customtkinter as ctk
import tkinter as tk

from argos_translator.config.constants import UIConfig
from argos_translator.config.settings import AppSettings
from argos_translator.ui.editor_layout import EditorLayout, apply_editor_layout, normalize_editor_layout
from argos_translator.ui.file_menu import (
    clear_window_menubar,
    create_file_popup_menu,
    create_toolbar_more_menu,
    file_menu_button_font,
    file_menu_button_text,
    show_popup_menu,
)
from argos_translator.ui.language_selector import CompactLanguageSelector
from argos_translator.ui.font_scale import ui_font
from argos_translator.ui.layout_config import (
    BUTTON_GAP,
    CARD_PADX,
    CARD_PADY,
    ELEMENT_GAP,
    FOOTER_FONT_SIZE,
    FOOTER_PADX,
    FOOTER_PADY,
    TOOLBAR_HEIGHT,
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
    transparent_frame,
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
    on_llm_stream_append: Callable[[], None]
    on_editor_layout_changed: Callable[[str], None]
    on_llm_enabled_changed: Callable[[bool], None]


@dataclass
class MainWindowView:
    main_frame: ctk.CTkFrame
    panels: ctk.CTkFrame
    lang_widget: CompactLanguageSelector
    src_panel: TextPanel
    translation_tabs: TranslationTabs
    streaming_enabled: tk.BooleanVar
    scroll_sync_enabled: tk.BooleanVar
    translate_status_var: tk.StringVar
    status_var: tk.StringVar
    llm_indicator_var: tk.StringVar
    llm_indicator: ctk.CTkLabel
    file_progress_var: tk.StringVar
    file_progress_label: ctk.CTkLabel
    file_progress_frame: ctk.CTkFrame
    status_label: ctk.CTkLabel


def apply_editor_font_scale(view: MainWindowView, scale: float) -> None:
    view.src_panel.apply_font_scale(scale)
    view.translation_tabs.apply_font_scale(scale)


def set_editor_layout(view: MainWindowView, mode: EditorLayout) -> None:
    apply_editor_layout(
        view.panels,
        view.src_panel,
        view.translation_tabs,
        mode,
        gap=ELEMENT_GAP,
    )
    view.src_panel.set_editor_layout_state(mode)
    view.translation_tabs.set_editor_layout_state(mode)


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
    editor_layout = normalize_editor_layout(settings.editor_layout)

    clear_window_menubar(root)

    main = transparent_frame(root)
    main.grid(row=0, column=0, sticky="nsew", padx=WINDOW_PADX, pady=WINDOW_PADY)
    main.grid_columnconfigure(0, weight=1)
    main.grid_rowconfigure(1, weight=1)

    toolbar = card_frame(main, theme=theme)
    toolbar.grid(row=0, column=0, sticky="ew", pady=(0, ELEMENT_GAP))
    toolbar_inner = transparent_frame(toolbar)
    toolbar_inner.pack(fill="x", padx=CARD_PADX, pady=CARD_PADY)
    toolbar_inner.grid_columnconfigure(1, weight=1)

    toolbar_left = transparent_frame(toolbar_inner)
    toolbar_left.grid(row=0, column=0, sticky="w")

    toolbar_center = transparent_frame(toolbar_inner)
    toolbar_center.grid(row=0, column=1, sticky="ew", padx=(BUTTON_GAP, BUTTON_GAP))
    toolbar_center.grid_columnconfigure(0, weight=1)

    toolbar_right = transparent_frame(toolbar_inner)
    toolbar_right.grid(row=0, column=2, sticky="e")

    file_menu = create_file_popup_menu(
        root,
        on_open=callbacks.on_file_open,
        on_save_translation=callbacks.on_file_save_translation,
        on_save_both=callbacks.on_file_save_both,
        on_quit=callbacks.on_quit,
        theme=theme,
    )
    file_btn = icon_button(
        toolbar_left,
        file_menu_button_text(),
        command=lambda: show_popup_menu(file_btn, file_menu),
        theme=theme,
        width=40,
        font=file_menu_button_font(),
    )
    file_btn.pack(side="left")
    create_tooltip(file_btn, "Файл: открыть, сохранить, выход", theme=theme)

    lang_widget = CompactLanguageSelector(toolbar_center, languages, cfg, theme=theme)
    lang_widget.grid(row=0, column=0, sticky="ew")

    streaming_enabled = tk.BooleanVar(value=settings.streaming)
    scroll_sync_enabled = tk.BooleanVar(value=settings.scroll_sync)

    more_menu = create_toolbar_more_menu(
        root,
        streaming_var=streaming_enabled,
        scroll_sync_var=scroll_sync_enabled,
        on_stream_toggle=callbacks.on_stream_toggle,
        on_scroll_sync_toggle=callbacks.on_scroll_sync_toggle,
        theme=theme,
    )
    more_btn = ghost_button(
        toolbar_right,
        "Ещё ▾",
        command=lambda: show_popup_menu(more_btn, more_menu),
        theme=theme,
        width=64,
    )
    more_btn.pack(side="left", padx=(0, BUTTON_GAP))
    create_tooltip(
        more_btn,
        "Потоковый перевод и синхронизация прокрутки",
        theme=theme,
    )

    translate_btn = primary_button(
        toolbar_right, "Перевести", callbacks.on_translate, theme=theme, width=100
    )
    translate_btn.pack(side="left", padx=(0, BUTTON_GAP))
    create_tooltip(translate_btn, "Перевести (Ctrl+Enter)", theme=theme)

    cancel_btn = ghost_button(
        toolbar_right, "Стоп", callbacks.on_cancel, theme=theme, width=72
    )
    cancel_btn.pack(side="left", padx=(0, BUTTON_GAP))
    create_tooltip(cancel_btn, "Остановить текущий перевод", theme=theme)

    settings_btn = icon_button(toolbar_right, "⚙", callbacks.on_open_settings, theme=theme, width=40)
    settings_btn.pack(side="left")
    create_tooltip(settings_btn, "Настройки (Ctrl+,)", theme=theme)

    try:
        toolbar.configure(height=TOOLBAR_HEIGHT)
    except Exception:
        pass

    panels = transparent_frame(main)
    panels.grid(row=1, column=0, sticky="nsew")
    panels.grid_columnconfigure(0, weight=1, uniform="editor_col")
    panels.grid_columnconfigure(1, weight=1, uniform="editor_col")
    panels.grid_rowconfigure(0, weight=1)

    src_panel = TextPanel(
        panels,
        "",
        editable=True,
        cfg=cfg,
        theme=theme,
        font_scale=font_scale,
        show_char_count=True,
        on_editor_layout_toggle=lambda: callbacks.on_editor_layout_changed("source"),
    )
    src_panel.grid(row=0, column=0, sticky="nsew", padx=(0, ELEMENT_GAP // 2))
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
        on_llm_stream_append=callbacks.on_llm_stream_append,
        on_editor_layout_toggle=lambda: callbacks.on_editor_layout_changed("translation"),
        on_llm_enabled_changed=callbacks.on_llm_enabled_changed,
        theme=theme,
        font_scale=font_scale,
    )
    translation_tabs.grid(row=0, column=1, sticky="nsew", padx=(ELEMENT_GAP // 2, 0))

    translate_status_var = tk.StringVar(value="")

    footer = transparent_frame(main)
    footer.grid(row=2, column=0, sticky="ew", pady=(4, 0))
    footer_inner = transparent_frame(footer)
    footer_inner.pack(fill="x", padx=FOOTER_PADX, pady=FOOTER_PADY)

    status_var = tk.StringVar(value="Готов к работе")
    footer_font = ui_font(FOOTER_FONT_SIZE)
    status_label = ctk.CTkLabel(
        footer_inner,
        textvariable=status_var,
        font=footer_font,
        text_color=colors["text_muted"],
        anchor="w",
    )
    status_label.pack(side="left", fill="x", expand=True)
    create_tooltip(
        status_label,
        "Ctrl+Enter — перевод · Ctrl+, — настройки · Ctrl+Shift+C — захват текста",
        theme=theme,
    )

    file_progress_frame = transparent_frame(footer_inner)
    file_progress_frame.pack(side="right")
    file_progress_frame.pack_forget()

    file_progress_var = tk.StringVar(value="")
    file_progress_label = ctk.CTkLabel(
        file_progress_frame,
        textvariable=file_progress_var,
        font=footer_font,
        text_color=colors["text_muted"],
    )
    file_progress_label.pack(side="right", padx=(8, 0))

    llm_indicator_var = tk.StringVar(value="")
    llm_indicator = ctk.CTkLabel(
        footer_inner,
        textvariable=llm_indicator_var,
        font=footer_font,
        text_color=colors["text_muted"],
        anchor="e",
    )
    llm_indicator.pack(side="right", padx=(8, 0))

    view = MainWindowView(
        main_frame=main,
        panels=panels,
        lang_widget=lang_widget,
        src_panel=src_panel,
        translation_tabs=translation_tabs,
        streaming_enabled=streaming_enabled,
        scroll_sync_enabled=scroll_sync_enabled,
        translate_status_var=translate_status_var,
        status_var=status_var,
        llm_indicator_var=llm_indicator_var,
        llm_indicator=llm_indicator,
        file_progress_var=file_progress_var,
        file_progress_label=file_progress_label,
        file_progress_frame=file_progress_frame,
        status_label=status_label,
    )
    set_editor_layout(view, editor_layout)
    return view
