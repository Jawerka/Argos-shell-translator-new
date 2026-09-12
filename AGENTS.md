# AGENTS.md — руководство для AI-агентов

**Основной продукт (v1):** Flutter Windows UI (`apps/translator`) + Python sidecar (`python -m sidecar` / frozen `argos_sidecar.exe`). Контракт: [`docs/PRODUCT.md`](docs/PRODUCT.md). Запуск: `scripts/dev.ps1`. Сборка: `scripts/build-windows.ps1` (Flutter Release + sidecar в `{app}/sidecar/` + Inno). Не смешивать PyInstaller `_internal` с корнем Flutter.

Ниже — **legacy CustomTkinter** (не развивать UI; `src/argos_translator` движки и pytest всё ещё нужны sidecar).

Десктопный переводчик **Argos Translate Streaming**: CustomTkinter UI, офлайн Argos + опциональный LLM (OpenAI-compatible API). Основная платформа — **Windows**.

## Быстрый старт

```bash
# Python 3.10–3.12 (рекомендуется; 3.14 — только для части тестов UI, не для сборки)
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
pip install pytest             # или: pip install -e ".[dev]"

python main.py                 # GUI
python -m argos_translator       # то же через пакет
```

Модели Argos: положить `*.argosmodel` в `argos_models/` и выполнить `python install_models.py`.

## Команды

| Задача | Команда |
|--------|---------|
| Flutter GUI | `scripts\dev.ps1` |
| Flutter-тесты | `dart analyze --fatal-infos packages/translator_core`; `dart test` в `packages/translator_core`; `flutter analyze --fatal-infos` и `flutter test` в `apps/translator` |
| Сборка Windows | `scripts\build-windows.ps1` → `dist/ArgosTranslate/` + Inno при наличии `iscc` |
| Smoke Flutter dist | `python scripts\smoke_flutter_dist.py` |
| Unit-тесты sidecar (CI) | `pytest tests/ -q -m "not integration"` |
| Все тесты | `pytest tests/ -q` |
| Линтер | `ruff check src tests` |
| Проверка spec | `python scripts/verify_spec.py` (CTk + ArgosSidecar.spec) |
| Legacy CTk EXE | `venv\Scripts\python.exe -m PyInstaller ArgosTranslator.spec --clean --noconfirm` |
| Сборка (bat, CTk) | `scripts\build.bat` — нужен рабочий `venv` |
| Smoke dist (CTk) | `python scripts\smoke_dist.py` |

Результат Flutter-сборки: `dist/ArgosTranslate/translator.exe` + `sidecar/argos_sidecar.exe`. Legacy CTk: `dist/ArgosTranslator/ArgosTranslator.exe`.

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
  config/                       # settings.json v8, paths, constants
  engines/                      # argos_engine, llm_engine, factory
  services/                     # tray, hotkeys, document_io, coordinator, cache
  ui/                           # CustomTkinter: main_window, panels, settings
tests/                          # pytest (~176 unit-тестов)
hooks/                          # PyInstaller hooks (numpy, ctranslate2, argostranslate)
ArgosTranslator.spec            # release-сборка (console=False)
```

Подробнее для пользователей: [README.md](README.md), сборка: [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md).

## Архитектура (куда смотреть при правках)

### UI

- [`src/argos_translator/ui/main_window.py`](src/argos_translator/ui/main_window.py) — тулбар, панели, компактный футер, `MainWindowCallbacks`
- [`src/argos_translator/ui/text_panel.py`](src/argos_translator/ui/text_panel.py) — исходный текст
- [`src/argos_translator/ui/translation_tabs.py`](src/argos_translator/ui/translation_tabs.py) — вкладки Argos/LLM, стриминг текста
- [`src/argos_translator/ui/editor_layout.py`](src/argos_translator/ui/editor_layout.py) — однопанельный режим (`split` / `source` / `translation`)
- [`src/argos_translator/ui/font_scale.py`](src/argos_translator/ui/font_scale.py) — `ui_font()` (13pt UI), `scaled_text_font()` (только поля ввода, до 200%)
- [`src/argos_translator/ui/themes.py`](src/argos_translator/ui/themes.py) — палитра; `text_editor` — цвет текста в редакторах

### Логика приложения

- [`src/argos_translator/app.py`](src/argos_translator/app.py) — ~1400 строк: перевод, файлы, scroll-sync, LLM worker, настройки
- [`src/argos_translator/services/translation_coordinator.py`](src/argos_translator/services/translation_coordinator.py) — job id, stale jobs, отмена
- [`src/argos_translator/engines/llm_engine.py`](src/argos_translator/engines/llm_engine.py) — SSE-стриминг, чанки файлов

### Потоки перевода

```
Ввод текста → debounce → worker thread → queue/callback → UI (root.after)
```

- **Argos**: `translate_queue` + `_poll_translate_queue`, обновление через `set_argos_text` (полная пересборка чанков)
- **LLM**: `translate_stream` → `on_token` → throttle 50ms → `append_llm_stream_text` (инкрементальная вставка, без мерцания скроллбара)

### Настройки

- Файл: `%USERPROFILE%\.argos_translate\settings.json`
- Класс: `AppSettings` в [`config/settings.py`](src/argos_translator/config/settings.py), версия **8**
- Важные поля: `font_scale`, `editor_layout`, `streaming`, `scroll_sync`, секция `llm`, `active_translation_tab`

## Соглашения при разработке

1. **Минимальный diff** — не рефакторить несвязанный код; UI на CustomTkinter, не веб.
2. **UI-шрифт** — фиксированный 13pt (`ui_font()`); масштаб слайдера влияет только на `CTkTextbox` в панелях.
3. **Обновление текста перевода** — для LLM-стриминга использовать `begin_llm_stream` / `append_llm_stream_text` / `end_llm_stream`, не полный `delete+insert` на каждый токен.
4. **Потокобезопасность** — обновления UI только из главного потока (`root.after(0, ...)`).
5. **Тесты** — добавлять в `tests/`; UI-тесты с фикстурой `ctk_root` из [`tests/conftest.py`](tests/conftest.py). Маркер `integration` — тесты с реальными моделями Argos/LLM.
6. **Сборка** — не добавлять `numpy` в excludes spec; кастомные хуки в `hooks/`.
7. **Коммиты** — только по явной просьбе пользователя; не коммитить `RUN.lnk`, секреты, `.env`.
8. **Язык** — UI и комментарии в коде на русском; имена идентификаторов на английском.

## Типичные задачи

| Задача | Где править |
|--------|-------------|
| Кнопка / layout главного окна | `ui/main_window.py`, колбэки в `app.py` |
| Поведение перевода | `app.py`, `engines/`, `services/translation_coordinator.py` |
| LLM API / стриминг | `engines/llm_engine.py` |
| Настройки / миграции | `config/settings.py`, `ui/settings_dialog.py` |
| Новый тест движка | `tests/test_*_engine.py` |
| PyInstaller | `ArgosTranslator.spec`, `hooks/`, `scripts/verify_spec.py` |

## Отладка

- Лог: `log/app_debug.log` (dev) или `{exe_dir}/log/app_debug.log` (frozen)
- Debug-сборка с консолью: `pyinstaller ArgosTranslator.debug.spec --clean --noconfirm`
- LLM URL задаётся в настройках Flutter (пустой LOCAL по умолчанию); моки в `tests/test_llm_engine.py`

## CI

GitHub Actions (`.github/workflows/ci.yml`): Python 3.11/3.12, `pytest -m "not integration"`, coverage ≥80% для `engines`, `services`, `config`, `ruff check`; отдельный job: `dart analyze` / `dart test` / `flutter analyze` / `flutter test`.

## Чего избегать

- Запуск сборки/тяжёлых тестов без необходимости в каждом изменении UI
- Правка `PLAN.md` / `CHANGELOG.md` без запроса
- Force push, amend чужих коммитов, изменение git config
- Использование Python 3.14 для production-сборки (несовместимость с argostranslate/ctranslate2)
