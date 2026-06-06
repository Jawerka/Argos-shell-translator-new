"""Координатор заданий перевода Argos + LLM (единый job_id, отмена, прогресс)."""

from __future__ import annotations

import threading
from typing import Dict, Optional, Tuple


class TranslationCoordinator:
    """Управляет идентификаторами заданий, флагами отмены и прогрессом Argos."""

    def __init__(self) -> None:
        self._job_seq = 0
        self.active_job: Optional[int] = None
        self.llm_active_job: Optional[int] = None
        self.argos_stop = threading.Event()
        self.llm_stop = threading.Event()
        self.partial_translations: Dict[int, Dict[int, Tuple[str, int]]] = {}
        self.total_units: Dict[int, int] = {}

    def allocate_job(self) -> int:
        self._job_seq += 1
        return self._job_seq

    def signal_argos_restart(self) -> None:
        """Сигнал предыдущему Argos-worker остановиться (перед новым заданием)."""
        self.argos_stop.set()

    def clear_argos_restart(self) -> None:
        self.argos_stop.clear()

    def start_argos(self, job_id: int, unit_count: int) -> None:
        self.active_job = job_id
        self.partial_translations[job_id] = {}
        self.total_units[job_id] = unit_count

    def signal_llm_restart(self) -> None:
        self.llm_stop.set()

    def clear_llm_restart(self) -> None:
        self.llm_stop.clear()

    def start_llm(self, job_id: int) -> None:
        self.llm_active_job = job_id

    def cancel(self) -> None:
        self.argos_stop.set()
        self.llm_stop.set()
        self.active_job = None
        self.llm_active_job = None

    def argos_should_stop(self, job_id: int) -> bool:
        return self.argos_stop.is_set() and job_id != self.active_job

    def llm_is_stale(self, job_id: int) -> bool:
        return job_id != self.llm_active_job

    def record_argos_chunk(
        self, job_id: int, idx: int, text: str, para_idx: int
    ) -> bool:
        """Сохранить чанк; вернуть True если job_id — активный Argos."""
        if job_id not in self.partial_translations:
            self.partial_translations[job_id] = {}
        self.partial_translations[job_id][idx] = (text, para_idx)
        return job_id == self.active_job

    def argos_progress(self, job_id: Optional[int] = None) -> Tuple[int, int]:
        """(translated_count, total) для job_id или active_job."""
        jid = job_id if job_id is not None else self.active_job
        if jid is None:
            return 0, 0
        total = self.total_units.get(jid, 0)
        done = len(self.partial_translations.get(jid, {}))
        return done, total
