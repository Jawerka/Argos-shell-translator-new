@echo off
REM =============================================================================
REM Argos Translate Streaming - Запуск приложения
REM =============================================================================
REM Этот скрипт запускает приложение используя Python из виртуального окружения
REM =============================================================================

cd /d "%~dp0"

REM Проверка наличия venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Виртуальное окружение не найдено!
    echo [ERROR] Создайте venv командой:
    echo        py -3.10 -m venv venv
    echo        venv\Scripts\activate
    echo        pip install -r requirements.txt
    pause
    exit /b 1
)

REM Запуск приложения
echo [INFO] Запуск Argos Translate Streaming...
venv\Scripts\python.exe main.py

REM Если приложение завершилось с ошибкой
if errorlevel 1 (
    echo [ERROR] Приложение завершилось с кодом ошибки %errorlevel%
    pause
)
