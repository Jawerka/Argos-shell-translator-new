#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тесты для проверки импортов и работы движка перевода Argos.

Запуск:
    python test_translation.py

Тесты проверяют:
1. Импорт argostranslate и его подмодулей
2. Работу fallback через ctranslate2
3. Наличие установленных моделей
4. Работу TranslateEngine
"""

import sys
import importlib
from pathlib import Path

# Добавляем корень проекта в path
project_root = Path(__file__).parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def test_argostranslate_import():
    """Тест 1: Проверка импорта argostranslate."""
    print("\n" + "=" * 60)
    print("ТЕСТ 1: Импорт argostranslate")
    print("=" * 60)
    
    try:
        argostranslate = importlib.import_module("argostranslate")
        print(f"✓ argostranslate импортирован: {argostranslate}")
        print(f"  Путь: {argostranslate.__file__}")
        return True
    except Exception as e:
        print(f"✗ Ошибка импорта argostranslate: {e}")
        return False


def test_package_import():
    """Тест 2: Проверка импорта argostranslate.package."""
    print("\n" + "=" * 60)
    print("ТЕСТ 2: Импорт argostranslate.package")
    print("=" * 60)
    
    try:
        package = importlib.import_module("argostranslate.package")
        print(f"✓ argostranslate.package импортирован: {package}")
        
        # Проверяем наличие get_installed_packages
        get_packages = getattr(package, "get_installed_packages", None)
        if callable(get_packages):
            print("✓ get_installed_packages доступна")
            return True
        else:
            print("✗ get_installed_packages не найдена")
            return False
    except Exception as e:
        print(f"✗ Ошибка импорта package: {e}")
        return False


def test_translate_import():
    """Тест 3: Проверка импорта argostranslate.translate."""
    print("\n" + "=" * 60)
    print("ТЕСТ 3: Импорт argostranslate.translate")
    print("=" * 60)
    
    try:
        translate = importlib.import_module("argostranslate.translate")
        print(f"✓ argostranslate.translate импортирован: {translate}")
        
        # Проверяем наличие функции translate
        translate_fn = getattr(translate, "translate", None)
        if callable(translate_fn):
            print("✓ Функция translate доступна")
            return True
        else:
            print("✗ Функция translate не найдена")
            return False
    except Exception as e:
        print(f"✗ Ошибка импорта translate: {e}")
        print("  Это ожидаемо для Python 3.14 из-за несовместимости spacy")
        return False


def test_ctranslate2_import():
    """Тест 4: Проверка импорта ctranslate2."""
    print("\n" + "=" * 60)
    print("ТЕСТ 4: Импорт ctranslate2")
    print("=" * 60)
    
    try:
        ctranslate2 = importlib.import_module("ctranslate2")
        print(f"✓ ctranslate2 импортирован: {ctranslate2}")
        
        # Проверяем наличие Translator
        Translator = getattr(ctranslate2, "Translator", None)
        if Translator:
            print("✓ Translator класс доступен")
            return True
        else:
            print("✗ Translator класс не найден")
            return False
    except Exception as e:
        print(f"✗ Ошибка импорта ctranslate2: {e}")
        return False


def test_tokenizer_import():
    """Тест 5: Проверка импорта argostranslate.tokenizer."""
    print("\n" + "=" * 60)
    print("ТЕСТ 5: Импорт argostranslate.tokenizer")
    print("=" * 60)
    
    try:
        tokenizer = importlib.import_module("argostranslate.tokenizer")
        print(f"✓ argostranslate.tokenizer импортирован: {tokenizer}")
        
        # Проверяем наличие Tokenizer
        Tokenizer = getattr(tokenizer, "Tokenizer", None)
        if Tokenizer:
            print("✓ Tokenizer класс доступен")
            return True
        else:
            print("✗ Tokenizer класс не найден")
            return False
    except Exception as e:
        print(f"✗ Ошибка импорта tokenizer: {e}")
        return False


def test_installed_packages():
    """Тест 6: Проверка установленных пакетов перевода."""
    print("\n" + "=" * 60)
    print("ТЕСТ 6: Установленные пакеты перевода")
    print("=" * 60)
    
    try:
        from argostranslate.package import get_installed_packages
        
        packages = get_installed_packages()
        print(f"Найдено пакетов: {len(packages)}")
        
        for pkg in packages:
            from_code = getattr(pkg, "from_code", "?")
            to_code = getattr(pkg, "to_code", "?")
            pkg_type = getattr(pkg, "type", "?")
            print(f"  • {from_code} -> {to_code} (тип: {pkg_type})")
        
        # Проверяем наличие пар ru-en и en-ru
        translate_packages = [
            pkg for pkg in packages 
            if getattr(pkg, "type", None) == "translate"
        ]
        
        pairs = {(p.from_code, p.to_code) for p in translate_packages}
        
        has_ru_en = ("ru", "en") in pairs
        has_en_ru = ("en", "ru") in pairs
        
        if has_ru_en and has_en_ru:
            print("✓ Пары ru->en и en->ru доступны")
            return True
        else:
            print(f"✗ Не хватает пар: ru->en={has_ru_en}, en->ru={has_en_ru}")
            return False
    except Exception as e:
        print(f"✗ Ошибка проверки пакетов: {e}")
        return False


def test_custom_translate_fallback():
    """Тест 7: Проверка fallback через ctranslate2."""
    print("\n" + "=" * 60)
    print("ТЕСТ 7: Fallback через ctranslate2")
    print("=" * 60)
    
    # Сначала пробуем импортировать translate напрямую
    try:
        translate_module = importlib.import_module("argostranslate.translate")
        print("✓ argostranslate.translate доступен (fallback не нужен)")
        return True
    except Exception:
        print("argostranslate.translate недоступен, пробуем fallback...")
    
    # Пробуем fallback
    try:
        ctranslate2 = importlib.import_module("ctranslate2")
        from argostranslate.package import get_installed_packages
        
        # Находим пакет
        packages = get_installed_packages()
        pkg = None
        for p in packages:
            if p.from_code == "en" and p.to_code == "ru":
                pkg = p
                break
        
        if pkg is None:
            print("✗ Пакет en->ru не найден")
            return False
        
        print(f"✓ Пакет найден: {pkg.package_path}")
        print(f"  Токенизатор: {pkg.tokenizer}")
        
        # Проверяем токенизатор
        if pkg.tokenizer is None:
            print("✗ Токенизатор не найден")
            return False
        
        # Пробуем создать Translator
        model_path = str(pkg.package_path / "model")
        print(f"  Путь к модели: {model_path}")
        
        translator = ctranslate2.Translator(model_path, device="cpu")
        print("✓ Translator создан")
        
        # Пробуем токенизировать через tokenizer пакета
        tokens = pkg.tokenizer.encode("Hello")
        print(f"✓ Токенизация: {tokens}")
        
        # Пробуем перевести
        result = translator.translate_batch([tokens])
        print(f"✓ Перевод выполнен: {result}")
        
        # Декодируем (используем атрибуты TranslationResult)
        translated_tokens = result[0].hypotheses[0]
        translated_text = pkg.tokenizer.decode(translated_tokens)
        print(f"✓ Декодирование: {translated_text}")
        
        print(f"\n✓ Fallback работает! Перевод: 'Hello' -> '{translated_text.strip()}'")
        return True
        
    except Exception as e:
        print(f"✗ Ошибка fallback: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_translate_engine():
    """Тест 8: Проверка TranslateEngine из main.py."""
    print("\n" + "=" * 60)
    print("ТЕСТ 8: TranslateEngine из main.py")
    print("=" * 60)
    
    try:
        # Импортируем main модуль
        import main
        
        # Проверяем статус импортов
        print(f"ARGOS_MODULE_STATUS: {main.ARGOS_MODULE_STATUS}")
        print(f"AT_TRANSLATE_MODULE: {main.AT_TRANSLATE_MODULE}")
        print(f"AT_PACKAGE_MODULE: {main.AT_PACKAGE_MODULE}")
        
        # Создаем движок
        engine = main.TranslateEngine()
        print(f"use_api: {engine.use_api}")
        print(f"cli_path: {engine.cli_path}")
        
        if engine.use_api:
            print("✓ API backend доступен")
            
            # Пробуем перевести
            result = engine.translate("Hello", "en", "ru")
            print(f"✓ Перевод: 'Hello' -> '{result}'")
            return True
        elif engine.cli_path:
            print("✓ CLI backend доступен")
            return True
        else:
            print("✗ Нет доступных backend'ов")
            return False
            
    except Exception as e:
        print(f"✗ Ошибка TranslateEngine: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Запуск всех тестов."""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ ARGOS TRANSLATE")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"Platform: {sys.platform}")
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    
    results = []
    
    # Запускаем тесты
    results.append(("argos import", test_argostranslate_import()))
    results.append(("package import", test_package_import()))
    results.append(("translate import", test_translate_import()))
    results.append(("ctranslate2 import", test_ctranslate2_import()))
    results.append(("tokenizer import", test_tokenizer_import()))
    results.append(("installed packages", test_installed_packages()))
    results.append(("fallback ctranslate2", test_custom_translate_fallback()))
    results.append(("TranslateEngine", test_translate_engine()))
    
    # Итоги
    print("\n" + "=" * 60)
    print("ИТОГИ")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nВсего: {passed}/{total} тестов пройдено")
    
    if passed == total:
        print("\n✓ Все тесты пройдены!")
        return 0
    else:
        print(f"\n✗ {total - passed} тестов не пройдено")
        return 1


if __name__ == "__main__":
    sys.exit(main())
