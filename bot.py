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
import html

from config import BOT_TOKEN, MAX_NOTES_PER_MESSAGE
from database import Database
from keyboards import (
    get_main_keyboard, get_admin_keyboard, get_admin_panel_keyboard, 
    get_admin_panel_inline_keyboard, get_role_management_keyboard, 
    get_users_list_keyboard, get_cancel_keyboard, get_admins_list_keyboard,
    get_referral_keyboard, get_referral_back_keyboard, get_debug_menu_keyboard, 
    get_debug_function_keyboard, get_debug_users_keyboard, get_debug_events_keyboard
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

class ReferralStates(StatesGroup):
    in_referral_menu = State()

# База данных и админ-панель
db = Database()
admin_panel = AdminPanel()

# Глобальная переменная для контроля состояния бота
bot_running = True
stop_event = None

def stop_bot():
    """Функция для остановки бота"""
    global bot_running, stop_event
    bot_running = False
    if stop_event:
        stop_event.set()

def get_admin_panel_text(user_id: int) -> str:
    return (
        "🔧 <b>Админ-панель:</b>\n\n"
        "Доступные функции:\n"
        "• ⏸️ Остановить бота - приостановить работу бота\n"
        "• ▶️ Запустить бота - возобновить работу бота\n"
        "• 👥 Список пользователей - просмотр статистики\n\n"
        f"🆔 Ваш ID: <tg-spoiler>{user_id}</tg-spoiler>"
    )

def update_user_username(user_id: int, username: str = None):
    """Обновляет username пользователя в базе данных"""
    if username:
        db.save_username(user_id, username)

def get_user_display_name(user_id: int) -> str:
    """Возвращает отображаемое имя пользователя (username или ссылку на профиль)"""
    username = db.get_username_by_id(user_id)
    if username and username != f"user{user_id}":
        return f"@{username}"
    else:
        return f"[Пользователь](tg://user?id={user_id})"

def get_user_display_name_html(user_id: int) -> str:
    """Возвращает отображаемое имя пользователя в HTML формате"""
    username = db.get_username_by_id(user_id)
    if username and username != f"user{user_id}":
        return f"@{username}"
    else:
        return f"<a href=\"tg://user?id={user_id}\">Пользователь</a>"

def get_role_display_name(role: str) -> str:
    """Возвращает отображаемое название роли"""
    role_mapping = {
        'user': 'user',
        'admin': 'Admin', 
        'main_admin': 'Boss'
    }
    return role_mapping.get(role, role)

async def check_bot_status(message: types.Message) -> bool:
    """Проверяет статус бота и отправляет сообщение если бот остановлен"""
    if not bot_running:
        await message.answer("❌ Бот в данный момент остановлен администратором.", parse_mode="HTML")
        return False
    return True

def get_user_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    """Возвращает клавиатуру для пользователя в зависимости от его роли"""
    if admin_panel.is_admin(user_id):
        return get_admin_keyboard()
    return get_main_keyboard()

def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики для диспетчера"""
    
    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        """Обработчик команды /start"""
        user_id = message.from_user.id
        username = message.from_user.username
        
        update_user_username(user_id, username)
        
        start_param = message.text.split()[1] if len(message.text.split()) > 1 else None
        
        if start_param and start_param.startswith('ref'):
            try:
                referrer_id = int(start_param[3:])
                if referrer_id != user_id:
                    db.add_referral(referrer_id, user_id)
                    db._update_referral_stats(referrer_id)
                    
                    referrer_username = db.get_username_by_id(referrer_id)
                    referrer_display = f"@{referrer_username}" if referrer_username else f"Пользователь {referrer_id}"
                    
                    welcome_text = (
                        f"🎉 <b>Добро пожаловать!</b>\n\n"
                        f"Вы были приглашены пользователем <b>{referrer_display}</b>\n"
                        f"Спасибо за использование нашего бота!\n\n"
                        f"📝 <b>Основные команды:</b>\n"
                        f"• /add - добавить заметку\n"
                        f"• /list - показать заметки\n"
                        f"• /delete - удалить заметку\n"
                        f"• /help - справка\n\n"
                        f"🆔 Ваш ID: <tg-spoiler>{user_id}</tg-spoiler>"
                    )
                else:
                    welcome_text = (
                        "🎉 <b>Добро пожаловать!</b>\n\n"
                        "📝 <b>Основные команды:</b>\n"
                        "• /add - добавить заметку\n"
                        "• /list - показать заметки\n"
                        "• /delete - удалить заметку\n"
                        "• /help - справка\n\n"
                        f"🆔 Ваш ID: <tg-spoiler>{user_id}</tg-spoiler>"
                    )
            except (ValueError, IndexError):
                welcome_text = (
                    "🎉 <b>Добро пожаловать!</b>\n\n"
                    "📝 <b>Основные команды:</b>\n"
                    "• /add - добавить заметку\n"
                    "• /list - показать заметки\n"
                    "• /delete - удалить заметку\n"
                    "• /help - справка\n\n"
                    f"🆔 Ваш ID: <tg-spoiler>{user_id}</tg-spoiler>"
                )
        else:
            welcome_text = (
                "🎉 <b>Добро пожаловать!</b>\n\n"
                "📝 <b>Основные команды:</b>\n"
                "• /add - добавить заметку\n"
                "• /list - показать заметки\n"
                "• /delete - удалить заметку\n"
                "• /help - справка\n\n"
                f"🆔 Ваш ID: <tg-spoiler>{user_id}</tg-spoiler>"
            )
        
        db.add_user(user_id, username)
        
        db.add_bot_event("USER_START", f"Пользователь {user_id} запустил бота", user_id, "info")
        
        keyboard = get_user_keyboard(user_id)
        await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

    @dp.message(Command("help"))
    async def cmd_help(message: types.Message):
        """Обработчик команды /help"""
        user_id = message.from_user.id
        update_user_username(user_id, message.from_user.username)
        
        help_text = (
            "📚 <b>Справка по командам:</b>\n\n"
            "📝 <b>Основные команды:</b>\n"
            "• /start - запуск бота\n"
            "• /add - добавить заметку\n"
            "• /list - показать заметки\n"
            "• /delete - удалить заметку\n"
            "• /help - эта справка\n\n"
        )
        
        if admin_panel.is_admin(user_id):
            help_text += (
                "🔧 <b>Админские команды:</b>\n"
                "• /admin - админ-панель\n"
                "• /users - список пользователей\n"
                "• /stop_bot - остановить бота\n"
                "• /start_bot - запустить бота\n\n"
            )
        
        help_text += (
            "👥 <b>Реферальная система:</b>\n"
            "• Используйте кнопку 'Реферальная система' для получения реферальной ссылки\n"
            "• Приглашайте друзей и получайте бонусы!\n\n"
            f"🆔 Ваш ID: <tg-spoiler>{user_id}</tg-spoiler>"
        )
        
        keyboard = get_user_keyboard(user_id)
        await message.answer(help_text, reply_markup=keyboard, parse_mode="HTML")

    @dp.message(Command("stop_bot"))
    async def cmd_stop_bot(message: types.Message):
        """Обработчик команды /stop_bot"""
        if not admin_panel.is_admin(message.from_user.id):
            await message.answer("❌ У вас нет прав для выполнения этой команды.", parse_mode="HTML")
            return
        
        global bot_running
        bot_running = False
        stop_bot()
        
        await message.answer("⏸️ Бот остановлен.", parse_mode="HTML")
        db.add_bot_event("BOT_STOPPED", f"Бот остановлен пользователем {message.from_user.id}", 
                        message.from_user.id, "warning")

    @dp.message(Command("start_bot"))
    async def cmd_start_bot(message: types.Message):
        """Обработчик команды /start_bot"""
        if not admin_panel.is_admin(message.from_user.id):
            await message.answer("❌ У вас нет прав для выполнения этой команды.", parse_mode="HTML")
            return
        
        global bot_running
        bot_running = True
        
        await message.answer("▶️ Бот запущен.", parse_mode="HTML")
        db.add_bot_event("BOT_STARTED", f"Бот запущен пользователем {message.from_user.id}", 
                        message.from_user.id, "info")

    @dp.message(Command("users"))
    async def cmd_users(message: types.Message):
        """Обработчик команды /users"""
        if not admin_panel.is_admin(message.from_user.id):
            await message.answer("❌ У вас нет прав для выполнения этой команды.", parse_mode="HTML")
            return
        
        update_user_username(message.from_user.id, message.from_user.username)
        
        total_users = db.get_total_users()
        active_users = db.get_active_users_count()
        new_users_today = db.get_new_users_today()
        
        users_text = (
            "👥 <b>Статистика пользователей:</b>\n\n"
            f"📊 Всего пользователей: <b>{total_users}</b>\n"
            f"✅ Активных пользователей: <b>{active_users}</b>\n"
            f"🆕 Новых сегодня: <b>{new_users_today}</b>\n\n"
            f"🆔 Ваш ID: <tg-spoiler>{message.from_user.id}</tg-spoiler>"
        )
        
        keyboard = get_admin_keyboard()
        await message.answer(users_text, reply_markup=keyboard, parse_mode="HTML")

    @dp.message(Command("admin"))
    async def cmd_admin_help(message: types.Message, state: FSMContext):
        """Обработчик команды /admin"""
        if not admin_panel.is_admin(message.from_user.id):
            await message.answer("❌ У вас нет прав для выполнения этой команды.", parse_mode="HTML")
            return
        
        update_user_username(message.from_user.id, message.from_user.username)
        await state.set_state(AdminPanelStates.in_admin_panel)
        
        admin_text = get_admin_panel_text(message.from_user.id)
        keyboard = get_admin_panel_keyboard()
        await message.answer(admin_text, reply_markup=keyboard, parse_mode="HTML")

    @dp.message(Command("add"))
    async def cmd_add_note(message: types.Message, state: FSMContext):
        """Обработчик команды /add"""
        if not await check_bot_status(message):
            return
        await add_note_handler(message, state)

    @dp.message(F.text == "📝 Добавить заметку")
    async def add_note_handler(message: types.Message, state: FSMContext):
        """Обработчик нажатия кнопки 'Добавить заметку'"""
        update_user_username(message.from_user.id, message.from_user.username)
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
        
        if not message.text or not message.text.strip():
            await message.answer("Пожалуйста, введите текст заметки:")
            return
        
        if len(message.text) > 4000:
            await message.answer(
                "Текст заметки слишком длинный. Максимальная длина - 4000 символов. "
                "Пожалуйста, сократите текст:"
            )
            return
        
        success, result_message = db.add_note(message.from_user.id, message.text.strip())
        
        if success:
            db.add_bot_event("NOTE_ADDED", f"Добавлена заметка (ID: {message.from_user.id})", 
                            message.from_user.id, "info")
        else:
            db.add_bot_event("NOTE_ADD_FAILED", f"Ошибка добавления заметки: {result_message}", 
                            message.from_user.id, "error")
        
        await message.answer(result_message, reply_markup=get_user_keyboard(message.from_user.id))
        await state.clear()

    @dp.message(Command("list"))
    async def cmd_list_notes(message: types.Message):
        """Обработчик команды /list"""
        if not await check_bot_status(message):
            return
        await list_notes_handler(message)

    @dp.message(F.text == "📋 Показать заметки")
    async def list_notes_handler(message: types.Message):
        """Обработчик нажатия кнопки 'Показать заметки'"""
        update_user_username(message.from_user.id, message.from_user.username)
        if not await check_bot_status(message):
            return
        
        notes = db.get_user_notes(message.from_user.id)
        
        if not notes:
            await message.answer(
                "У вас нет заметок.",
                reply_markup=get_user_keyboard(message.from_user.id)
            )
            return
        
        for i in range(0, len(notes), MAX_NOTES_PER_MESSAGE):
            batch = notes[i:i + MAX_NOTES_PER_MESSAGE]
            notes_text = "Ваши заметки:\n\n"
            
            for j, (note_id, note_text) in enumerate(batch, start=i+1):
                notes_text += f"{j}. {note_text}\n"
            
            await message.answer(notes_text, reply_markup=get_user_keyboard(message.from_user.id))

    @dp.message(Command("delete"))
    async def cmd_delete_note(message: types.Message, state: FSMContext):
        """Обработчик команды /delete"""
        if not await check_bot_status(message):
            return
        await delete_note_handler(message, state)

    @dp.message(F.text == "🗑 Удалить заметку")
    async def delete_note_handler(message: types.Message, state: FSMContext):
        """Обработчик нажатия кнопки 'Удалить заметку'"""
        update_user_username(message.from_user.id, message.from_user.username)
        if not await check_bot_status(message):
            return
        
        notes = db.get_user_notes(message.from_user.id)
        
        if not notes:
            await message.answer(
                "У вас нет заметок для удаления.",
                reply_markup=get_user_keyboard(message.from_user.id)
            )
            return
        
        await state.update_data(notes=notes)
        await state.set_state(NoteStates.waiting_for_delete_number)
        
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
        
        data = await state.get_data()
        notes = data.get('notes', [])
        
        if note_number > len(notes):
            await message.answer("Такой заметки нет. Попробуйте снова.")
            return
        
        note_id = notes[note_number - 1][0]
        
        success, result_message = db.delete_note(message.from_user.id, note_id)
        
        if success:
            db.add_bot_event("NOTE_DELETED", f"Удалена заметка {note_id} (ID: {message.from_user.id})", 
                            message.from_user.id, "info")
        else:
            db.add_bot_event("NOTE_DELETE_FAILED", f"Ошибка удаления заметки: {result_message}", 
                            message.from_user.id, "error")
        
        await message.answer(result_message, reply_markup=get_user_keyboard(message.from_user.id))
        await state.clear()

    # Обработчики кнопок админ-панели
    @dp.message(F.text == "🔧 Админ-панель")
    async def admin_panel_handler(message: types.Message, state: FSMContext):
        """Обработчик нажатия кнопки 'Админ-панель'"""
        update_user_username(message.from_user.id, message.from_user.username)
        if not admin_panel.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен. Только администратор может использовать эту функцию.")
            return
        
        await state.set_state(AdminPanelStates.in_admin_panel)
        
        admin_help = get_admin_panel_text(message.from_user.id)
        is_main_admin = admin_panel.is_main_admin(message.from_user.id)
        inline_keyboard = get_admin_panel_inline_keyboard(is_main_admin)
        
        await message.answer(admin_help, reply_markup=inline_keyboard, parse_mode="HTML")

    @dp.message(F.text == "🔙 Назад к меню")
    async def back_to_menu_handler(message: types.Message, state: FSMContext):
        """Обработчик нажатия кнопки 'Назад к меню'"""
        update_user_username(message.from_user.id, message.from_user.username)
        if not admin_panel.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен. Только администратор может использовать эту функцию.")
            return
        
        await state.clear()
        
        await message.answer(
            "🔙 Возврат в главное меню",
            reply_markup=get_user_keyboard(message.from_user.id)
        )

    @dp.message(F.text == "⏸️ Остановить бота")
    async def stop_bot_button_handler(message: types.Message):
        """Обработчик кнопки остановки бота"""
        update_user_username(message.from_user.id, message.from_user.username)
        success, result = admin_panel.stop_bot(message.from_user.id)
        
        if success:
            db.add_bot_event("BOT_STOP_BUTTON", f"Бот остановлен через кнопку администратором {message.from_user.username or message.from_user.id}", 
                            message.from_user.id, "warning")
        else:
            db.add_bot_event("BOT_STOP_BUTTON_FAILED", f"Попытка остановки бота через кнопку неудачна: {result}", 
                            message.from_user.id, "error")
        
        await message.answer(result, reply_markup=get_user_keyboard(message.from_user.id))

    @dp.message(F.text == "▶️ Запустить бота")
    async def start_bot_button_handler(message: types.Message):
        """Обработчик кнопки запуска бота"""
        update_user_username(message.from_user.id, message.from_user.username)
        success, result = admin_panel.start_bot(message.from_user.id)
        
        if success:
            db.add_bot_event("BOT_START_BUTTON", f"Бот запущен через кнопку администратором {message.from_user.username or message.from_user.id}", 
                            message.from_user.id, "info")
        else:
            db.add_bot_event("BOT_START_BUTTON_FAILED", f"Попытка запуска бота через кнопку неудачна: {result}", 
                            message.from_user.id, "error")
        
        await message.answer(result, reply_markup=get_user_keyboard(message.from_user.id))

    @dp.message(F.text == "👥 Список пользователей")
    async def users_list_button_handler(message: types.Message):
        """Обработчик нажатия кнопки 'Список пользователей'"""
        update_user_username(message.from_user.id, message.from_user.username)
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
        
        users_text = f"📊 {result}\n\n"
        
        for i, (user_id, notes_count, role, total_referrals, active_referrals) in enumerate(users_data['users'], 1):
            display_name = get_user_display_name(user_id)
            
            if role == "main_admin":
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} 👑 (Boss)\n"
            elif role == "admin":
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} ⭐ (Admin)\n"
            else:
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} 👤 (User)\n"
        
        keyboard = get_users_list_keyboard(
            users_data['page'], 
            users_data['total_pages'], 
            users_data['has_prev'], 
            users_data['has_next']
        )
        
        await message.answer(users_text, reply_markup=keyboard, parse_mode="Markdown")

    @dp.message(F.text == "👥 Реферальная система")
    async def referral_system_handler(message: types.Message, state: FSMContext):
        """Обработчик нажатия кнопки 'Реферальная система'"""
        update_user_username(message.from_user.id, message.from_user.username)
        if not await check_bot_status(message):
            return
        
        await state.set_state(ReferralStates.in_referral_menu)
        
        total_referrals, active_referrals = db.get_referral_stats(message.from_user.id)
        referrer_info = db.get_referrer_info(message.from_user.id)
        
        referral_text = (
            "👥 <b>Реферальная система:</b>\n\n"
            f"Вы пригласили: <b>{total_referrals}</b> пользователей\n"
            f"Активных рефералов: <b>{active_referrals}</b>\n"
            f"Конверсия: <b>{round(active_referrals/total_referrals*100, 1) if total_referrals > 0 else 0}%</b>\n"
        )
        
        if referrer_info:
            referrer_id, referrer_username = referrer_info
            referral_text += f"\n🎉 Вас пригласил: <b>@{referrer_username}</b>\n"
        
        referral_text += (
            "\nПриглашайте друзей и получайте бонусы!\n\n"
            "Выберите действие:"
        )
        
        await message.answer(referral_text, reply_markup=get_referral_keyboard(), parse_mode="HTML")

    # Обработчик неизвестных сообщений
    @dp.message()
    async def handle_unknown_message(message: types.Message):
        """Обработка неизвестных сообщений - показывает справку"""
        if not await check_bot_status(message):
            return
        
        await cmd_help(message)

    # Инлайн-кнопки админ-панели
    @dp.callback_query(F.data == "admin_stop_bot")
    async def admin_stop_bot_callback(callback: types.CallbackQuery):
        """Обработка кнопки остановки бота в админ-панели"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        success, result = admin_panel.stop_bot(callback.from_user.id)
        
        if success:
            db.add_bot_event("BOT_STOP_CALLBACK", f"Бот остановлен через админ-панель администратором {callback.from_user.username or callback.from_user.id}", 
                            callback.from_user.id, "warning")
        else:
            db.add_bot_event("BOT_STOP_CALLBACK_FAILED", f"Попытка остановки бота через админ-панель неудачна: {result}", 
                            callback.from_user.id, "error")
        
        await callback.answer(result, show_alert=True)
        await callback.message.edit_text(get_admin_panel_text(callback.from_user.id), reply_markup=get_admin_panel_inline_keyboard(), parse_mode="HTML")

    @dp.callback_query(F.data == "admin_start_bot")
    async def admin_start_bot_callback(callback: types.CallbackQuery):
        """Обработка кнопки запуска бота в админ-панели"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        success, result = admin_panel.start_bot(callback.from_user.id)
        
        if success:
            db.add_bot_event("BOT_START_CALLBACK", f"Бот запущен через админ-панель администратором {callback.from_user.username or callback.from_user.id}", 
                            callback.from_user.id, "info")
        else:
            db.add_bot_event("BOT_START_CALLBACK_FAILED", f"Попытка запуска бота через админ-панель неудачна: {result}", 
                            callback.from_user.id, "error")
        
        await callback.answer(result, show_alert=True)
        await callback.message.edit_text(get_admin_panel_text(callback.from_user.id), reply_markup=get_admin_panel_inline_keyboard(), parse_mode="HTML")

    @dp.callback_query(F.data == "admin_users_list")
    async def admin_users_list_callback(callback: types.CallbackQuery):
        """Обработка инлайн-кнопки 'Список пользователей'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
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
        
        users_text = f"📊 {result}\n\n"
        
        for i, (user_id, notes_count, role, total_referrals, active_referrals) in enumerate(users_data['users'], 1):
            display_name = get_user_display_name(user_id)
            
            if role == "main_admin":
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} 👑 (Boss)\n"
            elif role == "admin":
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} ⭐ (Admin)\n"
            else:
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} 👤 (User)\n"
        
        keyboard = get_users_list_keyboard(
            users_data['page'], 
            users_data['total_pages'], 
            users_data['has_prev'], 
            users_data['has_next']
        )
        
        await callback.message.edit_text(users_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()

    @dp.callback_query(F.data.startswith("users_page_"))
    async def users_page_callback(callback: types.CallbackQuery):
        """Обработка навигации по страницам списка пользователей"""
        update_user_username(callback.from_user.id, callback.from_user.username)
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
        
        users_text = f"📊 {result}\n\n"
        
        for i, (user_id, notes_count, role, total_referrals, active_referrals) in enumerate(users_data['users'], 1):
            display_name = get_user_display_name(user_id)
            
            if role == "main_admin":
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} 👑 (Boss)\n"
            elif role == "admin":
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} ⭐ (Admin)\n"
            else:
                users_text += f"{i}. {display_name} | Заметок: {notes_count} | Рефералов: {total_referrals} 👤 (User)\n"
        
        keyboard = get_users_list_keyboard(
            users_data['page'], 
            users_data['total_pages'], 
            users_data['has_prev'], 
            users_data['has_next']
        )
        
        await callback.message.edit_text(users_text, reply_markup=keyboard, parse_mode="Markdown")
        await callback.answer()

    @dp.callback_query(F.data == "users_info")
    async def users_info_callback(callback: types.CallbackQuery):
        """Обработка нажатия на информацию о странице"""
        await callback.answer("Текущая страница", show_alert=False)

    @dp.callback_query(F.data == "admin_manage_roles")
    async def admin_manage_roles_callback(callback: types.CallbackQuery):
        """Обработка инлайн-кнопки 'Управление ролями'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        roles_text = (
            "👑 <b>Управление ролями:</b>\n\n"
            "Выберите действие:\n"
            "• ➕ Выдать роль админа - назначить нового администратора\n"
            "• ➖ Снять роль админа - снять права администратора\n"
            "• 📋 Список администраторов - просмотр всех админов"
        )
        
        await callback.message.edit_text(roles_text, reply_markup=get_role_management_keyboard(), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "admin_admins_list")
    async def admin_admins_list_callback(callback: types.CallbackQuery):
        """Обработка инлайн-кнопки 'Список администраторов'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
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
        
        admins_text = f"👑 <b>{result}</b>\n\n"
        for i, (admin_id, role_type) in enumerate(admins_list, 1):
            safe_id = html.escape(str(admin_id))
            admins_text += f"{i}. ID: <tg-spoiler>{safe_id}</tg-spoiler> | {role_type}\n"
        if admin_panel.is_main_admin(callback.from_user.id):
            keyboard = get_admins_list_keyboard()
        else:
            keyboard = get_admin_panel_inline_keyboard(False)
        await callback.message.edit_text(admins_text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "admin_referral_stats")
    async def admin_referral_stats_callback(callback: types.CallbackQuery):
        """Обработка инлайн-кнопки 'Реферальная статистика'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        top_referrers = db.get_top_referrers(5)
        
        if not top_referrers:
            stats_text = "📊 <b>Реферальная статистика:</b>\n\nПока нет данных о рефералах."
        else:
            stats_text = "📊 <b>Реферальная статистика:</b>\n\n"
            stats_text += "🏆 <b>Топ-5 рефереров:</b>\n"
            for i, (user_id, total, active) in enumerate(top_referrers, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                stats_text += f"{medal} ID: {user_id} | {total} рефералов ({active} активных)\n"
            
            total_referrals = sum(total for _, total, _ in top_referrers)
            total_active = sum(active for _, _, active in top_referrers)
            stats_text += f"\n📈 <b>Общая статистика:</b>\n"
            stats_text += f"👥 Всего рефералов: {total_referrals}\n"
            stats_text += f"✅ Активных рефералов: {total_active}\n"
            stats_text += f"📊 Конверсия: {round(total_active/total_referrals*100, 1) if total_referrals > 0 else 0}%"
        
        await callback.message.edit_text(stats_text, reply_markup=get_admin_panel_inline_keyboard(admin_panel.is_main_admin(callback.from_user.id)), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "admin_debug_menu")
    async def admin_debug_menu_callback(callback: types.CallbackQuery):
        """Обработка инлайн-кнопки 'Дебаг'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        debug_text = (
            "🔧 <b>Дебаг меню:</b>\n\n"
            "Доступные функции отладки:\n"
            "• 🔍 Отладка username - просмотр username в базе данных\n"
            "• 📊 Отладка рефералов - детальная информация о рефералах\n"
            "• 👥 Отладка пользователей - информация о пользователях\n"
            "• 🔄 Обновить username - принудительное обновление\n"
            "• 🔧 Исправить рефералы - исправление реферальных связей\n\n"
            "Выберите действие:"
        )
        
        await callback.message.edit_text(debug_text, reply_markup=get_debug_menu_keyboard(), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "debug_usernames")
    async def debug_usernames_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Отладка username'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        debug_info = db.get_debug_usernames_info()
        
        if not debug_info:
            await callback.answer("❌ Ошибка при получении данных", show_alert=True)
            return
        
        debug_text = "🔍 <b>Отладка username в базе данных:</b>\n\n"
        
        debug_text += f"📋 <b>Таблица user_usernames ({len(debug_info['usernames'])} записей):</b>\n"
        for user_id, username in debug_info['usernames']:
            debug_text += f"ID: {user_id} → @{username}\n"
        
        debug_text += f"\n📋 <b>Таблица referrals ({len(debug_info['referrals'])} записей):</b>\n"
        for referrer_id, referred_id, referrer_username in debug_info['referrals']:
            debug_text += f"Реферер: {referrer_id} → @{referrer_username} | Реферал: {referred_id}\n"
        
        debug_text += f"\n📋 <b>Таблица user_roles ({len(debug_info['users'])} записей):</b>\n"
        for user_id, role in debug_info['users']:
            debug_text += f"ID: {user_id} → Роль: {role}\n"
        
        await callback.message.edit_text(debug_text, reply_markup=get_debug_function_keyboard(), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "debug_update_usernames")
    async def debug_update_usernames_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Обновить username'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await callback.answer("🔄 Обновление username...", show_alert=True)
        
        success = db.update_all_usernames_from_referrals()
        
        if success:
            db.add_bot_event("DEBUG_UPDATE_USERNAMES", f"Обновление username выполнено главным администратором {callback.from_user.username or callback.from_user.id}", 
                            callback.from_user.id, "info")
        else:
            db.add_bot_event("DEBUG_UPDATE_USERNAMES_FAILED", f"Ошибка обновления username главным администратором {callback.from_user.username or callback.from_user.id}", 
                            callback.from_user.id, "error")
        
        if success:
            await callback.message.edit_text(
                "✅ Username успешно обновлены в базе данных!\n\nНажмите '🔙 Назад к дебаг меню' для возврата.",
                reply_markup=get_debug_function_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                "❌ Ошибка при обновлении username.\n\nНажмите '🔙 Назад к дебаг меню' для возврата.",
                reply_markup=get_debug_function_keyboard(),
                parse_mode="HTML"
            )

    @dp.callback_query(F.data == "debug_fix_referrals")
    async def debug_fix_referrals_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Исправить рефералы'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await callback.answer("🔧 Исправление рефералов...", show_alert=True)
        
        fixed_count = db.fix_referral_usernames()
        
        db.add_bot_event("DEBUG_FIX_REFERRALS", f"Исправление рефералов выполнено главным администратором {callback.from_user.username or callback.from_user.id}. Исправлено: {fixed_count}", 
                        callback.from_user.id, "info")
        
        await callback.message.edit_text(
            f"✅ Исправлено {fixed_count} username в реферальной системе!\n\nНажмите '🔙 Назад к дебаг меню' для возврата.",
            reply_markup=get_debug_function_keyboard(),
            parse_mode="HTML"
        )

    @dp.callback_query(F.data == "debug_referrals")
    async def debug_referrals_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Отладка рефералов'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        debug_info = db.get_referrals_debug_info()
        
        if not debug_info:
            await callback.answer("❌ Ошибка при получении данных", show_alert=True)
            return
        
        debug_text = "📊 <b>Отладка рефералов:</b>\n\n"
        
        debug_text += f"📈 <b>Общая статистика:</b>\n"
        debug_text += f"Всего реферальных связей: {debug_info['total_referrals']}\n"
        debug_text += f"Уникальных рефереров: {debug_info['unique_referrers']}\n"
        debug_text += f"Уникальных рефералов: {debug_info['unique_referred']}\n\n"
        
        debug_text += f"📋 <b>Детальная информация ({len(debug_info['referrals'])} записей):</b>\n"
        for referrer_id, referred_id, referrer_username, joined_at in debug_info['referrals']:
            referrer_display = get_user_display_name_html(referrer_id)
            referred_display = get_user_display_name_html(referred_id)
            debug_text += f"• Реферер: {referrer_display} → Реферал: {referred_display} | {joined_at}\n"
        
        await callback.message.edit_text(debug_text, reply_markup=get_debug_function_keyboard(), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "debug_users")
    async def debug_users_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Отладка пользователей'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        debug_info = db.get_users_debug_info()
        
        if not debug_info:
            await callback.answer("❌ Ошибка при получении данных", show_alert=True)
            return
        
        debug_text = "👥 <b>Отладка пользователей:</b>\n\n"
        
        debug_text += f"📈 <b>Статистика пользователей:</b>\n"
        debug_text += f"Всего пользователей: {debug_info['total_users']}\n"
        debug_text += f"Админов: {debug_info['admin_users']}\n"
        debug_text += f"Boss: {debug_info['boss_users']}\n"
        debug_text += f"Обычных пользователей: {debug_info['regular_users']}\n\n"
        
        debug_text += f"🔍 <b>Все роли в системе:</b>\n"
        for role in debug_info['all_roles']:
            display_role = get_role_display_name(role)
            debug_text += f"• {display_role}\n"
        debug_text += "\n"
        
        debug_text += f"📋 <b>Детальная информация ({len(debug_info['users'])} записей):</b>\n"
        for user_id, role, granted_at, username, referrer_id, referrer_username, referred_id in debug_info['users']:
            display_name = get_user_display_name_html(user_id)
            
            referrer_info = ""
            if referrer_id:
                referrer_display = get_user_display_name_html(referrer_id)
                referrer_info = f" | Реферер: {referrer_display}"
            
            referral_info = ""
            if referred_id:
                referral_info = " | Есть рефералы"
            
            display_role = get_role_display_name(role)
            
            debug_text += f"• {display_name} → Роль: {display_role} | {granted_at}{referrer_info}{referral_info}\n"
        
        await callback.message.edit_text(debug_text, reply_markup=get_debug_users_keyboard(), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "debug_events")
    async def debug_events_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'События'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        stats = db.get_events_stats()
        recent_events = db.get_recent_events(10)
        
        debug_text = "📋 <b>События бота:</b>\n\n"
        
        debug_text += f"📊 <b>Статистика:</b>\n"
        debug_text += f"Всего событий: {stats.get('total_events', 0)}\n"
        debug_text += f"За 24 часа: {stats.get('events_24h', 0)}\n\n"
        
        if stats.get('events_by_type'):
            debug_text += f"📈 <b>События по типам:</b>\n"
            for event_type, count in stats['events_by_type']:
                debug_text += f"• {event_type}: {count}\n"
            debug_text += "\n"
        
        if stats.get('events_by_severity'):
            debug_text += f"⚠️ <b>События по важности:</b>\n"
            for severity, count in stats['events_by_severity']:
                severity_display = {
                    'info': 'ℹ️ Информация',
                    'warning': '⚠️ Предупреждение',
                    'error': '❌ Ошибка',
                    'critical': '🚨 Критично'
                }.get(severity, f"❓ {severity}")
                debug_text += f"• {severity_display}: {count}\n"
            debug_text += "\n"
        
        debug_text += f"🕒 <b>Последние события ({len(recent_events)}):</b>\n"
        for event_data in recent_events:
            event_type, event_description, user_id, severity, created_at, username = event_data
            
            display_username = "Система"
            if user_id:
                display_username = username or f"user{user_id}"
            
            severity_icon = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'critical': '🚨'
            }.get(severity, '❓')
            
            time_str = created_at.split(' ')[1][:5] if ' ' in created_at else created_at[:5]
            
            debug_text += f"{severity_icon} <b>{event_type}</b> | {display_username} | {time_str}\n"
            debug_text += f"   {event_description}\n\n"
        
        await callback.message.edit_text(debug_text, reply_markup=get_debug_events_keyboard(), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "debug_download_events")
    async def debug_download_events_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Скачать события'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await callback.answer("📥 Подготовка файла событий...", show_alert=True)
        
        try:
            import pandas as pd
            import io
            from datetime import datetime
            
            data = db.get_events_excel_data()
            
            if not data:
                await callback.answer("❌ Нет данных для экспорта", show_alert=True)
                return
            
            df = pd.DataFrame(data)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='События', index=False)
                
                worksheet = writer.sheets['События']
                
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            filename = f"bot_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            db.add_bot_event("DEBUG_DOWNLOAD_EVENTS", f"Экспорт событий выполнен главным администратором {callback.from_user.username or callback.from_user.id}. Экспортировано: {len(data)} событий", 
                            callback.from_user.id, "info")
            
            await callback.message.answer_document(
                types.BufferedInputFile(
                    output.getvalue(),
                    filename=filename
                ),
                caption=f"📋 <b>События бота</b>\n\n"
                       f"📅 Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                       f"📊 Всего событий: {len(data)}\n\n"
                       f"📋 <b>Содержит:</b>\n"
                       f"• Тип события\n"
                       f"• Описание\n"
                       f"• Пользователь\n"
                       f"• Важность\n"
                       f"• Дата\n\n"
                       f"📁 Формат: Excel (.xlsx)",
                parse_mode="HTML"
            )
            
            await callback.answer("✅ Файл событий успешно отправлен!", show_alert=True)
            
        except Exception as e:
            db.add_bot_event("DEBUG_DOWNLOAD_EVENTS_FAILED", f"Ошибка экспорта событий главным администратором {callback.from_user.username or callback.from_user.id}: {e}", 
                            callback.from_user.id, "error")
            await callback.answer(f"❌ Ошибка при создании файла: {e}", show_alert=True)
            await callback.message.edit_text(
                f"❌ Ошибка при создании файла: {e}\n\nНажмите '🔙 Назад к дебаг меню' для возврата.",
                reply_markup=get_debug_events_keyboard(),
                parse_mode="HTML"
            )

    @dp.callback_query(F.data == "debug_download_users")
    async def debug_download_users_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Скачать данные пользователей'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await callback.answer("📥 Подготовка файла пользователей...", show_alert=True)
        
        try:
            import pandas as pd
            import io
            from datetime import datetime
            
            data = db.get_users_excel_data()
            
            if not data:
                await callback.answer("❌ Нет данных для экспорта", show_alert=True)
                return
            
            df = pd.DataFrame(data)
            
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Пользователи', index=False)
                
                worksheet = writer.sheets['Пользователи']
                
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            filename = f"users_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            db.add_bot_event("DEBUG_DOWNLOAD_USERS", f"Экспорт данных пользователей выполнен главным администратором {callback.from_user.username or callback.from_user.id}. Экспортировано: {len(data)} пользователей", 
                            callback.from_user.id, "info")
            
            await callback.message.answer_document(
                types.BufferedInputFile(
                    output.getvalue(),
                    filename=filename
                ),
                caption=f"📊 <b>Данные пользователей</b>\n\n"
                       f"📅 Дата экспорта: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n"
                       f"👥 Всего пользователей: {len(data)}\n\n"
                       f"📋 <b>Содержит:</b>\n"
                       f"• ID пользователя\n"
                       f"• Username\n"
                       f"• Роль\n"
                       f"• Реферер ID\n"
                       f"• Реферер Username\n"
                       f"• Наличие рефералов\n"
                       f"• Дата регистрации\n"
                       f"• Дата последнего обновления\n\n"
                       f"📁 Формат: Excel (.xlsx)",
                parse_mode="HTML"
            )
            
            await callback.answer("✅ Файл пользователей успешно отправлен!", show_alert=True)
            
        except Exception as e:
            db.add_bot_event("DEBUG_DOWNLOAD_USERS_FAILED", f"Ошибка экспорта данных пользователей главным администратором {callback.from_user.username or callback.from_user.id}: {e}", 
                            callback.from_user.id, "error")
            await callback.answer(f"❌ Ошибка при создании файла: {e}", show_alert=True)
            await callback.message.edit_text(
                f"❌ Ошибка при создании файла: {e}\n\nНажмите '🔙 Назад к дебаг меню' для возврата.",
                reply_markup=get_debug_users_keyboard(),
                parse_mode="HTML"
            )

    @dp.callback_query(F.data == "admin_grant_role")
    async def admin_grant_role_callback(callback: types.CallbackQuery, state: FSMContext):
        """Обработка инлайн-кнопки 'Выдать роль админа'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await state.set_state(AdminPanelStates.waiting_for_grant_user_id)
        await callback.message.edit_text(
            "➕ <b>Выдача роли администратора:</b>\n\n"
            "Введите ID пользователя, которому хотите выдать роль администратора:",
            parse_mode="HTML"
        )
        await callback.answer()

    @dp.callback_query(F.data == "admin_revoke_role")
    async def admin_revoke_role_callback(callback: types.CallbackQuery, state: FSMContext):
        """Обработка инлайн-кнопки 'Снять роль админа'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_main_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await state.set_state(AdminPanelStates.waiting_for_revoke_user_id)
        await callback.message.edit_text(
            "➖ <b>Снятие роли администратора:</b>\n\n"
            "Введите ID пользователя, с которого хотите снять роль администратора:",
            parse_mode="HTML"
        )
        await callback.answer()

    @dp.callback_query(F.data == "admin_panel_back")
    async def admin_panel_back_callback(callback: types.CallbackQuery, state: FSMContext):
        """Обработка инлайн-кнопки 'Назад к админ-панели'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        if not admin_panel.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return
        
        await state.clear()
        
        admin_help = get_admin_panel_text(callback.from_user.id)
        is_main_admin = admin_panel.is_main_admin(callback.from_user.id)
        inline_keyboard = get_admin_panel_inline_keyboard(is_main_admin)
        
        await callback.message.edit_text(admin_help, reply_markup=inline_keyboard, parse_mode="HTML")
        await callback.answer()

    # Обработчики ввода ID пользователей
    @dp.message(AdminPanelStates.waiting_for_grant_user_id)
    async def process_grant_user_id(message: types.Message, state: FSMContext):
        """Обработка ввода ID пользователя для выдачи роли"""
        update_user_username(message.from_user.id, message.from_user.username)
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
            db.add_bot_event("ROLE_GRANTED", f"Роль админа выдана пользователю {target_user_id}", 
                            message.from_user.id, "info")
        else:
            db.add_bot_event("ROLE_GRANT_FAILED", f"Ошибка выдачи роли: {result}", 
                            message.from_user.id, "error")
        
        if success:
            await message.answer(f"✅ {result}", reply_markup=get_user_keyboard(message.from_user.id))
        else:
            await message.answer(f"❌ {result}", reply_markup=get_user_keyboard(message.from_user.id))
        
        await state.clear()

    @dp.message(AdminPanelStates.waiting_for_revoke_user_id)
    async def process_revoke_user_id(message: types.Message, state: FSMContext):
        """Обработка ввода ID пользователя для снятия роли"""
        update_user_username(message.from_user.id, message.from_user.username)
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
            db.add_bot_event("ROLE_REVOKED", f"Роль админа снята с пользователя {target_user_id}", 
                            message.from_user.id, "warning")
        else:
            db.add_bot_event("ROLE_REVOKE_FAILED", f"Ошибка снятия роли: {result}", 
                            message.from_user.id, "error")
        
        if success:
            await message.answer(f"✅ {result}", reply_markup=get_user_keyboard(message.from_user.id))
        else:
            await message.answer(f"❌ {result}", reply_markup=get_user_keyboard(message.from_user.id))
        
        await state.clear()

    # Реферальная система - инлайн-кнопки
    @dp.callback_query(F.data == "referral_top")
    async def referral_top_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Топ рефереров'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        top_referrers = db.get_top_referrers(10)
        
        if not top_referrers:
            top_text = "🏆 <b>Топ рефереров:</b>\n\nПока нет данных о реферерах."
        else:
            top_text = "🏆 <b>Топ рефереров:</b>\n\n"
            for i, (user_id, total, active) in enumerate(top_referrers, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                display_name = get_user_display_name_html(user_id)
                
                top_text += f"{medal} {display_name} | {total} рефералов ({active} активных)\n"
        
        await callback.message.edit_text(top_text, reply_markup=get_referral_back_keyboard(), parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "referral_share")
    async def referral_share_callback(callback: types.CallbackQuery):
        """Обработка кнопки 'Поделиться'"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        bot_username = (await bot.get_me()).username
        referral_link = f"https://t.me/{bot_username}?start=ref{callback.from_user.id}"
        
        share_text = (
            "📤 <b>Ваша реферальная ссылка:</b>\n\n"
            f"{referral_link}\n\n"
            "📋 <b>Как поделиться:</b>\n"
            "1. Ссылка уже скопирована в буфер обмена! 📋\n"
            "2. Отправьте другу в любой мессенджер\n"
            "3. Когда друг перейдет по ссылке и активирует бота, вы получите реферала!\n\n"
            "🎉 <b>Приглашайте друзей и получайте бонусы!</b>"
        )
        
        await callback.message.edit_text(share_text, reply_markup=get_referral_back_keyboard(), parse_mode="HTML")
        await callback.answer(f"Ссылка скопирована: {referral_link}", show_alert=True)

    @dp.callback_query(F.data == "referral_back")
    async def referral_back_callback(callback: types.CallbackQuery, state: FSMContext):
        """Обработка кнопки 'Назад' в реферальной системе"""
        update_user_username(callback.from_user.id, callback.from_user.username)
        total_referrals, active_referrals = db.get_referral_stats(callback.from_user.id)
        referrer_info = db.get_referrer_info(callback.from_user.id)
        
        referral_text = (
            "👥 <b>Реферальная система:</b>\n\n"
            f"Вы пригласили: <b>{total_referrals}</b> пользователей\n"
            f"Активных рефералов: <b>{active_referrals}</b>\n"
            f"Конверсия: <b>{round(active_referrals/total_referrals*100, 1) if total_referrals > 0 else 0}%</b>\n"
        )
        
        if referrer_info:
            referrer_id, referrer_username = referrer_info
            referral_text += f"\n🎉 Вас пригласил: <b>@{referrer_username}</b>\n"
        
        referral_text += (
            "\nПриглашайте друзей и получайте бонусы!\n\n"
            "Выберите действие:"
        )
        
        await callback.message.edit_text(referral_text, reply_markup=get_referral_keyboard(), parse_mode="HTML")
        await callback.answer()

async def main():
    """Главная функция запуска бота"""
    global bot_running, stop_event
    print("🚀 Запуск бота для заметок...")
    print(f"🔧 Главный админ ID: {admin_panel.get_admin_id()}")
    
    stop_event = asyncio.Event()
    
    bot_running = True
    
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    register_handlers(dp)
    
    try:
        polling_task = asyncio.create_task(dp.start_polling(bot, skip_updates=True))
        
        stop_task = asyncio.create_task(stop_event.wait())
        
        done, pending = await asyncio.wait([polling_task, stop_task], return_when=asyncio.FIRST_COMPLETED)
        
        for task in pending:
            task.cancel()
        
        if stop_event.is_set():
            print("Получен сигнал остановки бота...")
            try:
                await polling_task
            except asyncio.CancelledError:
                pass
            
    except Exception as e:
        print(f"Ошибка в main(): {e}")
    finally:
        print("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())