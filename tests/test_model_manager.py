"""Тесты ModelManager (пути, bundle)."""

from __future__ import annotations

from pathlib import Path

from argos_translator.services.model_manager import ModelManager


def test_packages_dir_uses_custom(tmp_path: Path) -> None:
    custom = tmp_path / "my_packages"
    mgr = ModelManager(str(custom))
    assert mgr.packages_dir == custom


def test_install_from_bundle_empty_dir(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    mgr = ModelManager(str(tmp_path / "packages"))
    assert mgr.install_from_bundle(bundle) == 0


def test_install_from_bundle_skips_existing(tmp_path: Path) -> None:
    bundle = tmp_path / "bundle"
    packages = tmp_path / "packages"
    bundle.mkdir()
    packages.mkdir()
    model = bundle / "translate-en_ru-1_0.argosmodel"
    model.write_bytes(b"fake")
    (packages / model.name).write_bytes(b"fake")

    mgr = ModelManager(str(packages))
    assert mgr.install_from_bundle(bundle) == 0


def test_has_pair(monkeypatch) -> None:
    mgr = ModelManager()
    monkeypatch.setattr(
        mgr,
        "list_installed_pairs",
        lambda: ["en->ru", "ru->en"],
    )
    assert mgr.has_pair("en", "ru") is True
    assert mgr.has_pair("de", "en") is False


def test_install_from_path_does_not_call_update_package_index(
    tmp_path: Path, monkeypatch
) -> None:
    model = tmp_path / "en_ru.argosmodel"
    model.write_bytes(b"fake")
    called = {"install": 0, "index": 0}

    def _install(_path: str) -> None:
        called["install"] += 1

    def _update() -> None:
        called["index"] += 1

    fake_pkg = type(
        "Pkg",
        (),
        {"install_from_path": staticmethod(_install), "update_package_index": staticmethod(_update)},
    )()
    monkeypatch.setattr(
        "argos_translator.services.model_manager.AT_PACKAGE_MODULE",
        fake_pkg,
    )
    mgr = ModelManager(str(tmp_path / "packages"))
    assert mgr.install_from_path(model) is True
    assert called["install"] == 1
    assert called["index"] == 0


def test_get_packages_dir(tmp_path: Path) -> None:
    mgr = ModelManager(str(tmp_path / "pkg"))
    assert mgr.get_packages_dir() == tmp_path / "pkg"
