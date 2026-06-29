"""Загрузка и сохранение settings.json."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from argos_translator.config.constants import UIConfig
from argos_translator.config.paths import get_settings_path
from argos_translator.ui.window_state import WindowState

logger = logging.getLogger("ArgosStreaming")

CURRENT_SETTINGS_VERSION = 8


@dataclass
class BehaviorSettings:
    close_action: str = "tray"
    start_minimized_to_tray: bool = False
    tray_click_action: str = "show"
    restore_clipboard_after_capture: bool = True
    global_hotkey: str = "ctrl+shift+c"
    minimize_to_tray_on_copy_hide: bool = True
    translation_cache_enabled: bool = False
    translation_cache_size: int = 500


@dataclass
class FileSettings:
    output_encoding: str = "same"
    output_suffix: str = "_translated"
    max_file_size_mb: int = 10
    hotkey_auto_translate_max_chars: int = 500
    large_file_warn_chars: int = 50000
    translate_code_blocks: bool = False


@dataclass
class ArgosSettings:
    packages_dir: str = ""
    prefer_api_over_cli: bool = True
    bundle_models_on_start: bool = True


@dataclass
class LLMSettings:
    enabled: bool = True
    provider: str = "local"
    base_url: str = "http://192.168.88.41:8989/v1"
    provider_urls: Dict[str, str] = field(
        default_factory=lambda: {
            "local": "http://192.168.88.41:8989/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "custom": "",
        }
    )
    api_keys: Dict[str, str] = field(default_factory=lambda: {"openrouter": "", "custom": ""})
    model: str = ""
    auth_header: str = "auto"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout_sec: int = 120
    stream: bool = True
    health_check_ttl_sec: int = 30
    system_prompt: str = ""
    chunk_max_chars: int = 6000
    file_chunk_max_chars: int = 3500
    file_chunk_context: bool = True


@dataclass
class AppSettings:
    version: int = CURRENT_SETTINGS_VERSION
    window_state: WindowState = field(default_factory=WindowState)
    theme: str = "dark"
    opacity: float = 1.0
    font_scale: float = 1.0
    editor_layout: str = "split"
    streaming: bool = True
    scroll_sync: bool = True
    debounce_ms: int = 700
    llm_debounce_ms: int = 1200
    auto_target_lang: str = "ru"
    lang_from: str = "auto"
    lang_to: str = "ru"
    llm: LLMSettings = field(default_factory=LLMSettings)
    files: FileSettings = field(default_factory=FileSettings)
    argos: ArgosSettings = field(default_factory=ArgosSettings)
    behavior: BehaviorSettings = field(default_factory=BehaviorSettings)
    active_translation_tab: str = "argos"
    geometry_legacy: Optional[str] = None
    settings_dialog_state: Optional[WindowState] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "window": {
                **self.window_state.to_dict(),
                "opacity": self.opacity,
                "theme": self.theme,
                "font_scale": self.font_scale,
                "editor_layout": self.editor_layout,
                "geometry_legacy": self.geometry_legacy,
            },
            "translation": {
                "default_engine": "both_adaptive",
                "streaming": self.streaming,
                "debounce_ms": self.debounce_ms,
                "llm_debounce_ms": self.llm_debounce_ms,
                "scroll_sync": self.scroll_sync,
                "auto_target_lang": self.auto_target_lang,
                "cache_enabled": self.behavior.translation_cache_enabled,
                "cache_size": self.behavior.translation_cache_size,
            },
            "languages": {"from": self.lang_from, "to": self.lang_to},
            "llm": {
                "enabled": self.llm.enabled,
                "provider": self.llm.provider,
                "base_url": self.llm.base_url,
                "provider_urls": self.llm.provider_urls,
                "api_keys": self.llm.api_keys,
                "model": self.llm.model,
                "auth_header": self.llm.auth_header,
                "temperature": self.llm.temperature,
                "max_tokens": self.llm.max_tokens,
                "timeout_sec": self.llm.timeout_sec,
                "stream": self.llm.stream,
                "health_check_ttl_sec": self.llm.health_check_ttl_sec,
                "system_prompt": self.llm.system_prompt,
                "chunk_max_chars": self.llm.chunk_max_chars,
                "file_chunk_max_chars": self.llm.file_chunk_max_chars,
                "file_chunk_context": self.llm.file_chunk_context,
            },
            "ui": {
                "active_translation_tab": self.active_translation_tab,
                "settings_dialog": (
                    self.settings_dialog_state.to_dict() if self.settings_dialog_state else None
                ),
            },
            "files": {
                "output_encoding": self.files.output_encoding,
                "output_suffix": self.files.output_suffix,
                "max_file_size_mb": self.files.max_file_size_mb,
                "hotkey_auto_translate_max_chars": self.files.hotkey_auto_translate_max_chars,
                "large_file_warn_chars": self.files.large_file_warn_chars,
                "translate_code_blocks": self.files.translate_code_blocks,
            },
            "argos": {
                "packages_dir": self.argos.packages_dir,
                "prefer_api_over_cli": self.argos.prefer_api_over_cli,
                "bundle_models_on_start": self.argos.bundle_models_on_start,
            },
            "behavior": {
                "close_action": self.behavior.close_action,
                "start_minimized_to_tray": self.behavior.start_minimized_to_tray,
                "tray_click_action": self.behavior.tray_click_action,
                "restore_clipboard_after_capture": self.behavior.restore_clipboard_after_capture,
                "global_hotkey": self.behavior.global_hotkey,
                "minimize_to_tray_on_copy_hide": self.behavior.minimize_to_tray_on_copy_hide,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], cfg: UIConfig) -> "AppSettings":
        data = migrate_settings(data)
        window = data.get("window", {})
        translation = data.get("translation", {})
        languages = data.get("languages", {})
        llm_data = data.get("llm", {})
        ui = data.get("ui", {})
        files_data = data.get("files", {})
        argos_data = data.get("argos", {})
        behavior_data = data.get("behavior", {})

        ws_data = {
            k: window[k]
            for k in (
                "state",
                "x",
                "y",
                "width",
                "height",
                "monitor_hint",
                "dpi_scale",
                "geometry_units",
            )
            if k in window
        }
        if ws_data:
            window_state = WindowState.from_dict(ws_data, WindowState(width=cfg.width, height=cfg.height))
        elif window.get("geometry"):
            window_state = WindowState.from_geometry_string(window["geometry"], cfg)
        else:
            window_state = WindowState(width=cfg.width, height=cfg.height)

        llm = LLMSettings(
            enabled=bool(llm_data.get("enabled", True)),
            provider=str(llm_data.get("provider", "local")),
            base_url=str(llm_data.get("base_url", "http://192.168.88.41:8989/v1")),
            provider_urls=llm_data.get("provider_urls") or LLMSettings().provider_urls,
            api_keys=_migrate_api_keys(llm_data),
            model=str(llm_data.get("model", "")),
            auth_header=str(llm_data.get("auth_header", "auto")),
            temperature=float(llm_data.get("temperature", 0.3)),
            max_tokens=int(llm_data.get("max_tokens", 4096)),
            timeout_sec=int(llm_data.get("timeout_sec", 120)),
            stream=bool(llm_data.get("stream", True)),
            health_check_ttl_sec=int(llm_data.get("health_check_ttl_sec", 30)),
            system_prompt=str(llm_data.get("system_prompt", "")),
            chunk_max_chars=int(llm_data.get("chunk_max_chars", 6000)),
            file_chunk_max_chars=int(llm_data.get("file_chunk_max_chars", 3500)),
            file_chunk_context=bool(llm_data.get("file_chunk_context", True)),
        )

        streaming = translation.get("streaming", window.get("streaming", True))

        files = FileSettings(
            output_encoding=str(files_data.get("output_encoding", "same")),
            output_suffix=str(files_data.get("output_suffix", "_translated")),
            max_file_size_mb=int(files_data.get("max_file_size_mb", 10)),
            hotkey_auto_translate_max_chars=int(files_data.get("hotkey_auto_translate_max_chars", 500)),
            large_file_warn_chars=int(files_data.get("large_file_warn_chars", 50000)),
            translate_code_blocks=bool(files_data.get("translate_code_blocks", False)),
        )

        argos = ArgosSettings(
            packages_dir=str(argos_data.get("packages_dir", "")),
            prefer_api_over_cli=bool(argos_data.get("prefer_api_over_cli", True)),
            bundle_models_on_start=bool(argos_data.get("bundle_models_on_start", True)),
        )

        cache_enabled = translation.get("cache_enabled", behavior_data.get("translation_cache_enabled", False))
        cache_size = int(translation.get("cache_size", behavior_data.get("translation_cache_size", 500)))

        behavior = BehaviorSettings(
            close_action=str(behavior_data.get("close_action", "tray")),
            start_minimized_to_tray=bool(behavior_data.get("start_minimized_to_tray", False)),
            tray_click_action=str(behavior_data.get("tray_click_action", "show")),
            restore_clipboard_after_capture=bool(
                behavior_data.get("restore_clipboard_after_capture", True)
            ),
            global_hotkey=str(behavior_data.get("global_hotkey", "ctrl+shift+c")),
            minimize_to_tray_on_copy_hide=bool(behavior_data.get("minimize_to_tray_on_copy_hide", True)),
            translation_cache_enabled=bool(cache_enabled),
            translation_cache_size=cache_size,
        )

        sd_data = ui.get("settings_dialog")
        if isinstance(sd_data, dict) and sd_data:
            settings_dialog_state = WindowState.from_dict(
                sd_data,
                WindowState(width=720, height=560),
            )
        else:
            settings_dialog_state = None

        return cls(
            version=int(data.get("version", CURRENT_SETTINGS_VERSION)),
            window_state=window_state,
            theme=str(window.get("theme", "dark")),
            opacity=float(window.get("opacity", 1.0)),
            font_scale=float(window.get("font_scale", 1.0)),
            editor_layout=str(window.get("editor_layout", "split")),
            streaming=bool(streaming),
            scroll_sync=bool(translation.get("scroll_sync", window.get("scroll_sync", True))),
            debounce_ms=int(translation.get("debounce_ms", 700)),
            llm_debounce_ms=int(translation.get("llm_debounce_ms", 1200)),
            auto_target_lang=str(translation.get("auto_target_lang", "ru")),
            lang_from=str(languages.get("from", "auto")),
            lang_to=str(languages.get("to", "ru")),
            llm=llm,
            files=files,
            argos=argos,
            behavior=behavior,
            active_translation_tab=str(ui.get("active_translation_tab", "argos")),
            geometry_legacy=window.get("geometry"),
            settings_dialog_state=settings_dialog_state,
        )


def _migrate_api_keys(llm_data: Dict[str, Any]) -> Dict[str, str]:
    keys = llm_data.get("api_keys")
    if isinstance(keys, dict):
        return {str(k): str(v) for k, v in keys.items()}
    legacy = llm_data.get("api_key", "")
    result = {"openrouter": "", "custom": ""}
    if legacy:
        result["openrouter"] = str(legacy)
    return result


def migrate_settings(data: Dict[str, Any]) -> Dict[str, Any]:
    version = int(data.get("version", 1))
    if version < 2:
        window = data.setdefault("window", {})
        if "streaming" in window and "translation" not in data:
            data.setdefault("translation", {})["streaming"] = window.pop("streaming")
        if "scroll_sync" in window:
            data.setdefault("translation", {})["scroll_sync"] = window.get("scroll_sync")
        version = 2
    if version < 3:
        data.setdefault("translation", {})["default_engine"] = "both_adaptive"
        version = 3
    if version < 4:
        llm = data.setdefault("llm", {})
        if "api_key" in llm and "api_keys" not in llm:
            llm["api_keys"] = _migrate_api_keys(llm)
        llm.setdefault("provider", "local")
        llm.setdefault("enabled", True)
        version = 4
    if version < 5:
        data.setdefault("files", {})
        files = data["files"]
        files.setdefault("output_encoding", "same")
        files.setdefault("output_suffix", "_translated")
        files.setdefault("max_file_size_mb", 10)
        files.setdefault("hotkey_auto_translate_max_chars", 500)
        files.setdefault("large_file_warn_chars", 50000)
        files.setdefault("translate_code_blocks", False)
        version = 5
    if version < 6:
        data.setdefault("argos", {})
        argos = data["argos"]
        argos.setdefault("packages_dir", "")
        argos.setdefault("prefer_api_over_cli", True)
        argos.setdefault("bundle_models_on_start", True)
        version = 6
    if version < 7:
        data.setdefault("behavior", {})
        beh = data["behavior"]
        beh.setdefault("close_action", "tray")
        beh.setdefault("start_minimized_to_tray", False)
        beh.setdefault("restore_clipboard_after_capture", True)
        beh.setdefault("minimize_to_tray_on_copy_hide", True)
        data.setdefault("translation", {})["cache_enabled"] = False
        data.setdefault("translation", {})["cache_size"] = 500
        version = 7
    if version < 8:
        llm = data.setdefault("llm", {})
        llm.setdefault("chunk_max_chars", 6000)
        llm.setdefault("file_chunk_max_chars", 3500)
        llm.setdefault("file_chunk_context", True)
        version = 8
    data["version"] = version
    return data


def clamp_settings(settings: AppSettings) -> AppSettings:
    """Ограничить числовые поля допустимыми диапазонами после загрузки."""
    settings.debounce_ms = max(100, min(5000, int(settings.debounce_ms)))
    settings.llm_debounce_ms = max(200, min(10000, int(settings.llm_debounce_ms)))
    settings.opacity = max(0.3, min(1.0, float(settings.opacity)))
    settings.llm.temperature = max(0.0, min(2.0, float(settings.llm.temperature)))
    settings.llm.max_tokens = max(64, min(128000, int(settings.llm.max_tokens)))
    settings.llm.timeout_sec = max(5, min(600, int(settings.llm.timeout_sec)))
    settings.llm.health_check_ttl_sec = max(5, min(300, int(settings.llm.health_check_ttl_sec)))
    settings.llm.chunk_max_chars = max(500, int(settings.llm.chunk_max_chars))
    settings.llm.file_chunk_max_chars = max(500, int(settings.llm.file_chunk_max_chars))
    settings.behavior.translation_cache_size = max(10, min(10000, int(settings.behavior.translation_cache_size)))
    settings.files.max_file_size_mb = max(1, min(500, int(settings.files.max_file_size_mb)))
    settings.files.large_file_warn_chars = max(1000, int(settings.files.large_file_warn_chars))
    settings.files.hotkey_auto_translate_max_chars = max(
        50, int(settings.files.hotkey_auto_translate_max_chars)
    )
    return settings


def load_settings(cfg: UIConfig, path: Optional[Path] = None) -> AppSettings:
    cfg_path = path or get_settings_path()
    if not cfg_path.exists():
        return clamp_settings(AppSettings())
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return clamp_settings(AppSettings.from_dict(data, cfg))
    except Exception as exc:
        logger.debug("Load settings failed: %s", exc)
        return clamp_settings(AppSettings())


def save_settings(settings: AppSettings, path: Optional[Path] = None) -> None:
    cfg_path = path or get_settings_path()
    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(settings.to_dict(), f, ensure_ascii=False, indent=2)
        logger.info("Settings saved")
    except Exception as exc:
        logger.error("Save settings failed: %s", exc)
