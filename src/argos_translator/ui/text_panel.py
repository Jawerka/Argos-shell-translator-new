"""Текстовая панель (источник / перевод) — CustomTkinter."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Any, Callable, List, Optional, Tuple

import customtkinter as ctk

from argos_translator.config.constants import UIConfig
from argos_translator.ui.editor_layout import EditorLayout
from argos_translator.ui.font_scale import scaled_text_font, ui_font
from argos_translator.ui.layout_config import (
    CARD_PADX,
    CARD_PADY,
    PANEL_BUTTON_ROW_HEIGHT,
    PANEL_HEADER_HEIGHT,
    PANEL_TAB_ROW_HEIGHT,
    RADIUS_CONTROL,
    get_text_inset_kwargs,
)
from argos_translator.ui.themes import ThemeName, get_color_theme
from argos_translator.ui.tooltip import create_tooltip
from argos_translator.ui.widgets import CardFrame, ghost_button, panel_title_label, transparent_frame
from argos_translator.utils.imports import (
    ImportStatus,
    PYPERCLIP_MODULE,
    PYPERCLIP_STATUS,
)

logger = logging.getLogger("ArgosStreaming")


class TextPanel(CardFrame):
    """Карточка с заголовком и текстовым полем."""

    def __init__(
        self,
        parent,
        title: str,
        editable: bool = True,
        extra_buttons: Optional[List[Tuple[str, Callable[..., Any]]]] = None,
        cfg: Optional[UIConfig] = None,
        theme: ThemeName = "dark",
        font_scale: float = 1.0,
        show_char_count: bool = False,
        on_editor_layout_toggle: Optional[Callable[[], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(parent, theme=theme, **kwargs)
        self.title = title
        self.editable = editable
        self.extra_buttons = extra_buttons or []
        self.cfg = cfg or UIConfig()
        self.theme = theme
        self._font_scale = font_scale
        self._colors = get_color_theme(theme)
        self._show_char_count = show_char_count and editable
        self._on_editor_layout_toggle = on_editor_layout_toggle
        self._editor_layout: EditorLayout = "split"
        self._char_count_job: Optional[str] = None
        self.text_host: ctk.CTkFrame
        self._char_count_label: Optional[ctk.CTkLabel] = None
        self._create_widgets()

    def _create_widgets(self) -> None:
        colors = self._colors
        inner = transparent_frame(self)
        inner.pack(fill="both", expand=True, padx=CARD_PADX, pady=CARD_PADY)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(inner, height=PANEL_HEADER_HEIGHT, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header_inner = transparent_frame(header)
        header_inner.pack(fill="both", expand=True)

        self._title_label: Optional[ctk.CTkLabel] = None
        if self.title:
            self._title_label = panel_title_label(
                header_inner,
                self.title,
                theme=self.theme,
                font=ui_font(weight="bold"),
            )
            self._title_label.pack(side="left", anchor="w")

        header_controls = transparent_frame(header_inner)
        header_controls.pack(side="right", anchor="e")

        if self._on_editor_layout_toggle is not None:
            self._layout_btn = ghost_button(
                header_controls,
                "⤢",
                self._on_editor_layout_toggle,
                theme=self.theme,
                width=32,
            )
            self._layout_btn.pack(side="left", padx=(0, 6))
            create_tooltip(self._layout_btn, "На всю ширину", theme=self.theme)

        if self._show_char_count:
            self._char_count_label = ctk.CTkLabel(
                header_controls,
                text="0 симв.",
                font=ui_font(),
                text_color=colors["text_muted"],
            )
            self._char_count_label.pack(side="left", anchor="e")

        tab_row = ctk.CTkFrame(inner, height=PANEL_TAB_ROW_HEIGHT, fg_color="transparent")
        tab_row.grid(row=1, column=0, sticky="ew")
        tab_row.grid_propagate(False)

        self.text_host = ctk.CTkFrame(inner, **get_text_inset_kwargs(self.theme))
        self.text_host.grid(row=2, column=0, sticky="nsew")
        self.text_host.grid_rowconfigure(0, weight=1)
        self.text_host.grid_columnconfigure(0, weight=1)

        self._ctk_text = ctk.CTkTextbox(
            self.text_host,
            font=scaled_text_font(self._font_scale),
            fg_color=colors["input"],
            text_color=colors["text_editor"],
            border_width=0,
            corner_radius=RADIUS_CONTROL,
            wrap="word",
        )
        self._ctk_text.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)

        self.text = self._ctk_text._textbox

        if not self.editable:
            self._ctk_text.configure(state="disabled")
        elif self._show_char_count:
            self.text.bind("<<Modified>>", self._schedule_char_count_update, add="+")
            self._update_char_count()

        btn_frame = ctk.CTkFrame(inner, height=PANEL_BUTTON_ROW_HEIGHT, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew")
        btn_frame.grid_propagate(False)
        btn_inner = transparent_frame(btn_frame)
        btn_inner.pack(fill="both", expand=True)

        if self.editable:
            ghost_button(btn_inner, "Вставить", self.paste_from_clipboard, theme=self.theme, width=90).pack(
                side="left"
            )
            ghost_button(btn_inner, "Очистить", self.clear, theme=self.theme, width=90).pack(side="left")
        else:
            self.copy_btn = ghost_button(btn_inner, "Копировать", self.copy_to_clipboard, theme=self.theme, width=100)
            self.copy_btn.pack(side="left")
            ghost_button(btn_inner, "Очистить", self.clear, theme=self.theme, width=90).pack(side="left")
            for btn_text, btn_command in self.extra_buttons:
                ghost_button(btn_inner, btn_text, btn_command, theme=self.theme, width=120).pack(side="left")

    def _schedule_char_count_update(self, _event: Optional[tk.Event] = None) -> None:
        if self._char_count_job:
            try:
                self.after_cancel(self._char_count_job)
            except Exception:
                pass
        self._char_count_job = self.after(120, self._update_char_count)

    def _update_char_count(self) -> None:
        self._char_count_job = None
        if self._char_count_label is None:
            return
        try:
            text = self._ctk_text.get("1.0", "end-1c")
            count = len(text)
            self._char_count_label.configure(text=f"{count} симв.")
        except Exception:
            pass

    def set_editor_layout_state(self, mode: EditorLayout) -> None:
        self._editor_layout = mode
        if not hasattr(self, "_layout_btn"):
            return
        expanded = mode == "source"
        self._layout_btn.configure(text="⤡" if expanded else "⤢")
        create_tooltip(
            self._layout_btn,
            "Две панели" if expanded else "На всю ширину",
            theme=self.theme,
        )

    def apply_font_scale(self, scale: float) -> None:
        self._font_scale = scale
        self._ctk_text.configure(font=scaled_text_font(scale))

    def get_text(self) -> str:
        if self.editable:
            return self._ctk_text.get("1.0", "end-1c").strip()
        self._ctk_text.configure(state="normal")
        text = self._ctk_text.get("1.0", "end-1c").strip()
        self._ctk_text.configure(state="disabled")
        return text

    def set_text(self, text: str) -> None:
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
                old_text = self._ctk_text.get("1.0", "end-1c")
                old_len = max(1, len(old_text))
            except Exception:
                old_len = 1
            old_pos_chars = int(cur_frac * (old_len - 1)) if old_len > 1 else 0

            self._ctk_text.configure(state="normal")
            self._ctk_text.delete("1.0", "end")
            self._ctk_text.insert("1.0", text)
            if not self.editable:
                self._ctk_text.configure(state="disabled")

            try:
                new_text = self._ctk_text.get("1.0", "end-1c")
                new_len = max(1, len(new_text))
            except Exception:
                new_len = 1
            new_frac = old_pos_chars / (new_len - 1) if new_len > 1 else 0.0
            new_frac = max(0.0, min(1.0, new_frac))
            try:
                self.text.mark_set(tk.INSERT, insert_index)
            except Exception:
                pass
            try:
                self.text.yview_moveto(new_frac)
            except Exception:
                pass
            if self._show_char_count:
                self._update_char_count()
        except Exception as exc:
            logger.debug("set_text error: %s", exc)

    def paste_from_clipboard(self) -> None:
        if PYPERCLIP_STATUS != ImportStatus.SUCCESS or PYPERCLIP_MODULE is None:
            messagebox.showwarning(
                "Буфер обмена",
                "Установите pyperclip для работы с буфером обмена",
            )
            return
        try:
            clip_text = PYPERCLIP_MODULE.paste()
            if clip_text:
                self._ctk_text.insert(tk.INSERT, clip_text)
        except Exception as exc:
            logger.error("Paste error: %s", exc)
            messagebox.showerror("Ошибка", f"Не удалось вставить: {exc}")

    def copy_to_clipboard(self) -> None:
        if PYPERCLIP_STATUS != ImportStatus.SUCCESS or PYPERCLIP_MODULE is None:
            messagebox.showwarning(
                "Буфер обмена",
                "Установите pyperclip для работы с буфером обмена",
            )
            return
        text = self.get_text()
        if not text:
            return
        try:
            PYPERCLIP_MODULE.copy(text)
            if hasattr(self, "copy_btn"):
                original_text = self.copy_btn.cget("text")
                self.copy_btn.configure(text="Скопировано!")
                self.after(1000, lambda: self.copy_btn.configure(text=original_text))
        except Exception as exc:
            logger.error("Copy error: %s", exc)
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {exc}")

    def clear(self) -> None:
        self._ctk_text.configure(state="normal")
        self._ctk_text.delete("1.0", "end")
        if not self.editable:
            self._ctk_text.configure(state="disabled")
        if self._show_char_count:
            self._update_char_count()
