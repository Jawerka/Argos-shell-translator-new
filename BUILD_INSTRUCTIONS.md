# Инструкция по сборке Argos Translate Streaming

## Проблема
Python 3.14 несовместим с numpy, ctranslate2 и argostranslate. Эти пакеты требуют Python 3.10-3.12.

## Решение: Сборка на Python 3.10

### 1. Установите Python 3.10
Скачайте с https://www.python.org/downloads/release/python-31011/

### 2. Создайте виртуальное окружение на Python 3.10
```bash
# Удалите старое окружение если есть
rmdir /s /q venv

# Создайте новое на Python 3.10
C:\Python310\python.exe -m venv venv

# Активируйте
venv\Scripts\activate
```

### 3. Установите зависимости
```bash
pip install -r requirements.txt
```

### 4. Проверьте работу
```bash
python main.py
```

### 5. Соберите исполняемый файл
```bash
python -m PyInstaller ArgosTranslator.spec --clean
```

### 6. Проверьте сборку
```bash
cd dist\ArgosTranslator
ArgosTranslator.exe
```

## Альтернатива: Использовать готовую сборку
Если сборка невозможна, используйте portable-версию с установленным Python 3.10.

## Примечания
- Модели перевода устанавливаются в `~/.local/share/argos-translate/packages/`
- Логи пишутся в `dist\ArgosTranslator\log\app_debug.log`
- Настройки сохраняются в `~/.argos_translate\settings.json`
