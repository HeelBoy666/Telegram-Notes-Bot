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
            
            conn.commit()
    
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
                
                # Обновление
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
        """Получение списка всех админов"""
        try:
            with sqlite3.connect(self.db_name) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT user_id FROM user_roles WHERE role = "admin"')
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении списка админов: {e}")
            return [] 