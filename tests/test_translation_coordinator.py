"""Тесты TranslationCoordinator."""

from __future__ import annotations

from argos_translator.services.translation_coordinator import TranslationCoordinator


def test_allocate_increments_job_id() -> None:
    coord = TranslationCoordinator()
    assert coord.allocate_job() == 1
    assert coord.allocate_job() == 2


def test_cancel_clears_active_jobs() -> None:
    coord = TranslationCoordinator()
    job = coord.allocate_job()
    coord.start_argos(job, 3)
    coord.start_llm(job)
    coord.cancel()
    assert coord.active_job is None
    assert coord.llm_active_job is None
    assert coord.argos_stop.is_set()
    assert coord.llm_stop.is_set()


def test_argos_should_stop_when_superseded() -> None:
    coord = TranslationCoordinator()
    old = coord.allocate_job()
    coord.start_argos(old, 2)
    coord.signal_argos_restart()
    new = coord.allocate_job()
    coord.start_argos(new, 2)
    assert coord.argos_should_stop(old) is True
    assert coord.argos_should_stop(new) is False


def test_record_and_progress() -> None:
    coord = TranslationCoordinator()
    job = coord.allocate_job()
    coord.start_argos(job, 4)
    assert coord.record_argos_chunk(job, 0, "a", 0) is True
    assert coord.record_argos_chunk(job, 1, "b", 0) is True
    done, total = coord.argos_progress()
    assert done == 2
    assert total == 4


def test_llm_is_stale() -> None:
    coord = TranslationCoordinator()
    coord.start_llm(5)
    assert coord.llm_is_stale(5) is False
    assert coord.llm_is_stale(4) is True
