# AGENTS.md — руководство для AI-агентов

**Основной продукт (v2.1):** Flutter Windows UI (`apps/translator`) + Python sidecar (`python -m sidecar` / frozen `argos_sidecar.exe`). Контракт: [`docs/PRODUCT.md`](docs/PRODUCT.md). Запуск: `scripts/dev.ps1`. Сборка: `scripts/build-windows.ps1` (Flutter Release + sidecar в `{app}/sidecar/` + Inno). Не смешивать PyInstaller `_internal` с корнем Flutter.

Flutter SDK: PATH, `FLUTTER_ROOT`, `.fvm/flutter_sdk` или `%LOCALAPPDATA%\flutter` — [`scripts/resolve-flutter.ps1`](scripts/resolve-flutter.ps1). Не хардкодить личные пути.

Ниже — **legacy CustomTkinter** (не развивать UI; `src/argos_translator` движки и pytest всё ещё нужны sidecar).

Десктопный переводчик **Argos Translate Streaming**: Flutter UI, офлайн Argos + опциональный LLM (OpenAI-compatible API). Основная платформа — **Windows**.

## Быстрый старт

```bash
# Python 3.10–3.12 (рекомендуется; 3.14 — только для части тестов UI, не для сборки)
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install pytest             # или: pip install -e ".[dev]"

scripts\dev.ps1                # Flutter GUI + sidecar
```

Модели Argos: положить `*.argosmodel` в `argos_models/` и выполнить `python install_models.py`.

Legacy CTk: `python main.py` / `python -m argos_translator`.

## Команды

| Задача | Команда |
|--------|---------|
| Flutter GUI | `scripts\dev.ps1` |
| Flutter-тесты | `dart analyze --fatal-infos packages/translator_core`; `dart test` в `packages/translator_core`; `flutter analyze --fatal-infos` и `flutter test` в `apps/translator` |
| Сборка Windows | `scripts\build-windows.ps1` → `dist/ArgosTranslate/` + Inno при наличии `iscc` |
| Smoke Flutter dist | `python scripts\smoke_flutter_dist.py` |
| Smoke sidecar EXE | `python scripts\smoke_sidecar.py` |
| Unit-тесты sidecar (CI) | `pytest tests/ -q -m "not integration"` |
| Все тесты | `pytest tests/ -q` |
| Линтер | `ruff check src tests sidecar` |
| Проверка spec | `python scripts/verify_spec.py` (CTk + ArgosSidecar.spec) |
| Legacy CTk EXE | `venv\Scripts\python.exe -m PyInstaller ArgosTranslator.spec --clean --noconfirm` |
| Сборка (bat, CTk) | `scripts\build.bat` — нужен рабочий `venv` |
| Smoke dist (CTk) | `python scripts\smoke_dist.py` |

Результат Flutter-сборки: `dist/ArgosTranslate/translator.exe` + `sidecar/argos_sidecar.exe`. Legacy CTk: `dist/ArgosTranslator/ArgosTranslator.exe`.

Sidecar: токен через `ARGOS_SIDECAR_TOKEN` (не в argv по умолчанию), `--parent-pid` для watchdog, лог `{log_dir}/sidecar.log`.

## Структура репозитория

```
apps/translator/                # Flutter Windows (основной UI)
packages/translator_core/       # settings v9, sidecar client, LLM SSE
sidecar/                        # HTTP вокруг src/argos_translator
sidecar_entry.py                # PyInstaller entry sidecar
ArgosSidecar.spec               # frozen argos_sidecar (console=False)
scripts/build-windows.ps1       # Flutter Release + sidecar + Inno
scripts/windows/argos-translate.iss
main.py                         # legacy CTk entry
src/argos_translator/
  app.py                        # TranslatorApp — координатор UI, потоков, файлов
  bootstrap/runner.py           # DPI, проверки, mainloop
  config/                       # settings.json v9, paths, constants
  engines/                      # argos_engine, llm_engine, factory
  services/                     # tray, hotkeys, document_io, coordinator, cache
  ui/                           # CustomTkinter: main_window, panels, settings
tests/                          # pytest
hooks/                          # PyInstaller hooks (numpy, ctranslate2, argostranslate)
ArgosTranslator.spec            # release-сборка CTk (console=False)
```

Подробнее для пользователей: [README.md](README.md), сборка: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md).

## Архитектура (куда смотреть при правках)

### Flutter (основной UI)

- [`apps/translator/lib/app.dart`](apps/translator/lib/app.dart) — старт sidecar, супервизия, тройной Ctrl+C, выход
- [`apps/translator/lib/features/session/workspace_controller.dart`](apps/translator/lib/features/session/workspace_controller.dart) — debounce, AUTO-пара, Argos/LLM, Stop
- [`apps/translator/lib/features/shell/main_split.dart`](apps/translator/lib/features/shell/main_split.dart) — шорткаты (Ctrl+Shift+X = swap)
- [`packages/translator_core/`](packages/translator_core/) — settings v9, `SidecarClient`, `LlmClient`
- [`apps/translator/lib/platform/sidecar_process.dart`](apps/translator/lib/platform/sidecar_process.dart) — spawn, `--parent-pid`, перезапуск
- [`sidecar/`](sidecar/) — HTTP, jobs, watchdog

### Legacy CTk UI

- [`src/argos_translator/ui/main_window.py`](src/argos_translator/ui/main_window.py) — тулбар, панели, компактный футер, `MainWindowCallbacks`
- [`src/argos_translator/ui/text_panel.py`](src/argos_translator/ui/text_panel.py) — исходный текст
- [`src/argos_translator/ui/translation_tabs.py`](src/argos_translator/ui/translation_tabs.py) — вкладки Argos/LLM, стриминг текста
- [`src/argos_translator/ui/editor_layout.py`](src/argos_translator/ui/editor_layout.py) — однопанельный режим (`split` / `source` / `translation`)
- [`src/argos_translator/ui/font_scale.py`](src/argos_translator/ui/font_scale.py) — `ui_font()` (13pt UI), `scaled_text_font()` (только поля ввода, до 200%)
- [`src/argos_translator/ui/themes.py`](src/argos_translator/ui/themes.py) — палитра; `text_editor` — цвет текста в редакторах

### Логика движков (общая для sidecar и CTk)

- [`src/argos_translator/app.py`](src/argos_translator/app.py) — legacy координатор
- [`src/argos_translator/services/translation_coordinator.py`](src/argos_translator/services/translation_coordinator.py) — job id, stale jobs, отмена
- [`src/argos_translator/engines/llm_engine.py`](src/argos_translator/engines/llm_engine.py) — SSE-стриминг, чанки файлов (CTk; Flutter LLM — Dart)

### Потоки перевода (Flutter)

```
Ввод текста → смена текста (не selection) → debounce → _resolvePair → Argos NDJSON + LLM SSE
```

- **Argos**: `SidecarClient.translate` → NDJSON `start`/`chunk`/`done`/`error`/`cancelled`
- **LLM**: `LlmClient.translate` → SSE; Stop вызывает `abort()`
- **AUTO**: `resolveAutoPair(detected, preferredTo)`; чип `EN → RU`

### Настройки

- Файл: `%USERPROFILE%\.argos_translate\settings.json`
- Класс: `AppSettings` в [`config/settings.py`](src/argos_translator/config/settings.py) и Dart `packages/translator_core` — версия **9**
- Важные поля: `font_scale`, `editor_layout`, `streaming`, `scroll_sync`, секция `llm`, `active_translation_tab`, `auto_target_lang`, `behavior.triple_copy_enabled`, `behavior.global_hotkey`

## Соглашения при разработке

1. **Минимальный diff** — не рефакторить несвязанный код. Основной UI — Flutter; CTk не развивать.
2. **UI-шрифт CTk** — фиксированный 13pt (`ui_font()`); масштаб слайдера влияет только на `CTkTextbox` в панелях.
3. **Обновление текста перевода (CTk)** — для LLM-стриминга использовать `begin_llm_stream` / `append_llm_stream_text` / `end_llm_stream`.
4. **Потокобезопасность CTk** — обновления UI только из главного потока (`root.after(0, ...)`).
5. **Тесты** — Python в `tests/`; Flutter в `apps/translator/test`; core в `packages/translator_core/test`. Маркер `integration` — реальные модели Argos/LLM.
6. **Сборка** — не добавлять `numpy` в excludes spec; кастомные хуки в `hooks/`. `build-windows.ps1` — только ASCII (PowerShell 5.1).
7. **Коммиты** — только по явной просьбе пользователя; не коммитить `RUN.lnk`, секреты, `.env`.
8. **Язык** — UI и комментарии в коде на русском; имена идентификаторов на английском.

## Типичные задачи

| Задача | Где править |
|--------|-------------|
| Главное окно Flutter | `apps/translator/lib/features/shell/` |
| Поведение перевода Flutter | `workspace_controller.dart`, `translator_core` |
| Sidecar HTTP / jobs | `sidecar/server.py`, `sidecar/jobs.py` |
| AUTO-язык | `text_utils.py` / `translator_core` `TextUtils.resolveAutoPair` |
| LLM API / стриминг | `packages/translator_core/lib/src/llm/` |
| Настройки / миграции | `config/settings.py`, `translator_core` settings, `settings_page.dart` |
| Хоткеи | `main_split.dart`, `selection_capture.dart`, `triple_copy.dart` |
| PyInstaller | `ArgosSidecar.spec` / `ArgosTranslator.spec`, `hooks/`, `scripts/verify_spec.py` |
| Legacy CTk окно | `ui/main_window.py`, колбэки в `app.py` |

## Отладка

- Лог Flutter: `log/app_debug.log` (ротация >2 МБ)
- Лог sidecar: `log/sidecar.log` (RotatingFileHandler, не stdout)
- Debug-сборка CTk с консолью: `pyinstaller ArgosTranslator.debug.spec --clean --noconfirm`
- LLM URL задаётся в настройках Flutter (пустой LOCAL по умолчанию)

## CI

GitHub Actions (`.github/workflows/ci.yml`):

- Ubuntu: Python 3.11/3.12, `pytest -m "not integration"` с coverage ≥80% для `engines`, `services`, `config`, `sidecar`; `ruff check src tests sidecar`; `verify_spec.py` (customtkinter опционален)
- Ubuntu: `dart analyze` / `dart test` / `flutter analyze` / `flutter test`
- Windows: pytest 3.11, `flutter test`, `flutter build windows --release`
- `workflow_dispatch`: опциональная сборка sidecar (PyInstaller) + `smoke_flutter_dist.py`

## Чего избегать

- Запуск сборки/тяжёлых тестов без необходимости в каждом изменении UI
- Правка `PLAN.md` / `CHANGELOG.md` без запроса
- Force push, amend чужих коммитов, изменение git config
- Использование Python 3.14 для production-сборки (несовместимость с argostranslate/ctranslate2)
