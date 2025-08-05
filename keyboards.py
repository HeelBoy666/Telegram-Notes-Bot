"""
Модуль клавиатур
Copyright (c) 2025 HeelBoy666
Licensed under MIT License (see LICENSE file)

Функции для создания клавиатур и кнопок интерфейса.
"""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создание основной клавиатуры с кнопками для обычных пользователей"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Добавить заметку"), KeyboardButton(text="📋 Показать заметки")],
            [KeyboardButton(text="🗑 Удалить заметку")],
            [KeyboardButton(text="👥 Реферальная система")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры с админ-кнопками"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Добавить заметку"), KeyboardButton(text="📋 Показать заметки")],
            [KeyboardButton(text="🗑 Удалить заметку")],
            [KeyboardButton(text="🔧 Админ-панель")],
            [KeyboardButton(text="⏸️ Остановить бота"), KeyboardButton(text="▶️ Запустить бота")],
            [KeyboardButton(text="👥 Список пользователей")],
            [KeyboardButton(text="👥 Реферальная система")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard

def get_admin_panel_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры для админ-панели с кнопками управления"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏸️ Остановить бота")],
            [KeyboardButton(text="▶️ Запустить бота")],
            [KeyboardButton(text="👥 Список пользователей")],
            [KeyboardButton(text="🔙 Назад к меню")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие"
    )
    return keyboard

def get_users_list_keyboard(page: int, total_pages: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """Создание клавиатуры для списка пользователей с пагинацией"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    
    if has_prev:
        nav_buttons.append(InlineKeyboardButton(text="⬅️", callback_data=f"users_page_{page-1}"))
    
    nav_buttons.append(InlineKeyboardButton(text=f"{page}/{total_pages}", callback_data="users_info"))
    
    if has_next:
        nav_buttons.append(InlineKeyboardButton(text="➡️", callback_data=f"users_page_{page+1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Кнопка возврата
    keyboard.append([InlineKeyboardButton(text="🔙 Назад к админ-панели", callback_data="admin_panel_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admin_panel_inline_keyboard(is_main_admin: bool = False) -> InlineKeyboardMarkup:
    """Создание инлайн-клавиатуры для админ-панели"""
    keyboard = []
    
    # Основные кнопки для всех админов
    keyboard.append([
        InlineKeyboardButton(text="⏸️ Остановить бота", callback_data="admin_stop_bot"),
        InlineKeyboardButton(text="▶️ Запустить бота", callback_data="admin_start_bot")
    ])
    keyboard.append([
        InlineKeyboardButton(text="👥 Список пользователей", callback_data="admin_users_list")
    ])
    
    # Кнопки главного админа
    if is_main_admin:
        keyboard.append([
            InlineKeyboardButton(text="👑 Управление ролями", callback_data="admin_manage_roles")
        ])
        keyboard.append([
            InlineKeyboardButton(text="📋 Список администраторов", callback_data="admin_admins_list")
        ])
        keyboard.append([
            InlineKeyboardButton(text="🔧 Дебаг", callback_data="admin_debug_menu")
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_role_management_keyboard() -> InlineKeyboardMarkup:
    """Создание инлайн-клавиатуры для управления ролями"""
    keyboard = [
        [InlineKeyboardButton(text="➕ Выдать роль админа", callback_data="admin_grant_role")],
        [InlineKeyboardButton(text="➖ Снять роль админа", callback_data="admin_revoke_role")],
        [InlineKeyboardButton(text="📋 Список администраторов", callback_data="admin_admins_list")],
        [InlineKeyboardButton(text="🔙 Назад к админ-панели", callback_data="admin_panel_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_admins_list_keyboard() -> InlineKeyboardMarkup:
    """Создание инлайн-клавиатуры для списка администраторов"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад к управлению ролями", callback_data="admin_manage_roles")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_debug_menu_keyboard() -> InlineKeyboardMarkup:
    """Создание инлайн-клавиатуры для дебаг меню"""
    keyboard = [
        [InlineKeyboardButton(text="🔍 Отладка username", callback_data="debug_usernames"),
         InlineKeyboardButton(text="🔄 Обновить username", callback_data="debug_update_usernames")],
        [InlineKeyboardButton(text="📊 Отладка рефералов", callback_data="debug_referrals")],
        [InlineKeyboardButton(text="👥 Отладка пользователей", callback_data="debug_users")],
        [InlineKeyboardButton(text="📋 События", callback_data="debug_events")],
        [InlineKeyboardButton(text="🔧 Исправить рефералы", callback_data="debug_fix_referrals")],
        [InlineKeyboardButton(text="🔙 Назад к админ-панели", callback_data="admin_panel_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_debug_function_keyboard() -> InlineKeyboardMarkup:
    """Создание инлайн-клавиатуры для функций дебаг меню (только кнопка назад)"""
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад к дебаг меню", callback_data="admin_debug_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_debug_users_keyboard() -> InlineKeyboardMarkup:
    """Создание инлайн-клавиатуры для отладки пользователей (с кнопкой скачать)"""
    keyboard = [
        [InlineKeyboardButton(text="📥 Скачать данные", callback_data="debug_download_users")],
        [InlineKeyboardButton(text="🔙 Назад к дебаг меню", callback_data="admin_debug_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_debug_events_keyboard() -> InlineKeyboardMarkup:
    """Создание инлайн-клавиатуры для отладки событий (с кнопкой скачать)"""
    keyboard = [
        [InlineKeyboardButton(text="📥 Скачать события", callback_data="debug_download_events")],
        [InlineKeyboardButton(text="🔙 Назад к дебаг меню", callback_data="admin_debug_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Создание клавиатуры с кнопкой отмены"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Введите текст заметки или нажмите Отмена"
    )
    return keyboard

def get_referral_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🏆 Топ рефереров", callback_data="referral_top"),
         InlineKeyboardButton(text="📤 Поделиться", callback_data="referral_share")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_referral_back_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton(text="🔙 Назад", callback_data="referral_back")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard) 