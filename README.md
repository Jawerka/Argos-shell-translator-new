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

Программа использует движок **Argos Translate** для выполнения перевода и может работать как через Python API, так и через CLI утилиту `argos-translate`. Приложение поддерживает автоматическое определение языка исходного текста и имеет множество удобных функций, таких как синхронизация прокрутки, работа в системном трее и глобальные горячие клавиши.

## Функциональность

### Основные возможности

- **Потоковый перевод (Streaming)**: перевод обновляется автоматически при наборе текста с задержкой (debounce)
- **Поддержка API и CLI**: приложение автоматически использует доступный бэкенд (API или CLI)
- **Автоматическое определение языка**: определение языка через `langdetect` или эвристику на основе кириллицы
- **Синхронизация прокрутки**: прокрутка исходного текста и перевода синхронизированы по позиции
- **Работа в системном трее**: возможность сворачивания в трей с горячими клавишами
- **Сохранение настроек**: размер окна, выбранные языки, режимы сохраняются между сеансами
- **Установка моделей из bundle**: возможность установки моделей перевода из папки `argos_models`
- **Многоязычный интерфейс**: поддержка 14+ языков (EN, RU, DE, FR, ES, IT, PT, UK, ZH, JA, KO, AR, HI, TR)

### Особенности интерфейса

- Две панели: исходный текст и перевод
- Компактный селектор языков с кнопкой обмена
- Режим "Copy & Hide": копирование перевода и скрытие в трей
- Статусная строка с подсказками
- Поддержка вставки из буфера обмена

## Требования

### Обязательные зависимости

- **Python**: 3.8 или выше
- **argostranslate**: основной движок перевода (API + CLI)
- **pyperclip**: работа с буфером обмена

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
| `Ctrl + S` | Поменять языки местами |
| `Ctrl + Shift + C` | Захватить текст из буфера обмена (глобально) |

## Конфигурация

### Файлы конфигурации

- **Настройки**: `~/.argos_translate/settings.json`
- **Логи**: `~/.argos_translate/app_streaming.log`

### Структура settings.json

```json
{
  "window": {
    "geometry": "1000x700+100+100",
    "streaming": true,
    "scroll_sync": true
  },
  "languages": {
    "from": "auto",
    "to": "ru"
  }
}
```

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
├── main.py              # Главный файл приложения
├── install_models.py    # Установка моделей из bundle
├── requirements.txt     # Зависимости Python
├── .gitignore          # Игнорируемые файлы
├── README.md           # Этот файл
├── argos_models/       # bundle моделей (опционально)
│   └── *.argosmodel
├── installers/         # Установщики (опционально)
└── venv/              # Виртуальное окружение (игнорируется)
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

1. Пользователь вводит текст → событие `<<Modified>>`
2. Запускается `debounce_job` (700мс)
3. По истечении времени → `translate(streaming=True)`
4. Текст разбивается на параграфы → предложения
5. Для каждого предложения → отдельный перевод в worker потоке
6. Результаты помещаются в очередь → `_poll_translate_queue`
7. UI обновляется через `_update_translated_text()`

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

Логи пишутся в `~/.argos_translate/app_streaming.log`. Уровень логирования можно изменить в `LoggingConfig.setup()`:

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
pyinstaller --onefile --windowed --icon=argos_translate.ico main.py
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