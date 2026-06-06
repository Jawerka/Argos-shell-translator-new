"""Общие CTk-виджеты и фабрики стилей."""

from __future__ import annotations

from typing import Callable, Optional

import customtkinter as ctk

from argos_translator.ui.layout_config import (
    CORNER_RADIUS,
    LABEL_FONT_SIZE,
    TITLE_FONT_SIZE,
    UI_FONT_FAMILY,
    get_button_accent_kwargs,
    get_button_primary_kwargs,
    get_card_kwargs,
    get_checkbox_kwargs,
)
from argos_translator.ui.themes import ThemeName, get_color_theme


def card_frame(master, theme: ThemeName = "dark", **kwargs) -> ctk.CTkFrame:
    opts = get_card_kwargs(theme)
    opts.update(kwargs)
    return ctk.CTkFrame(master, **opts)


def transparent_frame(master, **kwargs) -> ctk.CTkFrame:
    return ctk.CTkFrame(master, fg_color="transparent", **kwargs)


class TransparentFrame(ctk.CTkFrame):
    """Базовый прозрачный контейнер."""

    def __init__(self, master, **kwargs) -> None:
        kwargs.setdefault("fg_color", "transparent")
        super().__init__(master, **kwargs)


class CardFrame(ctk.CTkFrame):
    """Базовая карточка."""

    def __init__(self, master, theme: ThemeName = "dark", **kwargs) -> None:
        opts = get_card_kwargs(theme)
        opts.update(kwargs)
        super().__init__(master, **opts)


def section_title(master, text: str, theme: ThemeName = "dark") -> ctk.CTkLabel:
    colors = get_color_theme(theme)
    return ctk.CTkLabel(
        master,
        text=text,
        font=ctk.CTkFont(family=UI_FONT_FAMILY, size=TITLE_FONT_SIZE, weight="bold"),
        text_color=colors["text_primary"],
        anchor="w",
    )


def panel_title_label(
    master,
    text: str,
    theme: ThemeName = "dark",
    font: Optional[ctk.CTkFont] = None,
) -> ctk.CTkLabel:
    colors = get_color_theme(theme)
    return ctk.CTkLabel(
        master,
        text=text,
        font=font or ctk.CTkFont(family=UI_FONT_FAMILY, size=TITLE_FONT_SIZE, weight="bold"),
        text_color=colors["text_muted"],
        anchor="w",
    )


def muted_label(master, text: str, theme: ThemeName = "dark", wraplength: int = 0) -> ctk.CTkLabel:
    colors = get_color_theme(theme)
    kw: dict = {
        "font": ctk.CTkFont(family=UI_FONT_FAMILY, size=LABEL_FONT_SIZE),
        "text_color": colors["text_muted"],
        "anchor": "w",
    }
    if wraplength:
        kw["wraplength"] = wraplength
    return ctk.CTkLabel(master, text=text, **kw)


def primary_button(
    master,
    text: str,
    command: Optional[Callable[[], None]] = None,
    theme: ThemeName = "dark",
    width: int = 120,
    **kwargs,
) -> ctk.CTkButton:
    opts = get_button_primary_kwargs(theme)
    opts.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, width=width, **opts)


def accent_button(
    master,
    text: str,
    command: Optional[Callable[[], None]] = None,
    theme: ThemeName = "dark",
    width: int = 100,
    **kwargs,
) -> ctk.CTkButton:
    opts = get_button_accent_kwargs(theme)
    opts.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, width=width, **opts)


def ghost_button(
    master,
    text: str,
    command: Optional[Callable[[], None]] = None,
    theme: ThemeName = "dark",
    width: int = 100,
    **kwargs,
) -> ctk.CTkButton:
    colors = get_color_theme(theme)
    opts = {
        "height": get_button_accent_kwargs(theme)["height"],
        "corner_radius": CORNER_RADIUS,
        "fg_color": "transparent",
        "hover_color": colors["accent"],
        "border_width": 1,
        "border_color": colors["border"],
        "text_color": colors["text_primary"],
        "font": ctk.CTkFont(family=UI_FONT_FAMILY, size=LABEL_FONT_SIZE),
    }
    opts.update(kwargs)
    return ctk.CTkButton(master, text=text, command=command, width=width, **opts)


def icon_button(
    master,
    text: str,
    command: Optional[Callable[[], None]] = None,
    theme: ThemeName = "dark",
    width: int = 40,
    **kwargs,
) -> ctk.CTkButton:
    return accent_button(
        master,
        text,
        command,
        theme=theme,
        width=width,
        font=ctk.CTkFont(size=16),
        **kwargs,
    )


def themed_checkbox(
    master,
    text: str,
    variable,
    command: Optional[Callable[[], None]] = None,
    theme: ThemeName = "dark",
    width: int = 0,
    **kwargs,
) -> ctk.CTkCheckBox:
    opts = get_checkbox_kwargs(theme)
    opts.update(kwargs)
    return ctk.CTkCheckBox(master, text=text, variable=variable, command=command, width=width, **opts)


def separator(master, theme: ThemeName = "dark") -> ctk.CTkFrame:
    colors = get_color_theme(theme)
    return ctk.CTkFrame(master, height=1, fg_color=colors["border"], corner_radius=0)


def vertical_separator(master, theme: ThemeName = "dark", height: int = 28) -> ctk.CTkFrame:
    colors = get_color_theme(theme)
    frame = ctk.CTkFrame(master, width=1, height=height, fg_color=colors["border"], corner_radius=0)
    frame.pack_propagate(False)
    return frame


def panel_header(master, title: str, theme: ThemeName = "dark") -> ctk.CTkFrame:
    """Заголовок карточки-панели."""
    frame = transparent_frame(master)
    panel_title_label(frame, title, theme=theme).pack(fill="x")
    return frame
