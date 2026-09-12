# Argos Translate

Windows-переводчик: **Flutter UI** + **Python sidecar** (офлайн Argos). LLM ходит из Dart в OpenAI-compatible API. Контракт: [`docs/PRODUCT.md`](docs/PRODUCT.md). Макеты: [`ui-mockups/`](ui-mockups/).

## Быстрый старт

Нужны **Flutter 3.44.0** (см. [`.fvmrc`](.fvmrc); `flutter` в PATH, `FLUTTER_ROOT` или `%LOCALAPPDATA%\flutter`) и **Python 3.10–3.12** (не 3.14 для Argos/ctranslate2).

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# модели en↔ru (если есть файлы)
# положить *.argosmodel в argos_models\  затем:
python install_models.py

scripts\dev.ps1
```

`scripts\dev.ps1` делает `flutter pub get` и `flutter run -d windows`. Sidecar поднимается из репозитория (`python -m sidecar`).

Проверки без окна:

```powershell
flutter pub get
dart analyze --fatal-infos packages/translator_core
# в packages/translator_core:
dart test
# в apps/translator:
flutter analyze --fatal-infos
flutter test
pytest tests/ -q -m "not integration"
```

## Сборка Windows

```powershell
scripts\build-windows.ps1
```

Скрипт:

1. `flutter build windows --release` в `apps/translator`
2. PyInstaller `ArgosSidecar.spec` → `dist/argos_sidecar/`
3. Staging `dist/ArgosTranslate/`:
   - `translator.exe`, Flutter DLL и `data/`
   - `sidecar/argos_sidecar.exe` + `sidecar/_internal/` (не в корне Flutter — иначе конфликт DLL)
   - `argos_models/` если в репозитории есть `*.argosmodel`
4. Inno Setup (`iscc`), если установлен: `PrivilegesRequired=lowest`

Smoke: `python scripts\smoke_flutter_dist.py`.

Установщик: `dist/argos-translate-<version>-windows-x64-setup.exe`.

## Модели Argos

Положите `.argosmodel` в `argos_models/` (en↔ru). В установленном приложении bundle копируется в `{app}/argos_models/`. Установка из UI: настройки → Argos → установить bundle. Загрузка: https://www.argosopentech.com/argospm/

## Настройки

- Файл: `%USERPROFILE%\.argos_translate\settings.json` (версия **9**)
- Ключи LLM — в Windows credential store (`flutter_secure_storage`), не в JSON
- Новый инсталл: пустой LOCAL URL, глобальный хоткей выключен
- Лог: `log/app_debug.log` рядом с приложением / репозиторием

## Клавиатура

| Жест | Действие |
|------|----------|
| Ctrl+Enter | Перевести сейчас |
| Esc | Стоп |
| Ctrl+, | Настройки |
| Ctrl+O | Открыть файл |
| Ctrl+S | Сохранить перевод |
| Ctrl+Shift+S | Сохранить оба (Argos и LLM) |
| Ctrl+Shift+X | Поменять языки |
| Тройной Ctrl+C | Вставить скопированный текст и перевести |

## Архитектура

```
Ввод → debounce (Argos 700 мс / LLM 1200 мс)
  ├─ Argos: Flutter → POST /v1/translate (NDJSON) → sidecar → TranslateEngine
  └─ LLM:  Flutter → SSE chat/completions (Dart)
```

```
apps/translator/           Flutter Windows
packages/translator_core/  settings v9, sidecar client, LLM SSE
sidecar/                   HTTP вокруг src/argos_translator
src/argos_translator/      движки (CTk UI пока в git)
scripts/build-windows.ps1
scripts/windows/argos-translate.iss
```

Sidecar слушает только `127.0.0.1`. Flutter кладёт токен в `ARGOS_SIDECAR_TOKEN`, запускает `--host 127.0.0.1 --port 0 --parent-pid <pid>`, читает `{"ok":true,"port":N}`.

## Legacy CustomTkinter

Старый GUI не удаляется, пока нет полного паритета; **не основной вход**.

```powershell
python main.py
# portable onedir:
venv\Scripts\python.exe -m PyInstaller ArgosTranslator.spec --clean --noconfirm
python scripts\smoke_dist.py
```

Подробности CTk-сборки: [`BUILD_INSTRUCTIONS.md`](BUILD_INSTRUCTIONS.md).

## Лицензия

Проект использует Argos Translate — открытый движок перевода.
