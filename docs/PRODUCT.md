# Argos Translate — продуктовый контракт (Flutter + sidecar)

Windows-first переводчик: **Flutter UI** + **Python sidecar** для офлайн-Argos. LLM ходит из Dart в OpenAI-compatible API. Android, TTS, overlay à la DeepL, docx/pdf — вне v1.

Макеты в [`ui-mockups/`](../ui-mockups/) — визуальный контракт (не веб-приложение). CustomTkinter UI удалён.

## Уточнения к исходному плану

1. **Sidecar не копирует движки.** HTTP-процесс в `sidecar/` импортирует существующие `TranslateEngine`, `ModelManager`, `document_io`, `TextUtils`, `TranslationCoordinator`. Дублировать `argos_translator/` внутрь sidecar нельзя — сразу разъедется с pytest.
2. **Настройки принадлежат UI.** Sidecar не читает и не пишет `settings.json`. Параметры перевода приходят в каждом запросе. Секреты LLM — только во Flutter (`flutter_secure_storage`).
3. **Старт sidecar:** Flutter генерирует токен, кладёт его в `ARGOS_SIDECAR_TOKEN`, запускает процесс с `--host 127.0.0.1 --port 0 --parent-pid <pid>` (опционально `--token`), читает первую строку stdout или ready-файл `{"ok":true,"port":N}`. Слушать только loopback. Заголовок `X-Sidecar-Token` на всех методах, кроме опционального `GET /health` (liveness без деталей). Sidecar завершается, если родитель умер (watchdog). Лог: `{log_dir}/sidecar.log`, не stdout. Диагностика AUTO-языка: `{log_dir}/detect.log` (Flutter и sidecar; путь задаётся через `ARGOS_DETECT_LOG`).
4. **Melos не обязателен.** Два Dart-пакета — workspace в корневом `pubspec.yaml` и `scripts/dev.ps1`. Melos подключать, если пакетов станет больше.
5. **Settings v10 живут только в Dart** (`packages/translator_core`). Sidecar файл не читает. Новый инсталл: пустой LOCAL URL, хоткей не назначен. Явная пара en↔ru при миграции становится AUTO → RU.

## Как это работает

```
Ввод → debounce (Argos 700 мс / LLM 1200 мс)
  ├─ Argos: Flutter → POST /v1/translate (NDJSON) → sidecar → TranslateEngine
  └─ LLM:  Flutter → SSE chat/completions (Dart), sidecar не знает про LLM
```

Режим **both_adaptive**: оба движка параллельно, на экране одна вкладка.

## Главное окно

Контракт: [`ui-mockups/main.html`](../ui-mockups/main.html).

- Тулбар из трёх зон: Файл · языки+swap · Ещё / Перевести / Стоп / Настройки.
- Иконки векторные (Material), не эмодзи.
- Колонки 50/50, кнопки «на всю ширину», счётчик символов исходника.
- Переключение движка — segmented Argos / LLM. Бейджи только статус (готово / идёт / ошибка). Галочка LLM на панели **не дублирует** настройку: источник истины — `llm.enabled` в settings. Если LLM выключен, вкладка скрыта и worker не стартует.
- Пустая `tab_row` у исходника **не рисуется**.
- Редактор: Segoe UI Variable (системный пропорциональный). Опция «моноширинный» в настройках (`editor_font`: `system` | `mono`).
- Статусбар в покое: «Готово». Прогресс чанков — только пока идёт работа. Без «Backend missing» в UI.

### AUTO

- Селектор «откуда» остаётся AUTO. Правило фиксированное: **не русский → RU, русский → EN**.
- «Русский» — доля кириллицы от 0.3 после чистки (URL, упоминания, `:emoji:`, код). Имена и термины латиницей не входят в счёт: заглавная не в начале предложения, CamelCase, капс, цифры и `_`. Нет букв (ссылка, «OK», эмодзи) — как не русский.
- Нерусский язык: sidecar ставит метку Lingua (low-accuracy: en, de, fr, es, it, pt, nl, pl, cs, tr, sv, ja, zh, ko, ar, el, he, hi, th и установленные некириллические коды). Для латиницы метка берётся при 10+ буквах и уверенности от 0.8, иначе `en`. Кириллических языков в наборе нет. Метка уходит в LLM как есть. Argos без модели (например `de`) откатывается на `en→ru`.
- Пара считается один раз за цикл и одинаково уходит в Argos и LLM явными кодами (после resolve не `from=auto`). Детект sidecar вызывается только для нерусского.
- Чип рядом с селектором: `EN → RU` (метка → фактическая цель). Событие `start` чип не перетирает.
- Свап в AUTO разворачивает пару **только для текущего текста** (чип с точкой и отдельной подсказкой). Настройки не меняются. Повторный свап снимает разворот. Новый текст (вставка, а не правка: общий префикс и суффикс короче половины) снова идёт по правилу.
- Явная пара en↔ru разворачивается и сохраняется, если источник однозначный: доля кириллицы от 0.6 и минимум 2 кириллические буквы → `ru`; ни одной кириллической и минимум 2 латинские → `en`. Смесь явную пару не трогает. Другие пары (`de→fr`) не трогаются. Ручной свап или выбор в селекторе закрепляет текущий текст: автоправка его не меняет.
- Миграция settings v10: `languages.from` и `to` из {en, ru} становятся `from: auto`, `to: ru`, `auto_target_lang: ru`.
- Диагностика: `{log_dir}/detect.log`. В строке — превью 2–3 слов, счётчики и доля, метка, пара, причина (`auto` / `override` / `explicit` / `correct`). Свап пишет старую и новую пару. Путь: `DETECT path=...` в `app.log` / `sidecar.log`. `POST /v1/detect` возвращает `code` (для Argos) и `lang` (метка без подгонки).

### Streaming

| Режим | Поведение |
|-------|-----------|
| Поток вкл. | Ввод запускает Argos и LLM независимо (debounce 700 / 1200 мс). «Перевести» / Ctrl+Enter — немедленный прогон обоих без debounce. |
| Поток выкл. | Только кнопка / Ctrl+Enter. |

Тумблеры «поток» и «синхр. прокрутки» пишутся на диск сразу (не ждать resize).

### Стоп

Отменяет активные job (Argos + LLM), **оставляет уже полученный текст**, снимает busy. Esc = Стоп.

### Нет модели Argos

Правая панель Argos: empty/error + кнопка «Установить модели». LLM при этом может работать.

### Scroll-sync

Честный режим: **по абзацам** (якоря абзацев исходник ↔ перевод). Если якорей нет — подпись в настройках «приблизительно», линейный ratio без претензии на поабзацность. Мёртвые `src_offsets` не тащить.

### Файлы

DnD и «Открыть»: только plain-text из списка sidecar (`txt`, `md`, `csv`, `json`, …). Автокодировка — `POST /v1/files/decode`. Сохранить: активный перевод; Ctrl+Shift+S — оба (Argos и LLM в два файла, суффикс `_llm` для LLM как сейчас).

## Клавиатура

| Жест | Действие |
|------|----------|
| Ctrl+Enter | Перевести сейчас |
| Esc | Стоп |
| Ctrl+, | Настройки |
| Ctrl+O | Открыть файл |
| **Ctrl+S** | Сохранить перевод (не swap) |
| Ctrl+Shift+S | Сохранить оба |
| **Ctrl+Shift+X** (или кнопка ⇄) | Поменять языки |
| Тройной Ctrl+C (если включён) | Вставить скопированный текст и перевести |
| Tab | Фокус по контролам |

Глобальный хоткей **по умолчанию выключен** (пустая строка). Не перехватывать обычный Copy. Перед синтезом Ctrl+C ждать отпускания модификаторов; если буфер не изменился — не переводить старое содержимое. Тройной Ctrl+C: `behavior.triple_copy_enabled` (по умолчанию вкл.). Всплывающий overlay — фаза 2.

## Трей и окно

- Крестик → трей (если `close_action=tray`), пункт «Выход» в меню трея завершает sidecar и UI.
- Первый кадр: показать окно (или сразу трей, если `start_minimized_to_tray`).
- Геометрия: сохранить bounds, `clampToVisible`. Не вызывать `setProgressBar` (ACCESS_VIOLATION на части Windows).
- Трей инициализировать с задержкой ~800 мс (антивирус).
- Один экземпляр: named mutex + loopback agent UI (`POST /show`). Второй процесс отдаёт фокус первому и выходит.
- Sidecar — дочерний процесс UI: `--parent-pid` + watchdog, умирает вместе с родителем. Flutter следит за `exitCode` и перезапускает sidecar (до 3 попыток/мин) с баннером «движок перезапускается». Если sidecar не поднялся — экран ошибки с кнопкой «Открыть лог».

## First-run

Показывается, пока `first_run_done != true` (новый файл настроек). Существующие v8 при миграции получают `first_run_done=true`.

1. Тема (тёмная / светлая).
2. Установить bundle en↔ru.
3. LLM опционально: пустой URL, не LAN-IP. OpenRouter — предупреждение «текст уходит в облако».
4. «Закрытие сворачивает в трей».

## Настройки

Окно с левым NavigationView, 7 секций, как [`ui-mockups/settings.html`](../ui-mockups/settings.html). Не bottom sheet.

Секции: Внешний вид · Перевод · LLM · Файлы · Argos · Поведение · О программе.

Кнопки ОК / Применить / Отмена. Живой preview темы до ОК. Apply пишет файл сразу.

Модели LLM: диалог [`ui-mockups/model_picker.html`](../ui-mockups/model_picker.html) после «Загрузить модели», поиск по списку.

Копирайт UI: русский, sentence case. Имена Argos / LLM / LOCAL / OpenRouter допустимы. Строки «streaming», «Base URL», «Backend missing» в UI не использовать («потоковый перевод», «адрес сервера», «нет движка перевода»).

## Sidecar HTTP

Процесс: `python -m sidecar` (dev) или `argos_sidecar.exe` (frozen). Только `127.0.0.1`.

| Метод | Назначение |
|-------|------------|
| `GET /health` | `{ok, version}` без токена |
| `GET /v1/health` | токен; Argos доступен, пары моделей |
| `POST /v1/translate` | NDJSON-стрим чанков Argos |
| `POST /v1/detect` | `code` для Argos и `lang` — метка без подгонки |
| `GET /v1/languages` | словарь кодов |
| `GET /v1/models` | установленные пары + packages_dir |
| `POST /v1/models/install` | `{path}` или `{bundle: true}` |
| `POST /v1/files/decode` | `{path, max_size_mb}` |
| `POST /v1/cancel` | `{job_id?}` |

Заголовок: `X-Sidecar-Token`. Сравнение через `hmac.compare_digest`.

### NDJSON `/v1/translate`

Тело запроса:

```json
{
  "text": "...",
  "from": "auto",
  "to": "ru",
  "prefer_api": true,
  "translate_code_blocks": false,
  "cache": false,
  "packages_dir": ""
}
```

События (по строке):

```json
{"type":"start","job_id":1,"from":"en","to":"ru","unit_count":3}
{"type":"chunk","job_id":1,"index":0,"para_idx":0,"text":"...","done":1,"total":3}
{"type":"done","job_id":1}
{"type":"error","job_id":1,"message":"..."}
{"type":"cancelled","job_id":1}
```

Не подключать LibreTranslate и не писать Dart-FFI на CTranslate2.

Событие `error` всегда с `job_id`. Если пара моделей отсутствует (при непустом списке установленных) — `{"type":"error","message":"Нет модели en→ru"}` до вызова движка. `/v1/cancel` уважает `job_id`.

## Settings v10

Путь: `%USERPROFILE%\.argos_translate\settings.json`.

Новые поля относительно v8:

| Поле | Смысл |
|------|--------|
| `version` | `10` |
| `window.editor_font` | `system` \| `mono` |
| `ui.first_run_done` | мастер первого запуска |
| `llm.api_key_refs` | ссылки (`openrouter`, `custom`); сами ключи не в JSON |
| `llm.base_url` / `provider_urls.local` | по умолчанию `""` |
| `behavior.global_hotkey` | по умолчанию `""` |
| `behavior.triple_copy_enabled` | тройной Ctrl+C, по умолчанию `true` |

Миграция v8 → v9:

- `first_run_done = true` (не показывать мастер старому пользователю).
- URL и ключи **не стирать**. Flutter при первом чтении переносит plaintext `api_keys` в secure storage и записывает пустые `api_keys` + `api_key_refs`.
- Новый файл (нет settings.json): пустой LOCAL URL, хоткей выключен, `first_run_done=false`.

Миграция v9 → v10: если `languages.from` и `languages.to` оба из {en, ru}, записать `from: auto`, `to: ru`, `auto_target_lang: ru`. Пара вроде `de→fr` остаётся. URL и промпт не меняются.

## Визуал

Токены: [`ui-mockups/css/tokens.css`](../ui-mockups/css/tokens.css).

- Структура как MeshPad: `background / surface / border / primary / danger / success`.
- Акцент переводчика: циан `#3890b5` / hover `#0f92e6` (не синий MeshPad).
- Радиусы: 8 контролы, 12 карточки.
- Отступы: 4 / 8 / 12 / 16.
- UI 14px Regular, заголовки Semibold, Segoe UI Variable.
- Контраст WCAG AA, видимое фокус-кольцо, `Semantics` у кнопок.
- Немодальные подсказки сверху (не `messagebox` на каждую мелочь).
- LLM health: ошибка с кнопкой «Повторить», не вечный плейсхолдер `[LLM недоступна]` без Retry.

## Репозиторий

```
apps/translator/              Flutter Windows
packages/translator_core/     settings v10, sidecar client, LLM SSE, чанки
sidecar/                      HTTP вокруг src/argos_translator
src/argos_translator/        движки Argos для sidecar
ui-mockups/
scripts/                      dev.ps1, build-windows.ps1, *.iss
```

Pin Flutter: [`.fvmrc`](../.fvmrc) → `3.44.0` (как у HomeShare; channel stable). FVM не обязателен, если SDK на PATH.

Сборка v1: Flutter Release + PyInstaller sidecar (`console=False`) + `argos_models/` → Inno (`PrivilegesRequired=lowest`).

## Проверки этапа

| Этап | Можно считать готовым, если |
|------|------------------------------|
| 0 | PRODUCT.md + макеты с новыми токенами открываются в браузере |
| 1 | `python -m sidecar --help`; pytest translate/detect/models/decode/cancel |
| 2 | `scripts/dev.ps1` поднимает окно + sidecar; второй экземпляр отдаёт фокус |
| 3 | Ввод текста стримит Argos; LLM SSE в ту же панель; DnD файла |
| 4 | 7 секций настроек, picker моделей, установка Argos bundle |
| 5 | First-run, empty states, ключи не в JSON, дефолт без LAN-IP |
| 6 | Inno ставится на чистую Windows; CI: sidecar pytest + dart analyze + flutter test |
