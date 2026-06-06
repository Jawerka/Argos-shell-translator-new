from argos_translator.services.clipboard import capture_selection_text, clipboard_available
from argos_translator.services.hotkeys import hotkeys_available, register_global_hotkey
from argos_translator.services.model_manager import ModelManager
from argos_translator.services.tray import TrayManager

__all__ = [
    "ModelManager",
    "TrayManager",
    "capture_selection_text",
    "clipboard_available",
    "hotkeys_available",
    "register_global_hotkey",
]
