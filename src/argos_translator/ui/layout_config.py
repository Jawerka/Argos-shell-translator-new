"""Единые настройки разметки UI (CustomTkinter, flat layout)."""

from __future__ import annotations

from argos_translator.ui.themes import Spacing, get_color_theme

CORNER_RADIUS = 0
WINDOW_PADX = 0
WINDOW_PADY = 0
CARD_PADX = 0
CARD_PADY = 0
ELEMENT_PADX = 0
ELEMENT_PADY = 0
ELEMENT_GAP = 0
BUTTON_GAP = 0

BTN_HEIGHT = 34
BTN_HEIGHT_SM = 30
BTN_FONT_SIZE = 13
BTN_ICON_FONT_SIZE = 16
TEXT_FONT_SIZE = 12
TEXT_FONT_FAMILY = "Consolas"
UI_FONT_FAMILY = "Segoe UI"
LABEL_FONT_SIZE = 12
TITLE_FONT_SIZE = 13

PROGRESS_HEIGHT = 8
PROGRESS_WIDTH = 160

INPUT_HEIGHT = 36
COMBO_WIDTH = 180
TRANSLATION_TAB_BAR_HEIGHT = 44
PANEL_HEADER_HEIGHT = 26
PANEL_TAB_ROW_HEIGHT = 30
PANEL_BUTTON_ROW_HEIGHT = BTN_HEIGHT
EDITOR_GRID_ROW_TEXT = 2


def get_card_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "fg_color": colors["bg_card"],
        "corner_radius": CORNER_RADIUS,
        "border_width": 1,
        "border_color": colors["border"],
    }


def get_text_inset_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "fg_color": colors["input"],
        "corner_radius": CORNER_RADIUS,
        "border_width": 1,
        "border_color": colors["border"],
    }


def get_tabview_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "fg_color": colors["input"],
        "segmented_button_fg_color": colors["bg_secondary"],
        "segmented_button_selected_color": colors["primary"],
        "segmented_button_selected_hover_color": colors["primary_hover"],
        "segmented_button_unselected_color": colors["accent"],
        "segmented_button_unselected_hover_color": colors["accent_hover"],
        "text_color": colors["text_primary"],
        "corner_radius": CORNER_RADIUS,
        "border_width": 1,
        "border_color": colors["border"],
    }


def get_checkbox_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "fg_color": colors["primary"],
        "hover_color": colors["primary_hover"],
        "border_color": colors["border"],
        "checkmark_color": colors["primary_foreground"],
        "text_color": colors["text_primary"],
        "font": (UI_FONT_FAMILY, LABEL_FONT_SIZE),
    }


def get_button_primary_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "height": BTN_HEIGHT,
        "corner_radius": CORNER_RADIUS,
        "fg_color": colors["primary"],
        "hover_color": colors["primary_hover"],
        "text_color": colors["primary_foreground"],
        "font": (UI_FONT_FAMILY, BTN_FONT_SIZE, "bold"),
    }


def get_button_accent_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "height": BTN_HEIGHT,
        "corner_radius": CORNER_RADIUS,
        "fg_color": colors["accent"],
        "hover_color": colors["accent_hover"],
        "text_color": colors["accent_foreground"],
        "font": (UI_FONT_FAMILY, BTN_FONT_SIZE),
    }


def get_combobox_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "height": BTN_HEIGHT_SM,
        "corner_radius": CORNER_RADIUS,
        "border_width": 1,
        "border_color": colors["border"],
        "fg_color": colors["input"],
        "text_color": colors["text_primary"],
    }


def get_input_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "height": INPUT_HEIGHT,
        "corner_radius": CORNER_RADIUS,
        "border_width": 1,
        "border_color": colors["border"],
        "fg_color": colors["input"],
        "text_color": colors["text_primary"],
    }
