# PLAN.md — Ревизия проекта Argos Translate Streaming

> Документ описывает полный план переработки проекта: архитектура, UI, LLM, трей, настройки, сборка EXE.
> Версия плана: **2.1 (UI Polish завершён)** · Дата: 2026-06-06 · Базовый коммит: `73e2670`

### Статус выполнения

| Фаза | Статус | Итог |
|------|--------|------|
| **0** Подготовка | ✅ | pyproject, package layout, deps |
| **1** Рефакторинг | ✅ | `app.py` координатор, services, ui |
| **2** Тёмная тема | ✅ | `themes.py`, live preview в настройках |
| **3** Трей и геометрия | ✅ | трей, DPI, fix winfo/geometry drift |
| **4** Настройки | ✅ | settings v7, 7 вкладок |
| **5** LLM | ✅ | both_adaptive, streaming, retry, fallback |
| **6** Argos | ✅ | chunks, cache, coordinator, cancel |
| **7** Документы | ✅ | document_io, DnD, encodings fixtures |
| **8** EXE | ✅ | spec, hooks, frozen bootstrap, **сборка OK** (dev) |
| **9** Тесты/CI | ✅ | pytest, ruff, CI, release checklist |
| **10** UI Polish v2 | ✅ | §18.1–18.7; §18.8 backlog; §18.9 — ручная DPI QA |

**Ручная QA (после релиза):** запуск `dist/ArgosTranslator/ArgosTranslator.exe` на чистой Windows **без Python** — см. §13.6.

**Документация:** `README.md`, `BUILD_INSTRUCTIONS.md`, `CHANGELOG.md`, `docs/UI_BASELINE.md`.

**Текущий UI (baseline v2.0, `73e2670`):** CustomTkinter, flat layout, две колонки 50/50, popup «Файл ▾», segmented Argos/LLM, 7 вкладок настроек.

---

## Оглавление

1. [Цели и принципы](#1-цели-и-принципы)
2. [Принятые решения](#2-принятые-решения)
3. [Текущие проблемы (аудит)](#3-текущие-проблемы-аудит)
4. [Целевая архитектура](#4-целевая-архитектура)
5. [Фаза 0 — Подготовка](#5-фаза-0--подготовка)
6. [Фаза 1 — Рефакторинг и аудит](#6-фаза-1--рефакторинг-и-аудит)
7. [Фаза 2 — Тёмная тема](#7-фаза-2--тёмная-тема)
8. [Фаза 3 — Трей, окно и геометрия](#8-фаза-3--трей-окно-и-геометрия)
9. [Фаза 4 — Окно настроек](#9-фаза-4--окно-настроек)
10. [Фаза 5 — Интеграция LLM](#10-фаза-5--интеграция-llm)
11. [Фаза 6 — Оптимизация перевода](#11-фаза-6--оптимизация-перевода)
12. [Фаза 7 — Перевод документов](#12-фаза-7--перевод-документов)
13. [Фаза 8 — Сборка EXE и модели Argos](#13-фаза-8--сборка-exe-и-модели-argos)
14. [Фаза 9 — Тесты, документация, CI](#14-фаза-9--тесты-документация-ci)
15. [Структура settings.json (целевая)](#15-структура-settingsjson-целевая)
16. [Порядок выполнения и оценка](#16-порядок-выполнения-и-оценка)
17. [Риски](#17-риски)
18. [Фаза 10 — UI Polish v2](#18-фаза-10--ui-polish-v2)

---

## 1. Цели и принципы

### Главная цель

Превратить монолитный прототип в **поддерживаемое десктоп-приложение** с:

- тёмной темой по умолчанию;
- корректной работой трея (одиночный клик → разворот окна);
- окном настроек (прозрачность, движки, LLM, поведение);
- двумя движками перевода: **Argos (офлайн)** и **LLM (OpenAI-compatible API, локальный или OpenRouter)**;
- переводом **текстовых файлов** (TXT, MD и др.) без сторонних предустановок;
- **устойчивым запоминанием геометрии окна** (DPI, масштабирование Windows, несколько мониторов);
- надёжной portable-сборкой EXE с рабочими моделями Argos.

### Принципы разработки

| Принцип | Описание |
|---------|----------|
| Минимальный diff на этап | Каждая фаза — отдельный логический коммит/PR |
| Обратная совместимость настроек | Старый `settings.json` мигрируется автоматически |
| Graceful degradation | Нет LLM / нет моделей / нет трея — приложение работает с ограничениями |
| Один запрос LLM на задачу | Никогда не дробить текст на предложения для LLM |
| Argos остаётся офлайн | LLM — опциональный второй движок, не замена |
| Frozen-first | Все пути (модели, логи, настройки) учитывают PyInstaller |
| Адаптивный LLM | Оба движка работают параллельно; в UI видна только **выбранная** вкладка |
| Геометрия — structured state | Не полагаться только на строку `geometry` Tkinter |

---

## 2. Принятые решения

> Решения пользователя, зафиксированные в плане. Реализовать как описано ниже.

| # | Вопрос | Решение |
|---|--------|---------|
| D1 | Режим `both_adaptive` | **Оба движка (Argos + LLM) работают параллельно**, но в UI **видна только выбранная вкладка** (переключатель Argos / LLM). Если LLM занята/недоступна — работает только Argos; LLM-вкладка показывает статус |
| D2 | Крестик (X) | **Сворачивать в трей**. Полный выход — только через **ПКМ → Выход** в меню трея |
| D3 | Модели в bundle | **en→ru и ru→en** (оба направления, базовый набор). Остальные пары — **докачка по необходимости** |
| D8 | Кодировка файлов | **Автоопределение** (скрыто от пользователя). UTF-8/cp1251 — частые случаи; для экзотических — `charset-normalizer` / эвристики. **Обязательны тесты** |
| D4 | API key LLM | **Не обязателен** для LOCAL. **Обязателен** для OpenRouter. Хранится в настройках, маскируется в UI |
| D5 | URL LLM по умолчанию | `http://192.168.88.41:8989/v1` (провайдер LOCAL) |
| D6 | Перевод файлов | TXT, MD и другие **plain-text** форматы (открытый текст, без docx/pdf и т.п.) |
| D7 | Геометрия окна | Запоминать позицию и размер **устойчиво** к DPI, масштабированию Windows, смене мониторов |
| D9 | Включение LLM | **Переключатель в настройках** `llm.enabled`. При выключении — только Argos, вкладка LLM скрыта, worker не запускается |
| D10 | Провайдер LLM | Выбор из списка: **LOCAL**, **OpenRouter**, **Custom**. Пресет подставляет URL и правила API key; Custom — ручной URL |

---

## 3. Текущие проблемы (аудит)

### Архитектура

| # | Проблема | Где | Критичность |
|---|----------|-----|-------------|
| A1 | ~~Весь код в одном файле `main.py` (~2175 строк)~~ | `app.py` + пакет `src/argos_translator/` | ✅ |
| A2 | Нет `pyproject.toml`, нет entry points | корень | Средняя |
| A3 | Нет формальных тестов (только ручной скрипт) | `test_translation.py` | Средняя |
| A4 | `make_sentence_chunks()` объявлен, но не используется | `TextUtils` | Низкая |

### Баги и несоответствия

| # | Проблема | Где | Критичность |
|---|----------|-----|-------------|
| B1 | README указывает лог `~/.argos_translate/app_streaming.log`, код пишет в `log/app_debug.log` | README vs `LoggingConfig` | Средняя |
| B2 | Разные пути моделей на Windows: `install_models.py` использует fallback `~/.argos-translate/packages`, `main.py` — только Linux-путь | `install_models.py`, `main.py` | **Высокая** |
| B3 | Установка моделей — простое копирование `.argosmodel`, а не `package.install_from_path()` | `main.py`, `install_models.py` | **Высокая** |
| B4 | Трей: одиночный клик не разворачивает окно — нет `MenuItem(..., default=True)` | `_create_tray()` | **Высокая** |
| B5 | Попытки `on_click` / `on_double_click` через `setattr` — нестандартный API pystray | `_create_tray()` | Средняя |
| B6 | `_show_window()` уничтожает трей (`_stop_tray`) — при повторном сворачивании иконка пересоздаётся | `_show_window`, `_hide_to_tray` | Средняя |
| B7 | AUTO-режим жёстко переключает только `ru ↔ en` | `translate()` | Средняя |
| B8 | `DEBUG: print(...)` при импорте модулей | `main.py:142-219` | Низкая |
| B9 | `ArgosTranslator.spec`: `console=True` + противоречивые excludes для numpy | spec | Средняя |
| B10 | `_on_close()` вызывает `sys.exit(0)` — мешает тестам и встраиванию | `_on_close()` | Низкая |
| B11 | Смешанный RU/EN интерфейс без системы i18n | UI | Низкая |
| B12 | `log/app_debug.log` в git (шум в diff) | `.gitignore` | Низкая |

### UX (исходный аудит v1 — до рефакторинга)

| # | Проблема | Критичность | Статус после `73e2670` |
|---|----------|-------------|------------------------|
| U1 | Нет тёмной темы | Высокая | ✅ `themes.py`, dark по умолчанию |
| U2 | Нет окна настроек | Высокая | ✅ `SettingsDialog`, 7 вкладок |
| U3 | Нет выбора движка перевода | Высокая | ✅ Argos / LLM, both_adaptive |
| U4 | Закрытие окна = выход | Средняя | ✅ крестик → трей |
| U5 | Нет индикации движка | Средняя | ✅ бейджи Argos/LLM, LLM indicator |
| U6 | Геометрия «прыгает» (DPI) | **Высокая** | ✅ `geometry_units`, capture через `geometry()` |
| U7 | Нет перевода файлов | Высокая | ✅ document_io, DnD |

### 3.1. Сводка UI-аудитов (июнь 2026)

Проанализированы **три независимых аудита** UI после коммита `73e2670`. Ниже — что уже есть в коде, что отклонено и что берём в фазу 10.

#### Уже реализовано (не дублировать в плане)

| Область | Реализация | Файлы |
|---------|------------|-------|
| CustomTkinter, модульный UI | Пакет `src/argos_translator/ui/` | `main_window.py`, `widgets.py` |
| Две колонки редактора 50/50 | `uniform="editor_col"`, общая grid-структура панелей | `main_window.py`, `text_panel.py`, `translation_tabs.py` |
| Копировать / Очистить / Вставить | Кнопки в панелях | `text_panel.py`, `translation_tabs.py` |
| Горячие клавиши | Ctrl+Enter, Ctrl+,, Ctrl+Shift+C | `app.py`, подсказки в status |
| Поток + синхр. прокрутка | Checkbox в toolbar + tooltips | `main_window.py` |
| Статус + прогресс файла | Status card, progress bar | `main_window.py` |
| Меню файла без menubar | Popup «Файл ▾» | `file_menu.py` |
| Масштаб шрифта | Slider в настройках | `settings_dialog.py`, `font_scale.py` |
| Flat layout (осознанный выбор) | `CORNER_RADIUS=0`, spacing=0 | `layout_config.py` |

#### Аудит A — «Визуальная система и иерархия» (актуален)

| # | Предложение | Решение для фазы 10 | Приоритет |
|---|-------------|---------------------|-----------|
| A1 | Дизайн-токены (`UIStyle`, radii, heights) | ✅ Принять — `ui/style.py` или расширить `layout_config.py` | P0 |
| A2 | Шапка: лево / центр / право (меню · языки · действия) | ✅ Принять — рефактор `build_main_window` toolbar | P0 |
| A3 | Панели как «card editor» (рамка, заголовок, статус) | ⚠️ Частично — мягкие рамки и отступы **без** отказа от flat; radius 8–12, не 16+ | P1 |
| A4 | Упростить кнопки toolbar (1 primary + overflow) | ✅ Принять — «Файл», чекбоксы → меню «Ещё ▾» | P1 |
| A5 | Footer: статус · движок · прогресс (3 колонки) | ✅ Принять — grid footer вместо «случайного» текста | P1 |
| A6 | Настройки: sidebar или секции с описаниями | ✅ Принять — sidebar nav + content pane | P2 |
| A7 | Единые отступы, без magic numbers | ✅ Принять — вернуть `Spacing.*` > 0 точечно | P0 |

#### Аудит B — «Простой CTk-переводчик» (устарел)

| # | Предложение | Решение | Приоритет |
|---|-------------|---------|-----------|
| B1 | Вертикальный макет: ввод сверху, вывод снизу | ❌ Отклонено — продукт уже двухколоночный streaming-редактор | — |
| B2 | Правая панель «История переводов» | ⏸ Отложено — отдельная фича, не UI-polish | P3 |
| B3 | Озвучка (pyttsx3) | ⏸ Backlog | P3 |
| B4 | Блокировка кнопки «Перевести» | ✅ Уже частично через coordinator; усилить disabled state на primary | P2 |

#### Аудит C — «Современный polish» (выборочно)

| # | Предложение | Решение | Приоритет |
|---|-------------|---------|-----------|
| C1 | Тени / pseudo-elevation карточек | ❌ Не в v2.1 — конфликтует с flat; опционально в v2.2 «elevated theme» | P3 |
| C2 | Счётчик символов в заголовке панели | ✅ Принять | P1 |
| C3 | Акцентная полоска у заголовка | ⚠️ Опционально, если не перегружает flat | P2 |
| C4 | Смена палитры на indigo `#6366f1` | ❌ Отклонено — сохраняем UI-for-ytdlp (`#16a6ff`) | — |
| C5 | Ripple / fade анимации | ❌ Отложено — CTk/Tk ограничения, низкий ROI | P3 |
| C6 | Круглая кнопка swap языков | ⚠️ Микро-улучшение `language_selector.py` | P2 |

#### Принцип фазы 10

> **«Structured flat»** — сохранить плоский минимализм, добавить **иерархию через сетку, отступы и типографику**, а не через тени и скругления везде.

#### Новые UX-задачи (post-`73e2670`)

| # | Проблема | Критичность |
|---|----------|-------------|
| U8 | Toolbar перегружен короткими элементами в одну строку | Средняя | ✅ 3-zone + «Ещё ▾» |
| U9 | `Spacing`/`CARD_PAD*` = 0 — UI «склеен» | Средняя | ✅ tokens v2.1 |
| U10 | Настройки — плотный tabview, плохая сканируемость | Средняя | 🔄 SECTION_GAP; sidebar pending |
| U11 | Статусная строка не структурирована (left/center/right) | Низкая | ✅ footer grid |
| U12 | `docs/UI_BASELINE.md` не отражает flat v2.1 | Низкая | ✅ v2.1 |

### Геометрия окна (текущие недостатки)

| # | Проблема | Последствие |
|---|----------|-------------|
| G1 | Сохраняется только `root.geometry()` как строка | ✅ structured `WindowState` + `geometry_units` |
| G2 | Нет DPI awareness при старте процесса | ✅ `bootstrap/dpi.py` |
| G3 | Нет clamp к видимой области экрана | ✅ `clamp_to_visible_area` |
| G4 | Не сохраняется состояние maximized | ✅ `state: zoomed` |
| G5 | Центрирование перезаписывает геометрию | ✅ restore после `deiconify` |
| G6 | Capture через `winfo_*` вместо `geometry()` — рост окна на каждом запуске | ✅ fix в `73e2670` |

---

## 4. Целевая архитектура

### Структура каталогов

```
Argos-shell-translator-new/
├── pyproject.toml                 # entry point, зависимости, версия
├── PLAN.md                        # этот файл
├── README.md
├── requirements.txt               # оставить для совместимости или заменить на pyproject
│
├── src/
│   └── argos_translator/
│       ├── __init__.py
│       ├── __main__.py            # python -m argos_translator
│       ├── app.py                 # TranslatorApp (тонкий координатор)
│       │
│       ├── config/
│       │   ├── constants.py       # TranslationConstants, DefaultLanguages
│       │   ├── settings.py        # dataclass Settings, load/save/migrate
│       │   ├── llm_providers.py   # пресеты LOCAL / OpenRouter / Custom (D10)
│       │   └── paths.py           # get_resource_path, packages_dir, log_dir
│       │
│       ├── engines/
│       │   ├── base.py            # Protocol TranslationEngine
│       │   ├── argos_engine.py    # API / CLI / ctranslate2 fallback
│       │   ├── llm_engine.py      # OpenAI-compatible, SSE streaming
│       │   └── factory.py         # create_engine(name, settings)
│       │
│       ├── services/
│       │   ├── model_manager.py   # install/check/copy models
│       │   ├── llm_health.py      # доступность LLM, TTL-кэш, busy detection
│       │   ├── document_io.py     # чтение/запись plain-text файлов
│       │   └── encoding.py        # detect_encoding(), fallback-цепочка (D8)
│       │   ├── clipboard.py
│       │   ├── hotkeys.py
│       │   └── tray.py            # TrayManager
│       │
│       ├── ui/
│       │   ├── main_window.py
│       │   ├── text_panel.py
│       │   ├── language_selector.py
│       │   ├── settings_dialog.py
│       │   ├── themes.py          # dark (default) / light
│       │   ├── translation_tabs.py # переключатель Argos/LLM (одна видима, оба в фоне)
│       │   └── window_state.py    # DPI-aware save/restore геометрии
│       │
│       └── utils/
│           ├── imports.py         # safe_import, module status
│           └── text_utils.py
│
├── tests/
│   ├── test_text_utils.py
│   ├── test_settings.py
│   ├── test_argos_engine.py
│   ├── test_llm_engine.py
│   ├── test_window_state.py
│   ├── test_document_io.py
│   ├── test_encoding_detection.py
│   ├── test_llm_providers.py
│   ├── test_llm_enabled.py
│   ├── fixtures/
│   │   └── encodings/             # utf8, cp1251, cp866, koi8-r, latin1, …
│   └── conftest.py
│
├── assets/
│   ├── argos_translate.ico
│   ├── argos_translate.png
│   └── themes/                    # опционально: ttk theme files
│
├── argos_models/                  # bundle .argosmodel (не в git)
├── scripts/
│   ├── install_models.py          # тонкая обёртка → model_manager
│   └── build.bat                  # сборка EXE
│
├── hooks/                         # PyInstaller hooks
│   ├── hook-argostranslate.py
│   └── hook-numpy.py
│
├── ArgosTranslator.spec
├── run.bat
└── log/                           # в .gitignore
```

### Диаграмма потоков (целевая)

```mermaid
flowchart TB
    subgraph UI
        MW[MainWindow]
        Tabs[TranslationTabs\nArgos | LLM]
        SD[SettingsDialog]
    end

    subgraph Engines
        AF[EngineFactory]
        AE[ArgosEngine]
        LE[LLMEngine]
    end

    subgraph Services
        TM[TrayManager]
        MM[ModelManager]
        HK[Hotkeys]
    end

    MW --> Tabs
    MW --> SD
    MW --> AF
    AF --> AE
    AF --> LE
    MW --> TM
    MW --> HK
    main --> MM
    AE --> MM
```

---

## 5. Фаза 0 — Подготовка

### 5.1. Инфраструктура

- [x] Добавить `pyproject.toml` с `[project.scripts] argos-translator = argos_translator.__main__:main`
- [x] Добавить зависимость `charset-normalizer>=3.0` (автоопределение кодировки, D8)
- [x] Создать структуру `src/argos_translator/`
- [x] Перенести `assets/` (ico, png) из корня
- [x] Обновить `.gitignore`: `log/`, `*.log`, `dist/`, `build/`
- [x] Зафиксировать целевую версию Python: **3.10–3.12** (в README и pyproject)

### 4.2. Baseline

- [x] Запустить `test_translation.py` — baseline через `tests/test_translation_integration.py`
- [x] Сохранить описание UI → `docs/UI_BASELINE.md`
- [x] Проверить работу на Windows с установленными моделями en↔ru (`test_translation_integration.py`)

**Критерий готовности:** проект запускается из `src/` без регрессий.

---

## 6. Фаза 1 — Рефакторинг и аудит

### 5.1. Разделение `main.py`

Порядок выноса (от безопасного к рискованному):

1. [x] `config/paths.py`, `config/constants.py`
2. [x] `utils/imports.py`, `utils/text_utils.py`
3. [x] `engines/argos_engine.py` (+ ctranslate2 fallback)
4. [x] `config/settings.py`
5. [x] `ui/text_panel.py`, `ui/language_selector.py`, `ui/themes.py`
6. [x] `services/tray.py`, `services/hotkeys.py`, `services/clipboard.py`
7. [x] `services/model_manager.py` (`has_pair`, `install_file`, `get_packages_dir`)
8. [x] `app.py` + `ui/main_window.py`
9. [x] `__main__.py` — точка входа; `bootstrap/runner.py` — диагностика и mainloop

`main.py` в корне — thin-wrapper:

```python
from argos_translator.bootstrap.runner import main
if __name__ == "__main__":
    main()
```

**Критерий готовности:** ✅ функциональный паритет; **117** pytest проходят; `app.py` ~1200 строк (координатор, без tray/UI layout).

### 5.2. Исправления при рефакторинге

- [x] **B2**: единая функция `get_argos_packages_dir()` в `paths.py` (+ `ModelManager`, `install_models.py`)
- [x] **B3**: установка через `argostranslate.package.install_from_path()` + `update_package_index()`
- [x] **B8**: убрать все `print("DEBUG:...")`, заменить на `logger.debug`
- [x] **B10**: `_on_close()` без `sys.exit(0)` — только `root.destroy()`
- [x] **B7**: AUTO — определять язык, целевой выбирать из настроек (`auto_target` или последний выбранный TO)
- [x] **A4**: `make_sentence_chunks()` используется в Argos worker

### 5.3. ModelManager

```python
class ModelManager:
    def get_packages_dir() -> Path
    def list_installed_pairs() -> list[str]
    def install_from_bundle(bundle_dir: Path) -> int
    def install_file(path: Path) -> bool
    def has_pair(from_code, to_code) -> bool
```

**Критерий готовности:** функциональный паритет с текущим `main.py`, все тесты baseline проходят.

Дополнительно (целевая архитектура, опционально):

- [x] `engines/base.py` — Protocol `TranslationEngine`
- [x] `engines/factory.py` — `create_engine(name, settings)`

---

## 7. Фаза 2 — Тёмная тема

### 6.1. Требования

- Тёмная тема — **по умолчанию**
- Расположение элементов **не меняется**
- Поддержка `ttk` виджетов и `ScrolledText` (не ttk — кастомные цвета)

### 6.2. Реализация (`ui/themes.py`)

#### Палитра (Dark — default)

| Элемент | Цвет |
|---------|------|
| Фон окна / Frame | `#1e1e1e` |
| Фон панелей | `#252526` |
| Текст основной | `#d4d4d4` |
| Текст вторичный / hints | `#858585` |
| Акцент / кнопка primary | `#0e639c` |
| Акцент hover | `#1177bb` |
| Границы | `#3c3c3c` |
| Text widget bg | `#1e1e1e` |
| Text widget fg | `#d4d4d4` |
| Selection | `#264f78` |
| Insert cursor | `#d4d4d4` |
| Combobox dropdown | `#2d2d2d` |

#### Подход

1. **ttk.Style** — кастомная тема `argos_dark`:
   - `TFrame`, `TLabel`, `TButton`, `TCheckbutton`, `TCombobox`, `TNotebook` (для вкладок LLM)
   - На Windows: `style.theme_use('clam')` как база (позволяет менять цвета)
2. **ScrolledText** — `text.config(...)` напрямую
3. **Корневое окно** — `root.configure(bg=...)`
4. Светлая тема — опционально в настройках (`theme: "light"`)

### 6.3. Нюансы

- [x] Combobox на Windows: `style.map('TCombobox', fieldbackground=...)`
- [x] Скроллбары: `style.configure('Vertical.TScrollbar', ...)`
- [x] Иконка трея: fallback «A» на тёмном фоне + `assets/argos_translate.ico`
- [x] Settings dialog наследует ту же тему через `Toplevel` + `apply_theme(widget)`
- [x] При смене темы в настройках — `apply_theme()` без перезапуска (preview)

### 6.4. Функция применения

```python
def apply_theme(root: tk.Tk, theme: str = "dark") -> ttk.Style:
    """Применить тему ко всему дереву виджетов."""
```

**Критерий готовности:** все виджеты читаемы, нет белых «пятен», контраст достаточный.

---

## 8. Фаза 3 — Трей, окно и геометрия

### 8.1. Одиночный клик → разворот (B4, B5)

**Корневая причина:** pystray на Windows требует `MenuItem(..., default=True)` для действия по левому клику.

**Исправление в `services/tray.py`:**

```python
menu = pystray.Menu(
    pystray.MenuItem("Показать", on_show, default=True),  # ← левый клик
    pystray.MenuItem("Выход", on_exit),
)
icon = pystray.Icon("argos_translate", image, "Argos Translate", menu)
```

- [x] Удалить неработающие `setattr(on_click/on_double_click)` — используется `MenuItem(..., default=True)`
- [x] Проверить `pystray.Icon.HAS_DEFAULT_ACTION` при старте (логировать)
- [x] На Linux: документировать `PYSTRAY_BACKEND=gtk` если default action не работает (README)

### 8.2. Жизненный цикл трея (B6) — **решение D2**

**Зафиксированное поведение:**

| Действие | Результат |
|----------|-----------|
| Крестик (X) | Сворачивание в трей (`withdraw`), приложение **не завершается** |
| Сворачивание (Win+↓ / кнопка «—») | Сворачивание в трей |
| Левый клик по иконке трея | Разворот окна (`deiconify` + `lift`) |
| ПКМ по иконке → «Выход» | Корректное завершение (`_on_close`) |
| Copy & Hide | Копирование + сворачивание в трей |

**TrayManager:**

```python
class TrayManager:
    def ensure_icon_running()   # одна иконка на всё время работы приложения
    def show_window()
    def hide_window()
    def quit_app()              # только из меню ПКМ «Выход»
```

- [x] Иконка создаётся **при старте приложения** (или при первом hide), живёт до выхода
- [x] При показе окна иконка **не уничтожается** — остаётся в трее
- [x] `WM_DELETE_WINDOW` → `_hide_to_tray()`, **не** `destroy()`
- [x] Меню трея (ПКМ): **Показать**, **Настройки** (опционально), **Выход**
- [x] Убрать режим `close_exits` — крестик всегда в трей (решение D2)

### 8.3. Старт в трее

- [x] Настройка `start_minimized_to_tray: bool` — запуск без показа окна, только иконка

### 8.4. Запоминание геометрии окна (DPI, масштабирование, мониторы)

> **Цель:** окно после перезапуска появляется **в том же месте и размере**, независимо от DPI, масштаба Windows (100%/125%/150%), количества мониторов и перестановки дисплеев.

#### 8.4.1. Почему `geometry` строки недостаточно

Tkinter `geometry("1000x700+100+100")` хранит **пиксели текущей сессии**. Проблемы:

- при смене DPI Windows (100% → 150%) те же «логические» координаты дают другой физический результат;
- при отключении монитора `(x=2400, y=100)` оказывается вне экрана;
- `winfo` на Windows до DPI awareness возвращает масштабированные значения;
- maximized состояние не кодируется в geometry;
- `_setup_window()` сейчас **центрирует** окно после load — перезаписывает сохранённую позицию (G5).

#### 8.4.2. DPI Awareness (Windows) — обязательно до `tk.Tk()`

```python
# bootstrap/dpi.py — вызывать ДО создания root
def enable_dpi_awareness():
    if sys.platform == "win32":
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor V2
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()  # fallback Win7/8
            except Exception:
                pass
```

- [x] Вызов в `runner.main()` **до** `tk.Tk()`
- [x] Для PyInstaller: manifest `dpiAwareness` / `dpiAware` в spec (`assets/app.manifest`)
- [x] Логировать: `GetDpiForWindow`, `tk scaling`, версия Windows (`log_dpi_info`)

#### 8.4.3. Структура сохранения (`WindowState`)

Хранить **структурированный объект**, не только строку:

```json
"window": {
  "state": "normal",
  "x": 100,
  "y": 100,
  "width": 1000,
  "height": 700,
  "monitor_hint": {
    "work_area": [0, 0, 1920, 1040],
    "dpi": 96,
    "device_name": "\\\\.\\DISPLAY1"
  },
  "dpi_scale": 1.0,
  "tk_scaling": 1.0,
  "geometry_legacy": "1000x700+100+100"
}
```

| Поле | Назначение |
|------|------------|
| `state` | `normal` / `zoomed` (maximized на Windows) / `iconic` не сохранять — при старте всегда normal или zoomed |
| `x`, `y`, `width`, `height` | Позиция и размер в **пикселях рабочей области** на момент сохранения |
| `monitor_hint` | Привязка к монитору: work area + DPI + имя устройства |
| `dpi_scale` | `dpi / 96.0` на момент сохранения |
| `geometry_legacy` | Для миграции v1; после миграции не использовать |

#### 8.4.4. Модуль `ui/window_state.py`

```python
@dataclass
class WindowState:
    state: str = "normal"
    x: int = 100
    y: int = 100
    width: int = 1000
    height: int = 700
    monitor_hint: dict | None = None
    dpi_scale: float = 1.0

class WindowStateManager:
    def capture(root: tk.Tk) -> WindowState: ...
    def restore(root: tk.Tk, state: WindowState, settings: UIConfig) -> None: ...
    def clamp_to_visible_area(state: WindowState) -> WindowState: ...
    def find_best_monitor(hint: dict) -> MonitorInfo: ...
```

#### 8.4.5. Алгоритм сохранения

Триггеры сохранения:

- [x] При сворачивании в трей (перед `withdraw`) — `_persist_window_state()`
- [x] При выходе из приложения (меню трея «Выход») — `_persist_window_state()`
- [x] При изменении размера/позиции — **debounce 500 мс** (`WINDOW_SAVE_DEBOUNCE_MS`)
- [x] Не сохранять во время programmatic restore (`_skip_geometry_save`)

```python
def capture(root):
    state = root.state()  # 'normal', 'zoomed', 'iconic'
    if state == 'iconic':
        return last_saved_state  # не перезаписывать при скрытии в трей

    x = root.winfo_x()
    y = root.winfo_y()
    w = root.winfo_width()
    h = root.winfo_height()
    # + monitor_hint через ctypes (MonitorFromWindow, GetMonitorInfo, GetDpiForMonitor)
```

#### 8.4.6. Алгоритм восстановления

```
1. enable_dpi_awareness()  # уже выполнено
2. root = tk.Tk()
3. root.withdraw()         # скрыть до применения геометрии — нет «прыжка»
4. Загрузить WindowState из settings
5. Если monitor_hint есть:
     a. Найти монитор с ближайшим work_area / device_name
     b. Если монитор не найден → primary monitor
6. Масштабная коррекция (если dpi_scale изменился):
     - НЕ масштабировать x/y/w/h слепо (Per-Monitor V2 уже даёт правильные координаты)
     - Только clamp к текущей work area
7. clamp_to_visible_area():
     - x, y внутри [work_left, work_right - min_width]
     - width  ∈ [min_width, work_width]
     - height ∈ [min_height, work_height]
     - Минимум 30% окна видимо (не только заголовок)
8. root.geometry(f"{w}x{h}+{x}+{y}")
9. Если state == "zoomed": root.state("zoomed")
10. root.deiconify()
11. Убрать принудительное центрирование из _setup_window (G5)
```

#### 8.4.7. Сценарии и ожидаемое поведение

| Сценарий | Поведение |
|----------|-----------|
| Обычный перезапуск | Окно в той же позиции и размере |
| DPI 100% → 150% | Окно остаётся на том же мониторе, clamp к work area; без «улёта» за экран |
| Отключили второй монитор | Окно переносится на primary, **сохраняя размер**, позиция clamp |
| Сменили разрешение (1920→2560) | Позиция пропорционально не пересчитывается — clamp к новой work area |
| Maximised → перезапуск | Открывается maximised на том же мониторе |
| Первый запуск (нет settings) | Центр primary monitor, размер по умолчанию 1000×700 |
| Окно больше экрана (смена монитора) | Уменьшить до `work_area - margin` |
| RDP / удалённый рабочий стол | Сохранять как обычно; при другом DPI на reconnect — clamp |
| Несколько экземпляров приложения | Один `settings.json` — последний экземпляр wins (документировать) |

#### 8.4.8. Windows API (через `ctypes`)

- [x] `MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)`
- [x] `GetMonitorInfoW` → `rcWork` (без панели задач)
- [x] `GetDpiForMonitor` (shcore) → DPI монитора
- [x] `root.winfo_id()` → HWND для привязки к монитору

#### 8.4.9. Linux / macOS (fallback)

| ОС | Подход |
|----|--------|
| Linux | `winfo_x/y/width/height` + `root.winfo_screenwidth/height`; clamp; без monitor_hint |
| macOS | Аналогично; учесть Retina (`tk scaling` может быть 2.0) |

Полный Per-Monitor на Linux не гарантируется — но clamp решает 90% случаев.

#### 8.4.10. Исправление G5

- [x] **Удалить** принудительное центрирование после load — только `first_run`
- [x] Центрирование **только** при первом запуске (нет settings.json)
- [x] Порядок: `Tk()` → `withdraw()` → restore → build_ui → `deiconify()`

#### 8.4.11. Тесты (`test_window_state.py`)

- [x] `clamp` — окно за правым краем → перенос влево
- [x] `clamp` — окно больше экрана → уменьшение
- [x] Миграция v1 `geometry` string → `WindowState`
- [x] `state=zoomed` сохраняется и восстанавливается
- [x] debounce save не чаще 1 раз / 500ms

**Критерий готовности фазы 3:** левый клик по трею разворачивает окно; крестик сворачивает в трей; выход только из ПКМ; окно не прыгает при перезапуске и смене DPI.

---

## 9. Фаза 4 — Окно настроек

### 9.1. Точка входа

- Кнопка **⚙ Настройки** в `control_frame` (рядом с Translate)
- Горячая клавиша: `Ctrl+,` (опционально)

### 9.2. Вкладки диалога

#### Вкладка «Внешний вид»

| Параметр | Тип | По умолчанию | Примечание |
|----------|-----|--------------|------------|
| `theme` | select: dark / light | `dark` | |
| `window_opacity` | slider 0.3–1.0 | `1.0` | `root.attributes('-alpha', val)`; **только Windows/macOS** |
| `font_size` | int 10–18 | `13` | для текстовых панелей |
| `font_family` | select | `Consolas` | |

**Нюансы прозрачности:**

- На Linux большинство WM не поддерживают `-alpha` — показать предупреждение, disable slider
- При opacity < 1.0 предупредить о возможных артефактах при перетаскивании
- Применять live preview при движении слайдера
- Сохранять в settings при «ОК»

#### Вкладка «Перевод»

| Параметр | Тип | По умолчанию |
|----------|-----|--------------|
| `default_engine` | `both_adaptive` (фиксировано D1) | `both_adaptive` |
| `streaming_enabled` | bool | `true` |
| `debounce_ms` | int 300–2000 | `700` |
| `llm_debounce_ms` | int 500–3000 | `1200` |
| `scroll_sync` | bool | `true` |
| `auto_detect` | bool | `true` |
| `auto_target_lang` | code | `ru` |

#### Вкладка «LLM»

**Верхняя строка — главный переключатель (D9):**

```
[ ✓ ] Использовать LLM-перевод          ← llm.enabled
```

При снятии галочки — все поля ниже **disabled** (серые), изменения сохраняются, но LLM не вызывается до повторного включения.

| Параметр | Тип | По умолчанию | Примечание |
|----------|-----|--------------|------------|
| `llm.enabled` | **bool (checkbox)** | `true` | **D9** — главный выключатель LLM |
| `llm.provider` | **select** | `local` | **D10** — `local` / `openrouter` / `custom` |
| `llm.base_url` | str | см. пресет | Автозаполнение при смене провайдера; редактируемо для Custom |
| `llm.model` | str | `""` | Список моделей — `GET /v1/models` при «Проверить» |
| `llm.api_key` | str (masked) | `""` | Обязателен для OpenRouter; пусто для LOCAL |
| `llm.auth_header` | select | `auto` | `auto` / `Bearer` / `api-key` |
| `llm.temperature` | float 0–1 | `0.3` | |
| `llm.max_tokens` | int | `4096` | |
| `llm.system_prompt` | text | см. §10.6 | |
| `llm.timeout_sec` | int | `120` | LOCAL: 120; OpenRouter: 180 |
| `llm.stream` | bool | `true` | |

**Пресеты провайдеров (`config/llm_providers.py`, D10):**

| Провайдер | `provider` id | URL по умолчанию | API key | Доп. заголовки |
|-----------|---------------|------------------|---------|----------------|
| **LOCAL** | `local` | `http://192.168.88.41:8989/v1` | не нужен | — |
| **OpenRouter** | `openrouter` | `https://openrouter.ai/api/v1` | **обязателен** | `HTTP-Referer`, `X-Title` (опционально) |
| **Custom** | `custom` | пользовательский | по желанию | — |

```python
@dataclass
class LLMProviderPreset:
    id: str
    label: str
    default_base_url: str
    api_key_required: bool
    auth_header: str = "Bearer"
    cloud_warning: bool = False   # True для OpenRouter — предупреждение о облаке

PROVIDERS = {
    "local": LLMProviderPreset("local", "LOCAL", "http://192.168.88.41:8989/v1", False),
    "openrouter": LLMProviderPreset("openrouter", "OpenRouter", "https://openrouter.ai/api/v1", True, cloud_warning=True),
    "custom": LLMProviderPreset("custom", "Custom", "", False),
}
```

**Поведение UI при смене провайдера:**

1. Пользователь выбирает **LOCAL** → URL = `http://192.168.88.41:8989/v1`, поле API key disabled + подсказка «не требуется»
2. Выбирает **OpenRouter** → URL подставляется, API key **enabled + required**, жёлтое предупреждение: «Текст отправляется в облако OpenRouter»
3. Выбирает **Custom** → URL редактируемый, API key опционален
4. При переключении провайдера — **не стирать** API key пользователя (хранить отдельно per-provider в settings, см. ниже)

**Поведение приложения при `llm.enabled = false` (D9):**

| Компонент | Поведение |
|-----------|-----------|
| Вкладка LLM | **Скрыта** из Notebook (остаётся только Argos) |
| LLM worker | Не запускается |
| Health check | Не выполняется |
| Статус-бар | Индикатор `● LLM` скрыт |
| Меню «Сохранить оба…» | Скрыто / только Argos |
| Настройки | Вкладка LLM доступна — можно включить обратно |

**Системный промпт** — редактируемый в настройках, по умолчанию см. [§10.6](#106-системный-промпт-llm).

Кнопки: **Проверить соединение**, **Сбросить промпт**, **Загрузить модели** (`GET /v1/models`)

#### Вкладка «Argos»

| Параметр | Тип | По умолчанию |
|----------|-----|--------------|
| `packages_dir` | path | auto | portable: рядом с exe |
| `prefer_api_over_cli` | bool | `true` |
| `bundle_models_on_start` | bool | `true` |

Кнопки: **Открыть папку моделей**, **Установить из bundle**, **Список пар**

#### Вкладка «Поведение»

| Параметр | Тип | По умолчанию |
|----------|-----|--------------|
| `close_action` | фиксировано `tray` (D2) | `tray` |
| `start_minimized_to_tray` | bool | `false` |
| `tray_click_action` | show / toggle | `show` |
| `restore_clipboard_after_capture` | bool | `true` |
| `global_hotkey` | str | `ctrl+shift+c` |
| `minimize_to_tray_on_copy_hide` | bool | `true` |

#### Вкладка «О программе»

- Версия, путь к логам, кнопка «Открыть лог», статус движков

#### Вкладка «Файлы»

| Параметр | Тип | По умолчанию | Примечание |
|----------|-----|--------------|------------|
| `output_encoding` | select | `same` | `same` / `utf-8` / `utf-8-sig` — кодировка **сохранения** |
| `output_suffix` | str | `_translated` | |
| `preserve_filename` | bool | `true` | |
| `max_file_size_mb` | int | `10` | |

> **Кодировка при чтении** — только автоопределение (D8), **без настроек для пользователя**.
> Пользователь не выбирает кодировку вручную — декодер работает скрыто.

### 9.3. Техническая реализация

- `SettingsDialog(tk.Toplevel)` — модальный или немодальный
- `Settings` dataclass + `load()` / `save()` / `migrate(old_dict)`
- Кнопки: **Применить**, **ОК**, **Отмена**
- Валидация URL LLM, debounce ranges
- При `llm.enabled=false` — не валидировать LLM-поля
- При `provider=openrouter` без API key — блокировать «ОК» с сообщением
- Секреты (`api_key`) — хранить в settings, не логировать
- Per-provider кэш URL: `llm.provider_urls: { "local": "...", "openrouter": "...", "custom": "..." }`

**Критерий готовности:** все параметры сохраняются, переживают перезапуск, прозрачность работает на Windows.

---

## 10. Фаза 5 — Интеграция LLM

### 10.1. API и провайдеры (D10)

Все провайдеры используют **OpenAI-compatible API**. Конфигурация через `llm.provider`:

| Провайдер | Base URL | Когда использовать |
|-----------|----------|-------------------|
| **LOCAL** | `http://192.168.88.41:8989/v1` | Локальный сервер в LAN, без API key |
| **OpenRouter** | `https://openrouter.ai/api/v1` | Облачные модели, большие тексты; нужен API key |
| **Custom** | любой URL | Другие совместимые серверы (LM Studio, Ollama proxy и т.д.) |

```python
# llm_engine.py
def build_client(settings: Settings) -> LLMClient:
    if not settings.llm.enabled:
        raise LLMDisabledError()
    preset = get_provider(settings.llm.provider)
    base_url = settings.llm.base_url or preset.default_base_url
    api_key = settings.llm.api_key or None
    if preset.api_key_required and not api_key:
        raise LLMConfigError("API key required for OpenRouter")
    ...
```

**Эндпоинты (все провайдеры):**

- `GET /v1/models` — список моделей (кнопка «Проверить»)
- `POST /v1/chat/completions` — основной (stream: true/false)
- Fallback: `POST /v1/completions` — если chat не поддерживается

**Зависимость:** `httpx` (легче `openai`, без лишних зависимостей) или `openai>=1.0` с `base_url`.

- [x] `build_request_context()` / `LLMRequestContext` — подготовка URL и заголовков
- [x] Fallback `POST /v1/completions` при недоступности chat endpoint
- [x] Timeout: один повтор запроса перед ошибкой

### 10.2. UI — вкладки перевода (решение D1)

Правая панель (Translation) → `ttk.Notebook` — **переключатель вкладок**, одновременно видна **только одна**:

```
┌─────────────────────────────────────┐
│ [ Argos ●] [ LLM ]    ← заголовки   │  ← виден только активный контент
├─────────────────────────────────────┤
│                                     │
│   Текст перевода (read-only)        │  ← одна панель, два буфера
│                                     │
└─────────────────────────────────────┘
```

**Ключевое поведение `both_adaptive`:**

- Оба движка **переводят параллельно в фоне** (два worker-потока, два буфера результата)
- Пользователь **видит только активную вкладку** — переключение мгновенное, без повторного перевода
- Неактивная вкладка **продолжает обновляться** в фоне (streaming LLM идёт даже если вкладка Argos выбрана)
- Индикатор на заголовке неактивной вкладки: `LLM ●` (streaming) / `LLM ✓` (готово) / `LLM ✗` (ошибка)
- **Copy / Copy & Hide** — копирует с **активной** вкладки
- Запоминать последнюю выбранную вкладку в `settings.ui.active_translation_tab`

**Режим `both_adaptive` — логика движков:**

| Состояние LLM | Argos | LLM (фон) | Что видит пользователь на вкладке LLM |
|---------------|-------|-----------|---------------------------------------|
| Доступна | ✓ работает | ✓ работает | Актуальный перевод / streaming |
| Недоступна | ✓ работает | ✗ пропуск | «LLM недоступна» (последний статус) |
| Занята (429) | ✓ работает | ✗ пропуск | «LLM занята, повтор позже…» |
| **Отключена** (`llm.enabled=false`, D9) | ✓ работает | — не запускается | Вкладка LLM **скрыта**; только Argos |

**Реализация `translation_tabs.py`:**

```python
class TranslationTabs(ttk.Notebook):
    def set_argos_text(text: str) -> None      # обновляет буфер Argos
    def set_llm_text(text: str) -> None        # обновляет буфер LLM
    def get_active_engine() -> str             # "argos" | "llm"
    def get_active_text() -> str               # для Copy
    # При смене вкладки — показать соответствующий буфер, не запускать перевод
```

**Сервис `llm_health.py`:**

```python
class LLMHealthService:
    def check() -> LLMStatus          # available / busy / offline
    def cached_status() -> LLMStatus  # TTL 30 сек
    def mark_busy()                   # после 429
```

- [x] Health check при старте: только если `llm.enabled == true`
- [x] `GET {base_url}/models` (timeout 3 сек)
- [x] Перед LLM-переводом: использовать кэш (не проверять каждый раз)
- [x] После 429: `mark_busy()`, retry через 30–60 сек
- [x] Индикатор в статус-баре: `● LLM` зелёный / жёлтый / серый
- [x] Один ввод → Argos worker всегда; LLM worker — только если `status == available`
- [x] Статус: `Argos: 3/5 · LLM: streaming…` или `Argos: 3/5 · LLM: недоступна`

### 10.3. Стратегия запросов LLM — ключевые нюансы

#### ❌ Чего НЕ делать

- Дробить на предложения (как Argos) — **N запросов**, потеря контекста, огромная задержка
- Отправлять запрос на каждый символ — даже с debounce 700ms при быстром наборе это дорого
- Дублировать запросы при незавершённом предыдущем

#### ✅ Правильная стратегия

```
Пользователь печатает
    ↓
debounce (llm_debounce_ms = 1200ms, отдельно от Argos)
    ↓
job_id++
    ↓
ОДИН запрос: весь текущий текст
    ↓
SSE stream → обновление вкладки LLM по мере поступления токенов
    ↓
При новом вводе до завершения:
    - stop_flag для старого job_id
    - отмена HTTP (httpx stream close) или игнорирование stale chunks
    - новый запрос с полным текстом
```

#### Разбиение длинного текста (только если > лимита)

| Условие | Действие |
|---------|----------|
| Редактор, `len(text) <= chunk_max_chars` (6000) | Один запрос |
| Файл, `len(text) <= file_chunk_max_chars` (3500) | Один запрос |
| Длиннее лимита | **Disjoint**-чанки: абзацы → предложения → слова |
| Контекст между чанками | Read-only: source context + хвост перевода (не переводить повторно) |
| Overlap в translate | **Нет** — каждый символ исходника переводится один раз |
| Порядок | Последовательно (LLM медленнее, параллельные чанки перегрузят GPU) |
| Progress (файл) | `on_chunk_progress` → «LLM: блок X/Y», progress bar |

#### Streaming в UI

```python
# llm_engine.py
def translate_stream(text, from_lang, to_lang, on_token, on_done, cancel_event):
    with httpx.Client(timeout=...) as client:
        with client.stream("POST", url, json={..., "stream": True}) as resp:
            for line in resp.iter_lines():
                if cancel_event.is_set():
                    break
                # parse SSE: data: {"choices":[{"delta":{"content":"..."}}]}
                on_token(token)
    on_done(full_text)
```

- Обновлять Text widget через `root.after(0, ...)` из потока
- Throttle UI updates: не чаще 50ms (накопление буфера токенов)
- Индикатор: `LLM: ● streaming` / `LLM: ✓ готово` / `LLM: ✗ ошибка`

#### Промпт-инженерия

```python
messages = [
    {"role": "system", "content": build_system_prompt(settings, from_lang, to_lang)},
    {"role": "user", "content": text},
]
```

- Промпт собирается из шаблона в настройках + текущие языки программы
- Файлы: multi-part prompt с frozen context (source + хвост перевода); `file_chunk_context` в settings
- Не включать полную историю перевода (экономия токенов)
- `temperature=0.3` для стабильности перевода
- При смене языка — новый запрос (не кэшировать)
- API key LOCAL: заголовок `Authorization` **не отправляется**
- API key OpenRouter: `Authorization: Bearer {key}` + опционально `HTTP-Referer`, `X-Title`
- Custom: по настройке `auth_header` (`auto` → Bearer если key задан)

### 10.4. Обработка ошибок LLM

| Ошибка | Поведение |
|--------|-----------|
| Connection refused | Вкладка LLM: `[LLM недоступен: нет соединения]` |
| Timeout | Повтор 1 раз, затем ошибка |
| 404 model | Предложить выбрать модель в настройках |
| 429 / overload | Exponential backoff, статус в UI |
| Пустой ответ | `[LLM: пустой ответ]` |

**При ошибке LLM:** Argos продолжает работать (both_adaptive); LLM-вкладка показывает ошибку.

- [x] Connection refused → `[LLM недоступен: нет соединения]`
- [x] Timeout → повтор 1 раз, затем ошибка
- [x] 404 model → «выберите модель в настройках»
- [x] 429 → mark_busy + сообщение в UI
- [x] Пустой ответ → `[LLM: пустой ответ]`
- [x] Fallback `/v1/completions` если chat endpoint недоступен

### 10.5. Приватность и сеть

- Локальный LLM — данные в локальной сети
- OpenRouter — данные уходят в облако (предупреждение в настройках при смене URL)
- Не логировать текст и API key на уровне INFO
- API key хранить в `settings.json`; маскировать в UI (`sk-••••`)

### 10.6. Системный промпт LLM

Шаблон в настройках (`llm.system_prompt`). Подставляемые переменные:

| Переменная | Источник |
|------------|----------|
| `{source_lang}` | код и название языка FROM |
| `{target_lang}` | код и название языка TO |
| `{source_code}` | `en`, `ru`, … |
| `{target_code}` | `en`, `ru`, … |
| `{formality}` | настройка: `neutral` / `formal` / `informal` (опционально) |

**Промпт по умолчанию (русский, для локальных моделей):**

```
Ты — профессиональный переводчик.

Задача: переведи текст пользователя с языка «{source_lang}» ({source_code}) на язык «{target_lang}» ({target_code}).

Правила:
1. Выводи ТОЛЬКО перевод — без пояснений, примечаний и метаданных.
2. Сохраняй структуру оригинала: абзацы, переносы строк, списки, нумерацию.
3. Для Markdown (заголовки #, код ```, ссылки) сохраняй разметку; переводи только видимый текст.
4. Имена собственные, бренды, URL — оставляй как в оригинале, если нет устоявшегося перевода.
5. Сохраняй тон и стиль оригинала (нейтральный / формальный / разговорный).
6. Не добавляй контент, которого нет в исходном тексте.
7. Если текст уже на целевом языке — верни его без изменений.

Языки заданы настройками приложения. Следуй им строго.
```

**Промпт для OpenRouter / мощных моделей (альтернативный шаблон в настройках):**

```
You are a professional translator. Translate the user message from {source_lang} to {target_lang}.
Output ONLY the translated text. Preserve all formatting, markdown syntax, line breaks, and structure.
Do not add explanations. Follow the application's language settings strictly.
```

- [x] `build_system_prompt(settings, from_code, to_code, languages_dict)` в `llm_engine.py`
- [x] Кнопка «Сбросить промпт» восстанавливает шаблон по умолчанию
- [x] При переводе **файлов** — добавлять в user message: `File type: markdown` / `plain text` (не менять system prompt)

**Критерий готовности:** LLM переводит целый абзац одним запросом; streaming в UI; both_adaptive работает; промпт берётся из настроек с подстановкой языков.

---

## 11. Фаза 6 — Оптимизация перевода

### 11.1. Argos worker

- [x] Использовать `make_sentence_chunks()` для длинных параграфов (меньше вызовов API)
- [x] Батчинг: если CLI backend — передавать чанк целиком
- [x] Кэш перевода предложения в рамках сессии (LRU, max 500 entries) — опционально в настройках

### 11.2. Общий TranslationCoordinator

- [x] `services/translation_coordinator.py` — единый job_id, cancel, прогресс Argos
- [x] Интеграция в `app.py` (Argos worker + LLM worker)

```python
class TranslationCoordinator:
    def allocate_job() -> int
    def start_argos(job_id, unit_count)
    def start_llm(job_id)
    def cancel()
    def argos_should_stop(job_id) -> bool
    def llm_is_stale(job_id) -> bool
```

- Единый debounce timer per engine type — в `app.py` (отдельные debounce Argos/LLM)
- Статус-бар агрегирует прогресс — в `_update_combined_status()`

### 11.3. Мелкие UX-улучшения

- [x] Кнопка «Отменить перевод»
- [x] Индикация активного движка в статус-баре
- [x] Не запускать перевод при `len(text.strip()) < 2`
- [x] При hotkey capture: для текста > 500 символов — не автоперевод (настраиваемо в «Файлы»)
- [x] Copy & Hide: копировать с активной вкладки (Argos или LLM)

**Критерий готовности:** заметно меньше вызовов при длинных текстах, UI отзывчив.

---

## 12. Фаза 7 — Перевод документов

### 12.1. Поддерживаемые форматы

Только **plain-text** — данные в открытом виде, без COM/предустановок Office:

| Расширение | MIME / тип | Особенности перевода |
|------------|------------|----------------------|
| `.txt` | plain text | Прямой перевод |
| `.md`, `.markdown` | Markdown | Сохранять разметку; LLM-промпт с правилом #6 |
| `.csv` | CSV | Переводить только текстовые ячейки; сохранять разделители |
| `.json` | JSON | Переводить только string-значения; сохранять структуру |
| `.xml`, `.html`, `.htm` | разметка | Переводить текстовые узлы; теги не трогать (LLM предпочтительнее) |
| `.yaml`, `.yml` | YAML | Переводить значения, не ключи |
| `.ini`, `.cfg` | config | Переводить значения после `=` |
| `.log` | log | Как plain text |
| `.rst` | reStructuredText | Как Markdown |
| `.toml` | TOML | Переводить string-значения |

**Не поддерживается (v1):** `.docx`, `.pdf`, `.odt`, `.rtf` (бинарные / нужны библиотеки).

### 12.2. UI

- [x] Меню **Файл → Открыть…** (`Ctrl+O`) — `filedialog.askopenfilename`
- [x] **Файл → Сохранить перевод…** (`Ctrl+Shift+S`) — сохранить активную вкладку
- [x] **Файл → Сохранить оба…** — Argos и LLM в отдельные файлы (если LLM доступна)
- [x] Drag & Drop файла на окно (опционально, Windows — `pip install windnd`)
- [x] Строка статуса: `document.txt · изменён` (кодировку **не показывать** пользователю — D8)
- [x] При открытии файла — загрузить в Source panel, запустить перевод

### 12.3. Модуль `services/document_io.py` и автоопределение кодировки (D8)

**Зависимость:** `charset-normalizer>=3.0` (предпочтительнее `chardet` — быстрее, точнее на смешанных текстах).

```python
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ...}

@dataclass
class DecodedFile:
    text: str
    encoding: str          # для внутреннего использования и сохранения
    confidence: float      # 0.0–1.0

def read_text_file(path: Path) -> DecodedFile: ...
def write_text_file(path: Path, content: str, encoding: str) -> None: ...
def suggest_output_path(src: Path, suffix: str, engine: str) -> Path: ...
def detect_encoding(raw: bytes) -> tuple[str, float]: ...
```

#### Алгоритм `detect_encoding` (скрытый, многоуровневый)

```
1. Прочитать первые 64 KB файла (достаточно для определения)
2. BOM-маркеры (высший приоритет):
     EF BB BF → utf-8-sig
     FF FE     → utf-16-le
     FE FF     → utf-16-be
3. Попытка строгого UTF-8 decode всего sample → если OK, encoding=utf-8
4. charset-normalizer.from_bytes(sample).best() → encoding + confidence
5. Если confidence < 0.7 — дополнительные эвристики:
     a. Кириллица читается как mojibake? → попробовать cp1251, cp866, koi8-r, iso-8859-5
     b. Типичные русские слова в cp1251 → повысить confidence cp1251
6. Перебор fallback-цепочки с проверкой «читаемости»:
     utf-8 → cp1251 → cp866 → latin-1 → iso-8859-1
     Критерий: decode без exception + доля печатных символов > 95%
7. Последний resort: utf-8 с errors='replace' (логировать WARNING)
```

- [x] **Пользователю не показывать** выбор/результат кодировки — всё внутри `read_text_file()`
- [x] Логировать на DEBUG: `detected encoding=cp1251 confidence=0.92 path=file.txt`
- [x] При сохранении: по умолчанию `output_encoding=same` — писать в той же кодировке, что при чтении
- [x] Опция `output_encoding=utf-8` — нормализация всех файлов в UTF-8 при сохранении
- [x] Лимит размера: `max_file_size_mb` из настроек (по умолчанию 10 MB)
- [x] Большие файлы (> `large_file_warn_chars`): предупреждение + перевод по параграфам (LLM) / чанкам (Argos)

#### Тесты `test_document_io.py` (обязательные, D8)

| Тест | Вход | Ожидание |
|------|------|----------|
| `test_utf8_plain` | UTF-8 без BOM | `encoding=utf-8`, текст корректен |
| `test_utf8_bom` | UTF-8 с BOM | `encoding=utf-8-sig`, BOM не в тексте |
| `test_cp1251_russian` | cp1251 русский текст | корректная кириллица |
| `test_cp866_dos` | cp866 (DOS) | корректная кириллица |
| `test_latin1` | ISO-8859-1 западноевропейский | корректные символы |
| `test_mixed_utf8_cp1251` | преимущественно UTF-8 | UTF-8 (не ломать валидный UTF-8) |
| `test_koi8r` | KOI8-R | корректная кириллица (если charset-normalizer не справится — fallback) |
| `test_empty_file` | пустой файл | `text=""`, без исключения |
| `test_binary_garbage` | случайные байты | graceful decode, WARNING в лог |
| `test_save_same_encoding` | cp1251 → save same | выходной файл в cp1251 |
| `test_save_utf8_normalize` | cp1251 → save utf-8 | выходной файл в UTF-8 |

Фикстуры: файлы в `tests/fixtures/encodings/` (по 1 файлу на кодировку, ~1 KB). ✅

- [x] `test_encoding_detection.py` — статические фикстуры
- [x] `test_document_io.py` — programmatic fixtures

### 12.4. Стратегия перевода файлов

| Движок | Подход |
|--------|--------|
| Argos | Чанки по параграфам / `make_sentence_chunks()` |
| LLM | Один запрос на файл если ≤ лимита; иначе — по параграфам с сохранением структуры MD |

- [x] Для MD: не разрывать блоки кода `` ```...``` `` (пропуск при `translate_code_blocks: false`)
- [x] Progress bar для файлов: `Файл: 45% (чанк 9/20)`
- [x] Кнопка «Отменить» прерывает перевод файла

### 12.5. Имена выходных файлов

| Исходный | Argos | LLM |
|----------|-------|-----|
| `readme.md` | `readme_translated.md` | `readme_translated_llm.md` |

Настраиваемый `output_suffix` в settings.

**Критерий готовности:** открыть TXT/MD в любой поддерживаемой кодировке → текст читается корректно без участия пользователя; pytest для encodings зелёный; MD-разметка не ломается.

---

## 13. Фаза 8 — Сборка EXE и модели Argos

### 13.1. Проблема

PyInstaller упаковывает Python и библиотеки, но:

- модели Argos (~50–200 MB на пару) — отдельные файлы;
- `ctranslate2` требует DLL (`numpy.libs`, `ctranslate2` binaries);
- путь к моделям при `frozen` отличается от dev;
- простое копирование `.argosmodel` **не всегда** работает — нужен `install_from_path`.

### 13.2. Стратегия «Portable EXE»

```
dist/ArgosTranslator/
├── ArgosTranslator.exe
├── _internal/              # PyInstaller COLLECT
├── assets/
├── argos_models/           # bundle: en→ru + ru→en (решение D3)
│   ├── translate-en_ru-*.argosmodel
│   └── translate-ru_en-*.argosmodel
└── packages/               # создаётся при первом запуске
    ├── translate-en_ru-1_9/
    └── translate-ru_en-1_9/
```

**Докачка дополнительных пар (не в bundle):**

- [x] UI: **Настройки → Argos** — ссылка на https://www.argosopentech.com/argospm/
- [x] Кнопка «Установить из файла…» — выбор `.argosmodel` с диска
- [x] CLI-подсказка: `argos-translate mo-install en ru`
- [x] Базовый bundle: **только en↔ru**; de, fr, es и др. — докачка

### 13.3. Алгоритм первого запуска (frozen)

Реализовано в `services/frozen_bootstrap.py` + вызов из `bootstrap/runner.py`:

- [x] `is_frozen()`, `get_exe_dir()`, `get_log_dir()` в `config/paths.py`
- [x] `bootstrap_frozen_models()` — установка из bundle в `{exe_dir}/packages/`
- [x] `configure_argos_package_dir()` — env `ARGOS_TRANSLATE_PACKAGE_DIR` + patch `PACKAGE_DIR`
- [x] Логи frozen: `{exe_dir}/log/app_debug.log` (`logging_setup.py`)
- [x] Проверка на реальном EXE: сборка OK (PyInstaller 6.x, dev); smoke `scripts/smoke_dist.py`

```python
def bootstrap_models():
    if not is_frozen():
        return
    portable_packages = exe_dir / "packages"
    bundle = exe_dir / "argos_models"

    if not portable_packages.exists() or not any(portable_packages.iterdir()):
        portable_packages.mkdir(exist_ok=True)
        for model in bundle.glob("*.argosmodel"):
            package.install_from_path(str(model))  # в portable_packages

    # Указать argostranslate искать модели здесь
    os.environ["ARGOS_TRANSLATE_PACKAGE_DIR"] = str(portable_packages)
```

**Важно:** проверить, поддерживает ли `argostranslate` env-переменную; если нет — monkey-patch `package.PACKAGE_INDEX` или symlink.

### 13.4. PyInstaller spec — исправления

- [x] **B9**: `console=False` для release, `ArgosTranslator.debug.spec` для debug
- [x] Убрать `numpy` из `excludes` (конфликт с `hiddenimports`)
- [x] `collect_binaries('ctranslate2')` — явно включить DLL
- [x] `hiddenimports`: `pystray._win32`, `ctranslate2`, `httpx`, `charset_normalizer`
- [x] UPX: `upx_exclude` для `.dll`
- [x] `hookspath`: `hooks/`
- [x] Версия в exe: `--version-file` (`assets/version_info.txt`)

### 13.5. Скрипт сборки `scripts/build.bat`

```bat
py -3.10 -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\pip install pyinstaller httpx
venv\Scripts\pyinstaller ArgosTranslator.spec --clean
echo Копируйте argos_models в dist\ArgosTranslator\argos_models\
```

### 13.6. Чеклист тестирования EXE

> **Автоматически:** `python scripts/verify_spec.py`, `python scripts/smoke_dist.py` после `scripts/build.bat`.
> **Вручную** на чистой Windows без Python:

- [ ] Запуск на машине **без Python** (ручная QA)
- [ ] Перевод en→ru через Argos (модель в bundle)
- [ ] Перевод ru→en через Argos (модель в bundle)
- [ ] LLM перевод (если сервер доступен по сети)
- [ ] Трей: сворачивание, левый клик, выход
- [ ] Настройки сохраняются в `%USERPROFILE%\.argos_translate\`
- [x] Логи: код пишет в `{exe_dir}\log\app_debug.log`
- [x] Первый запуск: `bootstrap_frozen_models()` из bundle
- [x] Повторный запуск: модели не переустанавливаются
- [ ] Геометрия окна сохраняется после перезапуска EXE (ручная QA)
- [ ] DPI 100% и 150% — окно не уходит за экран (ручная QA)

### 13.7. Размер дистрибутива

| Компонент | ~Размер |
|-----------|---------|
| EXE + deps | 80–150 MB |
| Модели en→ru + ru→en | ~100–200 MB |
| **Итого (базовый)** | ~180–350 MB |

Дополнительные языковые пары — отдельная докачка пользователем.

**Критерий готовности:** `dist/ArgosTranslator/ArgosTranslator.exe` переводит en↔ru offline без установленного Python.

---

## 14. Фаза 9 — Тесты, документация, CI

### 14.1. Тесты (pytest)

| Файл | Что тестирует |
|------|---------------|
| `test_text_utils.py` | split, detect_language |
| `test_settings.py` | load/save/migrate, defaults |
| `test_argos_engine.py` | mock API / CLI translate |
| `test_llm_engine.py` | prompt, chunks, SSE, non-stream mock |
| `test_model_manager.py` | paths, bundle install skip |
| `test_document_io.py` | автоопределение кодировок, extensions, size limit |
| `test_window_state.py` | geometry parse, clamp |
| `test_llm_health.py` | disabled, busy, offline, cache TTL |
| `test_translation_cache.py` | LRU hit/miss, eviction |
| `test_paths.py` | `get_argos_packages_dir`, frozen portable |
| `test_translation_coordinator.py` | job_id, cancel, stale detection |
| `test_llm_providers.py` | пресеты LOCAL/OpenRouter/Custom |
| `test_llm_enabled.py` | при enabled=false worker не стартует, вкладка скрыта |
| `test_frozen_bootstrap.py` | portable bootstrap, skip if models present |
| `test_encoding_detection.py` | статические фикстуры `tests/fixtures/encodings/` |
| `test_translation_integration.py` | реальный Argos (`@pytest.mark.integration`) |
| `test_themes.py` | apply_theme dark/light (Tk) |

Интеграционные (помечены `@pytest.mark.integration`):
- Реальный Argos (если модели есть)
- Реальный LLM (если `LLM_TEST_URL` env задан)

### 14.2. Документация

- [x] **B1**: обновить README — пути логов, LLM, тёмная тема, настройки
- [x] Обновить `BUILD_INSTRUCTIONS.md`
- [x] Добавить `CHANGELOG.md`
- [x] Удалить или обновить устаревший `pyinstall.md`

### 14.3. CI (опционально)

- [x] GitHub Actions: `pytest` на push (`.github/workflows/ci.yml`)
- [x] `ruff check` в CI (критичные правила E9/F*)
- Сборка EXE — manual workflow

---

## 15. Структура settings.json (целевая)

```json
{
  "version": 4,
  "window": {
    "state": "normal",
    "x": 100,
    "y": 100,
    "width": 1000,
    "height": 700,
    "monitor_hint": {
      "work_area": [0, 0, 1920, 1040],
      "dpi": 96,
      "device_name": "\\\\.\\DISPLAY1"
    },
    "dpi_scale": 1.0,
    "opacity": 1.0,
    "theme": "dark",
    "geometry_legacy": null
  },
  "translation": {
    "default_engine": "both_adaptive",
    "streaming": true,
    "debounce_ms": 700,
    "llm_debounce_ms": 1200,
    "scroll_sync": true,
    "auto_target_lang": "ru"
  },
  "languages": {
    "from": "auto",
    "to": "ru"
  },
  "llm": {
    "enabled": true,
    "provider": "local",
    "base_url": "http://192.168.88.41:8989/v1",
    "provider_urls": {
      "local": "http://192.168.88.41:8989/v1",
      "openrouter": "https://openrouter.ai/api/v1",
      "custom": ""
    },
    "api_keys": {
      "openrouter": "",
      "custom": ""
    },
    "model": "",
    "auth_header": "auto",
    "temperature": 0.3,
    "max_tokens": 4096,
    "timeout_sec": 120,
    "stream": true,
    "health_check_ttl_sec": 30,
    "system_prompt": "Ты — профессиональный переводчик..."
  },
  "argos": {
    "packages_dir": "",
    "prefer_api": true,
    "bundle_on_start": true
  },
  "behavior": {
    "close_action": "tray",
    "start_minimized_to_tray": false,
    "tray_click_action": "show",
    "global_hotkey": "ctrl+shift+c",
    "restore_clipboard": true
  },
  "files": {
    "output_encoding": "same",
    "output_suffix": "_translated",
    "max_file_size_mb": 10,
    "translate_code_blocks": false
  },
  "ui": {
    "font_family": "Consolas",
    "font_size": 13,
    "active_translation_tab": "argos"
  }
}
```

**Миграции:**

- v1→v2: `window.streaming` → `translation.streaming`
- v2→v3: `window.geometry` string → structured `WindowState`; `default_engine: "both"` → `"both_adaptive"`
- v3→v4: `llm.api_key` → `llm.api_keys.{provider}`; добавить `llm.provider`, `llm.provider_urls`

---

## 16. Порядок выполнения и оценка

| Фаза | Описание | Оценка | Зависимости |
|------|----------|--------|-------------|
| 0 | Подготовка | 0.5 дн | — |
| 1 | Рефакторинг + аудит | 2–3 дн | 0 |
| 2 | Тёмная тема | 1 дн | 1 |
| 3 | Трей + геометрия окна (DPI) | 1.5–2 дн | 1 |
| 4 | Настройки | 1.5 дн | 1, 2, 3 |
| 5 | LLM + both_adaptive | 2–3 дн | 1, 4 |
| 6 | Оптимизация перевода | 1 дн | 5 |
| 7 | Перевод документов | 1.5–2 дн | 5, 6 |
| 8 | EXE сборка | 1.5–2 дн | 1, 5 |
| 9 | Тесты + docs | 1–2 дн | все |
| 10 | UI Polish v2 | 2–3 дн | 9, `73e2670` |

**Итого (фазы 0–9):** ~14–18 рабочих дней. **Фаза 10:** +2–3 дня.

### Рекомендуемый порядок PR

1. `refactor/split-main` — фаза 0–1
2. `feat/dark-theme` — фаза 2
3. `feat/tray-and-window-state` — фаза 3 (трей + DPI geometry)
4. `feat/settings-dialog` — фаза 4
5. `feat/llm-engine` — фаза 5
6. `perf/translation` — фаза 6
7. `feat/document-translation` — фаза 7
8. `build/pyinstaller` — фаза 8
9. `chore/tests-docs` — фаза 9
10. `feat/ui-polish-v2` — фаза 10 (см. §18)

---

## 18. Фаза 10 — UI Polish v2

**Цель:** заметно улучшить восприятие интерфейса **без** смены архитектуры и без возврата к монолиту. Опирается на аудиты A/B/C (§3.1) и baseline `docs/UI_BASELINE.md`.

**Ограничения:**

- Не менять логику перевода, coordinator, settings schema (кроме опциональных UI-only полей).
- Сохранить палитру UI-for-ytdlp (`#16a6ff` primary).
- Не вводить тяжёлые анимации и fake-shadow фреймы в v2.1.
- Каждый подэтап — отдельный коммит/PR, визуально проверяемый на Windows 125% DPI.

### 18.1. P0 — Design tokens и отступы (≈0.5 дн)

**Файлы:** `ui/layout_config.py`, `ui/widgets.py`.

- [x] Ввести `UIStyle` / `STYLE`: `radius_control`, `radius_card`, `toolbar_h`, `section_gap`.
- [x] Заменить magic numbers в `main_window.py`, `text_panel.py`, `settings_dialog.py` на токены.
- [x] Вернуть осмысленные отступы: `WINDOW_PADX/Y`, `CARD_PADX/Y`, `ELEMENT_GAP` > 0.
- [x] Зафиксировать в `docs/UI_BASELINE.md` версию **v2.1 structured flat**.

**Критерий:** grep по `padx=\d` / `pady=\d` в `ui/` — только константы из `layout_config`.

### 18.2. P0 — Toolbar: три зоны (≈0.5 дн)

**Файл:** `ui/main_window.py`.

- [x] Grid header: column 0 — меню + title; column 1 (weight=1) — `CompactLanguageSelector`; column 2 — actions.
- [x] Длинные подписи — в tooltip; в toolbar короткие или иконки.

**Критерий:** языковой селектор визуально в центре; actions не «прилипают» к combo.

### 18.3. P1 — Card editors (панели текста) (≈0.5 дн)

**Файлы:** `ui/text_panel.py`, `ui/translation_tabs.py`.

- [x] `text_host`: `border_width=1`, `corner_radius=8` (токен), единый для обеих колонок.
- [x] Заголовок: title + счётчик символов (исходник).
- [x] Нижняя строка кнопок — одинаковая высота `PANEL_BUTTON_ROW_HEIGHT`.

**Критерий:** поля ввода по-прежнему 50/50 и одной высоты (regression test layout).

### 18.4. P1 — Toolbar actions simplification (≈0.25 дн)

**Файлы:** `ui/main_window.py`, `ui/file_menu.py`.

- [x] Primary: «Перевести»; secondary: «Стоп»; icon: «⚙».
- [x] «Поток» / «Синхр.» → меню «Ещё ▾`.
- [x] Hotkeys и callbacks без изменений.

### 18.5. P1 — Status footer (≈0.25 дн)

**Файл:** `ui/main_window.py`.

- [x] Grid 3 колонки: `status_var` (w) · `llm_indicator` (center) · hints + progress (e).
- [x] Progress bar visible только при переводе файла.
- [x] Hints сокращены; полный список — tooltip.

### 18.6. P2 — Settings dialog UX (≈1 дн)

**Файл:** `ui/settings_dialog.py`.

- [x] Заменить верхний tabview на **sidebar + content** (168px nav).
- [x] К каждой секции — `muted_label` с одной строкой описания.
- [x] LLM tab: collapsible «Дополнительно» для temperature / prompt.
- [x] Размер окна: сохранение geometry через `WindowState` в `ui.settings_dialog`.

**Критерий:** ✅ LLM-секция с collapsible «Дополнительно»; tabview удалён (нет duplicate `fg_color`).

### 18.7. P2 — Language selector polish (≈0.25 дн)

**Файл:** `ui/language_selector.py`.

- [x] Визуальная стрелка направления (→) между combo.
- [x] Swap — кнопка 36×36, tooltip «Поменять языки местами».

### 18.8. P3 — Backlog (не блокирует релиз)

- [ ] История переводов (sidebar / drawer) — отдельная фича.
- [ ] TTS / озвучка.
- [ ] Elevated theme variant (тени, radius 16).
- [ ] `ui/animations.py` — только если появится реальная потребность.

### 18.9. Тесты и QA фазы 10

- [x] Smoke: `tests/test_translation_display.py`, `tests/test_llm_enabled.py`.
- [ ] Ручная матрица: Windows **100% / 125% / 150%** DPI — размер окна стабилен 3 перезапуска.
- [x] `docs/UI_BASELINE.md` обновлён (sidebar настроек).

### 18.10. Порядок работ (максимальный эффект / минимум риска)

1. **Tokens + spacing** (18.1)
2. **Toolbar 3-zone** (18.2)
3. **Card editors + char count** (18.3)
4. **Footer** (18.5)
5. **Actions simplification** (18.4)
6. **Settings sidebar** (18.6)
7. **Language selector** (18.7)

---

## 17. Риски

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| argostranslate не поддерживает custom packages dir | Средняя | Исследовать исходники; fallback — install_from_path |
| ctranslate2 DLL не работают после UPX | Средняя | `upx_exclude` |
| LLM сервер не OpenAI-compatible | Низкая | `GET /v1/models` при старте |
| Прозрачность окна не работает на Linux | Высокая | Disable + tooltip |
| pystray default action на Linux | Средняя | `PYSTRAY_BACKEND=gtk` |
| Bundle en↔ru раздувает EXE (~200 MB моделей) | Ожидаемо | Документировать размер; опциональный lite-сборка без моделей |
| DPI Per-Monitor на Linux неполный | Средняя | clamp к screen bounds |
| Перевод JSON/XML ломает структуру | Средняя | LLM + валидация после перевода; предупреждение |
| OpenRouter — утечка данных | Средняя | `cloud_warning` при выборе провайдера; подтверждение при первом использовании |
| Пользователь выключил LLM, но вкладка видна | Низкая | D9: скрывать вкладку при `enabled=false` |

---

## Приложение A — Быстрые wins (можно сделать до полного рефакторинга)

1. **Трей fix** — `MenuItem("Показать", on_show, default=True)` (~5 мин)
2. **Крестик → трей** — `WM_DELETE_WINDOW` → `_hide_to_tray` (~15 мин)
3. **DPI awareness** — `SetProcessDpiAwareness(2)` до `tk.Tk()` (~30 мин)
4. **Убрать центрирование** после load settings (~15 мин)
5. **Тёмная тема** — базовые цвета (~2 ч)
6. **`.gitignore` для log/** (~1 мин)

---

## Приложение B — Контрольный список «готово к релизу»

- [x] Тёмная тема по умолчанию
- [x] Геометрия окна стабильна (DPI, мониторы, maximized)
- [x] Крестик сворачивает в трей; выход — ПКМ → Выход
- [x] Левый клик по трею разворачивает окно
- [x] Окно настроек (прозрачность, провайдер, URL, API key, промпт)
- [x] LLM можно **выключить** в настройках (`llm.enabled`)
- [x] Выбор провайдера: **LOCAL** / **OpenRouter** / **Custom**
- [x] both_adaptive: оба движка в фоне, видна только выбранная вкладка
- [x] Системный промпт с подстановкой языков из настроек
- [x] LLM: один запрос + streaming; OpenRouter с API key
- [x] Перевод TXT, MD и plain-text файлов
- [x] EXE собирается (`scripts/build.bat`); en↔ru из bundle — код готов
- [x] Автоопределение кодировки файлов; pytest encodings зелёный
- [x] README актуален
- [x] pytest проходит
- [x] Нет DEBUG-print в `src/` (`test_release_checklist.py`)

**Фаза 10 (UI Polish v2):** см. [§18.10](#1810-порядок-работ-максимальный-эффект--минимум-риска).

**Остаётся вручную:** EXE на чистой Windows без Python (§13.6).

---

## Приложение C — Чеклист UI Polish v2

- [x] Design tokens, spacing > 0
- [x] Toolbar: left / center / right
- [x] Editor cards: border + radius 8, char count
- [x] Footer: status · engine · progress
- [x] Settings: sidebar + content (18.6)
- [x] `UI_BASELINE.md` обновлён до v2.1
- [ ] DPI 100/125/150% — стабильная геометрия (ручная QA)

---

*Документ v2.1: фазы 0–10 завершены (код UI Polish §18; commit `73e2670` + последующие правки); §18.8–18.9 backlog / ручная QA.*
