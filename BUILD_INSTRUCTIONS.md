# Инструкция по сборке Argos Translate

**Продукт:** Flutter UI + Python sidecar. Команда:

```powershell
scripts\build-windows.ps1
```

Результат: `dist/ArgosTranslate/` (`translator.exe`, `sidecar/argos_sidecar.exe`, не класть PyInstaller `_internal` в корень Flutter). Inno: `scripts/windows/argos-translate.iss` (`PrivilegesRequired=lowest`). Smoke: `python scripts/smoke_flutter_dist.py`.

Flutter SDK ищется через PATH, `FLUTTER_ROOT`, `.fvm/flutter_sdk` или `%LOCALAPPDATA%\flutter` (`scripts/resolve-flutter.ps1`). Pin: `.fvmrc` → 3.44.0.

## Требования

- **Flutter 3.44.0** (PATH / `FLUTTER_ROOT` / FVM / `%LOCALAPPDATA%\flutter`)
- **Python 3.10–3.12** (рекомендуется; Python 3.14 несовместим с numpy/ctranslate2/argostranslate)
- `venv` с `pip install -r requirements.txt` (для sidecar: `argostranslate`, `lingua-language-detector`, `charset-normalizer`; для сборки EXE — `pyinstaller`)
- Windows 10+ (основная платформа)

## Разработка

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pytest

scripts\dev.ps1

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

## Сборка Windows (Flutter + sidecar)

Перед сборкой (опционально):

```bash
python scripts/verify_spec.py
```

```powershell
scripts\build-windows.ps1
python scripts\smoke_flutter_dist.py
```

Sidecar отдельно:

```bash
pip install pyinstaller
pyinstaller ArgosSidecar.spec --clean --noconfirm
```

Результат PyInstaller: `dist/argos_sidecar/argos_sidecar.exe`. Скрипт сборки копирует его в `{app}/sidecar/` (не в корень Flutter — иначе конфликт DLL).

### Структура dist/

```
dist/ArgosTranslate/
├── translator.exe
├── data/                    ← Flutter assets
├── sidecar/
│   ├── argos_sidecar.exe
│   └── _internal/           ← PyInstaller runtime (не смешивать с корнем Flutter)
├── argos_models/            ← bundle *.argosmodel, если есть в репозитории
└── log/                     ← sidecar.log / app_debug.log (создаются при запуске)
```

### После сборки

1. Убедитесь, что `argos_models/*.argosmodel` попали в `dist/ArgosTranslate/argos_models/` (или поставьте bundle из UI)
2. Запустите `dist/ArgosTranslate/translator.exe` на машине без Python
3. Модели устанавливаются в `{app}/packages/` из настроек → Argos → установить bundle (`POST /v1/models/install {bundle:true}`)
4. Проверьте перевод en↔ru offline и лог `{app}/log/sidecar.log`

## Пути (dev и frozen)

| Что | Dev | Frozen (portable) |
|-----|-----|-------------------|
| Настройки | `%USERPROFILE%\.argos_translate\settings.json` | то же |
| Лог Flutter | `log/app_debug.log` (рядом с проектом) | `{app}/log/app_debug.log` |
| Лог sidecar | `log/sidecar.log` | `{app}/log/sidecar.log` |
| Модели Argos | `%LOCALAPPDATA%/argos-translate/packages/` | `{app}/packages/` |

## PyInstaller hooks

Кастомные хуки в `hooks/`:

- `hooks/hook-numpy.py` — numpy + DLL
- `hooks/hook-ctranslate2.py` — ctranslate2 DLL
- `hooks/hook-argostranslate.py` — подмодули argostranslate

## Известные проблемы

- **numpy в excludes** — не добавлять в spec (ломает ctranslate2)
- **UPX** — DLL ctranslate2 исключены из UPX (`upx_exclude`)
