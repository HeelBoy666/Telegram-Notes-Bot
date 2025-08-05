"""
Система уведомлений для веб-панели
"""

import os
import json
import smtplib
import requests
from datetime import datetime
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class NotificationSystem:
    """Система уведомлений"""
    
    def __init__(self):
        self.config = self.load_config()
        self.notifications_queue = []
        
    def load_config(self) -> Dict[str, Any]:
        """Загрузка конфигурации уведомлений"""
        config_path = os.path.join(os.path.dirname(__file__), 'notification_config.json')
        
        default_config = {
            'email': {
                'enabled': False,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': '',
                'password': '',
                'from_email': '',
                'to_emails': []
            },
            'telegram': {
                'enabled': False,
                'bot_token': '',
                'chat_ids': []
            },
            'webhook': {
                'enabled': False,
                'url': '',
                'headers': {}
            },
            'notifications': {
                'critical_events': True,
                'admin_actions': True,
                'system_alerts': True,
                'user_activity': False
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return default_config
        except Exception as e:
            print(f"Ошибка загрузки конфигурации уведомлений: {e}")
            return default_config
    
    def save_config(self):
        """Сохранение конфигурации"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'notification_config.json')
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Ошибка сохранения конфигурации: {e}")
            return False
    
    def send_notification(self, title: str, message: str, notification_type: str = 'info', 
                         priority: str = 'normal', channels: List[str] = None) -> bool:
        """Отправка уведомления"""
        if channels is None:
            channels = ['email', 'telegram', 'webhook']
        
        success = True
        
        if 'email' in channels and self.config['email']['enabled']:
            if not self.send_email_notification(title, message, notification_type, priority):
                success = False
        
        if 'telegram' in channels and self.config['telegram']['enabled']:
            if not self.send_telegram_notification(title, message, notification_type, priority):
                success = False
        
        if 'webhook' in channels and self.config['webhook']['enabled']:
            if not self.send_webhook_notification(title, message, notification_type, priority):
                success = False
        
        self.notifications_queue.append({
            'title': title,
            'message': message,
            'type': notification_type,
            'priority': priority,
            'timestamp': datetime.now().isoformat(),
            'success': success
        })
        
        if len(self.notifications_queue) > 100:
            self.notifications_queue = self.notifications_queue[-50:]
        
        return success
    
    def send_email_notification(self, title: str, message: str, notification_type: str, priority: str) -> bool:
        """Отправка email уведомления"""
        try:
            email_config = self.config['email']
            
            if not email_config['enabled'] or not email_config['to_emails']:
                return False
            
            msg = MIMEMultipart()
            msg['From'] = email_config['from_email']
            msg['To'] = ', '.join(email_config['to_emails'])
            msg['Subject'] = f"[{priority.upper()}] {title}"
            
            body = f"""
            <html>
            <body>
                <h2>{title}</h2>
                <p><strong>Тип:</strong> {notification_type}</p>
                <p><strong>Приоритет:</strong> {priority}</p>
                <p><strong>Время:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <hr>
                <p>{message}</p>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            with smtplib.SMTP(email_config['smtp_server'], email_config['smtp_port']) as server:
                server.starttls()
                server.login(email_config['username'], email_config['password'])
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Ошибка отправки email уведомления: {e}")
            return False
    
    def send_telegram_notification(self, title: str, message: str, notification_type: str, priority: str) -> bool:
        """Отправка Telegram уведомления"""
        try:
            telegram_config = self.config['telegram']
            
            if not telegram_config['enabled'] or not telegram_config['chat_ids']:
                return False
            
            emoji_map = {
                'info': 'ℹ️',
                'warning': '⚠️',
                'error': '❌',
                'critical': '🚨',
                'success': '✅'
            }
            
            emoji = emoji_map.get(notification_type, '📢')
            priority_emoji = '🔴' if priority == 'high' else '🟡' if priority == 'medium' else '🟢'
            
            text = f"""
{emoji} <b>{title}</b>

<b>Тип:</b> {notification_type}
<b>Приоритет:</b> {priority_emoji} {priority}
<b>Время:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{message}
            """.strip()
            
            for chat_id in telegram_config['chat_ids']:
                try:
                    url = f"https://api.telegram.org/bot{telegram_config['bot_token']}/sendMessage"
                    data = {
                        'chat_id': chat_id,
                        'text': text,
                        'parse_mode': 'HTML'
                    }
                    
                    response = requests.post(url, data=data, timeout=10)
                    if not response.ok:
                        print(f"Ошибка отправки в Telegram чат {chat_id}: {response.text}")
                        
                except Exception as e:
                    print(f"Ошибка отправки в Telegram чат {chat_id}: {e}")
            
            return True
            
        except Exception as e:
            print(f"Ошибка отправки Telegram уведомления: {e}")
            return False
    
    def send_webhook_notification(self, title: str, message: str, notification_type: str, priority: str) -> bool:
        """Отправка webhook уведомления"""
        try:
            webhook_config = self.config['webhook']
            
            if not webhook_config['enabled'] or not webhook_config['url']:
                return False
            
            payload = {
                'title': title,
                'message': message,
                'type': notification_type,
                'priority': priority,
                'timestamp': datetime.now().isoformat(),
                'source': 'web_admin_panel'
            }
            
            response = requests.post(
                webhook_config['url'],
                json=payload,
                headers=webhook_config.get('headers', {}),
                timeout=10
            )
            
            if not response.ok:
                print(f"Ошибка отправки webhook: {response.status_code} - {response.text}")
                return False
            
            return True
            
        except Exception as e:
            print(f"Ошибка отправки webhook уведомления: {e}")
            return False
    
    def notify_critical_event(self, event_type: str, description: str, user_id: Optional[int] = None):
        """Уведомление о критическом событии"""
        if not self.config['notifications']['critical_events']:
            return
        
        title = f"Критическое событие: {event_type}"
        message = f"Описание: {description}"
        if user_id:
            message += f"\nПользователь: {user_id}"
        
        self.send_notification(title, message, 'critical', 'high')
    
    def notify_admin_action(self, action: str, description: str, admin_id: int):
        """Уведомление о действии администратора"""
        if not self.config['notifications']['admin_actions']:
            return
        
        title = f"Действие администратора: {action}"
        message = f"Описание: {description}\nАдминистратор: {admin_id}"
        
        self.send_notification(title, message, 'info', 'medium')
    
    def notify_system_alert(self, alert_type: str, message: str, severity: str = 'warning'):
        """Уведомление о системном алерте"""
        if not self.config['notifications']['system_alerts']:
            return
        
        title = f"Системный алерт: {alert_type}"
        priority = 'high' if severity in ['critical', 'error'] else 'medium'
        
        self.send_notification(title, message, severity, priority)
    
    def get_notifications_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение истории уведомлений"""
        return self.notifications_queue[-limit:] if self.notifications_queue else []
    
    def test_notification(self, channel: str) -> bool:
        """Тестирование уведомлений"""
        title = "Тестовое уведомление"
        message = f"Это тестовое уведомление для проверки работы канала {channel}"
        
        return self.send_notification(title, message, 'info', 'normal', [channel])

# Глобальный экземпляр системы уведомлений
notification_system = NotificationSystem() 