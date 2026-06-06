"""Компактный селектор языков (CustomTkinter)."""

from __future__ import annotations

from typing import Dict, List

import customtkinter as ctk

from argos_translator.config.constants import UIConfig
from argos_translator.ui.layout_config import BTN_HEIGHT_SM, BUTTON_GAP, COMBO_WIDTH, UI_FONT_FAMILY, get_combobox_kwargs
from argos_translator.ui.themes import ThemeName, get_color_theme
from argos_translator.ui.tooltip import create_tooltip
from argos_translator.ui.widgets import accent_button, TransparentFrame


class CompactLanguageSelector(TransparentFrame):
    def __init__(
        self,
        parent,
        languages: Dict[str, str],
        cfg: UIConfig | None = None,
        theme: ThemeName = "dark",
        **kwargs,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.languages = languages
        self.cfg = cfg or UIConfig()
        self.theme = theme
        self._colors = get_color_theme(theme)
        self._create_widgets()

    def _create_widgets(self) -> None:
        colors = self._colors
        label_font = ctk.CTkFont(family=UI_FONT_FAMILY, size=12)
        combo_kw = get_combobox_kwargs(self.theme)

        self.grid_columnconfigure(1, weight=1)
        self.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(self, text="Из", font=label_font, text_color=colors["text_muted"]).grid(
            row=0, column=0, padx=(0, BUTTON_GAP)
        )

        self.var_from = ctk.StringVar(value="AUTO")
        self.combo_from = ctk.CTkComboBox(
            self,
            variable=self.var_from,
            values=["AUTO"] + self._get_language_options(),
            width=COMBO_WIDTH,
            state="readonly",
            button_color=colors["accent"],
            button_hover_color=colors["accent_hover"],
            dropdown_fg_color=colors["bg_card"],
            dropdown_hover_color=colors["accent_hover"],
            font=label_font,
            **combo_kw,
        )
        self.combo_from.grid(row=0, column=1, sticky="ew", padx=(0, BUTTON_GAP))

        ctk.CTkLabel(
            self,
            text="→",
            font=ctk.CTkFont(family=UI_FONT_FAMILY, size=14),
            text_color=colors["text_muted"],
        ).grid(row=0, column=2, padx=(0, BUTTON_GAP))

        self.btn_swap = accent_button(
            self,
            text="⇄",
            command=self.swap_languages,
            theme=self.theme,
            width=36,
            height=BTN_HEIGHT_SM,
            font=ctk.CTkFont(size=14),
        )
        self.btn_swap.grid(row=0, column=3, padx=(0, BUTTON_GAP))
        create_tooltip(self.btn_swap, "Поменять языки местами", theme=self.theme)

        ctk.CTkLabel(self, text="В", font=label_font, text_color=colors["text_muted"]).grid(
            row=0, column=4, padx=(0, BUTTON_GAP)
        )

        options = self._get_language_options()
        default_to = (
            "RU - Русский"
            if "ru" in self.languages
            else (options[0] if options else "EN - English")
        )
        self.var_to = ctk.StringVar(value=default_to)
        self.combo_to = ctk.CTkComboBox(
            self,
            variable=self.var_to,
            values=options,
            width=COMBO_WIDTH,
            state="readonly",
            button_color=colors["accent"],
            button_hover_color=colors["accent_hover"],
            dropdown_fg_color=colors["bg_card"],
            dropdown_hover_color=colors["accent_hover"],
            font=label_font,
            **combo_kw,
        )
        self.combo_to.grid(row=0, column=5, sticky="ew")

    def _get_language_options(self) -> List[str]:
        return [f"{code.upper()} - {name}" for code, name in sorted(self.languages.items())]

    def swap_languages(self) -> None:
        from_val = self.var_from.get()
        to_val = self.var_to.get()
        self.var_from.set(to_val)
        self.var_to.set(from_val)

    def get_from_code(self) -> str:
        value = self.var_from.get()
        if value.upper().startswith("AUTO"):
            return "auto"
        if " - " in value:
            return value.split(" - ", 1)[0].strip().lower()
        return value.strip().lower()

    def get_to_code(self) -> str:
        value = self.var_to.get()
        if " - " in value:
            return value.split(" - ", 1)[0].strip().lower()
        return value.strip().lower()
