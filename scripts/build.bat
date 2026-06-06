@echo off
REM Сборка portable EXE (Python 3.10–3.12 рекомендуется)
setlocal

cd /d "%~dp0\.."

if not exist venv\Scripts\python.exe (
    echo Создайте venv на Python 3.10–3.12: py -3.10 -m venv venv
    exit /b 1
)

call venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller

python scripts\verify_spec.py
if errorlevel 1 exit /b 1

pyinstaller ArgosTranslator.spec --clean --noconfirm

echo.
echo Готово: dist\ArgosTranslator\ArgosTranslator.exe
echo Скопируйте argos_models\*.argosmodel в dist\ArgosTranslator\argos_models\
