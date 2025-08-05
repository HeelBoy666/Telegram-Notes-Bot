"""
Модуль работы с базой данных
Copyright (c) 2025 HeelBoy666
Licensed under MIT License (see LICENSE file)

Класс для работы с SQLite базой данных заметок и пользователей.
"""

import sqlite3
from typing import List, Tuple, Optional
from datetime import datetime, timezone
from config import DATABASE_NAME

class Database:
    def __init__(self):
        self.db_name = DATABASE_NAME
        self.init_database()
    
    def init_database(self):
        """Создание таблиц базы данных"""
        with sqlite3.connect(self.db_name) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    note_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
                )
            ''')
            
            # Роли пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_roles (
                    user_id INTEGER PRIMARY KEY,
                    role TEXT NOT NULL DEFAULT 'user',
                    granted_by INTEGER,
                    granted_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
                )
            ''')
            
            # Кулдауны пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_cooldowns (
                    user_id INTEGER PRIMARY KEY,
                    last_add_time TIMESTAMP,
                    last_delete_time TIMESTAMP,
                    last_update_time TIMESTAMP
                )
            ''')
            
            # Реферальная система
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER NOT NULL,
                    referred_id INTEGER NOT NULL UNIQUE,
                    referrer_username TEXT,
                    joined_at TIMESTAMP DEFAULT (datetime('now', '+3 hours')),
                    FOREIGN KEY (referrer_id) REFERENCES user_roles (user_id),
                    FOREIGN KEY (referred_id) REFERENCES user_roles (user_id)
                )
            ''')
            
            # Статистика рефералов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS referral_stats (
                    user_id INTEGER PRIMARY KEY,
                    total_referrals INTEGER DEFAULT 0,
                    active_referrals INTEGER DEFAULT 0,
                    last_updated TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
                )
            ''')
            
            # Username пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_usernames (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    updated_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
                )
            ''')
            
            # События бота
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS bot_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    event_description TEXT NOT NULL,
                    user_id INTEGER,
                    severity TEXT DEFAULT 'info',
                    created_at TIMESTAMP DEFAULT (datetime('now', '+3 hours'))
                )
            ''')
            
            # Таблица статуса пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_status (
                    user_id INTEGER PRIMARY KEY,
                    is_blocked INTEGER DEFAULT 0,
                    blocked_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES user_roles (user_id)
                )
            ''')
            
            # Таблица групп пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_groups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    created_at TEXT,
                    created_by INTEGER,
                    FOREIGN KEY (created_by) REFERENCES user_roles (user_id)
                )
            ''')
            
            # Таблица участников групп
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_group_members (
                    group_id INTEGER,
                    user_id INTEGER,
                    added_at TEXT,
                    PRIMARY KEY (group_id, user_id),
                    FOREIGN KEY (group_id) REFERENCES user_groups (id),
                    FOREIGN KEY (user_id) REFERENCES user_roles (user_id)
                )
            ''')
            
            # Таблица аудита
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    action TEXT NOT NULL,
                    resource TEXT NOT NULL,
                    resource_id TEXT,
                    details TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success INTEGER DEFAULT 1,
                    duration_ms INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES user_roles (user_id)
                )
            ''')
            
            # Индексы для аудита
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_logs(timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user_id ON audit_logs(user_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_logs(resource)')
            
            conn.commit()
        
        # Инициализируем главного админа
        self.init_main_admin()
    
    def init_main_admin(self):
        """Инициализация главного админа из конфига"""
        try:
            from config import ADMIN_ID
            if ADMIN_ID:
                # Проверяем, есть ли уже главный админ в базе
                with sqlite3.connect(self.db_name) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT role FROM user_roles WHERE user_id = ?", (ADMIN_ID,))
                    result = cursor.fetchone()
                    
                    if not result:
                        # Добавляем главного админа
                        cursor.execute("""
                            INSERT OR REPLACE INTO user_roles (user_id, role, granted_by, granted_at)
                            VALUES (?, 'main_admin', ?, datetime('now', '+3 hours'))
                        """, (ADMIN_ID, ADMIN_ID))
                        
                        # Добавляем username для главного админа
                        cursor.execute("""
                            INSERT OR REPLACE INTO user_usernames (user_id, username, updated_at)
                            VALUES (?, 'boss', datetime('now', '+3 hours'))
                        """, (ADMIN_ID,))
                        
                        conn.commit()
                        print(f"✅ Главный админ (ID: {ADMIN_ID}) добавлен в базу данных")
                    else:
                        # Обновляем роль на main_admin если нужно
                        if result[0] != 'main_admin':
                            cursor.execute("""
                                UPDATE user_roles SET role = 'main_admin' WHERE user_id = ?
                            """, (ADMIN_ID,))
                            conn.commit()
                            print(f"✅ Роль главного админа обновлена для ID: {ADMIN_ID}")
        except Exception as e:
            print(f"❌ Ошибка при инициализации главного админа: {e}")
    
    def _validate_user_id(self, user_id) -> bool:
        """Проверка корректности user_id"""
        try:
            user_id = int(user_id)
            return user_id > 0
        except (ValueError, TypeError):
            return False
    
    def _validate_note_text(self, note_text: str) -> bool:
        """Проверка корректности текста заметки"""
        if not isinstance(note_text, str):
            return False
        
        # Максимальная длина 4000 символов
        if len(note_text) > 4000:
            return False
        
        # Текст не должен быть пустым после удаления пробелов
        if not note_text.strip():
            return False
        
        return True
    
    def _validate_note_id(self, note_id) -> bool:
        """Проверка корректности note_id"""
        try:
            note_id = int(note_id)
            return note_id > 0
        except (ValueError, TypeError):
            return False
    
    def _check_cooldown(self, user_id: int, operation: str, cooldown_seconds: int = 2) -> Tuple[bool, float]:
        """
        Проверка кулдауна для операции
        Возвращает (можно_выполнить, оставшееся_время)
        """
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Время операции
                time_column = f"last_{operation}_time"
                cursor.execute(f"SELECT {time_column} FROM user_cooldowns WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                
                if not result or not result[0]:
                    # Первая операция
                    return True, 0.0
                
                last_time_str = result[0]
                last_time = datetime.fromisoformat(last_time_str.replace('Z', '+00:00'))
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)
                
                current_time = datetime.now(timezone.utc)
                time_diff = (current_time - last_time).total_seconds()
                
                if time_diff >= cooldown_seconds:
                    return True, 0.0
                else:
                    remaining_time = cooldown_seconds - time_diff
                    return False, remaining_time
                    
        except Exception as e:
            print(f"Ошибка при проверке кулдауна: {e}")
            return True, 0.0  # В случае ошибки разрешаем операцию
    
    def _update_cooldown(self, user_id: int, operation: str) -> bool:
        """Обновление времени последней операции"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                current_time = datetime.now(timezone.utc).isoformat()
                
                # Запись кулдауна
                time_column = f"last_{operation}_time"
                cursor.execute(f'''
                    INSERT OR REPLACE INTO user_cooldowns (user_id, {time_column})
                    VALUES (?, ?)
                ''', (user_id, current_time))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Ошибка при обновлении кулдауна: {e}")
            return False
    
    def add_note(self, user_id: int, note_text: str) -> Tuple[bool, str]:
        """Добавление новой заметки с проверкой кулдауна"""
        # Входные данные
        if not self._validate_user_id(user_id):
            return False, f"Ошибка: некорректный user_id: {user_id}"
        
        if not self._validate_note_text(note_text):
            return False, "Ошибка: некорректный текст заметки"
        
        # Кулдаун
        can_proceed, remaining_time = self._check_cooldown(user_id, "add", 2)
        if not can_proceed:
            return False, f"Подождите {remaining_time:.1f} секунд перед добавлением новой заметки"
        
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                cursor.execute(
                    'INSERT INTO notes (user_id, note_text) VALUES (?, ?)',
                    (user_id, note_text.strip())
                )
                conn.commit()
                
                # Кулдаун
                self._update_cooldown(user_id, "add")
                
                return True, "Заметка добавлена!"
        except Exception as e:
            return False, f"Ошибка при добавлении заметки: {e}"
    
    def get_user_notes(self, user_id: int) -> List[Tuple[int, str]]:
        """Получение всех заметок пользователя"""
        # Входные данные
        if not self._validate_user_id(user_id):
            print(f"Ошибка: некорректный user_id: {user_id}")
            return []
        
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, note_text FROM notes WHERE user_id = ? ORDER BY created_at DESC',
                    (user_id,)
                )
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении заметок: {e}")
            return []
    
    def delete_note(self, user_id: int, note_id: int) -> Tuple[bool, str]:
        """Удаление заметки с проверкой кулдауна"""
        # Входные данные
        if not self._validate_user_id(user_id):
            return False, f"Ошибка: некорректный user_id: {user_id}"
        
        if not self._validate_note_id(note_id):
            return False, f"Ошибка: некорректный note_id: {note_id}"
        
        # Кулдаун
        can_proceed, remaining_time = self._check_cooldown(user_id, "delete", 2)
        if not can_proceed:
            return False, f"Подождите {remaining_time:.1f} секунд перед удалением заметки"
        
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Принадлежность заметки
                cursor.execute(
                    'SELECT id FROM notes WHERE id = ? AND user_id = ?',
                    (note_id, user_id)
                )
                
                if not cursor.fetchone():
                    return False, "Заметка не найдена или не принадлежит вам"
                
                # Удаление
                cursor.execute(
                    'DELETE FROM notes WHERE id = ? AND user_id = ?',
                    (note_id, user_id)
                )
                conn.commit()
                
                # Кулдаун
                self._update_cooldown(user_id, "delete")
                
                return True, "Заметка удалена!"
        except Exception as e:
            return False, f"Ошибка при удалении заметки: {e}"
    
    def update_note(self, user_id: int, note_id: int, new_text: str) -> Tuple[bool, str]:
        """Обновление заметки с проверкой кулдауна"""
        # Входные данные
        if not self._validate_user_id(user_id):
            return False, f"Ошибка: некорректный user_id: {user_id}"
        
        if not self._validate_note_id(note_id):
            return False, f"Ошибка: некорректный note_id: {note_id}"
        
        if not self._validate_note_text(new_text):
            return False, "Ошибка: некорректный текст заметки"
        
        # Кулдаун
        can_proceed, remaining_time = self._check_cooldown(user_id, "update", 2)
        if not can_proceed:
            return False, f"Подождите {remaining_time:.1f} секунд перед обновлением заметки"
        
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Принадлежность заметки
                cursor.execute(
                    'SELECT id FROM notes WHERE id = ? AND user_id = ?',
                    (note_id, user_id)
                )
                
                if not cursor.fetchone():
                    return False, "Заметка не найдена или не принадлежит вам"
                
                cursor.execute(
                    'UPDATE notes SET note_text = ? WHERE id = ? AND user_id = ?',
                    (new_text.strip(), note_id, user_id)
                )
                conn.commit()
                
                # Кулдаун
                self._update_cooldown(user_id, "update")
                
                return True, "Заметка обновлена!"
        except Exception as e:
            return False, f"Ошибка при обновлении заметки: {e}"
    
    def get_note_by_id(self, user_id: int, note_id: int) -> Optional[Tuple[int, str]]:
        """Получение заметки по ID для проверки существования"""
        # Входные данные
        if not self._validate_user_id(user_id):
            print(f"Ошибка: некорректный user_id: {user_id}")
            return None
        
        if not self._validate_note_id(note_id):
            print(f"Ошибка: некорректный note_id: {note_id}")
            return None
        
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT id, note_text FROM notes WHERE id = ? AND user_id = ?',
                    (note_id, user_id)
                )
                return cursor.fetchone()
        except Exception as e:
            print(f"Ошибка при получении заметки: {e}")
            return None
    
    def get_all_users_with_notes_count(self) -> List[Tuple[int, int]]:
        """Получение списка всех пользователей с количеством их заметок (для админа)"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, COUNT(*) as notes_count 
                    FROM notes 
                    GROUP BY user_id 
                    ORDER BY notes_count DESC
                ''')
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении списка пользователей: {e}")
            return []
    
    def get_all_notes_for_admin(self) -> List[Tuple[int, int, str, str]]:
        """Получение всех заметок для админа (user_id, note_id, note_text, created_at)"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, id, note_text, created_at 
                    FROM notes 
                    ORDER BY created_at DESC
                ''')
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении всех заметок: {e}")
            return []
    
    def get_user_notes_for_admin(self, user_id: int) -> List[Tuple[int, str, str]]:
        """Получение заметок конкретного пользователя для админа"""
        # Входные данные
        if not self._validate_user_id(user_id):
            print(f"Ошибка: некорректный user_id: {user_id}")
            return []
        
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, note_text, created_at 
                    FROM notes 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                ''', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении заметок пользователя: {e}")
            return []
    
    def get_users_with_admin_separation(self, admin_id: int) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]:
        """Получение списка пользователей с разделением на админов и обычных пользователей"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, COUNT(*) as notes_count 
                    FROM notes 
                    GROUP BY user_id 
                    ORDER BY notes_count DESC
                ''')
                all_users = cursor.fetchall()
                
                # Админы из БД
                cursor.execute('SELECT user_id FROM user_roles WHERE role = "admin"')
                db_admins = [row[0] for row in cursor.fetchall()]
                
                # Главный админ
                if admin_id not in db_admins:
                    db_admins.append(admin_id)
                
                # Разделение
                admins = []
                regular_users = []
                
                for user_id, notes_count in all_users:
                    if user_id in db_admins:
                        admins.append((user_id, notes_count))
                    else:
                        regular_users.append((user_id, notes_count))
                
                # Админы без заметок
                for admin_id_in_db in db_admins:
                    if not any(user_id == admin_id_in_db for user_id, _ in admins):
                        admins.append((admin_id_in_db, 0))
                
                return admins, regular_users
                
        except Exception as e:
            print(f"Ошибка при получении списка пользователей: {e}")
            return [], []
    
    def get_users_with_referral_info(self, admin_id: int) -> Tuple[List[Tuple[int, int, int, int]], List[Tuple[int, int, int, int]]]:
        """Получение списка пользователей с информацией о рефералах"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Получаем всех пользователей с количеством заметок и рефералов
                cursor.execute('''
                    SELECT 
                        ur.user_id, 
                        COALESCE(n.notes_count, 0) as notes_count,
                        COALESCE(rs.total_referrals, 0) as total_referrals,
                        COALESCE(rs.active_referrals, 0) as active_referrals
                    FROM user_roles ur
                    LEFT JOIN (
                        SELECT user_id, COUNT(*) as notes_count 
                        FROM notes 
                        GROUP BY user_id
                    ) n ON ur.user_id = n.user_id
                    LEFT JOIN referral_stats rs ON ur.user_id = rs.user_id
                    ORDER BY n.notes_count DESC
                ''')
                all_users = cursor.fetchall()
                
                # Админы из БД
                cursor.execute('SELECT user_id FROM user_roles WHERE role IN ("admin", "main_admin")')
                db_admins = [row[0] for row in cursor.fetchall()]
                
                # Главный админ
                if admin_id not in db_admins:
                    db_admins.append(admin_id)
                
                # Разделение
                admins = []
                regular_users = []
                
                for user_id, notes_count, total_referrals, active_referrals in all_users:
                    if user_id in db_admins:
                        admins.append((user_id, notes_count, total_referrals, active_referrals))
                    else:
                        regular_users.append((user_id, notes_count, total_referrals, active_referrals))
                
                # Админы без заметок
                for admin_id_in_db in db_admins:
                    if not any(user_id == admin_id_in_db for user_id, _, _, _ in admins):
                        admins.append((admin_id_in_db, 0, 0, 0))
                
                return admins, regular_users
                
        except Exception as e:
            print(f"Ошибка при получении списка пользователей с рефералами: {e}")
            return [], []
    
    def add_user_role(self, user_id: int, role: str, granted_by: int) -> bool:
        """Добавление или обновление роли пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_roles (user_id, role, granted_by, granted_at) 
                    VALUES (?, ?, ?, datetime('now', '+3 hours'))
                ''', (user_id, role, granted_by))
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении роли пользователя: {e}")
            return False
    
    def remove_user_role(self, user_id: int) -> bool:
        """Удаление роли пользователя (возврат к обычному пользователю)"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_roles WHERE user_id = ?', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при удалении роли пользователя: {e}")
            return False
    
    def get_user_role(self, user_id: int) -> str:
        """Получение роли пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT role FROM user_roles WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return result[0] if result else 'user'
        except Exception as e:
            print(f"Ошибка при получении роли пользователя: {e}")
            return 'user'
    
    def get_all_admins(self) -> List[int]:
        """Получение списка всех администраторов"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT user_id FROM user_roles WHERE role IN ('admin', 'main_admin')")
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении списка администраторов: {e}")
            return []

    def ensure_user_exists(self, user_id: int) -> bool:
        """Обеспечивает существование пользователя в базе данных"""
        try:
            if not self._validate_user_id(user_id):
                return False
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Проверяем, существует ли пользователь
                cursor.execute("SELECT user_id FROM user_roles WHERE user_id = ?", (user_id,))
                if not cursor.fetchone():
                    # Проверяем, не является ли это главным админом
                    from config import ADMIN_ID
                    if user_id == ADMIN_ID:
                        # Создаем главного админа
                        cursor.execute(
                            "INSERT INTO user_roles (user_id, role, granted_by) VALUES (?, 'main_admin', ?)",
                            (user_id, user_id)
                        )
                    else:
                        # Создаем обычного пользователя
                        cursor.execute(
                            "INSERT INTO user_roles (user_id, role) VALUES (?, 'user')",
                            (user_id,)
                        )
                    conn.commit()
                    return True
                return True
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            return False

    # РЕФЕРАЛЬНАЯ СИСТЕМА
    
    def add_referral(self, referrer_id: int, referred_id: int, referrer_username: str = None) -> bool:
        """Добавление реферальной связи"""
        try:
            if not self._validate_user_id(referrer_id) or not self._validate_user_id(referred_id):
                return False
            
            if referrer_id == referred_id:
                return False
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Обеспечиваем существование обоих пользователей
                self.ensure_user_exists(referrer_id)
                self.ensure_user_exists(referred_id)
                
                # Проверяем, что реферал еще не привязан
                cursor.execute("SELECT referred_id FROM referrals WHERE referred_id = ?", (referred_id,))
                if cursor.fetchone():
                    return False
                
                # Добавляем реферальную связь
                cursor.execute(
                    "INSERT INTO referrals (referrer_id, referred_id, referrer_username) VALUES (?, ?, ?)",
                    (referrer_id, referred_id, referrer_username)
                )
                
                conn.commit()
                
                # Обновляем статистику реферера
                self._update_referral_stats(referrer_id)
                
                return True
        except Exception as e:
            print(f"Ошибка при добавлении реферала: {e}")
            return False
    
    def get_referrer(self, user_id: int) -> Optional[int]:
        """Получение ID реферера пользователя"""
        try:
            if not self._validate_user_id(user_id):
                return None
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT referrer_id FROM referrals WHERE referred_id = ?", (user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Ошибка при получении реферера: {e}")
            return None
    
    def get_referrer_info(self, user_id: int) -> Optional[Tuple[int, str]]:
        """Получение информации о реферере (ID и username)"""
        try:
            if not self._validate_user_id(user_id):
                return None
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT referrer_id, referrer_username FROM referrals WHERE referred_id = ?", (user_id,))
                result = cursor.fetchone()
                return result if result else None
        except Exception as e:
            print(f"Ошибка при получении информации о реферере: {e}")
            return None
    
    def get_referrals(self, user_id: int) -> List[Tuple[int, str]]:
        """Получение списка рефералов пользователя"""
        try:
            if not self._validate_user_id(user_id):
                return []
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT r.referred_id, r.joined_at 
                    FROM referrals r 
                    WHERE r.referrer_id = ? 
                    ORDER BY r.joined_at DESC
                ''', (user_id,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении рефералов: {e}")
            return []
    
    def get_referral_stats(self, user_id: int) -> Tuple[int, int]:
        """Получение статистики рефералов пользователя"""
        try:
            if not self._validate_user_id(user_id):
                return (0, 0)
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT total_referrals, active_referrals 
                    FROM referral_stats 
                    WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                return result if result else (0, 0)
        except Exception as e:
            print(f"Ошибка при получении статистики рефералов: {e}")
            return (0, 0)
    
    def _update_referral_stats(self, user_id: int) -> bool:
        """Обновление статистики рефералов пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Подсчитываем общее количество рефералов
                cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,))
                total_referrals = cursor.fetchone()[0]
                
                # Подсчитываем активных рефералов (тех, кто пришел по реферальной ссылке)
                # Все рефералы в таблице referrals считаются активными, так как они пришли по ссылке
                active_referrals = total_referrals
                
                # Обновляем или создаем запись статистики
                cursor.execute('''
                    INSERT OR REPLACE INTO referral_stats 
                    (user_id, total_referrals, active_referrals, last_updated) 
                    VALUES (?, ?, ?, datetime('now', '+3 hours'))
                ''', (user_id, total_referrals, active_referrals))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении статистики рефералов: {e}")
            return False
    
    def get_top_referrers(self, limit: int = 10) -> List[Tuple[int, int, int]]:
        """Получение топ рефереров"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT rs.user_id, rs.total_referrals, rs.active_referrals 
                    FROM referral_stats rs 
                    ORDER BY rs.total_referrals DESC, rs.active_referrals DESC 
                    LIMIT ?
                ''', (limit,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении топ рефереров: {e}")
            return []
    
    def get_username_by_id(self, user_id: int) -> Optional[str]:
        """Получение username пользователя по ID"""
        try:
            if not self._validate_user_id(user_id):
                return None
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Сначала пытаемся получить из таблицы user_usernames
                cursor.execute("SELECT username FROM user_usernames WHERE user_id = ?", (user_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
                
                # Если не найдено, ищем в таблице referrals
                cursor.execute("SELECT referrer_username FROM referrals WHERE referrer_id = ? LIMIT 1", (user_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    # Сохраняем найденный username в user_usernames
                    self.save_username(user_id, result[0])
                    return result[0]
                
                return None
        except Exception as e:
            print(f"Ошибка при получении username: {e}")
            return None
    
    def save_username(self, user_id: int, username: str) -> bool:
        """Сохранение username пользователя"""
        try:
            if not self._validate_user_id(user_id) or not username:
                return False
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_usernames (user_id, username, updated_at) 
                    VALUES (?, ?, datetime('now', '+3 hours'))
                ''', (user_id, username))
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при сохранении username: {e}")
            return False
    
    def update_all_usernames_from_referrals(self) -> bool:
        """Обновляет все username из таблицы referrals"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Получаем все уникальные user_id из referrals
                cursor.execute("SELECT DISTINCT referrer_id FROM referrals")
                referrer_ids = [row[0] for row in cursor.fetchall()]
                
                cursor.execute("SELECT DISTINCT referred_id FROM referrals")
                referred_ids = [row[0] for row in cursor.fetchall()]
                
                # Объединяем и убираем дубликаты
                all_user_ids = list(set(referrer_ids + referred_ids))
                
                # Обновляем username для каждого пользователя
                for user_id in all_user_ids:
                    cursor.execute("SELECT referrer_username FROM referrals WHERE referrer_id = ? LIMIT 1", (user_id,))
                    result = cursor.fetchone()
                    if result and result[0]:
                        cursor.execute('''
                            INSERT OR REPLACE INTO user_usernames (user_id, username, updated_at) 
                            VALUES (?, ?, datetime('now', '+3 hours'))
                        ''', (user_id, result[0]))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении username: {e}")
            return False
    
    def create_usernames_for_all_users(self) -> bool:
        """Создает username для всех пользователей, у которых его нет"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Получаем всех пользователей из user_roles
                cursor.execute("SELECT user_id FROM user_roles")
                all_users = [row[0] for row in cursor.fetchall()]
                
                # Для каждого пользователя создаем username если его нет
                for user_id in all_users:
                    cursor.execute("SELECT username FROM user_usernames WHERE user_id = ?", (user_id,))
                    result = cursor.fetchone()
                    
                    if not result:
                        # Создаем username в формате user{id}
                        username = f"user{user_id}"
                        cursor.execute('''
                            INSERT INTO user_usernames (user_id, username, updated_at) 
                            VALUES (?, ?, datetime('now', '+3 hours'))
                        ''', (user_id, username))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при создании username: {e}")
            return False

    def get_users_debug_info(self) -> dict:
        """Получение отладочной информации о пользователях"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Статистика пользователей
                cursor.execute("SELECT COUNT(*) FROM user_roles")
                total_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_roles WHERE role = 'admin'")
                admin_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_roles WHERE role = 'main_admin'")
                boss_users = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM user_roles WHERE role = 'user'")
                regular_users = cursor.fetchone()[0]
                
                # Все роли в системе
                cursor.execute("SELECT DISTINCT role FROM user_roles")
                all_roles = [row[0] for row in cursor.fetchall()]
                
                # Детальная информация с дополнительными данными
                cursor.execute("""
                    SELECT ur.user_id, ur.role, ur.granted_at, 
                           uu.username,
                           r1.referrer_id, r1.referrer_username,
                           r2.referred_id
                    FROM user_roles ur
                    LEFT JOIN user_usernames uu ON ur.user_id = uu.user_id
                    LEFT JOIN (
                        SELECT DISTINCT referrer_id, referrer_username 
                        FROM referrals 
                        GROUP BY referrer_id
                    ) r1 ON ur.user_id = r1.referrer_id
                    LEFT JOIN (
                        SELECT DISTINCT referred_id 
                        FROM referrals 
                        GROUP BY referred_id
                    ) r2 ON ur.user_id = r2.referred_id
                    ORDER BY ur.granted_at DESC
                """)
                users = cursor.fetchall()
                
                return {
                    'total_users': total_users,
                    'admin_users': admin_users,
                    'boss_users': boss_users,
                    'regular_users': regular_users,
                    'all_roles': all_roles,
                    'users': users
                }
        except Exception as e:
            print(f"Ошибка при получении отладочной информации о пользователях: {e}")
            return {}

    def get_referrals_debug_info(self) -> dict:
        """Получение отладочной информации о рефералах"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Статистика рефералов
                cursor.execute("SELECT COUNT(*) FROM referrals")
                total_referrals = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT referrer_id) FROM referrals")
                unique_referrers = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT referred_id) FROM referrals")
                unique_referred = cursor.fetchone()[0]
                
                # Детальная информация
                cursor.execute("SELECT referrer_id, referred_id, referrer_username, joined_at FROM referrals ORDER BY joined_at DESC")
                referrals = cursor.fetchall()
                
                return {
                    'total_referrals': total_referrals,
                    'unique_referrers': unique_referrers,
                    'unique_referred': unique_referred,
                    'referrals': referrals
                }
        except Exception as e:
            print(f"Ошибка при получении отладочной информации о рефералах: {e}")
            return {}

    def get_users_excel_data(self) -> list:
        """Получение данных пользователей для Excel файла"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Получаем полную информацию о пользователях
                cursor.execute("""
                    SELECT 
                        ur.user_id,
                        uu.username,
                        ur.role,
                        ur.granted_at,
                        uu.updated_at,
                        r1.referrer_id,
                        r1.referrer_username,
                        CASE WHEN r2.referred_id IS NOT NULL THEN 'Да' ELSE 'Нет' END as has_referrals
                    FROM user_roles ur
                    LEFT JOIN user_usernames uu ON ur.user_id = uu.user_id
                    LEFT JOIN (
                        SELECT DISTINCT referrer_id, referrer_username 
                        FROM referrals 
                        GROUP BY referrer_id
                    ) r1 ON ur.user_id = r1.referrer_id
                    LEFT JOIN (
                        SELECT DISTINCT referred_id 
                        FROM referrals 
                        GROUP BY referred_id
                    ) r2 ON ur.user_id = r2.referred_id
                    ORDER BY ur.granted_at DESC
                """)
                
                users = cursor.fetchall()
                data = []
                
                for user_id, username, role, granted_at, updated_at, referrer_id, referrer_username, has_referrals in users:
                    # Форматируем даты
                    granted_date = granted_at if granted_at else "Неизвестно"
                    updated_date = updated_at if updated_at else "Неизвестно"
                    
                    # Username или "Нет"
                    username_display = username if username else "Нет"
                    
                    # Реферер информация
                    referrer_id_display = referrer_id if referrer_id else "Нет"
                    referrer_username_display = referrer_username if referrer_username else "Нет"
                    
                    data.append({
                        'ID пользователя': user_id,
                        'Username': username_display,
                        'Роль': role,
                        'Реферер ID': referrer_id_display,
                        'Реферер Username': referrer_username_display,
                        'Есть рефералы': has_referrals,
                        'Дата регистрации': granted_date,
                        'Дата последнего обновления': updated_date
                    })
                
                return data
        except Exception as e:
            print(f"Ошибка при получении данных для Excel: {e}")
            return []

    def fix_referral_usernames(self) -> int:
        """Исправление username рефералов. Возвращает количество исправленных записей"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT referrer_id, referred_id, referrer_username FROM referrals")
                referrals = cursor.fetchall()
                
                fixed_count = 0
                for referrer_id, referred_id, referrer_username in referrals:
                    # Проверяем, есть ли уже username для реферера
                    cursor.execute("SELECT username FROM user_usernames WHERE user_id = ?", (referrer_id,))
                    referrer_result = cursor.fetchone()
                    if not referrer_result and referrer_username:
                        self.save_username(referrer_id, referrer_username)
                        fixed_count += 1
                    
                    # Проверяем, есть ли уже username для реферала
                    cursor.execute("SELECT username FROM user_usernames WHERE user_id = ?", (referred_id,))
                    result = cursor.fetchone()
                    if not result:
                        username = f"user{referred_id}"
                        self.save_username(referred_id, username)
                        fixed_count += 1
                
                return fixed_count
        except Exception as e:
            print(f"Ошибка при исправлении username рефералов: {e}")
            return 0

    def get_debug_usernames_info(self) -> dict:
        """Получение отладочной информации о username"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Получаем все записи из user_usernames
                cursor.execute("SELECT user_id, username FROM user_usernames ORDER BY user_id")
                usernames = cursor.fetchall()
                
                # Получаем все записи из referrals
                cursor.execute("SELECT referrer_id, referred_id, referrer_username FROM referrals ORDER BY referrer_id")
                referrals = cursor.fetchall()
                
                # Получаем всех пользователей из user_roles
                cursor.execute("SELECT user_id, role FROM user_roles ORDER BY user_id")
                users = cursor.fetchall()
                
                return {
                    'usernames': usernames,
                    'referrals': referrals,
                    'users': users
                }
        except Exception as e:
            print(f"Ошибка при получении отладочной информации о username: {e}")
            return {}

    def fix_referral_username_simple(self) -> int:
        """Простое исправление username рефералов (для команды)"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Получаем все записи из referrals
                cursor.execute("SELECT referrer_id, referred_id, referrer_username FROM referrals")
                referrals = cursor.fetchall()
                
                fixed_count = 0
                for referrer_id, referred_id, referrer_username in referrals:
                    # Сохраняем username реферера
                    if referrer_username:
                        self.save_username(referrer_id, referrer_username)
                        fixed_count += 1
                    
                    # Создаем username для реферала если его нет
                    cursor.execute("SELECT username FROM user_usernames WHERE user_id = ?", (referred_id,))
                    result = cursor.fetchone()
                    if not result:
                        username = f"user{referred_id}"
                        self.save_username(referred_id, username)
                        fixed_count += 1
                
                return fixed_count
        except Exception as e:
            print(f"Ошибка при исправлении username: {e}")
            return 0

    def add_bot_event(self, event_type: str, event_description: str, user_id: int = None, severity: str = 'info') -> bool:
        """Добавление события бота"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO bot_events (event_type, event_description, user_id, severity, created_at)
                    VALUES (?, ?, ?, ?, datetime('now', '+3 hours'))
                ''', (event_type, event_description, user_id, severity))
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при добавлении события: {e}")
            return False

    def get_recent_events(self, limit: int = 20) -> list:
        """Получение последних событий с информацией о пользователях"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT e.event_type, e.event_description, e.user_id, e.severity, e.created_at,
                           u.username
                    FROM bot_events e
                    LEFT JOIN user_usernames u ON e.user_id = u.user_id
                    ORDER BY e.created_at DESC
                    LIMIT ?
                ''', (limit,))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении событий: {e}")
            return []

    def get_events_excel_data(self) -> list:
        """Получение данных событий для Excel файла"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT event_type, event_description, user_id, severity, created_at
                    FROM bot_events
                    ORDER BY created_at DESC
                ''')
                events = cursor.fetchall()
                
                data = []
                for event_type, event_description, user_id, severity, created_at in events:
                    # Получаем username пользователя
                    username = "Система"
                    if user_id:
                        username = self.get_username_by_id(user_id) or f"user{user_id}"
                    
                    # Определяем важность события
                    severity_display = {
                        'info': 'Информация',
                        'warning': 'Предупреждение',
                        'error': 'Ошибка',
                        'critical': 'Критично'
                    }.get(severity, severity)
                    
                    data.append({
                        'Тип события': event_type,
                        'Описание': event_description,
                        'Пользователь': username,
                        'Важность': severity_display,
                        'Дата': created_at
                    })
                
                return data
        except Exception as e:
            print(f"Ошибка при получении данных событий для Excel: {e}")
            return []

    def get_events_stats(self) -> dict:
        """Получение статистики событий"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Общее количество событий
                cursor.execute("SELECT COUNT(*) FROM bot_events")
                total_events = cursor.fetchone()[0]
                
                # События за последние 24 часа
                cursor.execute("""
                    SELECT COUNT(*) FROM bot_events 
                    WHERE created_at >= datetime('now', '-1 day', '+3 hours')
                """)
                events_24h = cursor.fetchone()[0]
                
                # События по типам
                cursor.execute("""
                    SELECT event_type, COUNT(*) 
                    FROM bot_events 
                    GROUP BY event_type 
                    ORDER BY COUNT(*) DESC
                """)
                events_by_type = cursor.fetchall()
                
                # События по важности
                cursor.execute("""
                    SELECT severity, COUNT(*) 
                    FROM bot_events 
                    GROUP BY severity 
                    ORDER BY COUNT(*) DESC
                """)
                events_by_severity = cursor.fetchall()
                
                return {
                    'total_events': total_events,
                    'events_24h': events_24h,
                    'events_by_type': events_by_type,
                    'events_by_severity': events_by_severity
                }
        except Exception as e:
            print(f"Ошибка при получении статистики событий: {e}")
            return {}
    
    def is_bot_stopped(self) -> bool:
        """Проверка остановлен ли бот"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM bot_events 
                    WHERE event_type = 'BOT_STOP' 
                    AND created_at > (
                        SELECT COALESCE(MAX(created_at), '1970-01-01') 
                        FROM bot_events 
                        WHERE event_type = 'BOT_START'
                    )
                """)
                return cursor.fetchone()[0] > 0
        except:
            return False
    
    def stop_bot(self) -> bool:
        """Остановка бота"""
        try:
            self.add_bot_event("BOT_STOP", "Бот остановлен через веб-панель", None, "warning")
            return True
        except:
            return False
    
    def start_bot(self) -> bool:
        """Запуск бота"""
        try:
            self.add_bot_event("BOT_START", "Бот запущен через веб-панель", None, "info")
            return True
        except:
            return False
    
    def grant_admin_role(self, user_id: int) -> bool:
        """Выдача роли администратора"""
        try:
            from config import ADMIN_ID
            return self.add_user_role(user_id, 'admin', ADMIN_ID)
        except:
            return False
    
    def revoke_admin_role(self, user_id: int) -> bool:
        """Снятие роли администратора"""
        try:
            return self.remove_user_role(user_id)
        except:
            return False
    
    def clear_all_tables(self) -> bool:
        """Очистка всех таблиц"""
        try:
            from config import ADMIN_ID
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Очищаем все таблицы
                tables = ['notes', 'user_roles', 'user_cooldowns', 'referrals', 
                         'referral_stats', 'user_usernames', 'bot_events']
                
                for table in tables:
                    cursor.execute(f"DELETE FROM {table}")
                
                conn.commit()
                
                # Логируем событие
                self.add_bot_event("WEB_CLEAR_DATABASE", "База данных очищена через веб-панель", 
                                ADMIN_ID, "critical")
                
                return True
        except Exception as e:
            print(f"Ошибка при очистке базы данных: {e}")
            return False 
    
    def update_note_admin(self, note_id: int, new_text: str, admin_id: int) -> Tuple[bool, str]:
        """Обновление заметки администратором"""
        try:
            if not self._validate_note_id(note_id):
                return False, f"Ошибка: некорректный note_id: {note_id}"
            
            if not self._validate_note_text(new_text):
                return False, "Ошибка: некорректный текст заметки"
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Проверяем существование заметки
                cursor.execute('SELECT user_id FROM notes WHERE id = ?', (note_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "Заметка не найдена"
                
                user_id = result[0]
                
                # Обновляем заметку
                cursor.execute(
                    'UPDATE notes SET note_text = ? WHERE id = ?',
                    (new_text.strip(), note_id)
                )
                conn.commit()
                
                # Логируем событие
                self.add_bot_event("ADMIN_UPDATE_NOTE", f"Админ {admin_id} обновил заметку {note_id} пользователя {user_id}", 
                                admin_id, "info")
                
                return True, "Заметка обновлена!"
        except Exception as e:
            return False, f"Ошибка при обновлении заметки: {e}"
    
    def delete_note_admin(self, note_id: int, admin_id: int) -> Tuple[bool, str]:
        """Удаление заметки администратором"""
        try:
            if not self._validate_note_id(note_id):
                return False, f"Ошибка: некорректный note_id: {note_id}"
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Проверяем существование заметки
                cursor.execute('SELECT user_id FROM notes WHERE id = ?', (note_id,))
                result = cursor.fetchone()
                
                if not result:
                    return False, "Заметка не найдена"
                
                user_id = result[0]
                
                # Удаляем заметку
                cursor.execute('DELETE FROM notes WHERE id = ?', (note_id,))
                conn.commit()
                
                # Логируем событие
                self.add_bot_event("ADMIN_DELETE_NOTE", f"Админ {admin_id} удалил заметку {note_id} пользователя {user_id}", 
                                admin_id, "warning")
                
                return True, "Заметка удалена!"
        except Exception as e:
            return False, f"Ошибка при удалении заметки: {e}"
    
    def get_notes_excel_data(self) -> list:
        """Получение данных заметок для Excel файла"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT n.id, n.user_id, n.note_text, n.created_at, uu.username
                    FROM notes n
                    LEFT JOIN user_usernames uu ON n.user_id = uu.user_id
                    ORDER BY n.created_at DESC
                ''')
                
                notes = cursor.fetchall()
                data = []
                
                for note_id, user_id, note_text, created_at, username in notes:
                    data.append({
                        'ID заметки': note_id,
                        'ID пользователя': user_id,
                        'Username': username or f"user{user_id}",
                        'Текст заметки': note_text,
                        'Дата создания': created_at,
                        'Длина текста': len(note_text)
                    })
                
                return data
        except Exception as e:
            print(f"Ошибка при получении данных заметок для Excel: {e}")
            return [] 
    
    def block_user(self, user_id: int) -> bool:
        """Блокировка пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO user_status (user_id, is_blocked, blocked_at)
                    VALUES (?, 1, datetime('now', '+3 hours'))
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при блокировке пользователя: {e}")
            return False
    
    def unblock_user(self, user_id: int) -> bool:
        """Разблокировка пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_status WHERE user_id = ?', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при разблокировке пользователя: {e}")
            return False
    
    def get_user_status(self, user_id: int) -> bool:
        """Получение статуса пользователя (True = активен, False = заблокирован)"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT is_blocked FROM user_status WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return not result or not result[0]  # True если не заблокирован
        except Exception as e:
            print(f"Ошибка при получении статуса пользователя: {e}")
            return True  # По умолчанию активен
    
    def get_user_created_at(self, user_id: int) -> Optional[str]:
        """Получение даты регистрации пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT granted_at FROM user_roles WHERE user_id = ?', (user_id,))
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Ошибка при получении даты регистрации: {e}")
            return None
    
    def get_user_last_activity(self, user_id: int) -> Optional[str]:
        """Получение времени последней активности пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT MAX(created_at) FROM notes WHERE user_id = ?
                ''', (user_id,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else None
        except Exception as e:
            print(f"Ошибка при получении времени активности: {e}")
            return None
    
    def create_user_admin(self, user_id: int, username: str, role: str = 'user', status: bool = True) -> bool:
        """Создание пользователя администратором"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Создаем пользователя
                cursor.execute('''
                    INSERT OR REPLACE INTO user_roles (user_id, role, granted_by, granted_at)
                    VALUES (?, ?, ?, datetime('now', '+3 hours'))
                ''', (user_id, role, ADMIN_ID))
                
                # Сохраняем username
                if username:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_usernames (user_id, username, updated_at)
                        VALUES (?, ?, datetime('now', '+3 hours'))
                    ''', (user_id, username))
                
                # Устанавливаем статус
                if not status:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_status (user_id, is_blocked, blocked_at)
                        VALUES (?, 1, datetime('now', '+3 hours'))
                    ''', (user_id,))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при создании пользователя: {e}")
            return False
    
    def update_user_admin(self, user_id: int, username: str, role: str, status: bool) -> bool:
        """Обновление пользователя администратором"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Обновляем роль
                cursor.execute('''
                    UPDATE user_roles SET role = ? WHERE user_id = ?
                ''', (role, user_id))
                
                # Обновляем username
                if username:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_usernames (user_id, username, updated_at)
                        VALUES (?, ?, datetime('now', '+3 hours'))
                    ''', (user_id, username))
                
                # Обновляем статус
                if status:
                    cursor.execute('DELETE FROM user_status WHERE user_id = ?', (user_id,))
                else:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_status (user_id, is_blocked, blocked_at)
                        VALUES (?, 1, datetime('now', '+3 hours'))
                    ''', (user_id,))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при обновлении пользователя: {e}")
            return False
    
    def create_user_group(self, name: str, description: str, user_ids: List[int]) -> bool:
        """Создание группы пользователей"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Создаем группу
                cursor.execute('''
                    INSERT INTO user_groups (name, description, created_at)
                    VALUES (?, ?, datetime('now', '+3 hours'))
                ''', (name, description))
                
                group_id = cursor.lastrowid
                
                # Добавляем пользователей в группу
                for user_id in user_ids:
                    cursor.execute('''
                        INSERT OR REPLACE INTO user_group_members (group_id, user_id, added_at)
                        VALUES (?, ?, datetime('now', '+3 hours'))
                    ''', (group_id, user_id))
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Ошибка при создании группы пользователей: {e}")
            return False 
    
    def get_users_extended_info(self) -> dict:
        """Получение расширенной информации о пользователях"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        ur.user_id,
                        (SELECT COUNT(*) FROM notes WHERE user_id = ur.user_id) as notes_count,
                        ur.role,
                        uu.username,
                        (SELECT COUNT(*) FROM referrals WHERE referrer_id = ur.user_id) as referrals_count,
                        ur.granted_at as created_at,
                        (SELECT MAX(created_at) FROM notes WHERE user_id = ur.user_id) as last_activity,
                        CASE WHEN us.is_blocked = 1 THEN 0 ELSE 1 END as status
                    FROM user_roles ur
                    LEFT JOIN user_usernames uu ON ur.user_id = uu.user_id
                    LEFT JOIN user_status us ON ur.user_id = us.user_id
                    ORDER BY ur.user_id DESC
                ''')
                
                users = cursor.fetchall()
                
                # Подсчитываем статистику
                total_users = len(users)
                regular_users = len([u for u in users if u[2] == 'user'])
                admin_users = len([u for u in users if u[2] == 'admin'])
                boss_users = len([u for u in users if u[2] == 'main_admin'])
                
                return {
                    'users': users,
                    'total_users': total_users,
                    'regular_users': regular_users,
                    'admin_users': admin_users,
                    'boss_users': boss_users
                }
        except Exception as e:
            print(f"Ошибка при получении расширенной информации о пользователях: {e}")
            return {
                'users': [],
                'total_users': 0,
                'regular_users': 0,
                'admin_users': 0,
                'boss_users': 0
            } 
    
    def get_notes_for_period(self, start_date: datetime, end_date: datetime) -> List[Tuple[int, int, str, str]]:
        """Получение заметок за период"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, id, note_text, created_at 
                    FROM notes 
                    WHERE created_at >= ? AND created_at < ?
                    ORDER BY created_at DESC
                ''', (start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
                return cursor.fetchall()
        except Exception as e:
            print(f"Ошибка получения заметок за период: {e}")
            return []
    
    def get_all_active_users(self) -> List[int]:
        """Получение всех активных пользователей для массовой рассылки"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT ur.user_id
                    FROM user_roles ur
                    LEFT JOIN user_status us ON ur.user_id = us.user_id
                    WHERE (us.is_blocked IS NULL OR us.is_blocked = 0)
                    ORDER BY ur.user_id
                ''')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка получения активных пользователей: {e}")
            return []

    def is_user_active(self, user_id: int) -> bool:
        """Проверка активности пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT is_blocked FROM user_status 
                    WHERE user_id = ?
                """, (user_id,))
                result = cursor.fetchone()
                return not result[0] if result else True  # По умолчанию считаем активным
        except Exception as e:
            print(f"Ошибка при проверке активности пользователя: {e}")
            return True

    def get_user_referral_count(self, user_id: int) -> int:
        """Получение количества рефералов пользователя"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM referrals 
                    WHERE referrer_id = ?
                """, (user_id,))
                return cursor.fetchone()[0]
        except Exception as e:
            print(f"Ошибка при получении количества рефералов: {e}")
            return 0

    def get_user_info(self, user_id: int) -> Optional[dict]:
        """Получение полной информации о пользователе"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT created_at, last_activity FROM user_status 
                    WHERE user_id = ?
                """, (user_id,))
                result = cursor.fetchone()
                
                if result:
                    return {
                        'created_at': result[0],
                        'last_activity': result[1]
                    }
                else:
                    # Если записи нет, создаем базовую информацию
                    self.ensure_user_exists(user_id)
                    from datetime import datetime
                    return {
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'last_activity': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
        except Exception as e:
            print(f"Ошибка при получении информации о пользователе: {e}")
            return None

    def get_user_comprehensive_info(self, user_id: int) -> Optional[dict]:
        """Получение полной информации о пользователе"""
        try:
            print(f"Получение комплексной информации о пользователе {user_id}")
            
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                
                # Сначала убеждаемся, что пользователь существует
                print(f"Проверка существования пользователя {user_id}")
                self.ensure_user_exists(user_id)
                
                # Получаем всю информацию одним запросом с LEFT JOIN
                query = """
                    SELECT 
                        COALESCE(ur.role, 'user') as role,
                        uu.username,
                        us.created_at,
                        us.last_activity,
                        COALESCE(us.is_blocked, 0) as is_blocked,
                        (SELECT COUNT(*) FROM notes WHERE user_id = ?) as notes_count,
                        (SELECT COUNT(*) FROM referrals WHERE referrer_id = ?) as referral_count,
                        r.referrer_id,
                        ru.username as referrer_username
                    FROM (SELECT ? as user_id) as u
                    LEFT JOIN user_roles ur ON u.user_id = ur.user_id
                    LEFT JOIN user_usernames uu ON u.user_id = uu.user_id
                    LEFT JOIN user_status us ON u.user_id = us.user_id
                    LEFT JOIN referrals r ON u.user_id = r.referred_id
                    LEFT JOIN user_usernames ru ON r.referrer_id = ru.user_id
                """
                
                print(f"Выполнение запроса для пользователя {user_id}")
                cursor.execute(query, (user_id, user_id, user_id))
                
                result = cursor.fetchone()
                print(f"Результат запроса для пользователя {user_id}: {result}")
                
                if result:
                    role, username, created_at, last_activity, is_blocked, notes_count, referral_count, referrer_id, referrer_username = result
                    
                    # Вычисляем активность пользователя
                    activity_score = 0
                    if created_at:
                        try:
                            from datetime import datetime
                            created = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                            now = datetime.now()
                            total_days = (now - created).days
                            if total_days > 0:
                                if is_blocked:
                                    activity_score = 10
                                elif last_activity:
                                    last_act = datetime.strptime(last_activity, '%Y-%m-%d %H:%M:%S')
                                    days_since_activity = (now - last_act).days
                                    if days_since_activity <= 1:
                                        activity_score = 95
                                    elif days_since_activity <= 7:
                                        activity_score = 75
                                    elif days_since_activity <= 30:
                                        activity_score = 50
                                    else:
                                        activity_score = 25
                                else:
                                    activity_score = 30
                            else:
                                activity_score = 100  # Новый пользователь
                        except Exception as calc_error:
                            print(f"Ошибка вычисления активности для пользователя {user_id}: {calc_error}")
                            activity_score = 50
                    
                    user_data = {
                        'id': user_id,
                        'username': username or f"user{user_id}",
                        'role': role or 'user',
                        'is_active': not is_blocked if is_blocked is not None else True,
                        'notes_count': notes_count or 0,
                        'referral_count': referral_count or 0,
                        'referrer_id': referrer_id,
                        'referrer_username': referrer_username,
                        'created_at': created_at or 'Неизвестно',
                        'last_activity': last_activity or 'Неизвестно',
                        'activity_score': activity_score
                    }
                    
                    print(f"Возвращаем данные для пользователя {user_id}: {user_data}")
                    return user_data
                else:
                    # Fallback: если основной запрос не вернул результатов, используем простой подход
                    print(f"Основной запрос не вернул результатов для пользователя {user_id}, используем fallback")
                    return self._get_user_info_fallback(user_id)
                    
        except Exception as e:
            print(f"Ошибка при получении комплексной информации о пользователе {user_id}: {e}")
            import traceback
            traceback.print_exc()
            # Fallback в случае ошибки
            return self._get_user_info_fallback(user_id)
    
    def _get_user_info_fallback(self, user_id: int) -> dict:
        """Получение базовой информации о пользователе"""
        try:
            print(f"Использование fallback метода для пользователя {user_id}")
            
            # Убеждаемся, что пользователь существует
            self.ensure_user_exists(user_id)
            
            # Получаем базовую информацию по частям
            role = self.get_user_role(user_id)
            username = self.get_username_by_id(user_id)
            is_active = self.is_user_active(user_id)
            notes_count = len(self.get_user_notes(user_id))
            referral_count = self.get_user_referral_count(user_id)
            referrer_info = self.get_referrer_info(user_id)
            user_info = self.get_user_info(user_id)
            
            from datetime import datetime
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            user_data = {
                'id': user_id,
                'username': username or f"user{user_id}",
                'role': role or 'user',
                'is_active': is_active,
                'notes_count': notes_count,
                'referral_count': referral_count,
                'referrer_id': referrer_info[0] if referrer_info else None,
                'referrer_username': referrer_info[1] if referrer_info else None,
                'created_at': user_info.get('created_at', now) if user_info else now,
                'last_activity': user_info.get('last_activity', now) if user_info else now,
                'activity_score': 75  # Базовый показатель активности
            }
            
            print(f"Fallback данные для пользователя {user_id}: {user_data}")
            return user_data
            
        except Exception as e:
            print(f"Ошибка в fallback методе для пользователя {user_id}: {e}")
            # Возвращаем минимальные данные
            from datetime import datetime
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            return {
                'id': user_id,
                'username': f"user{user_id}",
                'role': 'user',
                'is_active': True,
                'notes_count': 0,
                'referral_count': 0,
                'referrer_id': None,
                'referrer_username': None,
                'created_at': now,
                'last_activity': now,
                'activity_score': 50
            }