"""
Конфигурация Telegram-бота
Copyright (c) 2025 HeelBoy666
Licensed under MIT License (see LICENSE file)

Настройки и переменные окружения для бота.
"""

import os
from dotenv import load_dotenv

# Загрузка .env
load_dotenv()

# Токен бота
BOT_TOKEN = os.getenv('BOT_TOKEN')

# ID администратора
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# База данных
DATABASE_NAME = 'notes.db'

# Максимум заметок в сообщении
MAX_NOTES_PER_MESSAGE = 5

# Логи
LOG_FILE = 'admin_actions.log' 