#!/usr/bin/env python3
"""
X1 监控日志模块
记录操作日志、错误日志、性能指标
"""

import time
import traceback
from datetime import datetime
from functools import wraps
from database import get_db


def log_action(username, action, target='', detail=''):
    """记录操作日志"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO action_logs (time, user, action, target, detail)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                username,
                action,
                target,
                detail
            ))
    except Exception:
        pass


def log_error(error_type, error_msg, context=''):
    """记录错误日志"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO error_logs (time, type, message, context, traceback)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                error_type,
                error_msg,
                context,
                traceback.format_exc()
            ))
    except Exception:
        pass


def log_performance(operation, duration, details=''):
    """记录性能指标"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO performance_logs (time, operation, duration, details)
                VALUES (?, ?, ?, ?)
            ''', (
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                operation,
                round(duration, 3),
                details
            ))
    except Exception:
        pass


def monitor_performance(operation_name):
    """装饰器：监控函数性能"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                duration = time.time() - start_time
                log_performance(operation_name, duration, f'success')
                return result
            except Exception as e:
                duration = time.time() - start_time
                log_performance(operation_name, duration, f'error: {str(e)}')
                log_error(operation_name, str(e), f'args={args}, kwargs={kwargs}')
                raise
        return decorated_function
    return decorator


def get_error_logs(limit=50):
    """获取最近的错误日志"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM error_logs 
            ORDER BY id DESC 
            LIMIT ?
        ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]


def get_performance_stats(operation=None, hours=24):
    """获取性能统计"""
    cutoff_time = datetime.now().timestamp() - hours * 3600
    cutoff_str = datetime.fromtimestamp(cutoff_time).strftime('%Y-%m-%d %H:%M:%S')
    
    with get_db() as conn:
        cursor = conn.cursor()
        if operation:
            cursor.execute('''
                SELECT duration FROM performance_logs 
                WHERE time >= ? AND operation = ?
            ''', (cutoff_str, operation))
        else:
            cursor.execute('''
                SELECT duration FROM performance_logs 
                WHERE time >= ?
            ''', (cutoff_str,))
        
        durations = [row[0] for row in cursor.fetchall()]
        
        if not durations:
            return {}
        
        return {
            'count': len(durations),
            'avg': round(sum(durations) / len(durations), 3),
            'min': round(min(durations), 3),
            'max': round(max(durations), 3),
            'total': round(sum(durations), 3)
        }


def get_system_health():
    """获取系统健康状态"""
    with get_db() as conn:
        cursor = conn.cursor()
        cutoff_time = (datetime.now().timestamp() - 3600)
        cutoff_str = datetime.fromtimestamp(cutoff_time).strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute('''
            SELECT COUNT(*) FROM error_logs 
            WHERE time >= ?
        ''', (cutoff_str,))
        recent_errors = cursor.fetchone()[0]
    
    return {
        'status': 'healthy' if recent_errors == 0 else 'warning' if recent_errors < 5 else 'critical',
        'recent_errors': recent_errors,
        'uptime': 'N/A'
    }


def clear_error_logs():
    """清空错误日志"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM error_logs')
