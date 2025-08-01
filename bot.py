"""
Telegram-бот для заметок
Copyright (c) 2025 HeelBoy666
Licensed under MIT License (see LICENSE file)

Основной файл бота с обработчиками команд и состояний.
"""

import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup

from config import BOT_TOKEN, MAX_NOTES_PER_MESSAGE
from database import Database
from keyboards import (
    get_main_keyboard, get_admin_keyboard, get_admin_panel_keyboard, 
    get_admin_panel_inline_keyboard, get_role_management_keyboard, 
    get_users_list_keyboard, get_cancel_keyboard
)
from admin import AdminPanel

# Состояния FSM
class NoteStates(StatesGroup):
    waiting_for_note_text = State()
    waiting_for_delete_number = State()

class AdminPanelStates(StatesGroup):
    in_admin_panel = State()
    waiting_for_grant_user_id = State()
    waiting_for_revoke_user_id = State()

# Бот и диспетчер
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# База данных и админ-панель
db = Database()
admin_panel = AdminPanel()

# Статус бота
async def check_bot_status(message: types.Message) -> bool:
    """Проверка статуса бота и отправка сообщения если остановлен"""
    if admin_panel.is_bot_stopped() and not admin_panel.is_admin(message.from_user.id):
        await message.answer("🤖 Бот временно приостановлен администратором. Попробуйте позже.")
        return False
    return True

# Клавиатура
def get_user_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру в зависимости от роли пользователя"""
    if admin_panel.is_admin(user_id):
        return get_admin_keyboard()
    else:
        return get_main_keyboard()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработка команды /start"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    welcome_text = (
        "Привет! Я бот для заметок. 🤖\n\n"
        "Могу сохранить твои идеи, показать их или удалить. "
        "Что хочешь сделать?"
    )
    
    # Клавиатура по роли
    keyboard = get_user_keyboard(message.from_user.id)
    await message.answer(welcome_text, reply_markup=keyboard)

# АДМИН-КОМАНДЫ (только для админов)

@dp.message(Command("stop_bot"))
async def cmd_stop_bot(message: types.Message):
    """Команда для остановки бота (только для админа)"""
    success, result = admin_panel.stop_bot(message.from_user.id)
    await message.answer(result, reply_markup=get_user_keyboard(message.from_user.id))

@dp.message(Command("start_bot"))
async def cmd_start_bot(message: types.Message):
    """Команда для запуска бота (только для админа)"""
    success, result = admin_panel.start_bot(message.from_user.id)
    await message.answer(result, reply_markup=get_user_keyboard(message.from_user.id))

@dp.message(Command("users"))
async def cmd_users(message: types.Message):
    """Команда для просмотра списка пользователей (только для админа)"""
    success, result, users_data = admin_panel.get_users_list_paginated(message.from_user.id, page=1)
    
    if not success:
        await message.answer(result, reply_markup=get_user_keyboard(message.from_user.id))
        return
    
    if not users_data:
        await message.answer("Пользователей не найдено.", reply_markup=get_user_keyboard(message.from_user.id))
        return
    
    # Список пользователей
    users_text = f"📊 {result}\n\n"
    
    for i, (user_id, notes_count, role) in enumerate(users_data['users'], 1):
        if role == "main_admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👑 (Главный)\n"
        elif role == "admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} ⭐ (Админ)\n"
        else:
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👤\n"
    
    # Клавиатура с пагинацией
    keyboard = get_users_list_keyboard(
        users_data['page'], 
        users_data['total_pages'], 
        users_data['has_prev'], 
        users_data['has_next']
    )
    
    await message.answer(users_text, reply_markup=keyboard)

@dp.message(Command("admin"))
async def cmd_admin_help(message: types.Message, state: FSMContext):
    """Справка по админ-командам (только для админа)"""
    if not admin_panel.is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только администратор может использовать эту команду.")
        return
    
    # Состояние админ-панели
    await state.set_state(AdminPanelStates.in_admin_panel)
    
    admin_help = (
        "🔧 **Админ-панель:**\n\n"
        "Доступные функции:\n"
        "• ⏸️ Остановить бота - приостановить работу бота\n"
        "• ▶️ Запустить бота - возобновить работу бота\n"
        "• 👥 Список пользователей - просмотр статистики\n\n"
        f"🆔 Ваш ID: {message.from_user.id}"
    )
    
    # Инлайн-кнопки
    is_main_admin = admin_panel.is_main_admin(message.from_user.id)
    inline_keyboard = get_admin_panel_inline_keyboard(is_main_admin)
    
    await message.answer(admin_help, reply_markup=inline_keyboard)

# ОБЫЧНЫЕ КОМАНДЫ

@dp.message(Command("add"))
async def cmd_add_note(message: types.Message, state: FSMContext):
    """Обработка команды /add"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    await add_note_handler(message, state)

@dp.message(F.text == "📝 Добавить заметку")
async def add_note_handler(message: types.Message, state: FSMContext):
    """Обработка нажатия кнопки 'Добавить заметку'"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    await state.set_state(NoteStates.waiting_for_note_text)
    await message.answer(
        "Введите текст заметки:",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(NoteStates.waiting_for_note_text)
async def process_note_text(message: types.Message, state: FSMContext):
    """Обработка введенного текста заметки"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Добавление заметки отменено.",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
        return
    
    # Текст заметки
    if not message.text or not message.text.strip():
        await message.answer("Пожалуйста, введите текст заметки:")
        return
    
    # Длина текста
    if len(message.text) > 4000:
        await message.answer(
            "Текст заметки слишком длинный. Максимальная длина - 4000 символов. "
            "Пожалуйста, сократите текст:"
        )
        return
    
    # Сохранение в БД
    success, result_message = db.add_note(message.from_user.id, message.text.strip())
    
    if success:
        await message.answer(
            f"✅ {result_message}",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
    else:
        await message.answer(
            f"❌ {result_message}",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
    
    await state.clear()

@dp.message(Command("list"))
async def cmd_list_notes(message: types.Message):
    """Обработка команды /list"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    await list_notes_handler(message)

@dp.message(F.text == "📋 Показать заметки")
async def list_notes_handler(message: types.Message):
    """Обработка нажатия кнопки 'Показать заметки'"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    notes = db.get_user_notes(message.from_user.id)
    
    if not notes:
        await message.answer(
            "У вас нет заметок.",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
        return
    
    # Группы заметок
    for i in range(0, len(notes), MAX_NOTES_PER_MESSAGE):
        batch = notes[i:i + MAX_NOTES_PER_MESSAGE]
        notes_text = "Ваши заметки:\n\n"
        
        for j, (note_id, note_text) in enumerate(batch, start=i+1):
            notes_text += f"{j}. {note_text}\n"
        
        await message.answer(notes_text, reply_markup=get_user_keyboard(message.from_user.id))

@dp.message(Command("delete"))
async def cmd_delete_note(message: types.Message, state: FSMContext):
    """Обработка команды /delete"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    await delete_note_handler(message, state)

@dp.message(F.text == "🗑 Удалить заметку")
async def delete_note_handler(message: types.Message, state: FSMContext):
    """Обработка нажатия кнопки 'Удалить заметку'"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    notes = db.get_user_notes(message.from_user.id)
    
    if not notes:
        await message.answer(
            "У вас нет заметок для удаления.",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
        return
    
    # Сохранение в состояние
    await state.update_data(notes=notes)
    await state.set_state(NoteStates.waiting_for_delete_number)
    
    # Список заметок
    notes_text = "Выберите номер заметки для удаления:\n\n"
    for i, (note_id, note_text) in enumerate(notes, start=1):
        notes_text += f"{i}. {note_text}\n"
    
    await message.answer(
        notes_text,
        reply_markup=get_cancel_keyboard()
    )

@dp.message(NoteStates.waiting_for_delete_number)
async def process_delete_number(message: types.Message, state: FSMContext):
    """Обработка номера заметки для удаления"""
    if message.text == "❌ Отмена":
        await state.clear()
        await message.answer(
            "Удаление заметки отменено.",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
        return
    
    try:
        note_number = int(message.text)
        if note_number < 1:
            raise ValueError("Номер должен быть положительным")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный номер заметки:")
        return
    
    # Данные из состояния
    data = await state.get_data()
    notes = data.get('notes', [])
    
    if note_number > len(notes):
        await message.answer("Такой заметки нет. Попробуйте снова.")
        return
    
    # ID заметки
    note_id = notes[note_number - 1][0]
    
    # Удаление
    success, result_message = db.delete_note(message.from_user.id, note_id)
    
    if success:
        await message.answer(
            f"✅ {result_message}",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
    else:
        await message.answer(
            f"❌ {result_message}",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
    
    await state.clear()

# АДМИН-КНОПКИ

@dp.message(F.text == "🔧 Админ-панель")
async def admin_panel_handler(message: types.Message, state: FSMContext):
    """Обработка нажатия кнопки 'Админ-панель'"""
    if not admin_panel.is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только администратор может использовать эту функцию.")
        return
    
    # Состояние админ-панели
    await state.set_state(AdminPanelStates.in_admin_panel)
    
    admin_help = (
        "🔧 **Админ-панель:**\n\n"
        "Доступные функции:\n"
        "• ⏸️ Остановить бота - приостановить работу бота\n"
        "• ▶️ Запустить бота - возобновить работу бота\n"
        "• 👥 Список пользователей - просмотр статистики\n\n"
        f"🆔 Ваш ID: {message.from_user.id}"
    )
    
    # Инлайн-кнопки
    is_main_admin = admin_panel.is_main_admin(message.from_user.id)
    inline_keyboard = get_admin_panel_inline_keyboard(is_main_admin)
    
    await message.answer(admin_help, reply_markup=inline_keyboard)

@dp.message(F.text == "🔙 Назад к меню")
async def back_to_menu_handler(message: types.Message, state: FSMContext):
    """Обработка нажатия кнопки 'Назад к меню'"""
    if not admin_panel.is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только администратор может использовать эту функцию.")
        return
    
    # Очищаем состояние админ-панели
    await state.clear()
    
    await message.answer(
        "🔙 Возврат в главное меню",
        reply_markup=get_user_keyboard(message.from_user.id)
    )

@dp.message(F.text == "⏸️ Остановить бота")
async def stop_bot_button_handler(message: types.Message):
    """Обработка нажатия кнопки 'Остановить бота'"""
    if not admin_panel.is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только администратор может использовать эту функцию.")
        return
    
    success, result = admin_panel.stop_bot(message.from_user.id)
    await message.answer(result, reply_markup=get_admin_panel_keyboard())

@dp.message(F.text == "▶️ Запустить бота")
async def start_bot_button_handler(message: types.Message):
    """Обработка нажатия кнопки 'Запустить бота'"""
    if not admin_panel.is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только администратор может использовать эту функцию.")
        return
    
    success, result = admin_panel.start_bot(message.from_user.id)
    await message.answer(result, reply_markup=get_admin_panel_keyboard())

@dp.message(F.text == "👥 Список пользователей")
async def users_list_button_handler(message: types.Message):
    """Обработка нажатия кнопки 'Список пользователей'"""
    if not admin_panel.is_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только администратор может использовать эту функцию.")
        return
    
    success, result, users_data = admin_panel.get_users_list_paginated(message.from_user.id, page=1)
    
    if not success:
        await message.answer(result, reply_markup=get_admin_panel_keyboard())
        return
    
    if not users_data:
        await message.answer("Пользователей не найдено.", reply_markup=get_admin_panel_keyboard())
        return
    
    # Список пользователей
    users_text = f"📊 {result}\n\n"
    
    for i, (user_id, notes_count, role) in enumerate(users_data['users'], 1):
        if role == "main_admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👑 (Главный)\n"
        elif role == "admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} ⭐ (Админ)\n"
        else:
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👤\n"
    
    # Клавиатура с пагинацией
    keyboard = get_users_list_keyboard(
        users_data['page'], 
        users_data['total_pages'], 
        users_data['has_prev'], 
        users_data['has_next']
    )
    
    await message.answer(users_text, reply_markup=keyboard)

# ИНЛАЙН-КНОПКИ АДМИН-ПАНЕЛИ

@dp.callback_query(F.data == "admin_stop_bot")
async def admin_stop_bot_callback(callback: types.CallbackQuery):
    """Обработка инлайн-кнопки 'Остановить бота'"""
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success, result = admin_panel.stop_bot(callback.from_user.id)
    await callback.message.edit_text(f"⏸️ {result}")
    await callback.answer()

@dp.callback_query(F.data == "admin_start_bot")
async def admin_start_bot_callback(callback: types.CallbackQuery):
    """Обработка инлайн-кнопки 'Запустить бота'"""
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success, result = admin_panel.start_bot(callback.from_user.id)
    await callback.message.edit_text(f"▶️ {result}")
    await callback.answer()

@dp.callback_query(F.data == "admin_users_list")
async def admin_users_list_callback(callback: types.CallbackQuery):
    """Обработка инлайн-кнопки 'Список пользователей'"""
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success, result, users_data = admin_panel.get_users_list_paginated(callback.from_user.id, page=1)
    
    if not success:
        await callback.answer(result, show_alert=True)
        return
    
    if not users_data:
        await callback.answer("Пользователей не найдено.", show_alert=True)
        return
    
    # Список пользователей
    users_text = f"📊 {result}\n\n"
    
    for i, (user_id, notes_count, role) in enumerate(users_data['users'], 1):
        if role == "main_admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👑 (Главный)\n"
        elif role == "admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} ⭐ (Админ)\n"
        else:
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👤\n"
    
    # Клавиатура с пагинацией
    keyboard = get_users_list_keyboard(
        users_data['page'], 
        users_data['total_pages'], 
        users_data['has_prev'], 
        users_data['has_next']
    )
    
    # Обновление сообщения
    await callback.message.edit_text(users_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data.startswith("users_page_"))
async def users_page_callback(callback: types.CallbackQuery):
    """Обработка навигации по страницам списка пользователей"""
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    try:
        page = int(callback.data.split("_")[-1])
    except ValueError:
        await callback.answer("Ошибка номера страницы", show_alert=True)
        return
    
    success, result, users_data = admin_panel.get_users_list_paginated(callback.from_user.id, page=page)
    
    if not success:
        await callback.answer(result, show_alert=True)
        return
    
    if not users_data:
        await callback.answer("Пользователей не найдено.", show_alert=True)
        return
    
    # Список пользователей
    users_text = f"📊 {result}\n\n"
    
    for i, (user_id, notes_count, role) in enumerate(users_data['users'], 1):
        if role == "main_admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👑 (Главный)\n"
        elif role == "admin":
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} ⭐ (Админ)\n"
        else:
            users_text += f"{i}. ID: {user_id} | Заметок: {notes_count} 👤\n"
    
    # Клавиатура с пагинацией
    keyboard = get_users_list_keyboard(
        users_data['page'], 
        users_data['total_pages'], 
        users_data['has_prev'], 
        users_data['has_next']
    )
    
    # Обновление сообщения
    await callback.message.edit_text(users_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "users_info")
async def users_info_callback(callback: types.CallbackQuery):
    """Обработка нажатия на информацию о странице"""
    await callback.answer("Текущая страница", show_alert=False)

@dp.callback_query(F.data == "admin_manage_roles")
async def admin_manage_roles_callback(callback: types.CallbackQuery):
    """Обработка инлайн-кнопки 'Управление ролями'"""
    if not admin_panel.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    roles_text = (
        "👑 **Управление ролями:**\n\n"
        "Выберите действие:\n"
        "• ➕ Выдать роль админа - назначить нового администратора\n"
        "• ➖ Снять роль админа - снять права администратора\n"
        "• 📋 Список администраторов - просмотр всех админов"
    )
    
    await callback.message.edit_text(roles_text, reply_markup=get_role_management_keyboard())
    await callback.answer()

@dp.callback_query(F.data == "admin_admins_list")
async def admin_admins_list_callback(callback: types.CallbackQuery):
    """Обработка инлайн-кнопки 'Список администраторов'"""
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    success, result, admins_list = admin_panel.get_admins_list(callback.from_user.id)
    
    if not success:
        await callback.answer(result, show_alert=True)
        return
    
    if not admins_list:
        await callback.answer("Администраторов не найдено.", show_alert=True)
        return
    
    admins_text = f"👑 **{result}**\n\n"
    for i, (admin_id, role_type) in enumerate(admins_list, 1):
        admins_text += f"{i}. ID: {admin_id} | {role_type}\n"
    
    # Клавиатура
    if admin_panel.is_main_admin(callback.from_user.id):
        keyboard = get_role_management_keyboard()
    else:
        keyboard = get_admin_panel_inline_keyboard(False)
    
    await callback.message.edit_text(admins_text, reply_markup=keyboard)
    await callback.answer()

@dp.callback_query(F.data == "admin_grant_role")
async def admin_grant_role_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка инлайн-кнопки 'Выдать роль админа'"""
    if not admin_panel.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.set_state(AdminPanelStates.waiting_for_grant_user_id)
    await callback.message.edit_text(
        "➕ **Выдача роли администратора:**\n\n"
        "Введите ID пользователя, которому хотите выдать роль администратора:"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_revoke_role")
async def admin_revoke_role_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка инлайн-кнопки 'Снять роль админа'"""
    if not admin_panel.is_main_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.set_state(AdminPanelStates.waiting_for_revoke_user_id)
    await callback.message.edit_text(
        "➖ **Снятие роли администратора:**\n\n"
        "Введите ID пользователя, с которого хотите снять роль администратора:"
    )
    await callback.answer()

@dp.callback_query(F.data == "admin_panel_back")
async def admin_panel_back_callback(callback: types.CallbackQuery, state: FSMContext):
    """Обработка инлайн-кнопки 'Назад к админ-панели'"""
    if not admin_panel.is_admin(callback.from_user.id):
        await callback.answer("❌ Доступ запрещен", show_alert=True)
        return
    
    await state.clear()
    
    admin_help = (
        "🔧 **Админ-панель:**\n\n"
        "Доступные функции:\n"
        "• ⏸️ Остановить бота - приостановить работу бота\n"
        "• ▶️ Запустить бота - возобновить работу бота\n"
        "• 👥 Список пользователей - просмотр статистики\n\n"
        f"🆔 Ваш ID: {callback.from_user.id}"
    )
    
    is_main_admin = admin_panel.is_main_admin(callback.from_user.id)
    inline_keyboard = get_admin_panel_inline_keyboard(is_main_admin)
    
    await callback.message.edit_text(admin_help, reply_markup=inline_keyboard)
    await callback.answer()

# ВВОД ID ПОЛЬЗОВАТЕЛЕЙ

@dp.message(AdminPanelStates.waiting_for_grant_user_id)
async def process_grant_user_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для выдачи роли"""
    if not admin_panel.is_main_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только главный администратор может использовать эту функцию.")
        await state.clear()
        return
    
    try:
        target_user_id = int(message.text)
        if target_user_id <= 0:
            raise ValueError("ID должен быть положительным")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID пользователя (число):")
        return
    
    success, result = admin_panel.grant_admin_role(target_user_id, message.from_user.id)
    
    if success:
        await message.answer(f"✅ {result}", reply_markup=get_user_keyboard(message.from_user.id))
    else:
        await message.answer(f"❌ {result}", reply_markup=get_user_keyboard(message.from_user.id))
    
    await state.clear()

@dp.message(AdminPanelStates.waiting_for_revoke_user_id)
async def process_revoke_user_id(message: types.Message, state: FSMContext):
    """Обработка ввода ID пользователя для снятия роли"""
    if not admin_panel.is_main_admin(message.from_user.id):
        await message.answer("❌ Доступ запрещен. Только главный администратор может использовать эту функцию.")
        await state.clear()
        return
    
    try:
        target_user_id = int(message.text)
        if target_user_id <= 0:
            raise ValueError("ID должен быть положительным")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный ID пользователя (число):")
        return
    
    success, result = admin_panel.revoke_admin_role(target_user_id, message.from_user.id)
    
    if success:
        await message.answer(f"✅ {result}", reply_markup=get_user_keyboard(message.from_user.id))
    else:
        await message.answer(f"❌ {result}", reply_markup=get_user_keyboard(message.from_user.id))
    
    await state.clear()

@dp.message()
async def handle_unknown_message(message: types.Message):
    """Обработка неизвестных сообщений"""
    # Остановка бота
    if not await check_bot_status(message):
        return
    
    # Админ-справка
    if admin_panel.is_admin(message.from_user.id):
        await message.answer(
            "Используйте кнопки меню или команды:\n"
            "/start - Главное меню\n"
            "/add - Добавить заметку\n"
            "/list - Показать заметки\n"
            "/delete - Удалить заметку\n\n"
            "🔧 Админ-команды:\n"
            "/admin - Справка по админ-командам",
            reply_markup=get_user_keyboard(message.from_user.id)
        )
    else:
        await message.answer(
            "Извините, я не понимаю эту команду. Используйте кнопки меню:\n"
            "📝 Добавить заметку\n"
            "📋 Показать заметки\n"
            "🗑 Удалить заметку",
            reply_markup=get_user_keyboard(message.from_user.id)
        )

async def main():
    """Главная функция запуска бота"""
    print("🚀 Запуск бота для заметок...")
    print(f"🔧 Главный админ ID: {admin_panel.get_admin_id()}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 