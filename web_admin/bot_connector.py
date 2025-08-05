"""
Модуль для связи веб-панели с Telegram ботом
"""

import os
import sys
import json
import asyncio
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any

# Добавляем родительскую папку в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Database
from config import BOT_TOKEN, ADMIN_ID

class BotConnector:
    """Класс для связи с ботом"""
    
    def __init__(self):
        self.db = Database()
        self.bot_status = "unknown"
        self.bot_process = None
        self.bot_thread = None
        self.is_running = False
        self.last_activity = None
        self.start_time = None
        self._check_external_stops()
    
    def _check_external_stops(self):
        """Проверка внешних остановок бота"""
        try:
            if self.is_running and self.bot_thread and not self.bot_thread.is_alive():
                self.is_running = False
                self.db.stop_bot()
                self.db.add_bot_event("EXTERNAL_STOP_DETECTED", 
                                    "Обнаружена внешняя остановка бота", 
                                    ADMIN_ID, "warning")
            
            if self.is_running and self.db.is_bot_stopped():
                self.is_running = False
                self.start_time = None
                self.bot_thread = None
                self.db.add_bot_event("STATUS_SYNC", 
                                    "Синхронизация статуса бота", 
                                    ADMIN_ID, "info")
        except Exception as e:
            print(f"Ошибка проверки внешних остановок: {e}")
        
    def get_bot_status(self) -> str:
        """Получение статуса бота"""
        try:
            db_stopped = self.db.is_bot_stopped()
            
            if self.is_running and (not self.bot_thread or (self.bot_thread and not self.bot_thread.is_alive())):
                self.is_running = False
                self.db.stop_bot()
                return "stopped"
            
            if not self.is_running and not db_stopped:
                self.is_running = True
                return "running"
            
            if self.is_running and not db_stopped:
                return "running"
            else:
                return "stopped"
                
        except Exception as e:
            print(f"Ошибка получения статуса бота: {e}")
            return "unknown"
    
    def start_bot(self) -> Dict[str, Any]:
        """Запуск бота"""
        try:
            current_status = self.get_bot_status()
            if current_status == "running":
                return {
                    "success": False,
                    "message": "Бот уже запущен",
                    "status": "running"
                }
            
            self.db.add_bot_event("WEB_START_BOT", "Бот запущен через веб-панель", 
                                ADMIN_ID, "info")
            
            self.bot_thread = threading.Thread(target=self._run_bot)
            self.bot_thread.daemon = True
            self.bot_thread.start()
            self.is_running = True
            self.start_time = datetime.now()
            self.db.start_bot()
            
            time.sleep(1)
            
            return {
                "success": True,
                "message": "Бот успешно запущен",
                "status": "running"
            }
                
        except Exception as e:
            self.db.add_bot_event("WEB_START_BOT_FAILED", f"Ошибка запуска бота: {e}", 
                                ADMIN_ID, "error")
            return {
                "success": False,
                "message": f"Ошибка запуска бота: {e}",
                "status": "error"
            }
    
    def stop_bot(self) -> Dict[str, Any]:
        """Остановка бота"""
        try:
            self.db.add_bot_event("WEB_STOP_BOT", "Бот остановлен через веб-панель", 
                                ADMIN_ID, "warning")
            
            self.is_running = False
            
            # Устанавливаем флаг остановки в базе данных
            self.db.stop_bot()
            
            # Устанавливаем событие остановки в боте
            try:
                from bot import stop_bot
                stop_bot()
            except Exception as e:
                print(f"Ошибка установки события остановки бота: {e}")
            
            self.start_time = None
            self.bot_thread = None
            
            self._check_external_stops()
            
            return {
                "success": True,
                "message": "Бот успешно остановлен",
                "status": "stopped"
            }
                
        except Exception as e:
            self.db.add_bot_event("WEB_STOP_BOT_FAILED", f"Ошибка остановки бота: {e}", 
                                ADMIN_ID, "error")
            return {
                "success": False,
                "message": f"Ошибка остановки бота: {e}",
                "status": "error"
            }
    
    def _run_bot(self):
        """Запуск бота в отдельном потоке"""
        try:
            from bot import main
            asyncio.run(main())
        except Exception as e:
            self.db.add_bot_event("BOT_RUNTIME_ERROR", f"Ошибка выполнения бота: {e}", 
                                ADMIN_ID, "critical")
            self.is_running = False
            self.db.stop_bot()
            self.start_time = None
            self.bot_thread = None
    
    def get_bot_info(self) -> Dict[str, Any]:
        """Получение информации о боте"""
        try:
            self._check_external_stops()
            
            status = self.get_bot_status()
            uptime = None
            
            if self.start_time and status == "running":
                uptime = datetime.now() - self.start_time
                uptime_str = str(uptime).split('.')[0]
            else:
                uptime_str = "Неизвестно"
            
            return {
                "status": status,
                "uptime": uptime_str,
                "is_running": self.is_running,
                "last_activity": self.last_activity,
                "start_time": self.start_time.isoformat() if self.start_time else None
            }
        except Exception as e:
            return {
                "status": "error",
                "uptime": "Ошибка",
                "is_running": False,
                "last_activity": None,
                "start_time": None,
                "error": str(e)
            }
    
    def send_message_to_user(self, user_id: int, message: str) -> Dict[str, Any]:
        """Отправка сообщения пользователю через бота"""
        try:
            bot_status = self.get_bot_status()
            if bot_status != "running":
                return {
                    "success": False,
                    "message": "Бот не запущен. Запустите бота перед отправкой сообщений."
                }
            
            import asyncio
            from aiogram import Bot
            from config import BOT_TOKEN
            
            async def send_message():
                bot = Bot(token=BOT_TOKEN)
                try:
                    await bot.send_message(user_id, message)
                    await bot.session.close()
                    return True
                except Exception as e:
                    await bot.session.close()
                    raise e
            
            asyncio.run(send_message())
            
            self.db.add_bot_event("WEB_SEND_MESSAGE", f"Отправлено сообщение пользователю {user_id}: {message[:50]}...", 
                                ADMIN_ID, "info")
            
            return {
                "success": True,
                "message": f"Сообщение отправлено пользователю {user_id}"
            }
        except Exception as e:
            self.db.add_bot_event("WEB_SEND_MESSAGE_FAILED", f"Ошибка отправки сообщения пользователю {user_id}: {e}", 
                                ADMIN_ID, "error")
            return {
                "success": False,
                "message": f"Ошибка отправки сообщения: {e}"
            }
    
    def send_message_to_all_users(self, message: str) -> Dict[str, Any]:
        """Отправка сообщения всем пользователям"""
        try:
            bot_status = self.get_bot_status()
            if bot_status != "running":
                return {
                    "success": False,
                    "message": "Бот не запущен. Запустите бота перед отправкой сообщений."
                }
            
            users = self.db.get_all_active_users()
            if not users:
                return {
                    "success": False,
                    "message": "Нет активных пользователей для отправки сообщения"
                }
            
            import asyncio
            from aiogram import Bot
            from config import BOT_TOKEN
            
            async def send_message_to_all():
                bot = Bot(token=BOT_TOKEN)
                success_count = 0
                error_count = 0
                
                try:
                    for user_id in users:
                        try:
                            await bot.send_message(user_id, message)
                            success_count += 1
                        except Exception as e:
                            error_count += 1
                            print(f"Ошибка отправки пользователю {user_id}: {e}")
                    
                    await bot.session.close()
                    return success_count, error_count
                except Exception as e:
                    await bot.session.close()
                    raise e
            
            success_count, error_count = asyncio.run(send_message_to_all())
            
            self.db.add_bot_event("WEB_SEND_MESSAGE_ALL", 
                                f"Отправлено сообщение всем пользователям. Успешно: {success_count}, Ошибок: {error_count}", 
                                ADMIN_ID, "info")
            
            return {
                "success": True,
                "message": f"Сообщение отправлено {success_count} пользователям. Ошибок: {error_count}",
                "success_count": success_count,
                "error_count": error_count
            }
        except Exception as e:
            self.db.add_bot_event("WEB_SEND_MESSAGE_ALL_FAILED", f"Ошибка массовой отправки сообщений: {e}", 
                                ADMIN_ID, "error")
            return {
                "success": False,
                "message": f"Ошибка массовой отправки сообщений: {e}"
            }
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """Получение статистики в реальном времени"""
        try:
            users_info = self.db.get_users_debug_info()
            events_stats = self.db.get_events_stats()
            referrals_stats = self.db.get_referrals_debug_info()
            
            bot_info = self.get_bot_info()
            
            return {
                "users": {
                    "total": users_info.get('total_users', 0),
                    "regular": users_info.get('regular_users', 0),
                    "admin": users_info.get('admin_users', 0),
                    "boss": users_info.get('boss_users', 0)
                },
                "events": {
                    "total": events_stats.get('total_events', 0),
                    "last_24h": events_stats.get('events_24h', 0)
                },
                "referrals": {
                    "total": referrals_stats.get('total_referrals', 0),
                    "unique_referrers": referrals_stats.get('unique_referrers', 0)
                },
                "bot": bot_info,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Глобальный экземпляр коннектора
bot_connector = BotConnector() 