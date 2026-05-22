#!/usr/bin/env python3
"""
X1 数据库模块 - SQLite
统一管理用户、日志、记录数据
"""

import sqlite3
import json
import os
import secrets
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager
from werkzeug.security import generate_password_hash

BASE_DIR = Path(__file__).parent
DB_FILE = BASE_DIR / 'x1_data.db'
BOOTSTRAP_ADMIN_FILE = BASE_DIR / 'data' / 'bootstrap_admin_password.txt'


def _apply_sqlite_pragmas(conn):
    """统一主库 SQLite 并发参数。"""
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def get_db():
    """数据库连接上下文管理器"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    _apply_sqlite_pragmas(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """初始化数据库表结构"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 用户表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL,
                department TEXT,
                created_at TEXT NOT NULL,
                last_login TEXT,
                is_active INTEGER NOT NULL DEFAULT 1
            )
        ''')
        
        # 用户表增量字段迁移
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1')
        except sqlite3.OperationalError:
            pass

        # [已废弃] 角色权限旧表 — 运行时权限已完全由 role_permission_final 驱动
        # 保留 CREATE 语句仅防止旧代码引用时报错，新逻辑不写入此表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS role_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                permission_key TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL,
                UNIQUE(role, permission_key)
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_role_permissions_role ON role_permissions(role)')

        # 系统设置表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT NOT NULL UNIQUE,
                setting_value TEXT,
                value_type TEXT NOT NULL DEFAULT 'string',
                group_name TEXT,
                description TEXT,
                requires_restart INTEGER NOT NULL DEFAULT 0,
                is_sensitive INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL,
                updated_by TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_system_settings_group ON system_settings(group_name)')

        # 操作日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS action_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                user TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT,
                detail TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_time ON action_logs(time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_action_user ON action_logs(user)')
        
        # 错误日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                type TEXT NOT NULL,
                message TEXT NOT NULL,
                context TEXT,
                traceback TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_error_time ON error_logs(time)')
        
        # 性能日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                time TEXT NOT NULL,
                operation TEXT NOT NULL,
                duration REAL NOT NULL,
                details TEXT
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_perf_time ON performance_logs(time)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_perf_op ON performance_logs(operation)')
        
        # [已废弃] 检测记录表 — 业务数据已迁移到 data/x1_data.db 的 business 表
        # 此表无运行时写入，保留仅防止旧代码引用时报错
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS inspection_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_id TEXT UNIQUE NOT NULL,
                business_domain TEXT NOT NULL,
                detection_type TEXT NOT NULL,
                inspector_name TEXT NOT NULL,
                department TEXT,
                created_at TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                data_json TEXT NOT NULL
            )
        ''')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_record_id ON inspection_records(record_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_inspector ON inspection_records(inspector_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_created ON inspection_records(created_at)')
        
        # 检查是否有默认管理员
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', ('admin',))
        if cursor.fetchone()[0] == 0:
            bootstrap_password = os.getenv('X1_BOOTSTRAP_ADMIN_PASSWORD', '').strip() or secrets.token_urlsafe(12)
            cursor.execute('''
                INSERT INTO users (user_id, password_hash, display_name, role, department, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                'admin',
                generate_password_hash(bootstrap_password, method='pbkdf2:sha256'),
                '系统管理员',
                'admin',
                '',
                datetime.now().isoformat()
            ))
            BOOTSTRAP_ADMIN_FILE.parent.mkdir(parents=True, exist_ok=True)
            BOOTSTRAP_ADMIN_FILE.write_text(
                'X1 bootstrap admin password (generated on first init)\n'
                'username=admin\n'
                f'password={bootstrap_password}\n',
                encoding='utf-8'
            )


def migrate_from_json():
    """从JSON文件迁移数据到数据库"""
    users_file = BASE_DIR / 'users.json'
    if users_file.exists():
        users_data = json.loads(users_file.read_text())
        with get_db() as conn:
            cursor = conn.cursor()
            for user_id, user_info in users_data.items():
                cursor.execute('''
                    INSERT OR REPLACE INTO users 
                    (user_id, password_hash, display_name, role, department, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    user_info['password_hash'],
                    user_info['display_name'],
                    user_info['role'],
                    user_info.get('department', ''),
                    user_info['created_at']
                ))
        print(f"已迁移 {len(users_data)} 个用户")
    
    # 迁移日志文件
    logs_dir = BASE_DIR / 'logs_x1'
    if logs_dir.exists():
        with get_db() as conn:
            cursor = conn.cursor()
            
            # 迁移操作日志
            for log_file in logs_dir.glob('*.jsonl'):
                if 'errors_' in log_file.name or 'performance_' in log_file.name:
                    continue
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            cursor.execute('''
                                INSERT INTO action_logs (time, user, action, target, detail)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                entry['time'],
                                entry['user'],
                                entry['action'],
                                entry.get('target', ''),
                                entry.get('detail', '')
                            ))
                        except:
                            pass
            
            # 迁移错误日志
            for log_file in logs_dir.glob('errors_*.jsonl'):
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            cursor.execute('''
                                INSERT INTO error_logs (time, type, message, context, traceback)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (
                                entry['time'],
                                entry['type'],
                                entry['message'],
                                entry.get('context', ''),
                                entry.get('traceback', '')
                            ))
                        except:
                            pass
            
            # 迁移性能日志
            for log_file in logs_dir.glob('performance_*.jsonl'):
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        try:
                            entry = json.loads(line)
                            cursor.execute('''
                                INSERT INTO performance_logs (time, operation, duration, details)
                                VALUES (?, ?, ?, ?)
                            ''', (
                                entry['time'],
                                entry['operation'],
                                entry['duration'],
                                entry.get('details', '')
                            ))
                        except:
                            pass
        
        print(f"已迁移日志文件")


if __name__ == '__main__':
    print("初始化数据库...")
    init_database()
    print("数据库初始化完成")
    
    print("\n开始迁移数据...")
    migrate_from_json()
    print("数据迁移完成")
