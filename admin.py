import os
import shutil
import logging
from datetime import datetime
from typing import List, Tuple, Optional
from config import ADMIN_ID, DATABASE_NAME, LOG_FILE
from database import Database

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class AdminPanel:
    def __init__(self):
        self.db = Database()
        self.bot_stopped = False
        self.logger = logging.getLogger(__name__)
    
    def is_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        # Главный админ
        if user_id == ADMIN_ID:
            return True
        
        # Роль в БД
        role = self.db.get_user_role(user_id)
        return role == 'admin'
    
    def is_main_admin(self, user_id: int) -> bool:
        """Проверка, является ли пользователь главным администратором"""
        return user_id == ADMIN_ID
    
    def grant_admin_role(self, target_user_id: int, granted_by: int) -> Tuple[bool, str]:
        """Выдача роли админа пользователю (только главный админ)"""
        if not self.is_main_admin(granted_by):
            return False, "Доступ запрещен. Только главный администратор может выдавать роли."
        
        if target_user_id == ADMIN_ID:
            return False, "Нельзя изменить роль главного администратора."
        
        if self.is_admin(target_user_id):
            return False, "Пользователь уже является администратором."
        
        success = self.db.add_user_role(target_user_id, 'admin', granted_by)
        if success:
            self.log_admin_action(granted_by, "GRANT_ADMIN_ROLE", f"Granted admin role to user {target_user_id}")
            return True, f"Роль администратора выдана пользователю {target_user_id}."
        else:
            return False, "Ошибка при выдаче роли администратора."
    
    def revoke_admin_role(self, target_user_id: int, revoked_by: int) -> Tuple[bool, str]:
        """Снятие роли админа с пользователя (только главный админ)"""
        if not self.is_main_admin(revoked_by):
            return False, "Доступ запрещен. Только главный администратор может снимать роли."
        
        if target_user_id == ADMIN_ID:
            return False, "Нельзя снять роль с главного администратора."
        
        if not self.is_admin(target_user_id):
            return False, "Пользователь не является администратором."
        
        success = self.db.remove_user_role(target_user_id)
        if success:
            self.log_admin_action(revoked_by, "REVOKE_ADMIN_ROLE", f"Revoked admin role from user {target_user_id}")
            return True, f"Роль администратора снята с пользователя {target_user_id}."
        else:
            return False, "Ошибка при снятии роли администратора."
    
    def get_admins_list(self, requested_by: int) -> Tuple[bool, str, Optional[List[Tuple[int, str]]]]:
        """Получение списка всех администраторов"""
        if not self.is_admin(requested_by):
            return False, "Доступ запрещен. Только администратор может выполнить эту команду.", None
        
        try:
            admins = self.db.get_all_admins()
            admins_list = []
            
            # Главный админ
            admins_list.append((ADMIN_ID, "Главный администратор"))
            
            # Остальные админы
            for admin_id in admins:
                if admin_id != ADMIN_ID:
                    admins_list.append((admin_id, "Администратор"))
            
            self.log_admin_action(requested_by, "GET_ADMINS_LIST", f"Found {len(admins_list)} admins")
            return True, f"Найдено администраторов: {len(admins_list)}", admins_list
            
        except Exception as e:
            error_msg = f"Ошибка при получении списка администраторов: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def log_admin_action(self, admin_id: int, action: str, details: str = ""):
        """Логирование действий администратора"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[ADMIN] {timestamp} - User {admin_id}: {action}"
        if details:
            log_message += f" - {details}"
        
        self.logger.info(log_message)
    
    def stop_bot(self, admin_id: int) -> Tuple[bool, str]:
        """Остановка бота (только для админа)"""
        if not self.is_admin(admin_id):
            return False, "Доступ запрещен. Только администратор может выполнить эту команду."
        
        if self.bot_stopped:
            return False, "Бот уже остановлен."
        
        self.bot_stopped = True
        self.log_admin_action(admin_id, "STOP_BOT")
        return True, "Бот остановлен. Только администратор может использовать бота."
    
    def start_bot(self, admin_id: int) -> Tuple[bool, str]:
        """Запуск бота"""
        if not self.is_admin(admin_id):
            return False, "Доступ запрещен. Только администратор может выполнить эту команду."
        
        if not self.bot_stopped:
            return False, "Бот уже работает."
        
        self.bot_stopped = False
        self.log_admin_action(admin_id, "START_BOT")
        return True, "Бот запущен. Все пользователи могут использовать бота."
    
    def get_users_list(self, admin_id: int) -> Tuple[bool, str, Optional[List[Tuple[int, int]]]]:
        """Получение списка всех пользователей и количества их заметок"""
        if not self.is_admin(admin_id):
            return False, "Доступ запрещен. Только администратор может выполнить эту команду.", None
        
        try:
            users_data = self.db.get_all_users_with_notes_count()
            self.log_admin_action(admin_id, "GET_USERS_LIST", f"Found {len(users_data)} users")
            return True, f"Найдено пользователей: {len(users_data)}", users_data
            
        except Exception as e:
            error_msg = f"Ошибка при получении списка пользователей: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def get_users_list_separated(self, admin_id: int) -> Tuple[bool, str, Optional[Tuple[List[Tuple[int, int]], List[Tuple[int, int]]]]]:
        """Получение списка пользователей с разделением на админов и обычных пользователей"""
        if not self.is_admin(admin_id):
            return False, "Доступ запрещен. Только администратор может выполнить эту команду.", None
        
        try:
            admins, regular_users = self.db.get_users_with_admin_separation(admin_id)
            total_users = len(admins) + len(regular_users)
            self.log_admin_action(admin_id, "GET_USERS_LIST_SEPARATED", f"Found {total_users} users ({len(admins)} admins, {len(regular_users)} regular)")
            return True, f"Найдено пользователей: {total_users}", (admins, regular_users)
            
        except Exception as e:
            error_msg = f"Ошибка при получении списка пользователей: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def get_users_list_paginated(self, admin_id: int, page: int = 1, per_page: int = 10) -> Tuple[bool, str, Optional[dict]]:
        """Получение списка пользователей с пагинацией"""
        if not self.is_admin(admin_id):
            return False, "Доступ запрещен. Только администратор может выполнить эту команду.", None
        
        try:
            admins, regular_users = self.db.get_users_with_admin_separation(admin_id)
            
            # Объединение пользователей
            all_users = []
            
            # Главный админ
            main_admin_found = False
            for user_id, notes_count in admins:
                if user_id == admin_id:
                    all_users.append((user_id, notes_count, "main_admin"))
                    main_admin_found = True
                    break
            
            # Остальные админы
            for user_id, notes_count in admins:
                if user_id != admin_id:
                    all_users.append((user_id, notes_count, "admin"))
            
            # Обычные пользователи
            for user_id, notes_count in regular_users:
                all_users.append((user_id, notes_count, "user"))
            
            # Главный админ
            if not main_admin_found:
                # Количество заметок
                main_admin_notes = 0
                for user_id, notes_count in admins + regular_users:
                    if user_id == admin_id:
                        main_admin_notes = notes_count
                        break
                all_users.insert(0, (admin_id, main_admin_notes, "main_admin"))
            
            # Пагинация
            total_users = len(all_users)
            total_pages = (total_users + per_page - 1) // per_page
            
            if page < 1:
                page = 1
            elif page > total_pages:
                page = total_pages
            
            start_idx = (page - 1) * per_page
            end_idx = start_idx + per_page
            page_users = all_users[start_idx:end_idx]
            
            result_data = {
                'users': page_users,
                'page': page,
                'total_pages': total_pages,
                'total_users': total_users,
                'has_prev': page > 1,
                'has_next': page < total_pages
            }
            
            self.log_admin_action(admin_id, "GET_USERS_LIST_PAGINATED", f"Page {page}/{total_pages}, {len(page_users)} users")
            return True, f"Страница {page} из {total_pages} (всего пользователей: {total_users})", result_data
            
        except Exception as e:
            error_msg = f"Ошибка при получении списка пользователей: {e}"
            self.logger.error(error_msg)
            return False, error_msg, None
    
    def is_bot_stopped(self) -> bool:
        """Проверка, остановлен ли бот"""
        return self.bot_stopped
    
    def get_admin_id(self) -> int:
        """Получение ID администратора"""
        return ADMIN_ID 