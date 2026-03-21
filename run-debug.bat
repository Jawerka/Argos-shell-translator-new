@echo off
REM =============================================================================
REM Argos Translate Streaming - Запуск с консолью для отладки
REM =============================================================================
REM Этот скрипт запускает приложение с видимой консолью для просмотра логов
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

REM Запуск приложения с флагом отладки
echo [INFO] Запуск Argos Translate Streaming (режим отладки)...
echo [INFO] Логи будут записаны в: log\app_debug.log
echo.

venv\Scripts\python.exe main.py

REM Если приложение завершилось с ошибкой
if errorlevel 1 (
    echo.
    echo [ERROR] Приложение завершилось с кодом ошибки %errorlevel%
    echo [INFO] Проверьте log\app_debug.log для деталей
    pause
)
