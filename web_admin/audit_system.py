"""
Система логирования и аудита для веб-панели
"""

import os
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class AuditLog:
    """Запись аудита"""
    timestamp: str
    user_id: int
    username: str
    action: str
    resource: str
    resource_id: Optional[str]
    details: Dict[str, Any]
    ip_address: str
    user_agent: str
    success: bool
    duration_ms: int

class AuditSystem:
    """Система аудита"""
    
    def __init__(self, db_connection):
        self.db = db_connection
        self.setup_logging()
        
    def setup_logging(self):
        """Настройка логирования"""
        # Создаем директорию для логов
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        # Настраиваем логирование
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'audit.log'), encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('audit_system')
    
    def log_action(self, user_id: int, username: str, action: str, resource: str, 
                   resource_id: Optional[str] = None, details: Dict[str, Any] = None,
                   ip_address: str = '', user_agent: str = '', success: bool = True,
                   duration_ms: int = 0):
        """Логирование действия пользователя"""
        try:
            audit_log = AuditLog(
                timestamp=datetime.now().isoformat(),
                user_id=user_id,
                username=username,
                action=action,
                resource=resource,
                resource_id=resource_id,
                details=details or {},
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                duration_ms=duration_ms
            )
            
            # Сохраняем в базу данных
            self.save_to_database(audit_log)
            
            # Логируем в файл
            self.logger.info(f"AUDIT: {audit_log.username} ({audit_log.user_id}) - {action} {resource} {resource_id or ''} - {'SUCCESS' if success else 'FAILED'}")
            
            return True
        except Exception as e:
            self.logger.error(f"Ошибка логирования аудита: {e}")
            return False
    
    def save_to_database(self, audit_log: AuditLog):
        """Сохранение записи аудита в базу данных"""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO audit_logs (
                        timestamp, user_id, username, action, resource, resource_id,
                        details, ip_address, user_agent, success, duration_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    audit_log.timestamp,
                    audit_log.user_id,
                    audit_log.username,
                    audit_log.action,
                    audit_log.resource,
                    audit_log.resource_id,
                    json.dumps(audit_log.details),
                    audit_log.ip_address,
                    audit_log.user_agent,
                    audit_log.success,
                    audit_log.duration_ms
                ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Ошибка сохранения в БД: {e}")
    
    def get_audit_logs(self, user_id: Optional[int] = None, action: Optional[str] = None,
                      resource: Optional[str] = None, start_date: Optional[str] = None,
                      end_date: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Получение записей аудита с фильтрацией"""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                
                query = '''
                    SELECT timestamp, user_id, username, action, resource, resource_id,
                           details, ip_address, user_agent, success, duration_ms
                    FROM audit_logs
                    WHERE 1=1
                '''
                params = []
                
                if user_id:
                    query += ' AND user_id = ?'
                    params.append(user_id)
                
                if action:
                    query += ' AND action = ?'
                    params.append(action)
                
                if resource:
                    query += ' AND resource = ?'
                    params.append(resource)
                
                if start_date:
                    query += ' AND timestamp >= ?'
                    params.append(start_date)
                
                if end_date:
                    query += ' AND timestamp <= ?'
                    params.append(end_date)
                
                query += ' ORDER BY timestamp DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                logs = []
                for row in rows:
                    try:
                        details = json.loads(row[6]) if row[6] else {}
                    except:
                        details = {}
                    
                    logs.append({
                        'timestamp': row[0],
                        'user_id': row[1],
                        'username': row[2],
                        'action': row[3],
                        'resource': row[4],
                        'resource_id': row[5],
                        'details': details,
                        'ip_address': row[7],
                        'user_agent': row[8],
                        'success': bool(row[9]),
                        'duration_ms': row[10]
                    })
                
                return logs
        except Exception as e:
            self.logger.error(f"Ошибка получения записей аудита: {e}")
            return []
    
    def get_audit_stats(self, days: int = 30) -> Dict[str, Any]:
        """Получение статистики аудита"""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                
                start_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                # Общее количество действий
                cursor.execute('''
                    SELECT COUNT(*) FROM audit_logs WHERE timestamp >= ?
                ''', (start_date,))
                total_actions = cursor.fetchone()[0]
                
                # Успешные действия
                cursor.execute('''
                    SELECT COUNT(*) FROM audit_logs WHERE timestamp >= ? AND success = 1
                ''', (start_date,))
                successful_actions = cursor.fetchone()[0]
                
                # Неуспешные действия
                cursor.execute('''
                    SELECT COUNT(*) FROM audit_logs WHERE timestamp >= ? AND success = 0
                ''', (start_date,))
                failed_actions = cursor.fetchone()[0]
                
                # Топ действий
                cursor.execute('''
                    SELECT action, COUNT(*) as count
                    FROM audit_logs WHERE timestamp >= ?
                    GROUP BY action ORDER BY count DESC LIMIT 10
                ''', (start_date,))
                top_actions = cursor.fetchall()
                
                # Топ пользователей
                cursor.execute('''
                    SELECT username, COUNT(*) as count
                    FROM audit_logs WHERE timestamp >= ?
                    GROUP BY username ORDER BY count DESC LIMIT 10
                ''', (start_date,))
                top_users = cursor.fetchall()
                
                # Среднее время выполнения
                cursor.execute('''
                    SELECT AVG(duration_ms) FROM audit_logs 
                    WHERE timestamp >= ? AND duration_ms > 0
                ''', (start_date,))
                avg_duration = cursor.fetchone()[0] or 0
                
                return {
                    'total_actions': total_actions,
                    'successful_actions': successful_actions,
                    'failed_actions': failed_actions,
                    'success_rate': (successful_actions / total_actions * 100) if total_actions > 0 else 0,
                    'top_actions': [{'action': action, 'count': count} for action, count in top_actions],
                    'top_users': [{'username': username, 'count': count} for username, count in top_users],
                    'avg_duration_ms': round(avg_duration, 2)
                }
        except Exception as e:
            self.logger.error(f"Ошибка получения статистики аудита: {e}")
            return {}
    
    def export_audit_logs(self, format: str = 'json', **filters) -> str:
        """Экспорт записей аудита"""
        try:
            logs = self.get_audit_logs(**filters)
            
            if format == 'json':
                return json.dumps(logs, indent=2, ensure_ascii=False)
            elif format == 'csv':
                import csv
                from io import StringIO
                
                output = StringIO()
                writer = csv.DictWriter(output, fieldnames=[
                    'timestamp', 'user_id', 'username', 'action', 'resource', 
                    'resource_id', 'ip_address', 'success', 'duration_ms'
                ])
                
                writer.writeheader()
                for log in logs:
                    writer.writerow({
                        'timestamp': log['timestamp'],
                        'user_id': log['user_id'],
                        'username': log['username'],
                        'action': log['action'],
                        'resource': log['resource'],
                        'resource_id': log['resource_id'] or '',
                        'ip_address': log['ip_address'],
                        'success': 'Yes' if log['success'] else 'No',
                        'duration_ms': log['duration_ms']
                    })
                
                return output.getvalue()
            else:
                raise ValueError(f"Неподдерживаемый формат: {format}")
                
        except Exception as e:
            self.logger.error(f"Ошибка экспорта аудита: {e}")
            return ""
    
    def cleanup_old_logs(self, days: int = 90):
        """Очистка старых записей аудита"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with self.db.connect() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    DELETE FROM audit_logs WHERE timestamp < ?
                ''', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                conn.commit()
                
                self.logger.info(f"Удалено {deleted_count} старых записей аудита")
                return deleted_count
                
        except Exception as e:
            self.logger.error(f"Ошибка очистки старых записей: {e}")
            return 0
    
    def detect_suspicious_activity(self, user_id: int, hours: int = 24) -> List[Dict[str, Any]]:
        """Обнаружение подозрительной активности"""
        try:
            with self.db.connect() as conn:
                cursor = conn.cursor()
                
                start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
                
                # Получаем все действия пользователя за указанный период
                cursor.execute('''
                    SELECT action, resource, success, timestamp, ip_address
                    FROM audit_logs 
                    WHERE user_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                ''', (user_id, start_time))
                
                actions = cursor.fetchall()
                
                suspicious_activities = []
                
                # Проверяем количество неуспешных попыток входа
                failed_logins = [a for a in actions if a[0] == 'LOGIN' and not a[2]]
                if len(failed_logins) >= 5:
                    suspicious_activities.append({
                        'type': 'multiple_failed_logins',
                        'description': f'Множественные неуспешные попытки входа: {len(failed_logins)}',
                        'severity': 'high',
                        'actions': failed_logins
                    })
                
                # Проверяем необычную активность (много действий за короткое время)
                if len(actions) > 100:
                    suspicious_activities.append({
                        'type': 'high_activity',
                        'description': f'Высокая активность: {len(actions)} действий за {hours} часов',
                        'severity': 'medium',
                        'actions': actions[:10]  # Показываем только первые 10
                    })
                
                # Проверяем действия с разных IP адресов
                unique_ips = set(a[4] for a in actions if a[4])
                if len(unique_ips) > 3:
                    suspicious_activities.append({
                        'type': 'multiple_ips',
                        'description': f'Действия с разных IP адресов: {len(unique_ips)}',
                        'severity': 'medium',
                        'ips': list(unique_ips)
                    })
                
                return suspicious_activities
                
        except Exception as e:
            self.logger.error(f"Ошибка обнаружения подозрительной активности: {e}")
            return []

# Глобальный экземпляр системы аудита
audit_system = None

def init_audit_system(db_connection):
    """Инициализация системы аудита"""
    global audit_system
    audit_system = AuditSystem(db_connection)
    return audit_system 