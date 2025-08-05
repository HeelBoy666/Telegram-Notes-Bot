#!/usr/bin/env python3
"""
Скрипт для запуска веб-админ панели
"""

import os
import sys
import subprocess

def check_dependencies():
    """Проверка зависимостей"""
    try:
        import flask
        import flask_login
        print("✅ Зависимости установлены")
        return True
    except ImportError as e:
        print(f"❌ Отсутствуют зависимости: {e}")
        print("Установите зависимости командой: pip install -r requirements.txt")
        return False

def check_database():
    """Проверка наличия базы данных"""
    db_path = os.path.join(os.path.dirname(__file__), '..', 'notes.db')
    if os.path.exists(db_path):
        print("✅ База данных найдена")
        return True
    else:
        print("❌ База данных не найдена")
        print("Убедитесь, что файл notes.db существует в родительской папке")
        return False

def check_modules():
    """Проверка наличия модулей бота"""
    parent_dir = os.path.dirname(__file__)
    required_files = ['database.py', 'config.py']
    
    for file in required_files:
        file_path = os.path.join(parent_dir, '..', file)
        if os.path.exists(file_path):
            print(f"✅ {file} найден")
        else:
            print(f"❌ {file} не найден")
            return False
    
    return True

def main():
    """Главная функция"""
    print("🚀 Запуск веб-админ панели для Telegram бота")
    print("=" * 50)
    
    # Проверки
    if not check_dependencies():
        return 1
    
    if not check_database():
        return 1
    
    if not check_modules():
        return 1
    
    print("\n✅ Все проверки пройдены успешно!")
    print("\n🌐 Веб-панель будет доступна по адресам:")
    print("   • Локально: http://localhost:5000")
    print("   • С других устройств: http://188.123.231.247:5000")
    print("🔐 Для входа используйте ваш Telegram ID и пароль")
    print("\nНажмите Ctrl+C для остановки сервера")
    print("=" * 50)
    
    # Запуск Flask приложения
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\n\n👋 Веб-панель остановлена")
    except Exception as e:
        print(f"\n❌ Ошибка запуска: {e}")
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 