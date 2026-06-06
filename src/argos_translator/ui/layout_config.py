"""Единые настройки разметки UI (CustomTkinter, structured flat v2.1)."""

from __future__ import annotations

from dataclasses import dataclass

from argos_translator.ui.themes import Spacing, get_color_theme


@dataclass(frozen=True)
class UIStyle:
    """Дизайн-токены интерфейса (фаза 10)."""

    radius_card: int = 0
    radius_control: int = 8
    border: int = 1
    header_h: int = 28
    toolbar_h: int = 52
    button_h: int = 34
    panel_pad: int = 8
    section_gap: int = 12


STYLE = UIStyle()

# Обратная совместимость и алиасы
CORNER_RADIUS = STYLE.radius_card
RADIUS_CARD = STYLE.radius_card
RADIUS_CONTROL = STYLE.radius_control

WINDOW_PADX = Spacing.SM
WINDOW_PADY = Spacing.SM
CARD_PADX = Spacing.SM + 2
CARD_PADY = Spacing.SM
ELEMENT_PADX = Spacing.SM
ELEMENT_PADY = Spacing.SM
ELEMENT_GAP = Spacing.SM
BUTTON_GAP = Spacing.XS + 2
SECTION_GAP = STYLE.section_gap
PANEL_PAD = STYLE.panel_pad

BTN_HEIGHT = STYLE.button_h
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
PANEL_HEADER_HEIGHT = STYLE.header_h
PANEL_TAB_ROW_HEIGHT = 30
PANEL_BUTTON_ROW_HEIGHT = BTN_HEIGHT
TOOLBAR_HEIGHT = STYLE.toolbar_h
SETTINGS_SIDEBAR_WIDTH = 168
SETTINGS_DIALOG_WIDTH = 720
SETTINGS_DIALOG_HEIGHT = 560
SETTINGS_DIALOG_MIN_WIDTH = 640
SETTINGS_DIALOG_MIN_HEIGHT = 480
EDITOR_GRID_ROW_TEXT = 2


def get_card_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "fg_color": colors["bg_card"],
        "corner_radius": RADIUS_CARD,
        "border_width": STYLE.border,
        "border_color": colors["border"],
    }


def get_text_inset_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "fg_color": colors["input"],
        "corner_radius": RADIUS_CONTROL,
        "border_width": STYLE.border,
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
        "corner_radius": RADIUS_CONTROL,
        "border_width": STYLE.border,
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
        "corner_radius": RADIUS_CONTROL,
        "fg_color": colors["primary"],
        "hover_color": colors["primary_hover"],
        "text_color": colors["primary_foreground"],
        "font": (UI_FONT_FAMILY, BTN_FONT_SIZE, "bold"),
    }


def get_button_accent_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "height": BTN_HEIGHT,
        "corner_radius": RADIUS_CONTROL,
        "fg_color": colors["accent"],
        "hover_color": colors["accent_hover"],
        "text_color": colors["accent_foreground"],
        "font": (UI_FONT_FAMILY, BTN_FONT_SIZE),
    }


def get_combobox_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "height": BTN_HEIGHT_SM,
        "corner_radius": RADIUS_CONTROL,
        "border_width": STYLE.border,
        "border_color": colors["border"],
        "fg_color": colors["input"],
        "text_color": colors["text_primary"],
    }


def get_input_kwargs(theme: str = "dark") -> dict:
    colors = get_color_theme(theme)
    return {
        "height": INPUT_HEIGHT,
        "corner_radius": RADIUS_CONTROL,
        "border_width": STYLE.border,
        "border_color": colors["border"],
        "fg_color": colors["input"],
        "text_color": colors["text_primary"],
    }
