"""Менеджер иконки системного трея (pystray)."""

from __future__ import annotations

import importlib
import logging
import threading
from typing import Callable, Optional

from argos_translator.config.paths import get_resource_path
from argos_translator.utils.imports import PIL_MODULE, PYSTRAY_MODULE, TRAY_AVAILABLE

logger = logging.getLogger("ArgosStreaming")


class TrayManager:
    """Создание и управление иконкой трея."""

    def __init__(
        self,
        schedule_on_ui: Callable[[Callable[[], None]], None],
        schedule_delayed: Callable[[int, Callable[[], None]], None],
        *,
        on_show: Callable[[], None],
        on_settings: Callable[[], None],
        on_exit: Callable[[], None],
        enabled: bool = TRAY_AVAILABLE,
        max_create_attempts: int = 6,
    ) -> None:
        self._schedule = schedule_on_ui
        self._schedule_delayed = schedule_delayed
        self._on_show = on_show
        self._on_settings = on_settings
        self._on_exit = on_exit
        self.enabled = enabled
        self._max_attempts = max_create_attempts
        self.icon = None
        self.thread: Optional[threading.Thread] = None
        self.lock = threading.Lock()
        self._create_attempts = 0

    @property
    def active(self) -> bool:
        return self.icon is not None

    def ensure(self) -> None:
        if self.enabled and self.icon is None:
            self.create()

    def create(self) -> None:
        if not self.enabled:
            logger.debug("Tray not available (PYSTRAY or PIL missing).")
            return

        with self.lock:
            if self.icon is not None:
                return
            if self._create_attempts >= self._max_attempts:
                logger.warning("Tray creation attempts exhausted (%d)", self._create_attempts)
                return

        if PYSTRAY_MODULE is not None:
            has_default = getattr(PYSTRAY_MODULE.Icon, "HAS_DEFAULT_ACTION", None)
            logger.info("Tray HAS_DEFAULT_ACTION=%s", has_default)

        try:
            icon_img = self._load_icon_image()
            if icon_img is None:
                logger.warning("No tray icon image available")
                return

            def show_handler(icon=None, item=None):
                logger.debug("Tray -> Show")
                self._schedule(self._on_show)

            def settings_handler(icon=None, item=None):
                logger.debug("Tray -> Settings")
                self._schedule(self._on_settings)

            def exit_handler(icon=None, item=None):
                logger.debug("Tray -> Exit")
                self._schedule(self._on_exit)

            try:
                menu = PYSTRAY_MODULE.Menu(
                    PYSTRAY_MODULE.MenuItem("Показать", show_handler, default=True),
                    PYSTRAY_MODULE.MenuItem("Настройки", settings_handler),
                    PYSTRAY_MODULE.MenuItem("Выход", exit_handler),
                )
            except Exception:
                menu = None

            self.icon = PYSTRAY_MODULE.Icon(
                "argos_translate", icon_img, "Argos Translate", menu
            )

            run_detached = getattr(self.icon, "run_detached", None)
            if callable(run_detached):
                run_detached()
                logger.info("Tray icon started via run_detached()")
            else:

                def _run_icon() -> None:
                    try:
                        self.icon.run()
                    except Exception as exc:
                        logger.exception("Tray thread crashed: %s", exc)
                        with self.lock:
                            self.icon = None

                self.thread = threading.Thread(target=_run_icon, daemon=False)
                self.thread.start()
                logger.info("Tray icon thread started")

            self._create_attempts = 0
        except Exception as exc:
            self._create_attempts += 1
            logger.exception("Tray creation failed: %s", exc)
            delay_ms = min(60_000, 1000 * (2 ** (self._create_attempts - 1)))
            self._schedule_delayed(delay_ms, self.create)

    def stop(self) -> None:
        with self.lock:
            if self.icon is not None:
                try:
                    stop_fn = getattr(self.icon, "stop", None)
                    if callable(stop_fn):
                        stop_fn()
                    else:
                        setattr(self.icon, "visible", False)
                except Exception as exc:
                    logger.debug("Error stopping tray icon: %s", exc)
                finally:
                    self.icon = None

            if self.thread is not None:
                try:
                    if self.thread.is_alive():
                        self.thread.join(timeout=1.0)
                except Exception:
                    pass
                finally:
                    self.thread = None

    def _load_icon_image(self):
        Image = getattr(PIL_MODULE, "Image", None)
        ImageDraw = getattr(PIL_MODULE, "ImageDraw", None)
        ImageFont = getattr(PIL_MODULE, "ImageFont", None)

        if Image is None or ImageDraw is None:
            try:
                Image = importlib.import_module("PIL.Image")
                ImageDraw = importlib.import_module("PIL.ImageDraw")
            except Exception:
                from PIL import Image as _Image, ImageDraw as _ImageDraw  # type: ignore

                Image = _Image
                ImageDraw = _ImageDraw

        icon_path = get_resource_path("argos_translate.ico")
        if icon_path.exists():
            try:
                img = Image.open(str(icon_path)).convert("RGBA")
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", None)
                if resample is not None:
                    img.thumbnail((64, 64), resample)
                else:
                    img.thumbnail((64, 64))
                return img
            except Exception as exc:
                logger.debug("Failed to load tray icon %s: %s", icon_path, exc)

        try:
            img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.ellipse([(0, 0), (63, 63)], fill=(120, 120, 120, 255))
            if ImageFont is None:
                try:
                    ImageFont = importlib.import_module("PIL.ImageFont")
                except Exception:
                    ImageFont = None
            if ImageFont is not None:
                font = ImageFont.load_default()
                draw.text((18, 14), "A", fill=(255, 255, 255, 255), font=font)
            return img
        except Exception as exc:
            logger.exception("Creating fallback tray image failed: %s", exc)
            return None
