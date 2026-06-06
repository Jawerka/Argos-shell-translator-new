# Changelog

All notable changes to Argos Translate Streaming are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [2.0.0] — 2025-06-05

### Added

- Frozen EXE bootstrap: `services/frozen_bootstrap.py` installs Argos models from bundle on first run
- Portable paths: `get_exe_dir()`, `get_log_dir()`, `is_frozen()` in `config/paths.py`
- `engines/factory.py` with `create_engine(name, settings)`
- DPI diagnostics logged at startup (`log_dpi_info`)
- Tests: release checklist, encoding fixtures (**117** pytest total)
- PyInstaller: `assets/version_info.txt`, `assets/app.manifest` (DPI)
- `scripts/smoke_dist.py` post-build verification
- Theme live preview in settings; geometry save lock during restore
- `docs/UI_BASELINE.md` UI baseline description
- LLM: timeout retry, `/v1/completions` fallback, `build_request_context()`
- Encoding fixtures in `tests/fixtures/encodings/` + `test_encoding_detection.py`
- Integration tests: `tests/test_translation_integration.py` (`@pytest.mark.integration`)
- Modular package layout under `src/argos_translator/` with thin `main.py` entry
- Dark theme (`ui/themes.py`) applied at startup
- System tray: close button minimizes to tray; exit via tray context menu
- DPI-aware window geometry (`WindowStateManager`, structured `settings.json`)
- Settings dialog with tabs: Appearance, Translation, LLM, Files, Argos, Behavior, About
- LLM engine (OpenAI-compatible): LOCAL, OpenRouter, Custom providers
- `both_adaptive` mode: Argos and LLM run in parallel; UI shows one tab at a time
- File menu: open, save translation, save both; auto encoding detection (`document_io.py`)
- Optional drag & drop on Windows (`windnd`)
- Argos LRU translation cache (optional, session-scoped)
- `TranslationCoordinator` for unified job/cancel management
- PyInstaller spec, hooks, and `scripts/build.bat`
- pytest suite and GitHub Actions CI workflow (pytest + ruff)
- Markdown code fences skipped by default (`files.translate_code_blocks`)
- `assets/` for icons; `scripts/verify_spec.py` pre-build check
- `test_themes.py` for theme application

### Changed

- Legacy `test_translation.py` updated to use package imports; pytest integration baseline added
- Frozen logs write beside EXE (`{exe_dir}/log/`) instead of bundle `_MEIPASS`
- Phase 1 refactor: UI layout → `ui/main_window.py`; tray/hotkeys/clipboard → `services/`
- File translation shows progress bar and large-file confirmation dialog
- Icons relocated to `assets/`; PyInstaller specs and `get_resource_path()` updated
- Settings migrated automatically through v7 (`behavior`, `files`, `argos`, LLM sections)
- Model installation uses `argostranslate.package.install_from_path()` via `ModelManager`
- Unified `get_argos_packages_dir()` in `config/paths.py`

### Fixed

- Tray single-click restore (default menu action)
- README log path aligned with `LoggingConfig`
- Clipboard restore after global hotkey capture (configurable)

## [1.x] — legacy

- Monolithic `main.py` prototype with Argos offline translation only

[2.0.0]: https://github.com/compare/v1.0.0...v2.0.0
