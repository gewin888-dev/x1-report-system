"""
X1 消息通知模块
提供站内通知的创建、查询、标记已读功能
"""

import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


def _get_db():
    conn = sqlite3.connect(str(BASE_DIR / 'x1_data.db'))
    conn.row_factory = sqlite3.Row
    return conn


def ensure_notifications_table():
    """确保通知表存在"""
    conn = _get_db()
    conn.execute("""CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_role TEXT NOT NULL DEFAULT '',
        target_user TEXT NOT NULL DEFAULT '',
        title TEXT NOT NULL,
        content TEXT NOT NULL DEFAULT '',
        category TEXT NOT NULL DEFAULT 'system',
        link TEXT DEFAULT '',
        is_read INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_notif_target_read 
                    ON notifications(target_role, is_read, created_at DESC)""")
    conn.execute("""CREATE INDEX IF NOT EXISTS idx_notif_user_read 
                    ON notifications(target_user, is_read, created_at DESC)""")
    conn.commit()
    conn.close()


def create_notification(title, content='', category='system', target_role='', target_user='', link=''):
    # 防御 None
    target_role = target_role or ''
    target_user = target_user or ''
    link = link or ''
    """
    创建通知
    
    Args:
        title: 通知标题（简短）
        content: 通知详情
        category: 分类 (registration/urge/feedback/report/system)
        target_role: 目标角色 (admin/inspector/customer)，空=所有
        target_user: 目标用户名，空=按角色广播
        link: 关联链接/面板跳转标识
    """
    conn = _get_db()
    ensure_notifications_table()
    conn.execute(
        """INSERT INTO notifications (target_role, target_user, title, content, category, link, is_read, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 0, ?)""",
        [target_role, target_user, title, content, category, link, 
         datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    )
    conn.commit()
    conn.close()


def get_notifications(user_id, role, limit=50, unread_only=False):
    """
    获取用户可见的通知列表
    规则：target_user 精确匹配 OR target_role 匹配 OR 两者皆空（全局通知）
    """
    conn = _get_db()
    ensure_notifications_table()
    sql = """SELECT * FROM notifications 
             WHERE (target_user = ? OR target_role = ? OR (target_user = '' AND target_role = ''))"""
    params = [user_id, role]
    if unread_only:
        sql += " AND is_read = 0"
    sql += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_unread_count(user_id, role):
    """获取未读通知数"""
    conn = _get_db()
    ensure_notifications_table()
    row = conn.execute(
        """SELECT COUNT(*) as cnt FROM notifications 
           WHERE (target_user = ? OR target_role = ? OR (target_user = '' AND target_role = ''))
           AND is_read = 0""",
        [user_id, role]
    ).fetchone()
    conn.close()
    return row['cnt'] if row else 0


def mark_read(notification_id, user_id):
    """标记单条已读"""
    conn = _get_db()
    conn.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND (target_user = ? OR target_user = '')", 
                 [notification_id, user_id])
    conn.commit()
    conn.close()


def mark_all_read(user_id, role):
    """标记所有可见通知为已读"""
    conn = _get_db()
    conn.execute(
        """UPDATE notifications SET is_read = 1 
           WHERE (target_user = ? OR target_role = ? OR (target_user = '' AND target_role = ''))
           AND is_read = 0""",
        [user_id, role]
    )
    conn.commit()
    conn.close()


# ====== 业务快捷函数 ======

def notify_new_registration(company, contact_name, username):
    """客户注册待审核"""
    create_notification(
        title=f'新客户注册待审核',
        content=f'{company} · {contact_name} · 用户名: {username}',
        category='registration',
        target_role='admin',
        link='users:customer'
    )


def notify_customer_urge(client_name, project_name):
    """客户催促项目"""
    create_notification(
        title=f'客户催促',
        content=f'{client_name} 催促项目「{project_name}」进度',
        category='urge',
        target_role='admin',
        link='projects'
    )


def notify_report_feedback(client_name, project_name):
    """客户提交报告反馈"""
    create_notification(
        title=f'报告修正意见',
        content=f'{client_name} 对「{project_name}」提交了修正意见',
        category='feedback',
        target_role='admin',
        link='records'
    )


def notify_report_ready(project_name, target_user):
    """报告已出具通知客户"""
    create_notification(
        title=f'报告已出具',
        content=f'您的项目「{project_name}」检测报告已出具，可在线预览或下载',
        category='report',
        target_user=target_user,
        link='projects'
    )


def notify_registration_approved(username):
    """注册审核通过"""
    create_notification(
        title=f'注册审核通过',
        content='您的账号已通过审核，现在可以登录使用检测项目管理系统',
        category='system',
        target_user=username,
        link=''
    )


def notify_registration_rejected(username, reason=''):
    """注册审核驳回"""
    create_notification(
        title=f'注册审核未通过',
        content=f'原因：{reason}' if reason else '您的注册申请未通过审核，如有疑问请联系客服',
        category='system',
        target_user=username,
        link=''
    )


def notify_project_status_change(project_name, client_name, old_stage, new_stage):
    """项目状态变更通知客户"""
    stage_labels = {
        '未安排': '等待安排',
        '已安排': '已安排检测',
        '检测中': '正在检测',
        '检测完成': '检测已完成',
        '报告编制中': '报告编制中',
        '已出具': '报告已出具',
        '已发送客户': '报告已发送',
        '待客户确认': '等待您确认',
    }
    label = stage_labels.get(new_stage, new_stage)
    # 找到该 client_name 对应的客户用户
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE role='customer' AND client_name=? AND is_active=1",
            [client_name]
        ).fetchall()
        for row in rows:
            create_notification(
                title=f'项目进度更新',
                content=f'您的项目「{project_name}」状态已更新为：{label}',
                category='report',
                target_user=row['user_id'],
                link='projects'
            )
    finally:
        conn.close()


def notify_project_report_uploaded(project_name, client_name):
    """报告上传完成通知客户"""
    conn = _get_db()
    try:
        rows = conn.execute(
            "SELECT user_id FROM users WHERE role='customer' AND client_name=? AND is_active=1",
            [client_name]
        ).fetchall()
        for row in rows:
            create_notification(
                title=f'检测报告已出具',
                content=f'您的项目「{project_name}」检测报告已出具，可在线预览或下载',
                category='report',
                target_user=row['user_id'],
                link='projects'
            )
    finally:
        conn.close()
