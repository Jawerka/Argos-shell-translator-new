# AGENTS.md — руководство для AI-агентов

**Основной продукт (v2.1):** Flutter Windows UI (`apps/translator`) + Python sidecar (`python -m sidecar` / frozen `argos_sidecar.exe`). Контракт: [`docs/PRODUCT.md`](docs/PRODUCT.md). Запуск: `scripts/dev.ps1`. Сборка: `scripts/build-windows.ps1` (Flutter Release + sidecar в `{app}/sidecar/` + Inno). Не смешивать PyInstaller `_internal` с корнем Flutter.

Flutter SDK: PATH, `FLUTTER_ROOT`, `.fvm/flutter_sdk` или `%LOCALAPPDATA%\flutter` — [`scripts/resolve-flutter.ps1`](scripts/resolve-flutter.ps1). Не хардкодить личные пути.

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
| Проверка spec | `python scripts/verify_spec.py` |

Результат Flutter-сборки: `dist/ArgosTranslate/translator.exe` + `sidecar/argos_sidecar.exe`.

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
src/argos_translator/
  config/                       # constants, paths
  engines/                      # argos_engine
  services/                     # document_io, coordinator, cache, models
tests/                          # pytest
hooks/                          # PyInstaller hooks (numpy, ctranslate2, argostranslate)
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

### Логика движков (sidecar)

- [`src/argos_translator/services/translation_coordinator.py`](src/argos_translator/services/translation_coordinator.py) — job id, stale jobs, отмена
- [`src/argos_translator/engines/argos_engine.py`](src/argos_translator/engines/argos_engine.py) — офлайн Argos (API / CLI)

### Потоки перевода (Flutter)

```
Ввод текста → смена текста (не selection) → debounce → _resolvePair → Argos NDJSON + LLM SSE
```

- **Argos**: `SidecarClient.translate` → NDJSON `start`/`chunk`/`done`/`error`/`cancelled`
- **LLM**: `LlmClient.translate` → SSE; Stop вызывает `abort()`
- **AUTO**: `resolveAutoPair(detected, preferredTo)`; чип `EN → RU`

### Настройки

- Файл: `%USERPROFILE%\.argos_translate\settings.json`
- Модель: Dart-настройки в [`packages/translator_core`](packages/translator_core/) — версия **9** (Python-модели нет; sidecar `settings.json` не читает)
- Важные поля: `font_scale`, `editor_layout`, `streaming`, `scroll_sync`, секция `llm`, `active_translation_tab`, `auto_target_lang`, `behavior.triple_copy_enabled`, `behavior.global_hotkey`

## Соглашения при разработке

1. **Минимальный diff** — не рефакторить несвязанный код. Основной UI — Flutter.
2. **Тесты** — Python в `tests/`; Flutter в `apps/translator/test`; core в `packages/translator_core/test`. Маркер `integration` — реальные модели Argos/LLM.
3. **Сборка** — не добавлять `numpy` в excludes spec; кастомные хуки в `hooks/`. `build-windows.ps1` — только ASCII (PowerShell 5.1).
4. **Коммиты** — только по явной просьбе пользователя; не коммитить `RUN.lnk`, секреты, `.env`.
5. **Язык** — UI и комментарии в коде на русском; имена идентификаторов на английском.

## Типичные задачи

| Задача | Где править |
|--------|-------------|
| Главное окно Flutter | `apps/translator/lib/features/shell/` |
| Поведение перевода Flutter | `workspace_controller.dart`, `translator_core` |
| Sidecar HTTP / jobs | `sidecar/server.py`, `sidecar/jobs.py` |
| AUTO-язык | `text_utils.py` / `translator_core` `TextUtils.resolveAutoPair` |
| LLM API / стриминг | `packages/translator_core/lib/src/llm/` |
| Настройки / миграции | `translator_core` settings, `settings_page.dart` |
| Хоткеи | `main_split.dart`, `selection_capture.dart`, `triple_copy.dart` |
| PyInstaller | `ArgosSidecar.spec`, `hooks/`, `scripts/verify_spec.py` |

## Отладка

- Лог Flutter: `log/app_debug.log` (ротация >2 МБ)
- Лог sidecar: `log/sidecar.log` (RotatingFileHandler, не stdout)
- LLM URL задаётся в настройках Flutter (пустой LOCAL по умолчанию)

## CI

GitHub Actions (`.github/workflows/ci.yml`):

- Ubuntu: Python 3.11/3.12, `pytest -m "not integration"` с coverage ≥80% для `engines`, `services`, `config`, `sidecar`; `ruff check src tests sidecar`; `verify_spec.py`
- Ubuntu: `dart analyze` / `dart test` / `flutter analyze` / `flutter test`
- Windows: pytest 3.11, `flutter test`, `flutter build windows --release`
- `workflow_dispatch`: опциональная сборка sidecar (PyInstaller) + `smoke_flutter_dist.py`

## Чего избегать

- Запуск сборки/тяжёлых тестов без необходимости в каждом изменении UI
- Правка `CHANGELOG.md` без запроса
- Force push, amend чужих коммитов, изменение git config
- Использование Python 3.14 для production-сборки (несовместимость с argostranslate/ctranslate2)
