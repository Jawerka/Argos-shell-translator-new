"""Всплывающие подсказки для элементов интерфейса."""

from __future__ import annotations

from typing import Optional

import customtkinter as ctk

from argos_translator.ui.themes import ThemeName, get_color_theme

TOOLTIP_DELAY_MS = 600


class Tooltip:
    def __init__(
        self,
        widget: ctk.CTkBaseClass,
        text: str,
        delay: int = TOOLTIP_DELAY_MS,
        theme: ThemeName = "dark",
    ) -> None:
        self.widget = widget
        self.text = text
        self.delay = delay
        colors = get_color_theme(theme)
        self._bg = str(colors["bg_card"])
        self._border = str(colors["border"])
        self._fg = str(colors["text_primary"])
        self.tip_window: Optional[ctk.CTkToplevel] = None
        self._job: Optional[str] = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<Button>", self._hide, add="+")
        widget.bind("<Destroy>", self._on_destroy, add="+")

    def _schedule(self, _event=None) -> None:
        self._unschedule()
        self._job = self.widget.after(self.delay, self._show)

    def _unschedule(self) -> None:
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None

    def _show(self) -> None:
        if self.tip_window or not self.text:
            return
        x = self.widget.winfo_rootx()
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.wm_attributes("-topmost", True)
        frame = ctk.CTkFrame(
            tw,
            fg_color=self._bg,
            corner_radius=0,
            border_width=1,
            border_color=self._border,
        )
        frame.pack(fill="both", expand=True)
        ctk.CTkLabel(
            frame,
            text=self.text,
            text_color=self._fg,
            font=ctk.CTkFont(size=11),
            padx=6,
            pady=2,
        ).pack()

    def _hide(self, _event=None) -> None:
        self._unschedule()
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None

    def _on_destroy(self, _event=None) -> None:
        self._unschedule()
        self._hide()


def create_tooltip(
    widget: ctk.CTkBaseClass,
    text: str,
    theme: ThemeName = "dark",
    delay: int = TOOLTIP_DELAY_MS,
) -> Tooltip:
    return Tooltip(widget, text, delay=delay, theme=theme)
