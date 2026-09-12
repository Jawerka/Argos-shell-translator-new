"""Потоковый перевод Argos для sidecar (чанки + отмена)."""

from __future__ import annotations

import logging
from typing import Callable, Optional

from argos_translator.engines.argos_engine import TranslateEngine
from argos_translator.services.model_manager import ModelManager
from argos_translator.services.translation_cache import TranslationCache
from argos_translator.services.translation_coordinator import TranslationCoordinator
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
    ) -> None:
        self.coord = coordinator
        self.cache = cache
        self.packages_dir = packages_dir
        self.model_manager = ModelManager(packages_dir)

    def detect(self, text: str) -> str:
        return TextUtils.detect_language(text)

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
        if (from_code or "").lower() == "auto":
            resolved_from = self.detect(text)

        units = TextUtils.build_argos_units(
            text, translate_code_blocks=translate_code_blocks
        )
        job_id = self.coord.allocate_job()
        self.coord.signal_argos_restart()
        self.coord.clear_argos_restart()
        self.coord.start_argos(job_id, len(units))

        emit(
            {
                "type": "start",
                "job_id": job_id,
                "from": resolved_from,
                "to": to_code,
                "unit_count": len(units),
            }
        )

        if not units:
            emit({"type": "done", "job_id": job_id})
            return "done"

        engine = TranslateEngine(prefer_api=prefer_api)
        status = "done"
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
                        cached = self.cache.get(chunk_text, resolved_from, to_code)
                    if cached is not None:
                        output = cached
                    else:
                        output = engine.translate(chunk_text, resolved_from, to_code)
                        if use_cache:
                            self.cache.put(chunk_text, resolved_from, to_code, output)
            except Exception as exc:
                logger.error("sidecar job %s chunk %s failed: %s", job_id, i, exc)
                output = f"[Ошибка: {str(exc)[:80]}]"

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
        return status
