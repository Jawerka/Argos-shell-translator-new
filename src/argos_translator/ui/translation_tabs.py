"""Вкладки перевода Argos / LLM — CustomTkinter."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox
from typing import Callable, Dict, List, Optional, Tuple

import customtkinter as ctk

from argos_translator.config.constants import UIConfig
from argos_translator.ui.editor_layout import EditorLayout
from argos_translator.ui.font_scale import scaled_text_font, ui_font
from argos_translator.ui.layout_config import (
    BTN_ICON_WIDTH,
    BUTTON_GAP,
    CARD_PADX,
    CARD_PADY,
    CHECKBOX_COMPACT_SIZE,
    HEADER_CONTROLS_GAP,
    PANEL_BUTTON_ROW_HEIGHT,
    PANEL_HEADER_HEIGHT,
    PANEL_TAB_ROW_HEIGHT,
    RADIUS_CONTROL,
    get_text_inset_kwargs,
)
from argos_translator.ui.themes import ThemeName, get_color_theme, get_status_color
from argos_translator.ui.tooltip import create_tooltip
from argos_translator.ui.widgets import CardFrame, ghost_button, themed_checkbox, transparent_frame
from argos_translator.utils.imports import (
    ImportStatus,
    PYPERCLIP_MODULE,
    PYPERCLIP_STATUS,
)

logger = logging.getLogger("ArgosStreaming")

_STREAM_TAIL_THRESHOLD = 0.99

_TAB_KEYS = {"argos": "Argos", "llm": "LLM"}
_STATUS_DISPLAY = {
    "streaming": ("●", "busy"),
    "done": ("✓", "available"),
    "partial": ("!", "busy"),
    "error": ("✗", "error"),
    "offline": ("○", "offline"),
}


class TranslationTabs(CardFrame):
    """Правая панель: вкладки Argos / LLM."""

    def __init__(
        self,
        parent,
        cfg: Optional[UIConfig] = None,
        llm_enabled: bool = True,
        active_tab: str = "argos",
        extra_buttons: Optional[List[Tuple[str, Callable[..., object]]]] = None,
        on_tab_changed: Optional[Callable[[str], None]] = None,
        on_llm_stream_append: Optional[Callable[[], None]] = None,
        on_editor_layout_toggle: Optional[Callable[[], None]] = None,
        on_llm_enabled_changed: Optional[Callable[[bool], None]] = None,
        theme: ThemeName = "dark",
        font_scale: float = 1.0,
        **kwargs,
    ) -> None:
        super().__init__(parent, theme=theme, **kwargs)
        self.cfg = cfg or UIConfig()
        self.theme = theme
        self._font_scale = font_scale
        self._colors = get_color_theme(theme)
        self._llm_enabled = llm_enabled
        self._active_tab = active_tab if active_tab in ("argos", "llm") else "argos"
        self._on_tab_changed = on_tab_changed
        self._on_llm_stream_append = on_llm_stream_append
        self._on_editor_layout_toggle = on_editor_layout_toggle
        self._on_llm_enabled_changed = on_llm_enabled_changed
        self._editor_layout: EditorLayout = "split"
        self._llm_streaming = False
        self._tab_status: Dict[str, Optional[str]] = {"argos": None, "llm": None}
        self.extra_buttons = extra_buttons or []
        self._tab_name_map: Dict[str, str] = {}
        self._status_badges: Dict[str, ctk.CTkLabel] = {}
        self._argos_box: ctk.CTkTextbox
        self._llm_box: Optional[ctk.CTkTextbox] = None
        self._segmented: Optional[ctk.CTkSegmentedButton] = None
        self._llm_enable_var = tk.BooleanVar(value=llm_enabled)
        self._llm_enable_cb: Optional[ctk.CTkCheckBox] = None
        self._suppress_llm_enable_cb = False
        self.text_host: ctk.CTkFrame

        inner = transparent_frame(self)
        inner.pack(fill="both", expand=True, padx=CARD_PADX, pady=CARD_PADY)
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure(2, weight=1)

        header = ctk.CTkFrame(inner, height=PANEL_HEADER_HEIGHT, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)

        header_controls = transparent_frame(header)
        header_controls.pack(side="right")
        self._header_controls = header_controls
        gap = (0, HEADER_CONTROLS_GAP)

        if self._on_editor_layout_toggle is not None:
            self._layout_btn = ghost_button(
                header_controls,
                "⤢",
                self._on_editor_layout_toggle,
                theme=self.theme,
                width=BTN_ICON_WIDTH,
            )
            self._layout_btn.pack(side="left", padx=gap)
            create_tooltip(self._layout_btn, "На всю ширину", theme=self.theme)

        self._status_badges["argos"] = ctk.CTkLabel(
            header_controls,
            text=_TAB_KEYS["argos"],
            font=ui_font(),
            text_color=self._colors["text_muted"],
        )
        self._status_badges["argos"].pack(side="left", padx=gap)

        self._llm_enable_cb = themed_checkbox(
            header_controls,
            text="",
            variable=self._llm_enable_var,
            command=self._handle_llm_enable_toggle,
            theme=self.theme,
            width=CHECKBOX_COMPACT_SIZE,
            checkbox_width=CHECKBOX_COMPACT_SIZE,
            checkbox_height=CHECKBOX_COMPACT_SIZE,
        )
        self._llm_enable_cb.pack(side="left", padx=gap)
        create_tooltip(self._llm_enable_cb, "Использовать LLM-перевод", theme=self.theme)

        self._status_badges["llm"] = ctk.CTkLabel(
            header_controls,
            text=_TAB_KEYS["llm"],
            font=ui_font(),
            text_color=self._colors["text_muted"],
        )
        self._status_badges["llm"].pack(side="left")

        tab_row = ctk.CTkFrame(inner, height=PANEL_TAB_ROW_HEIGHT, fg_color="transparent")
        tab_row.grid(row=1, column=0, sticky="ew")
        tab_row.grid_propagate(False)
        self._tab_row = tab_row

        self.text_host = ctk.CTkFrame(inner, **get_text_inset_kwargs(self.theme))
        self.text_host.grid(row=2, column=0, sticky="nsew")
        self.text_host.grid_rowconfigure(0, weight=1)
        self.text_host.grid_columnconfigure(0, weight=1)

        self._register_tab("argos")
        self._argos_box = self._create_text_widget(self.text_host)
        self._argos_box.grid(row=0, column=0, sticky="nsew")

        if llm_enabled:
            self._register_tab("llm")
            self._llm_box = self._create_text_widget(self.text_host)
            self._llm_box.grid(row=0, column=0, sticky="nsew")
            self._build_segmented_button(tab_row)
        else:
            hidden = ctk.CTkFrame(self, fg_color="transparent")
            self._llm_box = self._create_text_widget(hidden)
            self._status_badges["llm"].pack_forget()

        btn_frame = ctk.CTkFrame(inner, height=PANEL_BUTTON_ROW_HEIGHT, fg_color="transparent")
        btn_frame.grid(row=3, column=0, sticky="ew")
        btn_frame.grid_propagate(False)
        btn_inner = transparent_frame(btn_frame)
        btn_inner.pack(fill="both", expand=True)

        self.copy_btn = ghost_button(btn_inner, "Копировать", self.copy_active, theme=self.theme, width=100)
        self.copy_btn.pack(side="left", padx=(0, BUTTON_GAP))
        ghost_button(btn_inner, "Очистить", self.clear_active, theme=self.theme, width=90).pack(
            side="left", padx=(0, BUTTON_GAP)
        )
        for btn_text, btn_command in self.extra_buttons:
            ghost_button(btn_inner, btn_text, btn_command, theme=self.theme, width=120).pack(
                side="left", padx=(0, BUTTON_GAP)
            )

        self._select_tab(self._active_tab)

    @property
    def argos_text(self) -> tk.Text:
        return self._argos_box._textbox

    @property
    def llm_text(self) -> Optional[tk.Text]:
        return self._llm_box._textbox if self._llm_box is not None else None

    @property
    def notebook(self):
        """Совместимость с тестами."""
        return self

    def tabs(self) -> list:
        return list(self._tab_name_map.keys())

    def set_editor_layout_state(self, mode: EditorLayout) -> None:
        self._editor_layout = mode
        if not hasattr(self, "_layout_btn"):
            return
        expanded = mode == "translation"
        self._layout_btn.configure(text="⤡" if expanded else "⤢")
        create_tooltip(
            self._layout_btn,
            "Две панели" if expanded else "На всю ширину",
            theme=self.theme,
        )

    def apply_font_scale(self, scale: float) -> None:
        self._font_scale = scale
        font = scaled_text_font(scale)
        self._argos_box.configure(font=font)
        if self._llm_box is not None:
            self._llm_box.configure(font=font)

    def _register_tab(self, engine: str) -> None:
        self._tab_name_map[engine] = _TAB_KEYS[engine]

    def _build_segmented_button(self, parent: ctk.CTkFrame) -> None:
        colors = self._colors
        values = [_TAB_KEYS[e] for e in ("argos", "llm") if e in self._tab_name_map]
        self._segmented = ctk.CTkSegmentedButton(
            parent,
            values=values,
            command=self._handle_segment_changed,
            height=PANEL_TAB_ROW_HEIGHT - 4,
            corner_radius=RADIUS_CONTROL,
            fg_color=colors["bg_secondary"],
            selected_color=colors["primary"],
            selected_hover_color=colors["primary_hover"],
            unselected_color=colors["accent"],
            unselected_hover_color=colors["accent_hover"],
            text_color=colors["text_primary"],
        )
        self._segmented.pack(fill="x", expand=True)

    def _create_text_widget(self, parent: ctk.CTkFrame) -> ctk.CTkTextbox:
        colors = self._colors
        widget = ctk.CTkTextbox(
            parent,
            font=scaled_text_font(self._font_scale),
            fg_color=colors["input"],
            text_color=colors["text_editor"],
            border_width=0,
            corner_radius=RADIUS_CONTROL,
            wrap="word",
            state="disabled",
        )
        return widget

    def _handle_segment_changed(self, selected: str) -> None:
        tab_id = "argos"
        for engine, name in self._tab_name_map.items():
            if name == selected:
                tab_id = engine
                break
        self._show_tab(tab_id)
        self._active_tab = tab_id
        if self._on_tab_changed:
            self._on_tab_changed(tab_id)

    def _show_tab(self, tab_id: str) -> None:
        if tab_id == "argos":
            self._argos_box.grid(row=0, column=0, sticky="nsew")
            if self._llm_box is not None and self._llm_enabled:
                self._llm_box.grid_remove()
        elif self._llm_box is not None and self._llm_enabled:
            self._llm_box.grid(row=0, column=0, sticky="nsew")
            self._argos_box.grid_remove()

    def _select_tab(self, tab_id: str) -> None:
        if tab_id == "llm" and not self._llm_enabled:
            tab_id = "argos"
        self._active_tab = tab_id
        self._show_tab(tab_id)
        if self._segmented is not None and tab_id in self._tab_name_map:
            try:
                self._segmented.set(self._tab_name_map[tab_id])
            except Exception:
                pass

    def _handle_llm_enable_toggle(self) -> None:
        if self._suppress_llm_enable_cb:
            return
        enabled = bool(self._llm_enable_var.get())
        if self._on_llm_enabled_changed:
            self._on_llm_enabled_changed(enabled)

    def set_llm_enabled(self, enabled: bool) -> None:
        self._suppress_llm_enable_cb = True
        try:
            self._llm_enable_var.set(enabled)
        finally:
            self._suppress_llm_enable_cb = False

        if enabled and not self._llm_enabled:
            self._register_tab("llm")
            self._llm_box = self._create_text_widget(self.text_host)
            self._llm_box.grid(row=0, column=0, sticky="nsew")
            self._llm_enabled = True
            self._status_badges["llm"].pack(side="left")
            if self._segmented is None:
                self._build_segmented_button(self._tab_row)
            else:
                self._segmented.configure(
                    values=[_TAB_KEYS[e] for e in ("argos", "llm") if e in self._tab_name_map]
                )
        elif not enabled and self._llm_enabled:
            if self._active_tab == "llm":
                self._select_tab("argos")
            self._tab_name_map.pop("llm", None)
            if self._llm_box is not None:
                self._llm_box.grid_remove()
            self._llm_enabled = False
            self._status_badges["llm"].pack_forget()
            if self._segmented is not None:
                self._segmented.configure(values=[_TAB_KEYS["argos"]])
                self._segmented.set(_TAB_KEYS["argos"])

    def set_tab_status(self, engine: str, status: Optional[str]) -> None:
        self._tab_status[engine] = status
        badge = self._status_badges.get(engine)
        if badge is None:
            return
        label = _TAB_KEYS.get(engine, engine)
        if not status or status not in _STATUS_DISPLAY:
            badge.configure(text=label, text_color=self._colors["text_muted"])
            return
        symbol, kind = _STATUS_DISPLAY[status]
        badge.configure(
            text=f"{label} {symbol}",
            text_color=get_status_color(self.theme, kind),
        )

    def get_active_engine(self) -> str:
        return self._active_tab

    def get_active_text_widget(self) -> tk.Text:
        box = self._argos_box if self._active_tab == "argos" else self._llm_box
        assert box is not None
        return box._textbox

    @property
    def text(self) -> tk.Text:
        return self.get_active_text_widget()

    @staticmethod
    def _is_view_at_bottom(tk_text: tk.Text, threshold: float = _STREAM_TAIL_THRESHOLD) -> bool:
        try:
            return float(tk_text.yview()[1]) >= threshold
        except Exception:
            return False

    def _append_box_stream_delta(self, box: ctk.CTkTextbox, text: str) -> bool:
        """Дописать дельту в конец без полной перезаписи. Возвращает True, если текст изменился."""
        tk_text = box._textbox
        try:
            current = box.get("1.0", "end-1c")
            if text == current:
                return False
            at_bottom = self._is_view_at_bottom(tk_text)
            if not text.startswith(current):
                box.delete("1.0", "end")
                if text:
                    box.insert("1.0", text)
                if at_bottom:
                    tk_text.see("end")
                return True
            delta = text[len(current) :]
            if not delta:
                return False
            tk_text.insert("end", delta)
            if at_bottom:
                tk_text.see("end")
            return True
        except Exception as exc:
            logger.warning("stream append failed: %s", exc)
            return False

    def _set_box_text(self, box: ctk.CTkTextbox, text: str) -> None:
        """Обновление через CTkTextbox API (не напрямую _textbox)."""
        tk_text = box._textbox
        try:
            try:
                cur_frac = float(tk_text.yview()[0])
            except Exception:
                cur_frac = 0.0
            try:
                old_text = box.get("1.0", "end-1c")
                old_len = max(1, len(old_text))
            except Exception:
                old_len = 1
            old_pos_chars = int(cur_frac * (old_len - 1)) if old_len > 1 else 0

            box.configure(state="normal")
            box.delete("1.0", "end")
            if text:
                box.insert("1.0", text)
            box.configure(state="disabled")

            try:
                new_len = max(1, len(box.get("1.0", "end-1c")))
            except Exception:
                new_len = 1
            new_frac = old_pos_chars / (new_len - 1) if new_len > 1 else 0.0
            tk_text.yview_moveto(max(0.0, min(1.0, new_frac)))
        except Exception as exc:
            logger.warning("set translation text failed: %s", exc)

    def _get_box_text(self, box: ctk.CTkTextbox) -> str:
        tk_text = box._textbox
        try:
            was_disabled = str(tk_text.cget("state")) == "disabled"
        except Exception:
            was_disabled = True
        if was_disabled:
            box.configure(state="normal")
        text = box.get("1.0", "end-1c").strip()
        if was_disabled:
            box.configure(state="disabled")
        return text

    def set_argos_text(self, text: str) -> None:
        self._set_box_text(self._argos_box, text)

    def set_llm_text(self, text: str) -> None:
        if self._llm_box is not None:
            if self._llm_streaming:
                self.end_llm_stream(final_text=text)
            else:
                self._set_box_text(self._llm_box, text)

    def begin_llm_stream(self) -> None:
        if self._llm_box is None:
            return
        try:
            self._llm_streaming = True
            self._llm_box.configure(state="normal")
            self._llm_box.delete("1.0", "end")
        except Exception as exc:
            logger.warning("begin LLM stream failed: %s", exc)
            self._llm_streaming = False

    def append_llm_stream_text(self, text: str) -> None:
        if self._llm_box is None:
            return
        if not self._llm_streaming:
            self.set_llm_text(text)
            return
        if self._append_box_stream_delta(self._llm_box, text) and self._on_llm_stream_append:
            self._on_llm_stream_append()

    def end_llm_stream(self, final_text: Optional[str] = None) -> None:
        if self._llm_box is None:
            self._llm_streaming = False
            return
        try:
            if final_text is not None:
                current = self._llm_box.get("1.0", "end-1c")
                if final_text != current:
                    if self._llm_streaming:
                        self._append_box_stream_delta(self._llm_box, final_text)
                    else:
                        self._set_box_text(self._llm_box, final_text)
            self._llm_box.configure(state="disabled")
        except Exception as exc:
            logger.warning("end LLM stream failed: %s", exc)
        finally:
            self._llm_streaming = False

    def get_active_text(self) -> str:
        box = self._argos_box if self._active_tab == "argos" else self._llm_box
        if box is None:
            return ""
        return self._get_box_text(box)

    def get_argos_text(self) -> str:
        return self._get_box_text(self._argos_box)

    def get_llm_text(self) -> str:
        if self._llm_box is None:
            return ""
        return self._get_box_text(self._llm_box)

    def clear_argos(self) -> None:
        self._set_box_text(self._argos_box, "")

    def clear_llm(self) -> None:
        if self._llm_box is not None:
            if self._llm_streaming:
                self.end_llm_stream(final_text="")
            else:
                self._set_box_text(self._llm_box, "")

    def clear_active(self) -> None:
        if self._active_tab == "argos":
            self.clear_argos()
        else:
            self.clear_llm()

    def clear_all(self) -> None:
        self.clear_argos()
        self.clear_llm()

    def copy_active(self) -> None:
        if PYPERCLIP_STATUS != ImportStatus.SUCCESS or PYPERCLIP_MODULE is None:
            messagebox.showwarning(
                "Буфер обмена",
                "Установите pyperclip для работы с буфером обмена",
            )
            return
        text = self.get_active_text()
        if not text:
            return
        try:
            PYPERCLIP_MODULE.copy(text)
            original = self.copy_btn.cget("text")
            self.copy_btn.configure(text="Скопировано!")
            self.after(1000, lambda: self.copy_btn.configure(text=original))
        except Exception as exc:
            logger.error("Copy error: %s", exc)
            messagebox.showerror("Ошибка", f"Не удалось скопировать: {exc}")

    def set_active_tab(self, tab_id: str) -> None:
        self._select_tab(tab_id)
