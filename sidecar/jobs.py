"""Потоковый перевод Argos для sidecar (чанки + отмена)."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.services.model_manager import ModelManager
from argos_translator.services.translation_cache import TranslationCache
from argos_translator.services.translation_coordinator import TranslationCoordinator
from argos_translator.utils.imports import AT_TRANSLATE_MODULE
from argos_translator.utils.text_utils import TextUtils

logger = logging.getLogger("ArgosStreaming")

ChunkSink = Callable[[dict], None]


class ArgosJobRunner:
    def __init__(
        self,
        *,
        coordinator: TranslationCoordinator,
        cache: TranslationCache,
        packages_dir: Optional[str] = None,
        translate_lock: Optional[threading.Lock] = None,
    ) -> None:
        self.coord = coordinator
        self.cache = cache
        self.packages_dir = packages_dir
        self.model_manager = ModelManager(packages_dir)
        self._translate_lock = translate_lock or threading.Lock()

    def detect(self, text: str) -> str:
        from_codes = TextUtils.installed_from_codes(self.model_manager.list_installed_pairs())
        return TextUtils.detect_language(text, installed_from_codes=from_codes)

    def _snap_missing_pair(
        self,
        text: str,
        from_code: str,
        to_code: str,
        preferred_to: str,
    ) -> tuple[str, str]:
        if not self._missing_pair_message(from_code, to_code):
            return from_code, to_code
        from_codes = TextUtils.installed_from_codes(self.model_manager.list_installed_pairs())
        snapped = TextUtils.snap_detected_lang(
            from_code,
            has_cyrillic=TextUtils.has_cyrillic(text),
            installed_from_codes=from_codes,
        )
        if snapped == (from_code or "").strip().lower():
            return from_code, to_code
        return TextUtils.resolve_auto_pair(snapped, preferred_to)

    def _missing_pair_message(self, from_code: str, to_code: str) -> Optional[str]:
        if not from_code or not to_code or from_code == to_code:
            return None
        pairs = self.model_manager.list_installed_pairs()
        if pairs:
            if self.model_manager.has_pair(from_code, to_code):
                return None
            return f"Нет модели {from_code}→{to_code}"
        get_fn = getattr(AT_TRANSLATE_MODULE, "get_translation_from_codes", None)
        if not callable(get_fn):
            return None
        try:
            translation = get_fn(from_code, to_code)
        except Exception:
            return f"Нет модели {from_code}→{to_code}"
        if translation is None:
            return f"Нет модели {from_code}→{to_code}"
        return None

    def run_translate(
        self,
        *,
        text: str,
        from_code: str,
        to_code: str,
        prefer_api: bool = True,
        translate_code_blocks: bool = False,
        use_cache: bool = False,
        emit: ChunkSink,
    ) -> str:
        resolved_from = from_code
        resolved_to = to_code
        preferred_to = to_code
        if (from_code or "").lower() == "auto":
            resolved_from = self.detect(text)
            resolved_from, resolved_to = TextUtils.resolve_auto_pair(resolved_from, to_code)
        resolved_from, resolved_to = self._snap_missing_pair(
            text, resolved_from, resolved_to, preferred_to
        )

        units = TextUtils.build_argos_units(
            text, translate_code_blocks=translate_code_blocks
        )
        job_id = self.coord.allocate_job()
        self.coord.start_argos(job_id, len(units))

        emit(
            {
                "type": "start",
                "job_id": job_id,
                "from": resolved_from,
                "to": resolved_to,
                "unit_count": len(units),
            }
        )

        missing = self._missing_pair_message(resolved_from, resolved_to)
        if missing:
            logger.warning("sidecar job %s: %s", job_id, missing)
            emit({"type": "error", "job_id": job_id, "message": missing})
            return "error"

        if not units:
            emit({"type": "done", "job_id": job_id})
            return "done"

        engine = TranslateEngine(prefer_api=prefer_api)
        for i, unit in enumerate(units):
            chunk_text, para_idx, translatable = unit
            if self.coord.argos_should_stop(job_id):
                logger.info("sidecar job %s cancelled at %s/%s", job_id, i, len(units))
                emit({"type": "cancelled", "job_id": job_id})
                return "cancelled"

            try:
                if not translatable:
                    output = chunk_text
                else:
                    cached = None
                    if use_cache:
                        cached = self.cache.get(chunk_text, resolved_from, resolved_to)
                    if cached is not None:
                        output = cached
                    else:
                        with self._translate_lock:
                            if self.coord.argos_should_stop(job_id):
                                emit({"type": "cancelled", "job_id": job_id})
                                return "cancelled"
                            output = engine.translate(chunk_text, resolved_from, resolved_to)
                        if use_cache:
                            self.cache.put(chunk_text, resolved_from, resolved_to, output)
            except Exception as exc:
                logger.error("sidecar job %s chunk %s failed: %s", job_id, i, exc)
                emit(
                    {
                        "type": "error",
                        "job_id": job_id,
                        "message": str(exc)[:200],
                    }
                )
                return "error"

            if self.coord.record_argos_chunk(job_id, i, output, para_idx):
                emit(
                    {
                        "type": "chunk",
                        "job_id": job_id,
                        "index": i,
                        "para_idx": para_idx,
                        "text": output,
                        "done": i + 1,
                        "total": len(units),
                    }
                )

        if self.coord.argos_should_stop(job_id):
            emit({"type": "cancelled", "job_id": job_id})
            return "cancelled"

        emit({"type": "done", "job_id": job_id})
        return "done"
