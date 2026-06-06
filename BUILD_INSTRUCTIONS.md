# Инструкция по сборке Argos Translate Streaming

## Требования

- **Python 3.10–3.12** (рекомендуется; Python 3.14 несовместим с numpy/ctranslate2/argostranslate)
- Windows 10+ (основная платформа)

## Разработка

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pytest

python main.py
# или
python -m argos_translator

pytest tests/ -q -m "not integration"
# полный прогон (включая integration, если модели Argos установлены):
pytest tests/ -q
```

## Модели Argos (bundle en↔ru)

Поместите `.argosmodel` в `argos_models/` и запустите:

```bash
python install_models.py
```

Или через **Настройки → Argos → Установить из bundle**.

## Сборка EXE (portable onedir)

Перед сборкой (опционально):

```bash
python scripts/verify_spec.py
```

```bat
scripts\build.bat
python scripts\smoke_dist.py
```

Или вручную:

```bash
pip install pyinstaller
pyinstaller ArgosTranslator.spec --clean --noconfirm
```

**Debug-сборка** (с консолью для диагностики):

```bash
pyinstaller ArgosTranslator.debug.spec --clean --noconfirm
```

### Структура dist/

```
dist/ArgosTranslator/
├── ArgosTranslator.exe
├── _internal/
├── assets/                  ← иконки (argos_translate.ico)
├── argos_models/          ← скопируйте *.argosmodel (en↔ru)
├── packages/              ← создаётся при первом запуске (bootstrap)
└── log/                   ← app_debug.log (создаётся при запуске)
```

### После сборки

1. Скопируйте `argos_models/*.argosmodel` в `dist/ArgosTranslator/argos_models/`
2. Запустите `dist/ArgosTranslator/ArgosTranslator.exe` на машине без Python
3. При первом запуске модели устанавливаются в `packages/` (`bootstrap_frozen_models`)
4. Проверьте перевод en↔ru offline и лог `{exe_dir}/log/app_debug.log`

## Пути (dev и frozen)

| Что | Dev | Frozen (portable) |
|-----|-----|-------------------|
| Настройки | `%USERPROFILE%\.argos_translate\settings.json` | то же |
| Логи | `log/app_debug.log` (рядом с проектом/exe) | `{exe_dir}/log/` |
| Модели Argos | `%LOCALAPPDATA%/argos-translate/packages/` | `{exe_dir}/packages/` |

## PyInstaller hooks

Кастомные хуки в `hooks/`:

- `hook-numpy.py` — numpy + DLL
- `hook-ctranslate2.py` — ctranslate2 DLL
- `hook-argostranslate.py` — подмодули argostranslate

## Известные проблемы

- **numpy в excludes** — не добавлять в spec (ломает ctranslate2)
- **UPX** — DLL ctranslate2 исключены из UPX (`upx_exclude`)
- При ошибках сборки используйте `ArgosTranslator.debug.spec`
