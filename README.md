# Argos Translate Streaming

Графический потоковый переводчик текста с использованием движка Argos Translate.

## Оглавление

- [Описание](#описание)
- [Функциональность](#функциональность)
- [Требования](#требования)
- [Установка](#установка)
- [Запуск](#запуск)
- [Настройка моделей](#настройка-моделей)
- [Горячие клавиши](#горячие-клавиши)
- [Конфигурация](#конфигурация)
- [Архитектура](#архитектура)
- [Устранение неполадок](#устранение-неполадок)
- [Лицензия](#лицензия)

## Описание

Argos Translate Streaming — это десктопное приложение для мгновенного перевода текста между языками. Приложение предоставляет графический интерфейс на Tkinter и поддерживает потоковый режим перевода, когда перевод обновляется автоматически при изменении исходного текста.

Программа использует два движка перевода:
- **Argos Translate** (офлайн) — через Python API или CLI `argos-translate`
- **LLM** (опционально) — OpenAI-compatible API: LOCAL, OpenRouter или Custom URL

Оба движка работают параллельно; в интерфейсе видна одна вкладка (Argos / LLM). Приложение поддерживает тёмную тему, окно настроек, автоматическое определение языка, синхронизацию прокрутки, работу в системном трее и глобальные горячие клавиши.

## Функциональность

### Основные возможности

- **Потоковый перевод (Streaming)**: Argos и LLM с отдельными задержками (debounce)
- **Два движка**: вкладки Argos / LLM; Copy копирует с активной вкладки
- **LLM-провайдеры**: LOCAL (`http://192.168.88.41:8989/v1`), OpenRouter, Custom
- **Окно настроек** (⚙ / `Ctrl+,`): тема, прозрачность, LLM, debounce, целевой язык AUTO
- **Тёмная тема** по умолчанию
- **Поддержка API и CLI Argos**: автоматический выбор бэкенда
- **Автоматическое определение языка**: `langdetect` или эвристика
- **Синхронизация прокрутки** между исходником и активной вкладкой перевода
- **Системный трей**: крестик сворачивает в трей; выход — ПКМ → Выход
- **Устойчивая геометрия окна**: позиция/размер с учётом DPI и мониторов
- **Установка моделей из bundle**: `argos_models/` (en↔ru)
- **14+ языков** в селекторе
- **Перевод файлов**: TXT, MD, CSV, JSON и др. plain-text; автоопределение кодировки (UTF-8, cp1251, cp866, koi8-r…)

### Особенности интерфейса

- Две панели: исходный текст и перевод (вкладки Argos / LLM)
- Компактный селектор языков с кнопкой обмена
- Режим "Copy & Hide": копирование с активной вкладки и скрытие в трей
- Индикатор LLM в статус-баре (`● LLM`)
- Поддержка вставки из буфера обмена

## Требования

### Обязательные зависимости

- **Python**: 3.10–3.12 (рекомендуется; 3.14 — с ограничениями)
- **argostranslate**: офлайн-движок перевода (API + CLI)
- **pyperclip**: работа с буфером обмена
- **httpx**: HTTP-клиент для LLM API

### Опциональные зависимости

- **keyboard**: глобальные горячие клавиши (опционально)
- **langdetect**: точное определение языка (опционально)
- **pystray** + **Pillow**: иконка в трее (опционально)

### Системные требования

- **ОС**: Windows, Linux, macOS
- **Тинтер**: входит в стандартную библиотеку Python
- **Место на диске**: ~500 МБ для моделей перевода

## Установка

### Способ 1: Из исходников с requirements.txt

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd Argos-shell-translator-new
```

2. Создайте виртуальное окружение (рекомендуется):
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Запустите приложение:
```bash
python main.py
```

### Способ 2: Ручная установка зависимостей

```bash
# Обязательные модули
pip install argostranslate pyperclip

# Опциональные модули (для полной функциональности)
pip install keyboard langdetect pystray Pillow
```

## Запуск

### Быстрый запуск

```bash
python main.py
# или через пакет:
python -m argos_translator
```

### Запуск без консоли (Windows)

Приложение автоматически перезапустится через `pythonw.exe` (если доступен) для скрытия консольного окна.

Если автоматический перезапуск не сработал, запустите вручную:

```bash
pythonw main.py
```

### Проверка работоспособности

При первом запуске приложение проверит:
1. Наличие `argostranslate` (API/CLI)
2. Наличие моделей перевода

Если компоненты отсутствуют, приложение предложит установить их.

## Настройка моделей перевода

### Модели из bundle

Если в папке `argos_models/` присутствуют файлы `.argosmodel`, приложение попытается установить их автоматически при первом запуске.

Для ручной установки:

```bash
python install_models.py
```

### Загрузка моделей

Модели можно загрузить с официального сайта:
- https://www.argosopentech.com/argospm/

Установка моделей через CLI:

```bash
argos-translate mo-install en-ru
argos-translate mo-install ru-en
```

Или через Python:

```python
import argostranslate.package
import argostranslate.translate

# Установка модели
argostranslate.package.install_from_path("model.argosmodel")

# Проверка установленных моделей
installed = argostranslate.package.get_installed_packages()
for pkg in installed:
    print(f"{pkg.from_code} -> {pkg.to_code}")
```

## Горячие клавиши

| Комбинация | Действие |
|------------|----------|
| `Ctrl + Enter` | Выполнить перевод |
| `Ctrl + O` | Открыть текстовый файл |
| `Ctrl + Shift + S` | Сохранить перевод (активная вкладка) |
| `Ctrl + ,` | Открыть настройки |
| `Ctrl + S` | Поменять языки местами |
| `Ctrl + Shift + C` | Захватить текст из буфера обмена (глобально) |

## Конфигурация

### Файлы конфигурации

- **Настройки**: `~/.argos_translate/settings.json`
- **Логи**: `log/app_debug.log` (dev, в каталоге проекта) или `{exe_dir}/log/app_debug.log` (portable EXE)

### Перевод файлов

Меню **Файл**:
- **Открыть…** — загрузить файл в панель Source и запустить перевод
- **Сохранить перевод…** — сохранить активную вкладку (Argos или LLM)
- **Сохранить оба…** — `*_translated.ext` и `*_translated_llm.ext`

Кодировка при чтении определяется автоматически (`charset-normalizer` + эвристики). Параметры сохранения — вкладка **Файлы** в настройках.

**Drag & Drop** (Windows): перетащите файл на окно — нужен опциональный пакет `pip install windnd`.

При открытии/переводе большого файла (> `large_file_warn_chars`, по умолчанию 50 000 символов) показывается предупреждение. Во время перевода файла в статусной строке отображается progress bar и «Файл: N% (чанк X/Y)»; для LLM — «LLM: блок X/Y…».

**LLM и большие файлы:** тексты длиннее `file_chunk_max_chars` (по умолчанию 3500 символов) переводятся **поблочно** без overlap в переводимом тексте: каждый фрагмент исходника переводится один раз. Между блоками в prompt передаётся read-only контекст (исходник + хвост предыдущего перевода) — настройка «Контекст между блоками» в LLM → дополнительные параметры. Таймаут и `max_tokens` масштабируются по размеру блока. Для LOCAL при медленной модели рекомендуется `timeout_sec` ≥ 180.

Блоки кода Markdown (`` ```…``` ``) по умолчанию **не переводятся** — включается опцией «Переводить блоки кода Markdown» на вкладке **Файлы**.

### Структура settings.json (v7)

```json
{
  "version": 7,
  "window": {
    "state": "normal",
    "x": 100, "y": 100, "width": 1000, "height": 700,
    "opacity": 1.0,
    "theme": "dark"
  },
  "translation": {
    "default_engine": "both_adaptive",
    "streaming": true,
    "debounce_ms": 700,
    "llm_debounce_ms": 1200,
    "scroll_sync": true,
    "auto_target_lang": "ru",
    "cache_enabled": false,
    "cache_size": 500
  },
  "languages": { "from": "auto", "to": "ru" },
  "llm": {
    "enabled": true,
    "provider": "local",
    "base_url": "http://192.168.88.41:8989/v1",
    "model": "",
    "api_keys": { "openrouter": "" }
  },
  "ui": { "active_translation_tab": "argos" },
  "files": {
    "output_encoding": "same",
    "output_suffix": "_translated",
    "max_file_size_mb": 10,
    "hotkey_auto_translate_max_chars": 500,
    "large_file_warn_chars": 50000,
    "translate_code_blocks": false
  },
  "argos": {
    "packages_dir": "",
    "prefer_api_over_cli": true,
    "bundle_models_on_start": true
  },
  "behavior": {
    "close_action": "tray",
    "start_minimized_to_tray": false,
    "restore_clipboard_after_capture": true,
    "global_hotkey": "ctrl+shift+c",
    "minimize_to_tray_on_copy_hide": true
  }
}
```

Старые настройки (v1 с `geometry`) мигрируются автоматически при загрузке.

### Параметры UI

Размеры окна можно настроить в коде класса `UIConfig`:

```python
@dataclass
class UIConfig:
    title: str = "Argos Translate"
    width: int = 1000
    height: int = 700
    min_width: int = 800
    min_height: int = 600
```

### Константы перевода

Класс `TranslationConstants` содержит настройки:

- `MAX_CHARS_PER_CHUNK` (4000) — максимальный размер чанка для перевода
- `DEBOUNCE_MS` (700) — задержка для потокового перевода
- `SCROLL_SYNC_INTERVAL_MS` (120) — интервал синхронизации прокрутки
- `HOTKEY_DELAY` (0.16) — задержка для глобальных хоткеев

## Архитектура

### Структура приложения

```
Argos-shell-translator-new/
├── assets/                    # argos_translate.ico, .png
├── main.py                    # тонкий entry (sys.path + runner)
├── pyproject.toml
├── ArgosTranslator.spec       # release-сборка (console=False)
├── ArgosTranslator.debug.spec # debug-сборка (console=True)
├── hooks/                     # PyInstaller hooks
├── scripts/build.bat
├── src/argos_translator/
│   ├── app.py                 # TranslatorApp (координатор перевода, ~1200 строк)
│   ├── bootstrap/runner.py    # DPI, проверки, mainloop
│   ├── config/                # settings v7, paths, llm_providers
│   ├── engines/               # argos_engine, llm_engine, factory, base.py
│   ├── services/              # tray, hotkeys, clipboard, frozen_bootstrap, …
│   └── ui/                    # main_window, text_panel, settings_dialog, …
├── tests/                     # pytest (117 tests)
│   └── fixtures/encodings/    # cp1251, utf-8, koi8-r, …
├── docs/UI_BASELINE.md        # описание UI v2
├── CHANGELOG.md
├── argos_models/              # bundle en↔ru (опционально)
└── log/                       # app_debug.log
```

### Основные классы

#### `TranslateEngine`
Движок перевода. Автоматически выбирает между:
- **API**: `argostranslate.translate.translate()`
- **CLI**: вызов `argos-translate` через subprocess

#### `TextUtils`
Утилиты для работы с текстом:
- `detect_language()` — определение языка
- `split_into_paragraphs()` — разбивка на параграфы
- `split_paragraph_into_sentences()` — разбивка на предложения
- `make_sentence_chunks()` — создание чанков для перевода

#### `TextPanel`
Компонент текстовой панели:
- Поддержка редактирования/только чтение
- Кнопки: Paste, Clear, Copy
- Дополнительные кастомные кнопки

#### `CompactLanguageSelector`
Селектор языков:
- Выбор исходного языка (включая AUTO)
- Выбор целевого языка
- Кнопка обмена языками

#### `TranslatorApp`
Главное приложение:
- Управление UI
- Потоковый перевод в отдельном потоке
- Синхронизация прокрутки
- Работа с настройками
- Системный трей

### Потоки и асинхронность

- **Основной поток**: UI (Tkinter mainloop)
- **Worker поток**: выполнение перевода
- **Tray поток**: иконка в трее (pystray)
- **Очередь**: `queue.Queue` для передачи результатов перевода

### Механизм потокового перевода

**Argos:**
1. Ввод текста → debounce (`debounce_ms`, по умолчанию 700 мс)
2. Разбивка на параграфы → предложения
3. Worker-поток переводит предложения по очереди
4. Результаты через очередь → вкладка Argos

**LLM** (если включён в настройках):
1. Отдельный debounce (`llm_debounce_ms`, по умолчанию 1200 мс)
2. Короткий текст — один запрос; длинный — disjoint-чанки (файл: 3500 симв., редактор: 6000)
3. Результат → вкладка LLM; Argos продолжает работать параллельно

### Синхронизация прокрутки

Алгоритм:
1. Отслеживание позиции прокрутки оригинального текста (`yview()`)
2. При изменении → вычисление приблизительной позиции в переводе
3. Учёт разных длин текстов через оффсеты параграфов
4. Блокировка обратной синхронизации во время программной прокрутки

## Устранение неполадок

### "No translation backend found"

**Причина**: не установлен `argostranslate` или отсутствует CLI.

**Решение**:
```bash
pip install argostranslate
```

### "No translation models found"

**Причина**: отсутствуют модели перевода.

**Решение**:
1. Скачайте модели с https://www.argosopentech.com/argospm/
2. Поместите `.argosmodel` файлы в `argos_models/`
3. Запустите `python install_models.py`
4. Или установите через `argos-translate mo-install`

### "Hotkey unavailable: requires pyperclip and keyboard"

**Причина**: отсутствуют модули для горячих клавиш.

**Решение**:
```bash
pip install pyperclip keyboard
```

### Проблемы с буфером обмена (Linux)

**Причина**: требуется `xclip` или `xsel`.

**Решение**:
```bash
# Ubuntu/Debian
sudo apt-get install xclip

# Fedora
sudo dnf install xclip
```

### Окно не сворачивается в трей

**Причина**: отсутствуют `pystray` или `Pillow`.

**Решение**:
```bash
pip install pystray Pillow
```

### Трей работает некорректно на Linux

Если левый клик по иконке не разворачивает окно, задайте backend GTK:

```bash
export PYSTRAY_BACKEND=gtk
python main.py
```

Проверьте, что установлен `libappindicator`:
```bash
sudo apt-get install libappindicator3-1
```

## Разработка

### Добавление новых языков

Добавьте язык в класс `DefaultLanguages`:

```python
class DefaultLanguages:
    LANGUAGES: Dict[str, str] = {
        "en": "English",
        "ru": "Русский",
        # ...
        "xx": "Новый язык",  # Добавьте здесь
    }
```

### Настройка UI

Колорит и шрифты настраиваются в `UIConfig`:

```python
@dataclass
class UIConfig:
    font_main: Tuple[str, int] = ("Segoe UI", 10)
    font_text: Tuple[str, int] = ("Consolas", 13)
```

### Логирование

Логи пишутся в `log/app_debug.log` (разработка) или `{exe_dir}/log/app_debug.log` (собранный portable EXE). Уровень логирования можно изменить в `LoggingConfig.setup()`:

```python
logging.basicConfig(
    level=logging.DEBUG,  # или logging.INFO, logging.WARNING
    # ...
)
```

### Сборка исполняемого файла

Для сборки используйте PyInstaller:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=assets/argos_translate.ico main.py
```

Используйте `ArgosTranslator.spec` для расширенных настроек сборки:

```bash
pyinstaller ArgosTranslator.spec
```

## Лицензия

Проект использует Argos Translate — открытый движок перевода. См. лицензию Argos Translate для подробностей.

---

**Версия**: 1.0.0  
**Автор**: Argos OpenTech  
**Поддержка**: https://www.argosopentech.com/