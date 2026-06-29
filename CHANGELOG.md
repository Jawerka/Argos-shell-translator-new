# Changelog

All notable changes to Argos Translate Streaming are documented here.

Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

### Added

- LLM file translation: disjoint chunking (paragraph → sentence → word) with `file_chunk_max_chars` (default 3500)
- Read-only context between LLM file chunks: source excerpt + translated tail (`file_chunk_context`)
- Adaptive `max_tokens` and per-chunk read timeout based on block size
- LLM file progress: «LLM: блок X/Y…» and shared file progress bar
- Settings (LLM advanced): file chunk size and inter-chunk context toggle
- `settings.json` v8: `chunk_max_chars`, `file_chunk_max_chars`, `file_chunk_context`

### Changed

- LLM chunking: removed translate overlap (fixes duplicate/mismatched segments at boundaries)
- **Pipeline resilience:** LLM per-chunk errors no longer abort the whole job; partial translation is preserved with `[LLM Error: …]` markers
- **LLM retries:** connect errors, HTTP 5xx and 429 get one automatic retry with backoff
- **Argos preflight:** missing language pair shows a clear message before starting the worker; LLM can still run
- **`prefer_api_over_cli`** setting is now respected by `TranslateEngine`
- Settings numeric fields are clamped to safe ranges on load (`clamp_settings`)

### Tests

- App pipeline tests: Argos worker, translate results, LLM pipeline, translate entry, file I/O
- Settings robustness tests (corrupt JSON, clamping, migrations)
- `pytest-cov` in CI for `engines/`, `services/`, `config/` (≥80%)

### Removed

- Legacy `test_translation.py` manual check script (use `pytest -m integration`)
- Obsolete `pyinstall.md` stub (see `BUILD_INSTRUCTIONS.md`)
- Duplicate root `hook-numpy.py` (use `hooks/hook-numpy.py`)

## [2.1.0] — 2026-06-06

### Added

- UI design tokens: `UIStyle` / `STYLE` in `ui/layout_config.py` (structured flat v2.1)
- Toolbar three-zone layout: file/title · languages · actions
- «Ещё ▾» popup menu for streaming and scroll-sync toggles
- Character count badge on source text panel
- Language selector: direction arrow (→) and grid layout for centering
- Settings dialog: sidebar navigation (168 px) with section intros; LLM advanced params collapsible
- Settings dialog geometry persisted in `ui.settings_dialog` (`WindowState`)

### Changed

- Restored meaningful spacing (`Spacing.SM`, `SECTION_GAP`) across main window and settings
- Editor `text_host` uses `radius_control=8` and 1px border; outer cards stay flat (`radius_card=0`)
- Status footer: three columns (status · LLM indicator · hints/progress)
- Primary action label: «Перевод» → «Перевести»
- Settings: replaced `CTkTabview` with sidebar + content panels
- `docs/UI_BASELINE.md` updated to v2.1

### Fixed

- Short-text language detection: script-based fallback when text < 20 chars (langdetect en↔nl, ru↔bg confusion)

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
