#!/usr/bin/env python3
"""
X1 用户认证模块
支持四级权限：admin（管理员）、supervisor（主管）、inspector（检测员）、viewer（访客，只读后台）
"""

from datetime import datetime
from functools import wraps
from flask_login import LoginManager, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db

DEFAULT_ROLE_PERMISSIONS = {
    'admin': {'*'},
    'supervisor': {
        'admin.access', 'admin.stats.view', 'admin.records.view', 'admin.logs.view', 'admin.logs.delete',
        'admin.standards.view', 'admin.templates.view', 'admin.templates.preview',
        'admin.templates.variables', 'admin.docs.view', 'files.preview', 'record.export.void',
        'record.scope.department', 'admin.migration.check',
        'admin.settings.view', 'admin.records.export',
        'admin.records.open_local', 'admin.records.open_feishu',
        'admin.records.scope.self', 'admin.records.scope.department',
        # 模板管理（细粒度）
        'admin.templates.registry.create', 'admin.templates.registry.update', 'admin.templates.registry.delete',
        'admin.templates.verify', 'admin.templates.smoke_export',
        'admin.templates.mapping.type_manage', 'admin.templates.mapping.semantic_manage',
        'admin.templates.default.set', 'admin.templates.delete', 'admin.templates.toggle',
        # 项目管理（细粒度）
        'admin.projects.view', 'admin.projects.create', 'admin.projects.update', 'admin.projects.delete',
        # 任务派单（细粒度）
        'admin.tasks.view', 'admin.tasks.create', 'admin.tasks.update', 'admin.tasks.delete',
        # 客户管理（细粒度）
        'admin.customers.view', 'admin.customers.create', 'admin.customers.update', 'admin.customers.delete',
        # 文件下载
        'admin.files.download',
        # 客户反馈回复
        'admin.customers.feedback_reply',
        # 上传历史报告
        'admin.projects.upload_report',
        # 财务查看
        'admin.finance.contract_amount', 'admin.finance.paid_amount', 'admin.finance.receivable_amount'
    },
    'viewer': {
        'admin.access', 'admin.stats.view', 'admin.records.view', 'admin.logs.view', 'admin.logs.delete',
        'admin.standards.view', 'admin.templates.view', 'admin.templates.preview',
        'admin.templates.variables', 'admin.docs.view', 'admin.users.view', 'record.scope.company',
        'admin.records.scope.company', 'admin.records.open_local', 'admin.records.open_feishu',
        # 项目管理（只读）
        'admin.projects.view',
        # 任务查看（只读）
        'admin.tasks.view',
        # 文件下载
        'admin.files.download'
    },
    'inspector': {
        'draft.read', 'draft.write', 'draft.transfer', 'record.export', 'files.download.own', 'files.preview.own',
        'record.export.void', 'record.scope.self', 'admin.records.scope.self',
        # 检测员任务执行
        'tasks.execute'
    },
    'customer': {
        'customer.access', 'customer.profile', 'customer.history', 'customer.projects', 'customer.feedback',
        'customer.urge', 'customer.confirm', 'customer.report.preview', 'customer.report.download'
    }
}


class User(UserMixin):
    def __init__(self, user_id, display_name, role, department, is_active=True, permissions=None, client_name=''):
        self.id = user_id
        self.display_name = display_name
        self.role = role
        self.department = department
        self._is_active = bool(is_active)
        self.permissions = set(permissions or [])
        self.client_name = client_name or ''

    @property
    def is_active(self):
        return self._is_active


def _load_role_permissions(role):
    if role == 'admin':
        return {'*'}
    perms = set(DEFAULT_ROLE_PERMISSIONS.get(role, set()))
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT permission_key, enabled FROM role_permissions WHERE role = ?', (role,))
            rows = cursor.fetchall()
            for row in rows:
                key = row['permission_key']
                if row['enabled']:
                    perms.add(key)
                else:
                    perms.discard(key)
    except Exception:
        pass
    return perms


def user_has_permission(user, permission):
    if not user:
        return False
    perms = set(getattr(user, 'permissions', set()) or set())
    if '*' in perms:
        return True
    aliases = {
        'admin.records.scope.self': {'record.scope.self'},
        'admin.records.scope.department': {'record.scope.department'},
        'admin.records.scope.company': {'record.scope.company'},
        'admin.records.open_local': set(),
        'admin.records.open_feishu': set(),
        'admin.records.void_export': {'record.export.void'},
        'admin.records.export': {'record.export'},
        'record.scope.self': {'admin.records.scope.self'},
        'record.scope.department': {'admin.records.scope.department'},
        'record.scope.company': {'admin.records.scope.company'},
        'record.export.void': {'admin.records.void_export'},
        'record.export': {'admin.records.export'},
    }
    if permission in perms:
        return True
    for alt in aliases.get(permission, set()):
        if alt in perms:
            return True
    return False


def get_user(user_id):
    """根据ID获取用户对象"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            return None
        perms = _load_role_permissions(row['role'])
        client_name = row['client_name'] if 'client_name' in row.keys() else ''
        return User(row['user_id'], row['display_name'], row['role'], row['department'], row['is_active'] if 'is_active' in row.keys() else 1, perms, client_name)


def verify_password(user_id, password):
    """验证密码（仅校验密码，不检查 is_active）"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT password_hash FROM users WHERE user_id = ?', (user_id,))
        row = cursor.fetchone()
        if not row:
            return False
        return check_password_hash(row['password_hash'], password)


def create_user(user_id, password, display_name, role='inspector', department='', client_name=''):
    """创建新用户"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone()[0] > 0:
            return False, '用户名已存在'
        
        cursor.execute('''
            INSERT INTO users (user_id, password_hash, display_name, role, department, client_name, created_at, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            user_id,
            generate_password_hash(password, method='pbkdf2:sha256'),
            display_name,
            role,
            department,
            client_name,
            datetime.now().isoformat(),
            1
        ))
        return True, '创建成功'


def update_user(user_id, **kwargs):
    """更新用户信息"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM users WHERE user_id = ?', (user_id,))
        if cursor.fetchone()[0] == 0:
            return False, '用户不存在'
        
        updates = []
        params = []
        
        if 'password' in kwargs:
            updates.append('password_hash = ?')
            params.append(generate_password_hash(kwargs['password'], method='pbkdf2:sha256'))
        if 'display_name' in kwargs:
            updates.append('display_name = ?')
            params.append(kwargs['display_name'])
        if 'role' in kwargs:
            updates.append('role = ?')
            params.append(kwargs['role'])
        if 'department' in kwargs:
            updates.append('department = ?')
            params.append(kwargs['department'])
        if 'is_active' in kwargs:
            updates.append('is_active = ?')
            params.append(1 if kwargs['is_active'] else 0)
        if 'client_name' in kwargs:
            updates.append('client_name = ?')
            params.append(kwargs['client_name'])
        
        if updates:
            params.append(user_id)
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?", params)
        
        return True, '更新成功'


def delete_user(user_id):
    """删除用户"""
    if user_id == 'admin':
        return False, '不能删除管理员账号'
    
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM users WHERE user_id = ?', (user_id,))
        if cursor.rowcount == 0:
            return False, '用户不存在'
        return True, '删除成功'


def can_view_record(user, record_data):
    """检查用户是否有权限查看记录（个人 / 部门 / 公司）"""
    if not user:
        return False
    if user_has_permission(user, '*') or user_has_permission(user, 'record.scope.company'):
        return True

    record_inspector = (record_data or {}).get('inspector_name', '') or ''
    if user_has_permission(user, 'record.scope.self'):
        if record_inspector == user.display_name or record_inspector == user.id:
            return True

    if user_has_permission(user, 'record.scope.department'):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT department FROM users
                WHERE (display_name = ? OR user_id = ?) AND department = ?
                LIMIT 1
            ''', (record_inspector, record_inspector, user.department))
            if cursor.fetchone() is not None:
                return True

    return False


def require_role(*roles):
    """装饰器：要求特定角色"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return {'error': '未登录'}, 401
            if current_user.role not in roles:
                return {'error': '权限不足'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(permission):
    """装饰器：要求特定权限"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return {'error': '未登录'}, 401
            if not user_has_permission(current_user, permission):
                return {'error': '权限不足'}, 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def init_login_manager(app):
    """初始化Flask-Login"""
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'login_page'
    
    @login_manager.user_loader
    def load_user(user_id):
        return get_user(user_id)
    
    return login_manager
