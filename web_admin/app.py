"""
Веб-админ панель для Telegram бота
Copyright (c) 2025 HeelBoy666
Licensed under MIT License (see LICENSE file)

Flask приложение для управления ботом через веб-интерфейс.
"""

import os
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import sqlite3
import hashlib
import secrets

# Добавляем родительскую папку в путь для импорта модулей бота
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from config import ADMIN_ID
from bot_connector import bot_connector
from notification_system import notification_system

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Инициализация Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Инициализация базы данных
db = Database()

class AdminUser(UserMixin):
    """Класс для представления администратора"""
    def __init__(self, user_id, username, role):
        self.id = user_id
        self.username = username
        self.role = role

@login_manager.user_loader
def load_user(user_id):
    """Загрузка пользователя для Flask-Login"""
    try:
        user_id = int(user_id)
        role = db.get_user_role(user_id)
        if role in ['admin', 'main_admin']:
            username = db.get_username_by_id(user_id) or f"user{user_id}"
            return AdminUser(user_id, username, role)
    except:
        pass
    return None

def is_main_admin():
    """Проверка является ли текущий пользователь главным админом"""
    return current_user.is_authenticated and current_user.role == 'main_admin'

def is_admin():
    """Проверка является ли текущий пользователь админом"""
    return current_user.is_authenticated and current_user.role in ['admin', 'main_admin']

@app.route('/')
def index():
    """Главная страница - редирект на dashboard"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Страница входа"""
    if request.method == 'POST':
        user_id = request.form.get('user_id')
        password = request.form.get('password')
        
        try:
            user_id = int(user_id)
            role = db.get_user_role(user_id)
            
            if role in ['admin', 'main_admin']:
                if user_id == ADMIN_ID or role == 'admin':
                    username = db.get_username_by_id(user_id) or f"user{user_id}"
                    user = AdminUser(user_id, username, role)
                    login_user(user)
                    return redirect(url_for('dashboard'))
            
            flash('Неверные данные для входа', 'error')
        except ValueError:
            flash('Неверный формат ID пользователя', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """Выход из системы"""
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Главная страница админ-панели"""
    stats = get_dashboard_stats()
    
    recent_events = db.get_recent_events(5)
    
    bot_info = bot_connector.get_bot_info()
    bot_status = bot_info.get('status', 'unknown')
    
    return render_template('dashboard.html', 
                         stats=stats, 
                         recent_events=recent_events,
                         bot_status=bot_status)

@app.route('/users')
@login_required
def users():
    """Страница управления пользователями"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    selected_role = request.args.get('role', '')
    
    users_data = get_users_paginated(page, search, selected_role)
    
    users_stats = get_users_stats()
    
    return render_template('users.html', 
                         users=users_data['users'],
                         pagination=users_data['pagination'],
                         search=search,
                         selected_role=selected_role,
                         stats=users_stats)

@app.route('/events')
@login_required
def events():
    """Страница событий"""
    page = request.args.get('page', 1, type=int)
    event_type = request.args.get('type', '')
    severity = request.args.get('severity', '')
    
    events_data = get_events_paginated(page, event_type, severity)
    
    return render_template('events.html',
                         events=events_data['events'],
                         pagination=events_data['pagination'],
                         filters={'type': event_type, 'severity': severity})

@app.route('/settings')
@login_required
def settings():
    """Страница настроек"""
    if not is_main_admin():
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('settings.html')

@app.route('/notifications')
@login_required
def notifications():
    """Страница настроек уведомлений"""
    if not is_main_admin():
        flash('Доступ запрещен', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('notifications.html')

@app.route('/api/notifications/config')
@login_required
def api_notifications_config():
    """API для получения конфигурации уведомлений"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        return jsonify({'success': True, 'config': notification_system.config})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/config/email', methods=['POST'])
@login_required
def api_notifications_email_config():
    """API для сохранения email конфигурации"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        notification_system.config['email'] = data
        notification_system.save_config()
        return jsonify({'success': True, 'message': 'Email конфигурация сохранена'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/config/telegram', methods=['POST'])
@login_required
def api_notifications_telegram_config():
    """API для сохранения Telegram конфигурации"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        notification_system.config['telegram'] = data
        notification_system.save_config()
        return jsonify({'success': True, 'message': 'Telegram конфигурация сохранена'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/config/webhook', methods=['POST'])
@login_required
def api_notifications_webhook_config():
    """API для сохранения webhook конфигурации"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        notification_system.config['webhook'] = data
        notification_system.save_config()
        return jsonify({'success': True, 'message': 'Webhook конфигурация сохранена'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/config/settings', methods=['POST'])
@login_required
def api_notifications_settings_config():
    """API для сохранения настроек уведомлений"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        notification_system.config['notifications'] = data
        notification_system.save_config()
        return jsonify({'success': True, 'message': 'Настройки уведомлений сохранены'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/test/email', methods=['POST'])
@login_required
def api_test_email():
    """API для тестирования email уведомлений"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        success = notification_system.test_notification('email')
        return jsonify({'success': success, 'message': 'Тестовое email уведомление отправлено' if success else 'Ошибка отправки'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/test/telegram', methods=['POST'])
@login_required
def api_test_telegram():
    """API для тестирования Telegram уведомлений"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        success = notification_system.test_notification('telegram')
        return jsonify({'success': success, 'message': 'Тестовое Telegram уведомление отправлено' if success else 'Ошибка отправки'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/test/webhook', methods=['POST'])
@login_required
def api_test_webhook():
    """API для тестирования webhook уведомлений"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        success = notification_system.test_notification('webhook')
        return jsonify({'success': success, 'message': 'Тестовое webhook уведомление отправлено' if success else 'Ошибка отправки'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notifications/history')
@login_required
def api_notifications_history():
    """API для получения истории уведомлений"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        history = notification_system.get_notifications_history(50)
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/notes')
@login_required
def notes():
    """Страница управления заметками"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    selected_user = request.args.get('user_id', '')
    
    notes_data = get_notes_paginated(page, search, selected_user)
    
    users_info = db.get_users_debug_info()
    users = users_info.get('users', [])
    
    notes_stats = get_notes_stats()
    
    return render_template('notes.html', 
                         notes=notes_data['notes'],
                         pagination=notes_data['pagination'],
                         search=search,
                         selected_user=selected_user,
                         users=users,
                         stats=notes_stats)

@app.route('/api/notes')
@login_required
def api_notes():
    """API для получения заметок"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    user_id = request.args.get('user_id', '')
    notes_data = get_notes_paginated(page, search, user_id)
    return jsonify(notes_data)

@app.route('/api/notes/update', methods=['POST'])
@login_required
def api_update_note():
    """API для обновления заметки"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        note_id = data.get('note_id')
        note_text = data.get('note_text')
        
        if not note_id or not note_text:
            return jsonify({'success': False, 'message': 'Не указаны note_id или note_text'})
        
        success, message = db.update_note_admin(note_id, note_text, current_user.id)
        
        if success:
            db.add_bot_event("WEB_UPDATE_NOTE", f"Заметка {note_id} обновлена через веб-панель", 
                            current_user.id, "info")
            return jsonify({'success': True, 'message': 'Заметка обновлена'})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notes/delete', methods=['POST'])
@login_required
def api_delete_note():
    """API для удаления заметки"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        note_id = data.get('note_id')
        
        if not note_id:
            return jsonify({'success': False, 'message': 'Не указан note_id'})
        
        success, message = db.delete_note_admin(note_id, current_user.id)
        
        if success:
            db.add_bot_event("WEB_DELETE_NOTE", f"Заметка {note_id} удалена через веб-панель", 
                            current_user.id, "warning")
            return jsonify({'success': True, 'message': 'Заметка удалена'})
        else:
            return jsonify({'success': False, 'message': message})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notes/bulk-delete', methods=['POST'])
@login_required
def api_bulk_delete_notes():
    """API для массового удаления заметок"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        note_ids = data.get('note_ids', [])
        
        if not note_ids:
            return jsonify({'success': False, 'message': 'Не указаны заметки для удаления'})
        
        deleted_count = 0
        for note_id in note_ids:
            success, _ = db.delete_note_admin(note_id, current_user.id)
            if success:
                deleted_count += 1
        
        if deleted_count > 0:
            db.add_bot_event("WEB_BULK_DELETE_NOTES", f"Удалено {deleted_count} заметок через веб-панель", 
                            current_user.id, "warning")
            return jsonify({'success': True, 'deleted_count': deleted_count, 'message': f'Удалено {deleted_count} заметок'})
        else:
            return jsonify({'success': False, 'message': 'Не удалось удалить заметки'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/notes/export')
@login_required
def api_export_notes():
    """API для экспорта заметок"""
    try:
        import pandas as pd
        from io import BytesIO
        
        # Получаем все заметки
        notes_data = get_notes_export_data()
        
        # Создаем DataFrame
        df = pd.DataFrame(notes_data)
        
        # Создаем Excel файл в памяти
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Заметки', index=False)
        
        output.seek(0)
        
        # Логируем событие
        db.add_bot_event("WEB_EXPORT_NOTES", "Экспорт заметок через веб-панель", 
                        current_user.id, "info")
        
        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'notes_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка экспорта: {e}'})

@app.route('/api/users/<int:user_id>')
@login_required
def api_user_details(user_id):
    """API для получения деталей пользователя"""
    try:
        print(f"Запрос информации о пользователе {user_id}")
        
        # Получаем всю информацию одним запросом
        user_data = db.get_user_comprehensive_info(user_id)
        
        if user_data:
            print(f"Успешно получены данные для пользователя {user_id}: {user_data}")
            return jsonify({'success': True, 'user': user_data})
        else:
            print(f"Пользователь {user_id} не найден в базе данных")
            return jsonify({'success': False, 'message': 'Пользователь не найден'})
        
    except Exception as e:
        print(f"Ошибка при получении информации о пользователе {user_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'message': f'Ошибка: {str(e)}'})

@app.route('/api/users/bulk-action', methods=['POST'])
@login_required
def api_users_bulk_action():
    """API для массовых операций с пользователями"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        action = data.get('action')
        user_ids = data.get('user_ids', [])
        
        if not user_ids:
            return jsonify({'success': False, 'message': 'Не выбраны пользователи'})
        
        success_count = 0
        for user_id in user_ids:
            try:
                user_id = int(user_id)
                if action == 'grant_admin':
                    if db.grant_admin_role(user_id):
                        success_count += 1
                elif action == 'revoke_admin':
                    if db.revoke_admin_role(user_id):
                        success_count += 1
                elif action == 'block':
                    if db.block_user(user_id):
                        success_count += 1
                elif action == 'unblock':
                    if db.unblock_user(user_id):
                        success_count += 1
            except:
                continue
        
        # Логируем событие
        action_names = {
            'grant_admin': 'назначение администраторами',
            'revoke_admin': 'снятие прав администратора',
            'block': 'блокировка',
            'unblock': 'разблокировка'
        }
        
        db.add_bot_event("WEB_BULK_USER_ACTION", 
                        f"Массовое действие: {action_names.get(action, action)} для {success_count} пользователей", 
                        current_user.id, "info")
        
        return jsonify({
            'success': True, 
            'success_count': success_count,
            'message': f'Операция выполнена для {success_count} пользователей'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/users/export')
@login_required
def api_users_export():
    """API для экспорта пользователей"""
    try:
        import pandas as pd
        from io import BytesIO
        
        # Получаем данные пользователей
        users_data = get_users_export_data()
        
        # Создаем DataFrame
        df = pd.DataFrame(users_data)
        
        # Создаем Excel файл в памяти
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Пользователи', index=False)
        
        output.seek(0)
        
        # Логируем событие
        db.add_bot_event("WEB_EXPORT_USERS", "Экспорт пользователей через веб-панель", 
                        current_user.id, "info")
        
        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'users_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка экспорта: {e}'})

@app.route('/api/users/import', methods=['POST'])
@login_required
def api_users_import():
    """API для импорта пользователей"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'Файл не загружен'})
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'Файл не выбран'})
        
        if not file.filename.endswith('.csv'):
            return jsonify({'success': False, 'message': 'Поддерживаются только CSV файлы'})
        
        skip_existing = request.form.get('skip_existing', 'false').lower() == 'true'
        update_existing = request.form.get('update_existing', 'false').lower() == 'true'
        
        # Читаем CSV файл
        import csv
        from io import StringIO
        
        content = file.read().decode('utf-8')
        csv_reader = csv.DictReader(StringIO(content))
        
        imported_count = 0
        for row in csv_reader:
            try:
                user_id = int(row.get('ID', 0))
                username = row.get('Username', '')
                role = row.get('Role', 'user')
                status = row.get('Status', '1') == '1'
                
                if user_id > 0:
                    # Проверяем существование пользователя
                    existing_role = db.get_user_role(user_id)
                    
                    if existing_role and skip_existing:
                        continue
                    
                    if existing_role and update_existing:
                        # Обновляем существующего пользователя
                        db.update_user_admin(user_id, username, role, status)
                    elif not existing_role:
                        # Создаем нового пользователя
                        db.create_user_admin(user_id, username, role, status)
                    
                    imported_count += 1
                    
            except Exception as e:
                print(f"Ошибка импорта пользователя {row}: {e}")
                continue
        
        # Логируем событие
        db.add_bot_event("WEB_IMPORT_USERS", f"Импортировано {imported_count} пользователей", 
                        current_user.id, "info")
        
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'message': f'Импортировано {imported_count} пользователей'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка импорта: {e}'})

@app.route('/api/users/groups/create', methods=['POST'])
@login_required
def api_users_groups_create():
    """API для создания группы пользователей"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        name = data.get('name')
        description = data.get('description', '')
        users = data.get('users', [])
        
        if not name:
            return jsonify({'success': False, 'message': 'Не указано название группы'})
        
        # Создаем группу в базе данных
        success = db.create_user_group(name, description, users)
        
        if success:
            db.add_bot_event("WEB_CREATE_USER_GROUP", f"Создана группа пользователей: {name}", 
                            current_user.id, "info")
            return jsonify({'success': True, 'message': 'Группа создана'})
        else:
            return jsonify({'success': False, 'message': 'Ошибка создания группы'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/users/<int:user_id>/details')
@login_required
def api_user_details_extended(user_id):
    """API для получения детальной информации о пользователе"""
    try:
        # Получаем базовую информацию
        role = db.get_user_role(user_id)
        username = db.get_username_by_id(user_id)
        
        # Получаем заметки пользователя
        notes = db.get_user_notes(user_id)
        notes_count = len(notes)
        recent_notes = [note[1][:50] + '...' if len(note[1]) > 50 else note[1] for note in notes[:3]]
        
        # Получаем информацию о реферере
        referrer_info = db.get_referrer_info(user_id)
        referrer = None
        if referrer_info:
            referrer_username = db.get_username_by_id(referrer_info[0]) or f"user{referrer_info[0]}"
            referrer = f"{referrer_username} (ID: {referrer_info[0]})"
        
        # Получаем статистику рефералов
        referrals_count = 0
        if role in ['admin', 'main_admin']:
            referrals_count = len(db.get_referrals(user_id))
        
        # Получаем дату регистрации и последнюю активность
        created_at = db.get_user_created_at(user_id)
        last_activity = db.get_user_last_activity(user_id)
        
        # Получаем статус пользователя
        status = db.get_user_status(user_id)
        
        user_data = {
            'id': user_id,
            'username': username or f"user{user_id}",
            'role': role,
            'status': status,
            'notes_count': notes_count,
            'notes': recent_notes,
            'referrals_count': referrals_count,
            'referrer': referrer,
            'created_at': created_at or 'Неизвестно',
            'last_activity': last_activity or 'Неизвестно'
        }
        
        return jsonify({'success': True, 'user': user_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/users/<int:user_id>', methods=['GET'])
@login_required
def api_get_user(user_id):
    """API для получения информации о пользователе"""
    try:
        role = db.get_user_role(user_id)
        username = db.get_username_by_id(user_id)
        status = db.get_user_status(user_id)
        
        user_data = {
            'id': user_id,
            'username': username or f"user{user_id}",
            'role': role,
            'status': status
        }
        
        return jsonify({'success': True, 'user': user_data})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/users/update', methods=['POST'])
@login_required
def api_update_user():
    """API для обновления пользователя"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        user_id = data.get('user_id')
        username = data.get('username')
        role = data.get('role')
        status = data.get('status')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Не указан user_id'})
        
        success = db.update_user_admin(user_id, username, role, status)
        
        if success:
            db.add_bot_event("WEB_UPDATE_USER", f"Обновлен пользователь {user_id}", 
                            current_user.id, "info")
            return jsonify({'success': True, 'message': 'Пользователь обновлен'})
        else:
            return jsonify({'success': False, 'message': 'Ошибка обновления'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/users/role', methods=['POST'])
@login_required
def api_change_user_role():
    """API для изменения роли пользователя"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        user_id = data.get('user_id')
        role = data.get('role')
        
        if not user_id or not role:
            return jsonify({'success': False, 'message': 'Не указаны user_id или role'})
        
        if role == 'admin':
            success = db.grant_admin_role(user_id)
        else:
            success = db.revoke_admin_role(user_id)
        
        if success:
            action = 'назначен администратором' if role == 'admin' else 'сняты права администратора'
            db.add_bot_event("WEB_CHANGE_USER_ROLE", f"Пользователь {user_id} {action}", 
                            current_user.id, "info")
            return jsonify({'success': True, 'message': 'Роль изменена'})
        else:
            return jsonify({'success': False, 'message': 'Ошибка изменения роли'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/users/status', methods=['POST'])
@login_required
def api_change_user_status():
    """API для изменения статуса пользователя"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        user_id = data.get('user_id')
        status = data.get('status')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Не указан user_id'})
        
        if status:
            success = db.unblock_user(user_id)
            action = 'разблокирован'
        else:
            success = db.block_user(user_id)
            action = 'заблокирован'
        
        if success:
            db.add_bot_event("WEB_CHANGE_USER_STATUS", f"Пользователь {user_id} {action}", 
                            current_user.id, "warning")
            return jsonify({'success': True, 'message': f'Пользователь {action}'})
        else:
            return jsonify({'success': False, 'message': 'Ошибка изменения статуса'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

# API endpoints
@app.route('/api/stats')
@login_required
def api_stats():
    """API для получения статистики"""
    return jsonify(get_dashboard_stats())

@app.route('/api/users')
@login_required
def api_users():
    """API для получения пользователей"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    users_data = get_users_paginated(page, search)
    return jsonify(users_data)

@app.route('/api/events')
@login_required
def api_events():
    """API для получения событий"""
    page = request.args.get('page', 1, type=int)
    event_type = request.args.get('type', '')
    severity = request.args.get('severity', '')
    events_data = get_events_paginated(page, event_type, severity)
    return jsonify(events_data)

@app.route('/api/bot/status', methods=['GET', 'POST'])
@login_required
def api_bot_status():
    """API для управления статусом бота"""
    if request.method == 'POST':
        action = request.json.get('action')
        if action == 'start':
            result = bot_connector.start_bot()
            return jsonify(result)
        elif action == 'stop':
            result = bot_connector.stop_bot()
            return jsonify(result)
        else:
            return jsonify({'success': False, 'message': 'Неизвестное действие'})
    
    # GET запрос - получение статуса
    bot_info = bot_connector.get_bot_info()
    return jsonify(bot_info)

@app.route('/api/bot/info')
@login_required
def api_bot_info():
    """API для получения информации о боте"""
    bot_info = bot_connector.get_bot_info()
    return jsonify(bot_info)

@app.route('/api/bot/send-message', methods=['POST'])
@login_required
def api_send_message():
    """API для отправки сообщения пользователю"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    
    if not user_id or not message:
        return jsonify({'success': False, 'message': 'Не указаны user_id или message'})
    
    result = bot_connector.send_message_to_user(user_id, message)
    return jsonify(result)

@app.route('/api/bot/send-message-all', methods=['POST'])
@login_required
def api_send_message_all():
    """API для отправки сообщения всем пользователям"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    data = request.json
    message = data.get('message')
    
    if not message:
        return jsonify({'success': False, 'message': 'Не указано сообщение'})
    
    result = bot_connector.send_message_to_all_users(message)
    return jsonify(result)

@app.route('/api/user/current')
@login_required
def api_current_user():
    """API для получения информации о текущем пользователе"""
    return jsonify({
        'success': True,
        'user_id': current_user.id,
        'username': current_user.username,
        'role': current_user.role
    })

@app.route('/api/realtime/stats')
@login_required
def api_realtime_stats():
    """API для получения статистики в реальном времени"""
    stats = bot_connector.get_real_time_stats()
    return jsonify(stats)

# Системные API endpoints
@app.route('/api/system/info')
@login_required
def api_system_info():
    """API для получения информации о системе"""
    try:
        import os
        import psutil
        
        # Размер базы данных
        db_path = os.path.join(os.path.dirname(__file__), '..', 'notes.db')
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0
        db_size_mb = round(db_size / (1024 * 1024), 2)
        
        # Информация о системе
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Информация о боте
        bot_info = bot_connector.get_bot_info()
        
        return jsonify({
            'db_size': f"{db_size_mb} MB",
            'uptime': bot_info.get('uptime', 'Неизвестно'),
            'last_activity': bot_info.get('last_activity'),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            },
            'bot': bot_info
        })
    except Exception as e:
        return jsonify({
            'error': str(e),
            'db_size': 'Ошибка',
            'uptime': 'Ошибка',
            'last_activity': None
        })

@app.route('/api/system/test-connection')
@login_required
def api_test_connection():
    """API для тестирования подключения к базе данных"""
    try:
        db.get_users_debug_info()
        return jsonify({'success': True, 'message': 'Подключение успешно'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка подключения: {e}'})

@app.route('/api/system/update-usernames', methods=['POST'])
@login_required
def api_update_usernames():
    """API для обновления username"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        success = db.update_all_usernames_from_referrals()
        return jsonify({'success': success, 'message': 'Username обновлены' if success else 'Ошибка обновления'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/system/fix-referrals', methods=['POST'])
@login_required
def api_fix_referrals():
    """API для исправления рефералов"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        fixed_count = db.fix_referral_usernames()
        return jsonify({'success': True, 'fixed_count': fixed_count, 'message': f'Исправлено {fixed_count} рефералов'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/system/create-usernames', methods=['POST'])
@login_required
def api_create_usernames():
    """API для создания username для всех пользователей"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        success = db.create_usernames_for_all_users()
        return jsonify({'success': success, 'message': 'Username созданы' if success else 'Ошибка создания'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/system/init-boss', methods=['POST'])
@login_required
def api_init_boss():
    """API для инициализации главного админа"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        db.init_main_admin()
        return jsonify({'success': True, 'message': 'Главный админ инициализирован'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/system/backup', methods=['POST'])
@login_required
def api_backup():
    """API для создания резервной копии"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        import shutil
        from datetime import datetime
        
        # Путь к базе данных
        db_path = os.path.join(os.path.dirname(__file__), '..', 'notes.db')
        backup_path = os.path.join(os.path.dirname(__file__), '..', f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        
        # Копируем файл
        shutil.copy2(db_path, backup_path)
        
        return jsonify({'success': True, 'message': 'Резервная копия создана'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/system/clear-database', methods=['POST'])
@login_required
def api_clear_database():
    """API для очистки базы данных"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        # Очищаем все таблицы
        db.clear_all_tables()
        return jsonify({'success': True, 'message': 'База данных очищена'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

# Административные API endpoints
@app.route('/api/admins/list')
@login_required
def api_admins_list():
    """API для получения списка администраторов"""
    try:
        users_info = db.get_users_debug_info()
        admins = []
        
        for user in users_info.get('users', []):
            if user[2] in ['admin', 'main_admin']:
                admins.append({
                    'id': user[0],
                    'username': user[3] or f"user{user[0]}",
                    'role': user[2]
                })
        
        return jsonify({'success': True, 'admins': admins})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/admins/add', methods=['POST'])
@login_required
def api_add_admin():
    """API для добавления администратора"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Не указан user_id'})
        
        # Добавляем пользователя как админа
        success = db.grant_admin_role(user_id)
        
        if success:
            db.add_bot_event("WEB_ADD_ADMIN", f"Добавлен администратор {user_id}", 
                            current_user.id, "info")
            return jsonify({'success': True, 'message': 'Администратор добавлен'})
        else:
            return jsonify({'success': False, 'message': 'Ошибка добавления администратора'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/admins/remove', methods=['POST'])
@login_required
def api_remove_admin():
    """API для удаления администратора"""
    if not is_main_admin():
        return jsonify({'success': False, 'message': 'Доступ запрещен'})
    
    try:
        data = request.json
        user_id = data.get('user_id')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'Не указан user_id'})
        
        # Удаляем права администратора
        success = db.revoke_admin_role(user_id)
        
        if success:
            db.add_bot_event("WEB_REMOVE_ADMIN", f"Удален администратор {user_id}", 
                            current_user.id, "warning")
            return jsonify({'success': True, 'message': 'Администратор удален'})
        else:
            return jsonify({'success': False, 'message': 'Ошибка удаления администратора'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

def get_dashboard_stats():
    """Получение статистики для dashboard"""
    try:
        # Получаем статистику пользователей
        users_info = db.get_users_debug_info()
        
        # Получаем статистику событий
        events_stats = db.get_events_stats()
        
        # Получаем статистику рефералов
        referrals_stats = db.get_referrals_debug_info()
        
        return {
            'total_users': users_info.get('total_users', 0),
            'admin_users': users_info.get('admin_users', 0),
            'boss_users': users_info.get('boss_users', 0),
            'regular_users': users_info.get('regular_users', 0),
            'total_events': events_stats.get('total_events', 0),
            'events_24h': events_stats.get('events_24h', 0),
            'total_referrals': referrals_stats.get('total_referrals', 0),
            'unique_referrers': referrals_stats.get('unique_referrers', 0)
        }
    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
        return {}

def get_users_paginated(page, search='', selected_role=''):
    """Получение пользователей с пагинацией"""
    try:
        # Получаем всех пользователей с расширенной информацией
        users_info = db.get_users_extended_info()
        users = users_info.get('users', [])
        
        # Фильтрация по поиску
        if search:
            filtered_users = []
            for user in users:
                if (search.lower() in str(user[0]).lower() or 
                    search.lower() in (user[3] or '').lower()):
                    filtered_users.append(user)
            users = filtered_users
        
        # Фильтрация по роли
        if selected_role:
            filtered_users = []
            for user in users:
                if user[2] == selected_role:
                    filtered_users.append(user)
            users = filtered_users
        
        # Пагинация
        per_page = 20
        total = len(users)
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'users': users[start:end],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")
        return {'users': [], 'pagination': {'page': 1, 'per_page': 20, 'total': 0, 'pages': 0}}

def get_users_stats():
    """Получение статистики пользователей"""
    try:
        users_info = db.get_users_extended_info()
        users = users_info.get('users', [])
        
        # Общее количество пользователей
        total_users = len(users)
        
        # Активные сегодня (пользователи с заметками за сегодня)
        today = datetime.now().strftime('%Y-%m-%d')
        active_today = len([user for user in users if user[6] and user[6].startswith(today)])
        
        # Новые за неделю
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        new_week = len([user for user in users if user[5] and user[5] >= week_ago])
        
        # Пользователи с рефералами
        with_referrals = len([user for user in users if user[4] and user[4] > 0])
        
        return {
            'total_users': total_users,
            'active_today': active_today,
            'new_week': new_week,
            'with_referrals': with_referrals
        }
    except Exception as e:
        print(f"Ошибка при получении статистики пользователей: {e}")
        return {
            'total_users': 0,
            'active_today': 0,
            'new_week': 0,
            'with_referrals': 0
        }

def get_events_paginated(page, event_type='', severity=''):
    """Получение событий с пагинацией"""
    try:
        events = db.get_recent_events(100)  # Получаем больше событий для фильтрации
        
        # Фильтрация
        if event_type:
            events = [e for e in events if e[0] == event_type]
        if severity:
            events = [e for e in events if e[3] == severity]
        
        # Пагинация
        per_page = 20
        total = len(events)
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'events': events[start:end],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    except Exception as e:
        print(f"Ошибка при получении событий: {e}")
        return {'events': [], 'pagination': {'page': 1, 'per_page': 20, 'total': 0, 'pages': 0}}

def get_notes_paginated(page, search='', user_id=''):
    """Получение заметок с пагинацией"""
    try:
        # Получаем все заметки для админа
        all_notes = db.get_all_notes_for_admin()
        
        # Фильтрация по поиску
        if search:
            filtered_notes = []
            for note in all_notes:
                if search.lower() in note[2].lower():
                    filtered_notes.append(note)
            all_notes = filtered_notes
        
        # Фильтрация по пользователю
        if user_id:
            filtered_notes = []
            for note in all_notes:
                if str(note[0]) == str(user_id):
                    filtered_notes.append(note)
            all_notes = filtered_notes
        
        # Добавляем username для каждой заметки
        notes_with_username = []
        for note in all_notes:
            user_id_note, note_id, note_text, created_at = note
            username = db.get_username_by_id(user_id_note) or f"user{user_id_note}"
            notes_with_username.append((user_id_note, note_id, note_text, created_at, username))
        
        # Пагинация
        per_page = 20
        total = len(notes_with_username)
        start = (page - 1) * per_page
        end = start + per_page
        
        return {
            'notes': notes_with_username[start:end],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
    except Exception as e:
        print(f"Ошибка при получении заметок: {e}")
        return {'notes': [], 'pagination': {'page': 1, 'per_page': 20, 'total': 0, 'pages': 0}}

def get_notes_stats():
    """Получение статистики заметок"""
    try:
        # Получаем все заметки
        all_notes = db.get_all_notes_for_admin()
        
        # Общее количество заметок
        total_notes = len(all_notes)
        
        # Активные пользователи (с заметками)
        active_users = len(set(note[0] for note in all_notes))
        
        # Заметки за сегодня
        today = datetime.now().strftime('%Y-%m-%d')
        notes_today = len([note for note in all_notes if note[3].startswith(today)])
        
        # Среднее количество заметок на пользователя
        avg_notes = total_notes / active_users if active_users > 0 else 0
        
        return {
            'total_notes': total_notes,
            'active_users': active_users,
            'notes_today': notes_today,
            'avg_notes': avg_notes
        }
    except Exception as e:
        print(f"Ошибка при получении статистики заметок: {e}")
        return {
            'total_notes': 0,
            'active_users': 0,
            'notes_today': 0,
            'avg_notes': 0
        }

def get_notes_export_data():
    """Получение данных заметок для экспорта"""
    try:
        all_notes = db.get_all_notes_for_admin()
        export_data = []
        
        for note in all_notes:
            user_id, note_id, note_text, created_at = note
            username = db.get_username_by_id(user_id) or f"user{user_id}"
            
            export_data.append({
                'ID заметки': note_id,
                'ID пользователя': user_id,
                'Username': username,
                'Текст заметки': note_text,
                'Дата создания': created_at,
                'Длина текста': len(note_text)
            })
        
        return export_data
    except Exception as e:
        print(f"Ошибка при получении данных для экспорта: {e}")
        return []

def get_users_export_data():
    """Получение данных пользователей для экспорта"""
    try:
        users_info = db.get_users_debug_info()
        export_data = []
        
        for user in users_info.get('users', []):
            user_id, role, status, username, created_at, last_activity = user
            export_data.append({
                'ID пользователя': user_id,
                'Username': username or f"user{user_id}",
                'Роль': role,
                'Статус': 'Активен' if status else 'Заблокирован',
                'Дата регистрации': created_at,
                'Последняя активность': last_activity
            })
        
        return export_data
    except Exception as e:
        print(f"Ошибка при получении данных для экспорта пользователей: {e}")
        return []

@app.route('/analytics')
@login_required
def analytics():
    """Страница аналитики и графиков"""
    return render_template('analytics.html')

# API endpoints для аналитики
@app.route('/api/analytics/overview')
@login_required
def api_analytics_overview():
    """API для получения общей аналитики с поддержкой фильтров"""
    try:
        period = request.args.get('period', '30d')
        
        # Получаем фильтры
        filters = {
            'role': request.args.get('role', ''),
            'timezone': request.args.get('timezone', ''),
            'min_notes': request.args.get('minNotes', '0'),
            'min_referrals': request.args.get('minReferrals', '0'),
            'start_date': request.args.get('startDate', ''),
            'end_date': request.args.get('endDate', ''),
            'active_only': request.args.get('activeOnly', 'false').lower() == 'true',
            'with_referrals': request.args.get('withReferrals', 'false').lower() == 'true',
            'recent_activity': request.args.get('recentActivity', 'false').lower() == 'true'
        }
        
        metrics = get_analytics_metrics(period, filters)
        charts = get_analytics_charts(period, filters)
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'charts': charts
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/analytics/charts')
@login_required
def api_analytics_charts():
    """API для получения данных графиков с поддержкой фильтров"""
    try:
        period = request.args.get('period', '30d')
        
        # Получаем фильтры
        filters = {
            'role': request.args.get('role', ''),
            'timezone': request.args.get('timezone', ''),
            'min_notes': request.args.get('minNotes', '0'),
            'min_referrals': request.args.get('minReferrals', '0'),
            'start_date': request.args.get('startDate', ''),
            'end_date': request.args.get('endDate', ''),
            'active_only': request.args.get('activeOnly', 'false').lower() == 'true',
            'with_referrals': request.args.get('withReferrals', 'false').lower() == 'true',
            'recent_activity': request.args.get('recentActivity', 'false').lower() == 'true'
        }
        
        charts = get_analytics_charts(period, filters)
        
        return jsonify({
            'success': True,
            'charts': charts
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/analytics/anomalies')
@login_required
def api_analytics_anomalies():
    """API для получения аномалий в данных"""
    try:
        anomalies = detect_anomalies()
        return jsonify({
            'success': True,
            'anomalies': anomalies
        })
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка: {e}'})

@app.route('/api/analytics/export')
@login_required
def api_analytics_export():
    """API для экспорта аналитики"""
    try:
        period = request.args.get('period', '30d')
        
        import pandas as pd
        from io import BytesIO
        
        # Получаем данные для экспорта
        export_data = get_analytics_export_data(period)
        
        # Создаем Excel файл с несколькими листами
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Лист с метриками
            pd.DataFrame([export_data['metrics']]).to_excel(writer, sheet_name='Метрики', index=False)
            
            # Лист с активностью
            pd.DataFrame(export_data['activity']).to_excel(writer, sheet_name='Активность', index=False)
            
            # Лист с рефералами
            pd.DataFrame(export_data['referrals']).to_excel(writer, sheet_name='Рефералы', index=False)
            
            # Лист с заметками
            pd.DataFrame(export_data['notes']).to_excel(writer, sheet_name='Заметки', index=False)
        
        output.seek(0)
        
        # Логируем событие
        db.add_bot_event("WEB_EXPORT_ANALYTICS", f"Экспорт аналитики за период {period}", 
                        current_user.id, "info")
        
        from flask import send_file
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'analytics_{period}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Ошибка экспорта: {e}'})

def get_analytics_metrics(period: str, filters: dict = None) -> dict:
    """Получение метрик аналитики с реальными данными и фильтрами"""
    try:
        if filters is None:
            filters = {}
            
        days = int(period.replace('d', ''))
        start_date = datetime.now() - timedelta(days=days)
        start_date_str = start_date.strftime('%Y-%m-%d')
        
        # Применяем фильтры дат
        if filters.get('start_date'):
            start_date = datetime.fromisoformat(filters['start_date'])
            start_date_str = start_date.strftime('%Y-%m-%d')
        
        end_date = datetime.now()
        if filters.get('end_date'):
            end_date = datetime.fromisoformat(filters['end_date'])
        
        # Получаем данные из базы с фильтрами
        users_info = get_filtered_users_info(filters)
        notes_stats = get_filtered_notes_stats(filters, start_date, end_date)
        referrals_stats = get_filtered_referrals_stats(filters, start_date, end_date)
        
        # Новые пользователи за период
        new_users = len([u for u in users_info.get('users', []) 
                        if u[5] and u[5] >= start_date_str])
        
        # Активные пользователи (с заметками за период)
        active_users = len([u for u in users_info.get('users', []) 
                          if u[6] and u[6] >= start_date_str])
        
        # Новые заметки за период
        new_notes = get_notes_count_for_period_with_filters(days, start_date, filters)
        
        # Рефералы за период
        referrals = get_referrals_count_for_period_with_filters(days, start_date, filters)
        
        # Процентные изменения (сравнение с предыдущим периодом)
        prev_start_date = start_date - timedelta(days=days)
        prev_start_date_str = prev_start_date.strftime('%Y-%m-%d')
        
        prev_new_users = len([u for u in users_info.get('users', []) 
                            if u[5] and prev_start_date_str <= u[5] < start_date_str])
        prev_active_users = len([u for u in users_info.get('users', []) 
                               if u[6] and prev_start_date_str <= u[6] < start_date_str])
        prev_new_notes = get_notes_count_for_period_with_filters(days, prev_start_date, filters)
        prev_referrals = get_referrals_count_for_period_with_filters(days, prev_start_date, filters)
        
        new_users_change = calculate_percentage_change(prev_new_users, new_users)
        active_users_change = calculate_percentage_change(prev_active_users, active_users)
        new_notes_change = calculate_percentage_change(prev_new_notes, new_notes)
        referrals_change = calculate_percentage_change(prev_referrals, referrals)
        
        return {
            'new_users': new_users,
            'new_users_change': new_users_change,
            'active_users': active_users,
            'active_users_change': active_users_change,
            'new_notes': new_notes,
            'new_notes_change': new_notes_change,
            'referrals': referrals,
            'referrals_change': referrals_change
        }
    except Exception as e:
        print(f"Ошибка получения метрик: {e}")
        return {
            'new_users': 0,
            'new_users_change': 0,
            'active_users': 0,
            'active_users_change': 0,
            'new_notes': 0,
            'new_notes_change': 0,
            'referrals': 0,
            'referrals_change': 0
        }

def get_analytics_charts(period: str, filters: dict = None) -> dict:
    """Получение данных для графиков"""
    try:
        days = int(period.replace('d', ''))
        
        # График активности
        activity_data = get_activity_chart_data(days)
        
        # График рефералов
        referrals_data = get_referrals_chart_data()
        
        # График заметок
        notes_data = get_notes_chart_data(days)
        
        # График ролей
        roles_data = get_roles_chart_data()
        
        # График времени
        time_data = get_time_chart_data()
        
        # Географический график
        geo_data = get_geo_chart_data()
        
        # Топ пользователей
        top_users = get_top_users_data()
        
        # Географическая статистика
        geo_stats = get_geo_stats_data()
        
        return {
            'activity': activity_data,
            'referrals': referrals_data,
            'notes': notes_data,
            'roles': roles_data,
            'time': time_data,
            'geo': geo_data,
            'top_users': top_users,
            'geo_stats': geo_stats
        }
    except Exception as e:
        print(f"Ошибка получения данных графиков: {e}")
        return {}

def get_activity_chart_data(days: int) -> dict:
    """Реальные данные для графика активности"""
    try:
        labels = []
        new_users = []
        active_users = []
        
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            labels.append(date)
            
            day_start = datetime.now() - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            # Новые пользователи за день
            day_new_users = get_users_count_for_date(day_start, day_end)
            new_users.append(day_new_users)
            
            # Активные пользователи за день (с заметками)
            day_active_users = get_active_users_count_for_date(day_start, day_end)
            active_users.append(day_active_users)
        
        return {
            'labels': labels,
            'new_users': new_users,
            'active_users': active_users
        }
    except Exception as e:
        print(f"Ошибка получения данных активности: {e}")
        return {'labels': [], 'new_users': [], 'active_users': []}

def get_notes_chart_data(days: int) -> dict:
    """Реальные данные для графика заметок"""
    try:
        labels = []
        data = []
        
        for i in range(days, 0, -1):
            date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            labels.append(date)
            
            day_start = datetime.now() - timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            day_notes = get_notes_count_for_date(day_start, day_end)
            data.append(day_notes)
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"Ошибка получения данных заметок: {e}")
        return {'labels': [], 'data': []}

def get_time_chart_data() -> list:
    """Реальные данные активности по времени"""
    try:
        # Получаем данные активности по часам за последние 7 дней
        time_data = [0] * 24  # 24 часа
        
        # Получаем все заметки за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        notes = db.get_notes_for_period(week_ago, datetime.now())
        
        for note in notes:
            try:
                # Парсим время создания заметки
                created_time = datetime.fromisoformat(note[3].replace('Z', '+00:00'))
                hour = created_time.hour
                time_data[hour] += 1
            except:
                continue
        
        # Возвращаем данные по 4-часовым интервалам
        return [
            sum(time_data[0:4]),   # 00:00-03:59
            sum(time_data[4:8]),   # 04:00-07:59
            sum(time_data[8:12]),  # 08:00-11:59
            sum(time_data[12:16]), # 12:00-15:59
            sum(time_data[16:20]), # 16:00-19:59
            sum(time_data[20:24])  # 20:00-23:59
        ]
    except Exception as e:
        print(f"Ошибка получения данных времени: {e}")
        return [0] * 6

def get_geo_chart_data() -> dict:
    """Реальные географические данные (по часовым поясам)"""
    try:
        # Получаем данные по часовым поясам на основе времени активности
        timezone_data = get_timezone_distribution()
        
        labels = list(timezone_data.keys())
        data = list(timezone_data.values())
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"Ошибка получения географических данных: {e}")
        return {'labels': [], 'data': []}

def get_top_users_data() -> list:
    """Данные топ пользователей"""
    try:
        users_info = db.get_users_extended_info()
        users = users_info.get('users', [])
        
        # Сортируем по количеству заметок
        sorted_users = sorted(users, key=lambda x: x[1], reverse=True)[:10]
        
        top_users = []
        for user in sorted_users:
            user_id, notes_count, role, username = user[0], user[1], user[2], user[3]
            referrals_count = len(db.get_referrals(user_id))
            
            top_users.append({
                'username': username or f"user{user_id}",
                'notes_count': notes_count,
                'referrals_count': referrals_count,
                'role': role
            })
        
        return top_users
    except Exception as e:
        print(f"Ошибка получения топ пользователей: {e}")
        return []

def get_geo_stats_data() -> dict:
    """Географическая статистика"""
    try:
        return {
            'total_countries': 5,
            'top_region': 'Россия',
            'avg_per_country': 18.8
        }
    except Exception as e:
        print(f"Ошибка получения географической статистики: {e}")
        return {
            'total_countries': 0,
            'top_region': 'Неизвестно',
            'avg_per_country': 0
        }

def get_analytics_export_data(period: str) -> dict:
    """Данные для экспорта аналитики"""
    try:
        metrics = get_analytics_metrics(period)
        charts = get_analytics_charts(period)
        
        # Подготавливаем данные для экспорта
        activity_data = []
        for i, label in enumerate(charts['activity']['labels']):
            activity_data.append({
                'Дата': label,
                'Новые пользователи': charts['activity']['new_users'][i],
                'Активные пользователи': charts['activity']['active_users'][i]
            })
        
        referrals_data = []
        for i, label in enumerate(charts['referrals']['labels']):
            referrals_data.append({
                'Пользователь': label,
                'Количество рефералов': charts['referrals']['data'][i]
            })
        
        notes_data = []
        for i, label in enumerate(charts['notes']['labels']):
            notes_data.append({
                'Дата': label,
                'Количество заметок': charts['notes']['data'][i]
            })
        
        return {
            'metrics': metrics,
            'activity': activity_data,
            'referrals': referrals_data,
            'notes': notes_data
        }
    except Exception as e:
        print(f"Ошибка подготовки данных для экспорта: {e}")
        return {}

def get_referrals_chart_data() -> dict:
    """Реальные данные для графика рефералов"""
    try:
        # Получаем топ рефереров
        top_referrers = db.get_top_referrers(5)
        
        labels = []
        data = []
        
        for user_id, referrals_count, total_referrals in top_referrers:
            username = db.get_username_by_id(user_id) or f"user{user_id}"
            labels.append(username)
            data.append(referrals_count)
        
        return {
            'labels': labels,
            'data': data
        }
    except Exception as e:
        print(f"Ошибка получения данных рефералов: {e}")
        return {'labels': [], 'data': []}

def get_roles_chart_data() -> list:
    """Реальные данные для графика ролей"""
    try:
        users_info = db.get_users_extended_info()
        users = users_info.get('users', [])
        
        regular_users = len([u for u in users if u[2] == 'user'])
        admin_users = len([u for u in users if u[2] == 'admin'])
        boss_users = len([u for u in users if u[2] == 'main_admin'])
        
        return [regular_users, admin_users, boss_users]
    except Exception as e:
        print(f"Ошибка получения данных ролей: {e}")
        return [0, 0, 0]

def get_notes_count_for_period(days: int, start_date: datetime = None) -> int:
    """Получение количества заметок за период"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=days)
        end_date = start_date + timedelta(days=days)
        
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM notes 
                WHERE created_at >= ? AND created_at < ?
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества заметок: {e}")
        return 0

def get_referrals_count_for_period(days: int, start_date: datetime = None) -> int:
    """Получение количества рефералов за период"""
    try:
        if not start_date:
            start_date = datetime.now() - timedelta(days=days)
        end_date = start_date + timedelta(days=days)
        
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM referrals 
                WHERE created_at >= ? AND created_at < ?
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества рефералов: {e}")
        return 0

def get_users_count_for_date(start_date: datetime, end_date: datetime) -> int:
    """Получение количества новых пользователей за дату"""
    try:
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM user_roles 
                WHERE granted_at >= ? AND granted_at < ?
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества пользователей: {e}")
        return 0

def get_active_users_count_for_date(start_date: datetime, end_date: datetime) -> int:
    """Получение количества активных пользователей за дату"""
    try:
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(DISTINCT user_id) FROM notes 
                WHERE created_at >= ? AND created_at < ?
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества активных пользователей: {e}")
        return 0

def get_notes_count_for_date(start_date: datetime, end_date: datetime) -> int:
    """Получение количества заметок за дату"""
    try:
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM notes 
                WHERE created_at >= ? AND created_at < ?
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества заметок за дату: {e}")
        return 0

def calculate_percentage_change(old_value: int, new_value: int) -> float:
    """Расчет процентного изменения"""
    if old_value == 0:
        return 100.0 if new_value > 0 else 0.0
    return round(((new_value - old_value) / old_value) * 100, 1)

def get_timezone_distribution() -> dict:
    """Получение распределения по часовым поясам"""
    try:
        # Упрощенное определение по времени активности
        timezone_data = {
            'Москва (UTC+3)': 0,
            'Екатеринбург (UTC+5)': 0,
            'Новосибирск (UTC+7)': 0,
            'Владивосток (UTC+10)': 0,
            'Другие': 0
        }
        
        # Получаем все заметки за последние 30 дней
        month_ago = datetime.now() - timedelta(days=30)
        notes = db.get_notes_for_period(month_ago, datetime.now())
        
        for note in notes:
            try:
                created_time = datetime.fromisoformat(note[3].replace('Z', '+00:00'))
                hour = created_time.hour
                
                # Определяем часовой пояс по времени
                if 6 <= hour <= 22:  # Москва
                    timezone_data['Москва (UTC+3)'] += 1
                elif 8 <= hour <= 24:  # Екатеринбург
                    timezone_data['Екатеринбург (UTC+5)'] += 1
                elif 10 <= hour <= 26:  # Новосибирск
                    timezone_data['Новосибирск (UTC+7)'] += 1
                elif 12 <= hour <= 28:  # Владивосток
                    timezone_data['Владивосток (UTC+10)'] += 1
                else:
                    timezone_data['Другие'] += 1
            except:
                timezone_data['Другие'] += 1
        
        return timezone_data
    except Exception as e:
        print(f"Ошибка получения распределения по часовым поясам: {e}")
        return {'Неизвестно': 0}

def detect_anomalies() -> list:
    """Обнаружение аномалий в данных"""
    anomalies = []
    
    try:
        # Получаем данные за последние 7 дней
        week_ago = datetime.now() - timedelta(days=7)
        today = datetime.now()
        
        # Аномалия 1: Резкое падение активности
        today_notes = get_notes_count_for_date(today, today + timedelta(days=1))
        yesterday_notes = get_notes_count_for_date(today - timedelta(days=1), today)
        
        if yesterday_notes > 0 and today_notes < yesterday_notes * 0.3:
            anomalies.append({
                'type': 'activity_drop',
                'description': f'Резкое падение активности: {today_notes} заметок сегодня vs {yesterday_notes} вчера',
                'severity': 'warning'
            })
        
        # Аномалия 2: Необычно много новых пользователей
        today_users = get_users_count_for_date(today, today + timedelta(days=1))
        avg_daily_users = sum([get_users_count_for_date(today - timedelta(days=i), today - timedelta(days=i-1)) 
                              for i in range(2, 8)]) / 6
        
        if avg_daily_users > 0 and today_users > avg_daily_users * 3:
            anomalies.append({
                'type': 'user_spike',
                'description': f'Необычно много новых пользователей: {today_users} сегодня (среднее: {avg_daily_users:.1f})',
                'severity': 'info'
            })
        
        # Аномалия 3: Нет активности более 12 часов
        last_activity = get_last_activity_time()
        if last_activity:
            hours_since_activity = (datetime.now() - last_activity).total_seconds() / 3600
            if hours_since_activity > 12:
                anomalies.append({
                    'type': 'no_activity',
                    'description': f'Нет активности {hours_since_activity:.1f} часов',
                    'severity': 'error'
                })
        
        # Аномалия 4: Необычное время активности
        time_data = get_time_chart_data()
        if time_data:
            max_activity = max(time_data)
            if max_activity > 0:
                # Проверяем активность в необычное время (2-6 утра)
                night_activity = time_data[0]  # 00:00-03:59
                if night_activity > max_activity * 0.5:
                    anomalies.append({
                        'type': 'night_activity',
                        'description': f'Высокая активность в ночное время: {night_activity} действий',
                        'severity': 'warning'
                    })
        
        # Аномалия 5: Много ошибок в логах
        error_count = get_error_count_last_hour()
        if error_count > 10:
            anomalies.append({
                'type': 'high_errors',
                'description': f'Много ошибок в логах: {error_count} за последний час',
                'severity': 'error'
            })
        
    except Exception as e:
        print(f"Ошибка обнаружения аномалий: {e}")
    
    return anomalies

def get_last_activity_time() -> datetime:
    """Получение времени последней активности"""
    try:
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(created_at) FROM notes
            ''')
            result = cursor.fetchone()
            if result and result[0]:
                return datetime.fromisoformat(result[0].replace('Z', '+00:00'))
    except Exception as e:
        print(f"Ошибка получения времени последней активности: {e}")
    return None

def get_error_count_last_hour() -> int:
    """Получение количества ошибок за последний час"""
    try:
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            hour_ago = (datetime.now() - timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                SELECT COUNT(*) FROM bot_events 
                WHERE severity = 'error' AND timestamp >= ?
            ''', (hour_ago,))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества ошибок: {e}")
        return 0

def get_filtered_users_info(filters: dict) -> dict:
    """Получение информации о пользователях с фильтрами"""
    try:
        users_info = db.get_users_extended_info()
        users = users_info.get('users', [])
        
        # Фильтр по роли
        if filters.get('role'):
            users = [u for u in users if u[2] == filters['role']]
        
        # Фильтр по минимальному количеству заметок
        if filters.get('min_notes'):
            min_notes = int(filters['min_notes'])
            users = [u for u in users if u[1] >= min_notes]
        
        # Фильтр по минимальному количеству рефералов
        if filters.get('min_referrals'):
            min_referrals = int(filters['min_referrals'])
            users = [u for u in users if u[4] >= min_referrals]
        
        # Фильтр только активных пользователей
        if filters.get('active_only'):
            users = [u for u in users if u[6]]  # Есть последняя активность
        
        # Фильтр только с рефералами
        if filters.get('with_referrals'):
            users = [u for u in users if u[4] > 0]
        
        return {'users': users}
    except Exception as e:
        print(f"Ошибка получения отфильтрованных пользователей: {e}")
        return {'users': []}

def get_filtered_notes_stats(filters: dict, start_date: datetime, end_date: datetime) -> dict:
    """Получение статистики заметок с фильтрами"""
    try:
        stats = get_notes_stats()
        
        # Применяем фильтры
        if filters.get('recent_activity'):
            # Только заметки за последние 24 часа
            day_ago = datetime.now() - timedelta(days=1)
            stats['notes_today'] = get_notes_count_for_date(day_ago, datetime.now())
        
        return stats
    except Exception as e:
        print(f"Ошибка получения отфильтрованной статистики заметок: {e}")
        return {'notes_today': 0}

def get_filtered_referrals_stats(filters: dict, start_date: datetime, end_date: datetime) -> dict:
    """Получение статистики рефералов с фильтрами"""
    try:
        stats = db.get_referrals_debug_info()
        
        # Применяем фильтры по датам
        if start_date and end_date:
            stats['total_referrals'] = get_referrals_count_for_date(start_date, end_date)
        
        return stats
    except Exception as e:
        print(f"Ошибка получения отфильтрованной статистики рефералов: {e}")
        return {'total_referrals': 0}

def get_notes_count_for_period_with_filters(days: int, start_date: datetime, filters: dict) -> int:
    """Получение количества заметок за период с фильтрами"""
    try:
        end_date = start_date + timedelta(days=days)
        
        # Базовый запрос
        query = '''
            SELECT COUNT(*) FROM notes 
            WHERE created_at >= ? AND created_at < ?
        '''
        params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        
        # Добавляем фильтры
        if filters.get('role'):
            query += ' AND user_id IN (SELECT user_id FROM user_roles WHERE role = ?)'
            params.append(filters['role'])
        
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества заметок с фильтрами: {e}")
        return 0

def get_referrals_count_for_period_with_filters(days: int, start_date: datetime, filters: dict) -> int:
    """Получение количества рефералов за период с фильтрами"""
    try:
        end_date = start_date + timedelta(days=days)
        
        # Базовый запрос
        query = '''
            SELECT COUNT(*) FROM referrals 
            WHERE created_at >= ? AND created_at < ?
        '''
        params = [start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')]
        
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества рефералов с фильтрами: {e}")
        return 0

def get_referrals_count_for_date(start_date: datetime, end_date: datetime) -> int:
    """Получение количества рефералов за дату"""
    try:
        with sqlite3.connect(db.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM referrals 
                WHERE created_at >= ? AND created_at < ?
            ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Ошибка получения количества рефералов за дату: {e}")
        return 0

if __name__ == '__main__':
    # Запуск веб-панели на всех сетевых интерфейсах (0.0.0.0)
    # Доступно по адресам:
    # - localhost:5000 (локально)
    # - IP_КОМПЬЮТЕРА:5000 (с других устройств в сети)
    print("🌐 Веб-панель запущена на http://0.0.0.0:5000")
    print("📱 Доступ с других устройств: http://188.123.231.247:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 