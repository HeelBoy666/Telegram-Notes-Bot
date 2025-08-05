#!/usr/bin/env python3
"""
Скрипт для получения IP адреса компьютера
"""

import socket
import subprocess
import platform

def get_local_ip():
    """Получение локального IP адреса"""
    try:
        # Создаем временное соединение для определения IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "Не удалось определить"

def get_all_ips():
    """Получение всех IP адресов"""
    ips = []
    
    try:
        # Получаем имя хоста
        hostname = socket.gethostname()
        
        # Получаем все IP адреса
        for info in socket.getaddrinfo(hostname, None):
            ip = info[4][0]
            if ip not in ips and not ip.startswith('127.'):
                ips.append(ip)
    except Exception:
        pass
    
    return ips

def main():
    """Главная функция"""
    print("🌐 Определение IP адресов для доступа к веб-панели")
    print("=" * 50)
    
    local_ip = get_local_ip()
    all_ips = get_all_ips()
    
    print(f"📍 Основной IP адрес: {local_ip}")
    print(f"🌍 Все доступные IP адреса:")
    
    for ip in all_ips:
        print(f"   • http://{ip}:5000")
    
    print("\n📱 Для доступа с других устройств используйте любой из этих адресов")
    print("🔐 Логин: ваш Telegram ID")
    print("🔑 Пароль: ваш пароль от веб-панели")
    print("\n💡 Если не работает, проверьте:")
    print("   • Брандмауэр Windows (разрешить порт 5000)")
    print("   • Антивирус (разрешить доступ)")
    print("   • Сетевое подключение")

if __name__ == '__main__':
    main() 