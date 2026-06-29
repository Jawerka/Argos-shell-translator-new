"""Всплывающее меню «Файл» (без menubar)."""

from __future__ import annotations

import sys
import tkinter as tk
from typing import Callable

import customtkinter as ctk

from argos_translator.ui.themes import ThemeName, apply_menu_theme, style_menu

# Segoe MDL2 Assets (Windows): E7C3 Page — лист с загнутым углом; E8E5 OpenFile — документ со строками.
_FILE_MENU_GLYPH_WIN = "\uE7C3"
_FILE_MENU_GLYPH_FALLBACK = "\U0001F4C3"  # 📃 page with curl
_TOOLBAR_ICON_SIZE = 18


def file_menu_button_text() -> str:
    """Иконка «файл / документ» для кнопки меню."""
    if sys.platform == "win32":
        return _FILE_MENU_GLYPH_WIN
    return _FILE_MENU_GLYPH_FALLBACK


def file_menu_button_font() -> ctk.CTkFont:
    if sys.platform == "win32":
        return ctk.CTkFont(family="Segoe MDL2 Assets", size=_TOOLBAR_ICON_SIZE)
    return ctk.CTkFont(size=_TOOLBAR_ICON_SIZE)


def create_toolbar_more_menu(
    root: ctk.CTk,
    *,
    streaming_var: tk.BooleanVar,
    scroll_sync_var: tk.BooleanVar,
    on_stream_toggle: Callable[[], None],
    on_scroll_sync_toggle: Callable[[], None],
    theme: ThemeName = "dark",
) -> tk.Menu:
    """Меню «Ещё»: потоковый перевод и синхронизация прокрутки."""
    apply_menu_theme(root, theme)
    menu = tk.Menu(root, tearoff=0)
    style_menu(menu, theme)
    menu.add_checkbutton(
        label="Потоковый перевод",
        variable=streaming_var,
        command=on_stream_toggle,
    )
    menu.add_checkbutton(
        label="Синхронизация прокрутки",
        variable=scroll_sync_var,
        command=on_scroll_sync_toggle,
    )
    return menu


def create_file_popup_menu(
    root: ctk.CTk,
    *,
    on_open: Callable[[], None],
    on_save_translation: Callable[[], None],
    on_save_both: Callable[[], None],
    on_quit: Callable[[], None],
    theme: ThemeName = "dark",
) -> tk.Menu:
    apply_menu_theme(root, theme)
    menu = tk.Menu(root, tearoff=0)
    style_menu(menu, theme)
    menu.add_command(label="Открыть…", command=on_open, accelerator="Ctrl+O")
    menu.add_command(
        label="Сохранить перевод…",
        command=on_save_translation,
        accelerator="Ctrl+Shift+S",
    )
    menu.add_command(label="Сохранить оба…", command=on_save_both)
    menu.add_separator()
    menu.add_command(label="Выход", command=on_quit)
    return menu


def show_popup_menu(anchor: ctk.CTkBaseClass, menu: tk.Menu) -> None:
    try:
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height()
        menu.tk_popup(x, y)
    finally:
        menu.grab_release()


def clear_window_menubar(root: ctk.CTk) -> None:
    try:
        root.configure(menu="")
    except Exception:
        pass
