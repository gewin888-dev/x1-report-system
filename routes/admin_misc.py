"""
routes/admin_misc.py - Admin miscellaneous routes Blueprint

Includes: registrations, role permissions, users CRUD, logs, standards, stats,
notifications, inspectors list, and x/meta.
"""

import json
import os
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from auth import (
    require_role,
    require_permission,
    DEFAULT_ROLE_PERMISSIONS,
    _ensure_role_permission_final_table,
    _get_final_permissions_from_db,
    _save_final_permissions,
)
from config_loader import load_x1_config
from database import get_db
from monitor import log_action
from notifications import (
    get_notifications, get_unread_count,
    mark_read, mark_all_read,
    notify_registration_approved, notify_registration_rejected
)

BASE_DIR = Path(__file__).resolve().parent.parent
CFG = load_x1_config(BASE_DIR)
PATHS = CFG.get("paths", {})
RECORDS_DIR = BASE_DIR / PATHS.get("records", "records_x1")
REPORTS_DIR = BASE_DIR / PATHS.get("reports", "reports_x1")

LOG_ACTION_CATEGORY_MAP = {
    "login": "认证与会话",
    "login_failed": "认证与会话",
    "logout": "认证与会话",
    "导出报告": "报告记录治理",
    "删除记录": "报告记录治理",
    "批量删除记录": "报告记录治理",
    "作废记录": "报告记录治理",
    "重试飞书上传": "报告记录治理",
    "批量删除操作日志": "操作日志治理",
    "更新系统设置": "系统设置与运维",
    "执行路径巡检": "系统设置与运维",
    "创建系统设置目录": "系统设置与运维",
    "创建子目录": "系统设置与运维",
    "测试飞书配置": "系统设置与运维",
    "执行立即备份": "系统设置与运维",
    "更新角色权限": "权限与用户管理",
    "新增用户": "权限与用户管理",
    "编辑用户": "权限与用户管理",
    "删除用户": "权限与用户管理",
    "重置用户密码": "权限与用户管理",
    "注册模板": "模板注册与模板治理",
    "上传并注册模板": "模板注册与模板治理",
    "模板导出验证": "模板注册与模板治理",
    "删除模板注册": "模板注册与模板治理",
    "切换模板启停": "模板注册与模板治理",
    "验证模板": "模板注册与模板治理",
    "设置默认模板": "模板注册与模板治理",
    "加入模板候选": "模板注册与模板治理",
    "设置语义默认模板": "模板注册与模板治理",
    "加入语义模板候选": "模板注册与模板治理",
    "查看模板": "标准库/文档/查看类",
}

LOG_ACTION_CATEGORIES = [
    "认证与会话", "报告记录治理", "操作日志治理", "系统设置与运维",
    "权限与用户管理", "模板注册与模板治理", "标准库/文档/查看类", "其他/未分类"
]


def get_log_action_category(action: str) -> str:
    return LOG_ACTION_CATEGORY_MAP.get((action or "").strip(), "其他/未分类")


def _ensure_registration_table(conn):
    """确保 customer_registrations 表存在"""
    conn.execute("""CREATE TABLE IF NOT EXISTS customer_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        company TEXT NOT NULL,
        contact_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        reviewed_by TEXT DEFAULT '',
        reviewed_at TEXT DEFAULT '',
        reject_reason TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )""")


admin_misc_bp = Blueprint("admin_misc", __name__)


# ============================================================
# Notifications API
# ============================================================

@admin_misc_bp.route('/api/notifications')
@login_required
def api_notifications():
    """获取当前用户的通知列表"""
    limit = request.args.get('limit', 30, type=int)
    unread_only = request.args.get('unread_only', '') == '1'
    items = get_notifications(current_user.id, current_user.role, limit=limit, unread_only=unread_only)
    return jsonify({'success': True, 'items': items})


@admin_misc_bp.route('/api/notifications/unread_count')
@login_required
def api_notifications_unread_count():
    """获取未读通知数"""
    count = get_unread_count(current_user.id, current_user.role)
    return jsonify({'success': True, 'count': count})


@admin_misc_bp.route('/api/notifications/<int:nid>/read', methods=['POST'])
@login_required
def api_notification_mark_read(nid):
    """标记单条已读"""
    mark_read(nid, current_user.id)
    return jsonify({'success': True})


@admin_misc_bp.route('/api/notifications/read_all', methods=['POST'])
@login_required
def api_notification_read_all():
    """全部标记已读"""
    mark_all_read(current_user.id, current_user.role)
    return jsonify({'success': True})


# ============================================================
# Registrations API
# ============================================================

@admin_misc_bp.route('/admin/api/registrations')
@login_required
@require_permission('admin.users.customer.view')
def admin_api_registrations():
    """获取客户注册申请列表"""
    status = request.args.get('status', 'pending')
    with get_db() as conn:
        _ensure_registration_table(conn)
        if status == 'all':
            rows = conn.execute('SELECT * FROM customer_registrations ORDER BY created_at DESC').fetchall()
        else:
            rows = conn.execute('SELECT * FROM customer_registrations WHERE status=? ORDER BY created_at DESC', [status]).fetchall()
    result = []
    for r in rows:
        result.append({
            'id': r['id'],
            'username': r['username'],
            'company': r['company'],
            'contact_name': r['contact_name'],
            'phone': r['phone'],
            'address': r['address'] or '',
            'status': r['status'],
            'reviewed_by': r['reviewed_by'] or '',
            'reviewed_at': r['reviewed_at'] or '',
            'reject_reason': r['reject_reason'] or '',
            'created_at': (r['created_at'] or '')[:19]
        })
    return jsonify(result)


@admin_misc_bp.route('/admin/api/registrations/<int:reg_id>/approve', methods=['POST'])
@login_required
@require_permission('admin.users.customer.approve')
def admin_api_approve_registration(reg_id):
    """审核通过客户注册，同时自动创建/更新 client_profiles"""
    with get_db() as conn:
        _ensure_registration_table(conn)
        reg = conn.execute('SELECT * FROM customer_registrations WHERE id=?', [reg_id]).fetchone()
        if not reg:
            return jsonify({'success': False, 'message': '注册记录不存在'})
        if reg['status'] != 'pending':
            return jsonify({'success': False, 'message': '该申请已处理'})
        
        # 激活用户账号
        conn.execute('UPDATE users SET is_active=1 WHERE user_id=?', [reg['username']])
        # 更新注册记录
        conn.execute(
            """UPDATE customer_registrations SET status='approved', reviewed_by=?, reviewed_at=datetime('now','localtime') WHERE id=?""",
            [current_user.id, reg_id]
        )
        conn.commit()

    # 自动创建/更新 client_profiles（业务数据库）
    company = (reg['company'] or '').strip()
    contact_name = (reg['contact_name'] or '').strip()
    phone = (reg['phone'] or '').strip()
    address = (reg['address'] or '').strip() if 'address' in reg.keys() else ''
    if company:
        try:
            from helpers.db_utils import get_x1_data_conn
            biz_conn = get_x1_data_conn()
            try:
                existing = biz_conn.execute(
                    'SELECT id FROM client_profiles WHERE client_name=?', (company,)
                ).fetchone()
                now = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if existing:
                    # 更新联系人信息（不覆盖已有的开票/收件信息）
                    biz_conn.execute(
                        'UPDATE client_profiles SET contact_name=?, contact_phone=?, updated_at=? WHERE client_name=?',
                        (contact_name, phone, now, company)
                    )
                else:
                    # 新建 profile
                    biz_conn.execute(
                        'INSERT INTO client_profiles (client_name, contact_name, contact_phone, recipient_name, recipient_phone, recipient_address, updated_at) VALUES (?,?,?,?,?,?,?)',
                        (company, contact_name, phone, contact_name, phone, address, now)
                    )
                biz_conn.commit()
            finally:
                biz_conn.close()
        except Exception:
            pass  # profile 创建失败不影响审批结果

    log_action(current_user.id, 'approve_registration', reg['username'], f"审核通过客户注册：{reg['company']} / {reg['contact_name']}")
    notify_registration_approved(reg['username'])
    return jsonify({'success': True, 'message': '已通过审核，客户可登录使用'})


@admin_misc_bp.route('/admin/api/registrations/<int:reg_id>/reject', methods=['POST'])
@login_required
@require_permission('admin.users.customer.approve')
def admin_api_reject_registration(reg_id):
    """驳回客户注册"""
    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or '').strip() or '未通过审核'
    with get_db() as conn:
        _ensure_registration_table(conn)
        reg = conn.execute('SELECT * FROM customer_registrations WHERE id=?', [reg_id]).fetchone()
        if not reg:
            return jsonify({'success': False, 'message': '注册记录不存在'})
        if reg['status'] != 'pending':
            return jsonify({'success': False, 'message': '该申请已处理'})
        
        # 更新注册记录（不激活账号）
        conn.execute(
            """UPDATE customer_registrations SET status='rejected', reviewed_by=?, reviewed_at=datetime('now','localtime'), reject_reason=? WHERE id=?""",
            [current_user.id, reason, reg_id]
        )
        conn.commit()
    log_action(current_user.id, 'reject_registration', reg['username'], f"驳回客户注册：{reg['company']}，原因：{reason}")
    notify_registration_rejected(reg['username'], reason)
    return jsonify({'success': True, 'message': '已驳回'})


# ============================================================
# Role Permissions API
# ============================================================

@admin_misc_bp.route('/admin/api/permissions/roles')
@login_required
@require_permission('admin.permissions.view')
def admin_api_role_permissions():
    result = []
    with get_db() as conn:
        _ensure_role_permission_final_table(conn)
    for role, defaults in DEFAULT_ROLE_PERMISSIONS.items():
        with get_db() as conn:
            final_set = _get_final_permissions_from_db(conn, role)
        effective_map = {}
        all_keys = sorted(set(defaults) | set(final_set))
        for key in all_keys:
            effective_map[key] = key in final_set
        disabled = sorted([k for k in all_keys if k not in final_set])
        custom_permissions = {}
        for key in all_keys:
            base_enabled = key in defaults
            final_enabled = key in final_set
            if base_enabled != final_enabled:
                custom_permissions[key] = final_enabled
        result.append({
            'role': role,
            'default_permissions': sorted(defaults),
            'custom_permissions': custom_permissions,
            'effective_permissions': sorted(final_set),
            'effective_map': effective_map,
            'disabled_permissions': disabled,
            'storage_mode': 'final',
        })
    return jsonify({'success': True, 'roles': result})


@admin_misc_bp.route('/admin/api/permissions/roles/<role>', methods=['PUT'])
@login_required
@require_permission('admin.permissions.manage')
def admin_api_role_permissions_update(role):
    if role == 'admin':
        return jsonify({'success': False, 'error': 'admin 角色权限不可修改'}), 403
    if role not in DEFAULT_ROLE_PERMISSIONS:
        return jsonify({'success': False, 'error': '角色不存在'}), 404
    data = request.get_json(silent=True) or {}
    effective_permissions = data.get('effective_permissions')
    if not isinstance(effective_permissions, list):
        return jsonify({'success': False, 'error': 'effective_permissions 必须为数组'}), 400
    clean_permissions = sorted({str(key or '').strip() for key in effective_permissions if str(key or '').strip()})
    now = datetime.now().isoformat()
    defaults = set(DEFAULT_ROLE_PERMISSIONS.get(role, set()))
    custom_permissions = {}
    for key in sorted(set(defaults) | set(clean_permissions)):
        base_enabled = key in defaults
        final_enabled = key in clean_permissions
        if base_enabled != final_enabled:
            custom_permissions[key] = final_enabled
    with get_db() as conn:
        _ensure_role_permission_final_table(conn)
        _save_final_permissions(conn, role, clean_permissions, updated_at=now)
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '更新角色权限', role, json.dumps({'effective_permissions': clean_permissions}, ensure_ascii=False))
    return jsonify({
        'success': True,
        'role': role,
        'effective_permissions': clean_permissions,
        'custom_permissions': custom_permissions,
        'storage_mode': 'final'
    })


# ============================================================
# Users CRUD API
# ============================================================

@admin_misc_bp.route('/admin/api/users')
@login_required
@require_permission('admin.users.view')
def admin_api_users():
    """用户列表（从数据库读取）"""
    with get_db() as conn:
        cursor = conn.cursor()
        columns = {row['name'] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        has_is_active = 'is_active' in columns
        has_last_login = 'last_login' in columns
        select_fields = ['user_id', 'display_name', 'role', 'department', 'created_at']
        if has_last_login:
            select_fields.append('last_login')
        if has_is_active:
            select_fields.append('is_active')
        has_client_name = 'client_name' in columns
        if has_client_name:
            select_fields.append('client_name')
        cursor.execute(f"SELECT {', '.join(select_fields)} FROM users ORDER BY created_at DESC")
        rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append({
            'username': row['user_id'],
            'display_name': row['display_name'] or row['user_id'],
            'role': row['role'] or 'inspector',
            'department': row['department'] or '',
            'created': (row['created_at'] or '')[:19].replace('T', ' '),
            'last_login': ((row['last_login'] or '')[:19].replace('T', ' ')) if has_last_login and row['last_login'] else '',
            'is_active': bool(row['is_active']) if has_is_active else True,
            'client_name': (row['client_name'] or '') if has_client_name else ''
        })
    return jsonify(result)


@admin_misc_bp.route('/admin/api/users', methods=['POST'])
@login_required
@require_permission('admin.users.manage')
def admin_api_users_create():
    """新增用户（写入数据库）"""
    from auth import create_user
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    display_name = (data.get('display_name') or '').strip()
    role = data.get('role', 'inspector')
    department = (data.get('department') or '').strip()
    if not username or not password:
        return jsonify({'success': False, 'error': '用户名和密码不能为空'}), 400
    ok, msg = create_user(username, password, display_name or username, role, department, data.get('client_name', ''))
    if not ok:
        return jsonify({'success': False, 'error': msg}), 400
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '新增用户', username, f'角色: {role}, 部门: {department}')
    return jsonify({'success': True, 'message': f'用户 {display_name or username} 创建成功'})


@admin_misc_bp.route('/admin/api/users/<username>', methods=['PUT'])
@login_required
@require_permission('admin.users.manage')
def admin_api_users_update(username):
    """编辑用户（更新数据库）"""
    from auth import update_user
    data = request.get_json(silent=True) or {}
    kwargs = {}
    if 'display_name' in data:
        kwargs['display_name'] = data['display_name']
    if 'role' in data:
        kwargs['role'] = data['role']
    if 'department' in data:
        kwargs['department'] = data['department']
    if 'is_active' in data:
        kwargs['is_active'] = bool(data['is_active'])
    if data.get('password'):
        kwargs['password'] = data['password']
    if 'client_name' in data:
        kwargs['client_name'] = data.get('client_name', '')
    ok, msg = update_user(username, **kwargs)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 404
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '编辑用户', username, str({k:v for k,v in data.items() if k != 'password'}))
    return jsonify({'success': True, 'message': '用户信息已更新'})


@admin_misc_bp.route('/admin/api/users/<username>', methods=['DELETE'])
@login_required
@require_permission('admin.users.manage')
def admin_api_users_delete(username):
    """删除用户（从数据库删除）"""
    from auth import delete_user
    inspect_only = request.args.get('inspect_only', '').strip() in ('1', 'true', 'yes')
    with get_db() as conn:
        cursor = conn.cursor()
        user_row = cursor.execute('SELECT user_id, display_name, role, department, is_active FROM users WHERE user_id = ?', (username,)).fetchone()
        if not user_row:
            return jsonify({'success': False, 'error': '用户不存在'}), 404
        display_name = user_row['display_name'] if user_row else username
        impact = {
            'user_id': user_row['user_id'],
            'display_name': user_row['display_name'] or '',
            'role': user_row['role'] or '',
            'department': user_row['department'] or '',
            'is_active': bool(user_row['is_active']) if 'is_active' in user_row.keys() else True,
            'protected_admin': username == 'admin',
        }
    if inspect_only:
        return jsonify({'success': True, 'impact': impact})
    ok, msg = delete_user(username)
    if not ok:
        status = 400 if username == 'admin' else 404
        return jsonify({'success': False, 'error': msg}), status
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '删除用户', username, f'姓名: {display_name}')
    return jsonify({'success': True, 'message': f'用户 {display_name} 已删除', 'impact': impact})


@admin_misc_bp.route('/admin/api/users/<username>/toggle_active', methods=['POST'])
@login_required
@require_permission('admin.users.manage')
def admin_api_users_toggle_active(username):
    from auth import update_user
    if username == 'admin':
        return jsonify({'success': False, 'error': '不能禁用admin用户'}), 400
    data = request.get_json(silent=True) or {}
    is_active = bool(data.get('is_active', True))
    ok, msg = update_user(username, is_active=is_active)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 404
    action = '启用用户' if is_active else '禁用用户'
    state_text = '启用' if is_active else '禁用'
    log_action(current_user.id if current_user.is_authenticated else 'unknown', action, username, f'状态: {state_text}')
    return jsonify({'success': True, 'message': f'用户已{state_text}'})


@admin_misc_bp.route('/admin/api/users/<username>/reset_password', methods=['POST'])
@login_required
@require_permission('admin.users.manage')
def admin_api_users_reset_password(username):
    from auth import update_user
    data = request.get_json(silent=True) or {}
    password = (data.get('password') or '').strip()
    if not password:
        return jsonify({'success': False, 'error': '新密码不能为空'}), 400
    ok, msg = update_user(username, password=password)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 404
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '重置用户密码', username, '管理员后台重置密码')
    return jsonify({'success': True, 'message': '密码已重置'})


# ============================================================
# Logs API
# ============================================================

@admin_misc_bp.route('/admin/api/logs')
@login_required
@require_permission('admin.logs.view')
def admin_api_logs():
    """操作日志列表（分页）"""
    month = (request.args.get('month') or datetime.now().strftime('%Y-%m')).strip()
    user_filter = (request.args.get('user') or '').strip()
    action_filter = (request.args.get('action') or '').strip()
    category_filter = (request.args.get('category') or '').strip()
    keyword = (request.args.get('keyword') or '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = max(1, min(500, int(request.args.get('page_size', 50))))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            'SELECT id, time, user, action, target, detail FROM action_logs WHERE time LIKE ? ORDER BY id DESC',
            [f'{month}%']
        )
        month_rows = [dict(row) for row in cursor.fetchall()]

        filtered_rows = []
        for row in month_rows:
            row['category'] = get_log_action_category(row.get('action'))
            if user_filter and row.get('user') != user_filter:
                continue
            if action_filter and row.get('action') != action_filter:
                continue
            if category_filter and row.get('category') != category_filter:
                continue
            if keyword:
                haystack = ' '.join([str(row.get('target') or ''), str(row.get('detail') or ''), str(row.get('user') or ''), str(row.get('action') or ''), str(row.get('category') or '')]).lower()
                if keyword.lower() not in haystack:
                    continue
            filtered_rows.append(row)

        total = len(filtered_rows)

        cursor.execute('SELECT DISTINCT user_id FROM users ORDER BY user_id COLLATE NOCASE')
        user_options = [row['user_id'] for row in cursor.fetchall() if row['user_id']]

        action_values = sorted({row.get('action') for row in month_rows if row.get('action')})
        default_action_options = [
            'login', 'login_failed', 'logout', '导出报告', '删除记录', '作废记录', '批量删除记录',
            '重试飞书上传', '更新系统设置', '执行路径巡检', '创建系统设置目录', '测试飞书配置',
            '创建子目录', '执行立即备份', '更新角色权限', '新增用户', '编辑用户', '删除用户',
            '重置用户密码', '批量删除操作日志', '注册模板', '上传并注册模板', '模板导出验证',
            '删除模板注册', '切换模板启停', '验证模板', '设置默认模板', '加入模板候选',
            '设置语义默认模板', '加入语义模板候选', '查看模板'
        ]
        action_options = sorted(set(action_values) | set(default_action_options))
        category_options = list(LOG_ACTION_CATEGORIES)
        category_action_map = {cat: [] for cat in LOG_ACTION_CATEGORIES}
        for action_name in action_options:
            category_action_map.setdefault(get_log_action_category(action_name), []).append(action_name)

        category_counter = {}
        for row in filtered_rows:
            cat = row.get('category') or '其他/未分类'
            category_counter[cat] = category_counter.get(cat, 0) + 1
        category_summary = [{'category': cat, 'count': category_counter.get(cat, 0)} for cat in LOG_ACTION_CATEGORIES]

        total_pages = max(1, (total + page_size - 1) // page_size)
        if page > total_pages:
            page = total_pages
        offset = (page - 1) * page_size
        logs = filtered_rows[offset:offset + page_size]

    return jsonify({'logs': logs, 'total': total, 'page': page, 'page_size': page_size, 'total_pages': total_pages, 'user_options': user_options, 'action_options': action_options, 'category_options': category_options, 'category_action_map': category_action_map, 'category_summary': category_summary})


@admin_misc_bp.route('/admin/api/logs/batch_delete', methods=['POST'])
@login_required
@require_permission('admin.logs.delete')
def admin_api_logs_batch_delete():
    """批量删除操作日志"""
    data = request.get_json(silent=True) or {}
    log_ids = data.get('log_ids', [])
    inspect_only = bool(data.get('inspect_only', False))
    if not isinstance(log_ids, list) or not log_ids:
        return jsonify({'success': False, 'error': '请选择要删除的日志'}), 400
    ids = [int(x) for x in log_ids if str(x).isdigit()]
    if not ids:
        return jsonify({'success': False, 'error': '日志ID无效'}), 400
    placeholders = ','.join('?' for _ in ids)
    with get_db() as conn:
        cursor = conn.cursor()
        rows = cursor.execute(f'SELECT id, time, user, action, target FROM action_logs WHERE id IN ({placeholders}) ORDER BY id DESC', ids).fetchall()
        impact = {
            'requested_count': len(ids),
            'matched_count': len(rows),
            'missing_count': max(0, len(ids) - len(rows)),
            'sample': [dict(r) for r in rows[:10]],
        }
        if inspect_only:
            return jsonify({'success': True, 'impact': impact})
        cursor.execute(f'DELETE FROM action_logs WHERE id IN ({placeholders})', ids)
        deleted_count = cursor.rowcount
        conn.commit()
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '批量删除操作日志', '', f'删除 {deleted_count} 条日志')
    return jsonify({'success': True, 'deleted_count': deleted_count, 'impact': impact})


@admin_misc_bp.route('/admin/api/logs/months')
@login_required
@require_permission('admin.logs.view')
def admin_api_logs_months():
    """日志月份列表"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT substr(time, 1, 7) as month FROM action_logs ORDER BY month DESC")
        months = [row['month'] for row in cursor.fetchall()]
    
    if not months:
        months = [datetime.now().strftime('%Y-%m')]
    return jsonify(months)


# ============================================================
# Standards API
# ============================================================

@admin_misc_bp.route('/admin/api/standards')
@login_required
@require_permission('admin.standards.view')
def admin_api_standards():
    """标准数据库列表"""
    import json as _json
    ranges_file = BASE_DIR / 'static' / 'standards_ranges.json'
    domain_map_file = BASE_DIR / 'static' / 'standards_domain_map.json'
    try:
        with open(ranges_file, 'r', encoding='utf-8') as f:
            ranges = _json.load(f)
        domain_map = {}
        if domain_map_file.exists():
            with open(domain_map_file, 'r', encoding='utf-8') as f:
                domain_map = _json.load(f)
        result = []
        for std_code, obj_data in ranges.items():
            obj_list = [k for k in obj_data.keys() if not k.startswith('_') and not k.endswith('_trial')]
            result.append({
                'code': std_code,
                'objects': obj_list,
                'object_count': len(obj_list),
                'domains': domain_map.get(std_code, [])
            })
        return jsonify({'standards': result, 'total': len(result)})
    except Exception as e:
        return jsonify({'standards': [], 'total': 0, 'error': str(e)})


@admin_misc_bp.route('/admin/api/standards/<path:std_code>')
@login_required
@require_permission('admin.standards.view')
def admin_api_standard_detail(std_code):
    """标准详情"""
    import json as _json
    ranges_file = BASE_DIR / 'static' / 'standards_ranges.json'
    try:
        with open(ranges_file, 'r', encoding='utf-8') as f:
            ranges = _json.load(f)
        if std_code not in ranges:
            return jsonify({'error': '标准不存在'}), 404
        # 过滤掉内部参数节点（*_trial）
        filtered_data = {k: v for k, v in ranges[std_code].items() if not k.endswith('_trial')}
        return jsonify({'code': std_code, 'data': filtered_data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============================================================
# Stats API
# ============================================================

@admin_misc_bp.route('/admin/api/stats')
@login_required
@require_permission('admin.stats.view')
def admin_api_stats():
    """数据统计 API"""
    import re as _re

    def _draft_has_visible_content(project: dict, data: dict) -> bool:
        if not isinstance(project, dict):
            return False
        rooms = project.get('rooms') or []
        strong_fields = [
            project.get('project_name', ''),
            project.get('client_name', ''),
            project.get('contact_info', ''),
            project.get('project_address', ''),
            project.get('inspection_area', ''),
            project.get('detection_type', ''),
            project.get('detection_type_name', ''),
            project.get('remarks', ''),
        ]
        if any(str(v).strip() for v in strong_fields if v is not None):
            return True
        if project.get('detection_date'):
            return True
        if rooms:
            return True
        return False

    total_drafts = 0
    for draft_file in RECORDS_DIR.glob('*.json'):
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            project = data.get('project', {})
            if _draft_has_visible_content(project, data):
                total_drafts += 1
        except:
            continue

    export_json = sorted(REPORTS_DIR.glob('X1EXPORT_*.json'))
    total_exports = len(export_json)

    today = datetime.now().strftime('%Y%m%d')
    today_exports = len([e for e in export_json if today in e.name])

    by_month = {}
    by_day = {}
    by_week = {}
    by_year = {}
    by_domain = {}
    by_domain_week = {}
    by_domain_month = {}
    by_domain_year = {}
    by_operator = {}
    by_client = {}
    date_pattern = _re.compile(r'^X1EXPORT_(\d{8})')

    for export_file in export_json:
        m = date_pattern.match(export_file.name)
        if m:
            date_str = m.group(1)
            dt = datetime.strptime(date_str, '%Y%m%d')
            month = dt.strftime('%Y-%m')
            day = dt.strftime('%Y-%m-%d')
            iso_year, iso_week, _ = dt.isocalendar()
            week = f"{iso_year}-W{iso_week:02d}"
            year = dt.strftime('%Y')
            by_month[month] = by_month.get(month, 0) + 1
            by_day[day] = by_day.get(day, 0) + 1
            by_week[week] = by_week.get(week, 0) + 1
            by_year[year] = by_year.get(year, 0) + 1
        try:
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            ep = data.get('export_payload', data)
            proj = ep.get('project', {})
            domain = proj.get('domain', '') or '未知'
            operator = proj.get('operator', '') or proj.get('inspector', '') or '未知检测员'
            client_name = proj.get('client_name', '') or '未知委托单位'
            by_domain[domain] = by_domain.get(domain, 0) + 1
            by_operator[operator] = by_operator.get(operator, 0) + 1
            by_client[client_name] = by_client.get(client_name, 0) + 1
            if m:
                month = dt.strftime('%Y-%m')
                iso_year, iso_week, _ = dt.isocalendar()
                week = f"{iso_year}-W{iso_week:02d}"
                year = dt.strftime('%Y')
                by_domain_month.setdefault(month, {})
                by_domain_month[month][domain] = by_domain_month[month].get(domain, 0) + 1
                by_domain_week.setdefault(week, {})
                by_domain_week[week][domain] = by_domain_week[week].get(domain, 0) + 1
                by_domain_year.setdefault(year, {})
                by_domain_year[year][domain] = by_domain_year[year].get(domain, 0) + 1
        except:
            pass

    top_domains = sorted(by_domain.items(), key=lambda x: x[1], reverse=True)[:5]
    top_operators = sorted(by_operator.items(), key=lambda x: x[1], reverse=True)[:5]
    top_clients = sorted(by_client.items(), key=lambda x: x[1], reverse=True)[:5]
    top_months = sorted(by_month.items(), key=lambda x: x[1], reverse=True)[:5]
    month_items = sorted(by_month.items())
    recent_6_months = dict(month_items[-6:])
    peak_month = max(by_month.items(), key=lambda x: x[1]) if by_month else ('-', 0)
    latest_month = month_items[-1] if month_items else ('-', 0)
    prev_month = month_items[-2] if len(month_items) >= 2 else ('-', 0)
    delta = latest_month[1] - prev_month[1] if len(month_items) >= 2 else 0
    lead_domain = top_domains[0] if top_domains else ('未知', 0)

    return jsonify({
        'total_records': total_drafts,
        'total_exports': total_exports,
        'month_records': by_month.get(datetime.now().strftime('%Y-%m'), 0),
        'total_users': 1,
        'today_actions': today_exports,
        'by_month': dict(sorted(by_month.items(), reverse=True)),
        'recent_6_months': recent_6_months,
        'by_day': dict(sorted(by_day.items())),
        'by_week': dict(sorted(by_week.items())),
        'by_year': dict(sorted(by_year.items())),
        'by_domain': by_domain,
        'by_domain_week': dict(sorted(by_domain_week.items())),
        'by_domain_month': dict(sorted(by_domain_month.items())),
        'by_domain_year': dict(sorted(by_domain_year.items())),
        'top_domains': [{'domain': k, 'count': v} for k, v in top_domains],
        'top_operators': [{'name': k, 'count': v} for k, v in top_operators],
        'top_clients': [{'name': k, 'count': v} for k, v in top_clients],
        'top_months': [{'name': k, 'count': v} for k, v in top_months],
        'summary': {
            'peak_month': {'label': peak_month[0], 'count': peak_month[1]},
            'latest_month': {'label': latest_month[0], 'count': latest_month[1]},
            'prev_month': {'label': prev_month[0], 'count': prev_month[1]},
            'month_delta': delta,
            'lead_domain': {'domain': lead_domain[0], 'count': lead_domain[1]}
        },
        'stats_notes': {
            'exports_scope': '导出统计仅按标准命名 X1EXPORT_* 记录计算',
            'domain_scope': '领域分布仅按正式导出记录统计，草稿不纳入',
            'trend_scope': '折线图支持按周/月/年查看导出趋势，柱状图按月份 × 领域统计，草稿不纳入',
            'top_scope': '检测员TOP、领域TOP、月度TOP、客户TOP（客户=委托单位）均仅按正式导出记录统计'
        },
        'by_operator': by_operator
    })


# ============================================================
# Inspectors & Meta API
# ============================================================

@admin_misc_bp.route('/api/x/inspectors')
@login_required
def api_x_inspectors():
    """返回可转让的内部人员列表（不含当前用户、不含客户）"""
    result = []
    with get_db() as conn:
        columns = {row['name'] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        has_is_active = 'is_active' in columns
        has_role = 'role' in columns
        sql = 'SELECT user_id, display_name, role' + (', is_active' if has_is_active else '') + ' FROM users ORDER BY user_id'
        rows = conn.execute(sql).fetchall()
        for row in rows:
            uid = row['user_id']
            if uid == current_user.id:
                continue
            if has_is_active and not row['is_active']:
                continue
            if has_role and row['role'] == 'customer':
                continue
            result.append({'username': uid, 'display_name': row['display_name'] or uid})
    return jsonify({'success': True, 'inspectors': result})


@admin_misc_bp.route('/api/x/meta')
@login_required
def api_x_meta():
    return jsonify({
        'success': True,
        'message': 'X1 独立服务已启动，当前已具备健康检查、暂存、恢复、导出构建、正式导出、模板探测与导出列表接口。',
        'capabilities': [
            'health',
            'save_draft',
            'list_drafts',
            'load_draft',
            'build_export',
            'submit_export',
            'template_probe',
            'list_exports',
            'compat_save',
            'compat_submit_and_export',
            'compat_list',
        ],
        'next': [
            '补齐旧前端仍在使用的兼容接口并逐步迁移到 /api/x/*',
            '继续完成未落地对象类型的主链能力',
            '补一份 README/交接说明，明确启动与接口使用方式',
            '增加最小化回归校验脚本，覆盖保存、列表、导出链路',
        ]
    })
