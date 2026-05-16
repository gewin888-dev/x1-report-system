"""
helpers/db.py - 统一数据库访问层

提供两个数据库连接：
- get_db(): 主库 (x1_data.db) — 用户/日志/通知/记录元数据/系统设置
- get_x1_data_conn(): 业务库 (data/x1_data.db) — 项目/客户/任务/反馈

使用说明：
    from helpers.db import get_x1_data_conn, get_db_context

    # 业务库
    conn = get_x1_data_conn()
    
    # 主库（上下文管理器）
    with get_db_context() as conn:
        conn.execute(...)
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
_DATA_DIR = BASE_DIR / 'data'


def get_x1_data_conn():
    """获取业务数据库连接 (data/x1_data.db)"""
    db_path = _DATA_DIR / 'x1_data.db'
    os.makedirs(str(_DATA_DIR), exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


@contextmanager
def get_db_context():
    """主库上下文管理器（自动关闭）"""
    from database import get_db
    conn = get_db()
    try:
        yield conn
    finally:
        pass  # get_db() 由 Flask 管理生命周期


def init_business_projects_table():
    """初始化业务项目表"""
    conn = get_x1_data_conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS business_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_no TEXT UNIQUE,
            project_name TEXT NOT NULL DEFAULT '',
            client_name TEXT DEFAULT '',
            contact_name TEXT DEFAULT '',
            contact_phone TEXT DEFAULT '',
            project_address TEXT DEFAULT '',
            domain TEXT DEFAULT '',
            detection_types TEXT DEFAULT '[]',
            inspector_names TEXT DEFAULT '[]',
            priority TEXT DEFAULT 'normal',
            stage TEXT DEFAULT 'pending',
            contract_status TEXT DEFAULT '',
            invoice_status TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            report_status TEXT DEFAULT '',
            delivery_status TEXT DEFAULT '',
            task_summary TEXT DEFAULT '{}',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            created_by TEXT DEFAULT '',
            archived INTEGER DEFAULT 0
        );
        
        CREATE INDEX IF NOT EXISTS idx_bp_stage ON business_projects(stage);
        CREATE INDEX IF NOT EXISTS idx_bp_client ON business_projects(client_name);
        CREATE INDEX IF NOT EXISTS idx_bp_created ON business_projects(created_at);
    ''')
    
    # 动态添加可能缺失的列
    cursor = conn.execute("PRAGMA table_info(business_projects)")
    existing_cols = {row[1] for row in cursor.fetchall()}
    
    new_cols = {
        'contract_status': "TEXT DEFAULT ''",
        'invoice_status': "TEXT DEFAULT ''",
        'report_status': "TEXT DEFAULT ''",
        'delivery_status': "TEXT DEFAULT ''",
        'task_summary': "TEXT DEFAULT '{}'",
        'archived': "INTEGER DEFAULT 0",
    }
    
    for col, typedef in new_cols.items():
        if col not in existing_cols:
            conn.execute(f"ALTER TABLE business_projects ADD COLUMN {col} {typedef}")
    
    conn.commit()
    conn.close()


def init_project_tasks_table():
    """初始化项目任务表"""
    conn = get_x1_data_conn()
    conn.executescript('''
        CREATE TABLE IF NOT EXISTS project_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            task_type TEXT NOT NULL DEFAULT 'inspection',
            assigned_to TEXT DEFAULT '',
            assigned_by TEXT DEFAULT '',
            status TEXT DEFAULT 'pending_assign',
            priority TEXT DEFAULT 'normal',
            notes TEXT DEFAULT '',
            result_summary TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT '',
            accepted_at TEXT DEFAULT '',
            started_at TEXT DEFAULT '',
            completed_at TEXT DEFAULT '',
            cancelled_at TEXT DEFAULT '',
            cancel_reason TEXT DEFAULT ''
        );
        
        CREATE INDEX IF NOT EXISTS idx_pt_project ON project_tasks(project_id);
        CREATE INDEX IF NOT EXISTS idx_pt_assigned ON project_tasks(assigned_to);
        CREATE INDEX IF NOT EXISTS idx_pt_status ON project_tasks(status);
    ''')
    conn.commit()
    conn.close()


# ==================== 通用数据访问函数 ====================

@contextmanager
def x1_transaction():
    """业务库事务上下文管理器（自动 commit/rollback/close）"""
    conn = get_x1_data_conn()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def x1_query(sql, params=(), one=False):
    """执行查询，返回 dict 列表或单条 dict"""
    conn = get_x1_data_conn()
    try:
        rows = conn.execute(sql, params).fetchall()
        result = [dict(r) for r in rows]
        return result[0] if one and result else (None if one else result)
    finally:
        conn.close()


def x1_execute(sql, params=()):
    """执行写操作（INSERT/UPDATE/DELETE），返回 lastrowid"""
    conn = get_x1_data_conn()
    try:
        cursor = conn.execute(sql, params)
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def x1_count(table, where='', params=()):
    """计数查询"""
    sql = f"SELECT COUNT(*) as cnt FROM {table}"
    if where:
        sql += f" WHERE {where}"
    row = x1_query(sql, params, one=True)
    return row['cnt'] if row else 0


def x1_get_by_id(table, row_id):
    """按 ID 查询单条记录"""
    return x1_query(f"SELECT * FROM {table} WHERE id=?", (row_id,), one=True)


def x1_insert(table, data: dict):
    """插入一条记录，返回 lastrowid"""
    cols = list(data.keys())
    placeholders = ', '.join(['?'] * len(cols))
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({placeholders})"
    return x1_execute(sql, list(data.values()))


def x1_update(table, row_id, data: dict):
    """按 ID 更新记录"""
    sets = ', '.join(f"{k}=?" for k in data.keys())
    params = list(data.values()) + [row_id]
    return x1_execute(f"UPDATE {table} SET {sets} WHERE id=?", params)


def x1_delete(table, row_id):
    """按 ID 删除记录"""
    return x1_execute(f"DELETE FROM {table} WHERE id=?", (row_id,))
