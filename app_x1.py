#!/usr/bin/env python3
"""
X1 检测记录系统 - 独立运行骨架

设计目标：
1. 与 V/T 完全隔离
2. 独立目录、独立记录、独立报告、独立日志、独立缓存
3. 先提供 X1 自己的首页与 API 骨架，不复用 T/V 的运行态路径
"""

from pathlib import Path
import json
import os
import re
import sqlite3
import secrets
import psutil
import subprocess
import shutil
import tarfile
import tempfile
from datetime import datetime
from flask import Flask, render_template, jsonify, request, redirect, url_for, flash, session, send_file
from flask_compress import Compress
from flask_login import login_user, logout_user, login_required, current_user
from adapters.export_docx import build_canonical_object_report
from adapters.export_excel import build_canonical_excel_report
from adapters.template_fill import build_template_bound_docx, build_mixed_report_docx
from template_rules import resolve_template_rule
from report_context_builder import build_report_context
from clean_class_semantics import build_clean_class_semantics, _normalize_operating_room_context
from judgement_engine import judge_room
from template_resources import resolve_template_resource, apply_type_default_template, apply_semantic_default_template
from config_loader import load_x1_config
from feishu_utils import resolve_feishu_upload_folder, get_feishu_folder_meta, upload_file_to_feishu, get_feishu_config, get_feishu_token, download_file_from_feishu, download_file_content_from_feishu
from payload_normalizer import normalize_project_payload, validate_normalized_project
from database import init_database, get_db
from auth import init_login_manager, get_user, verify_password, require_role, require_permission, DEFAULT_ROLE_PERMISSIONS, can_view_record
from monitor import log_action, log_error, monitor_performance, get_system_health
from notifications import (create_notification, get_notifications, get_unread_count,
    mark_read, mark_all_read, ensure_notifications_table,
    notify_new_registration, notify_customer_urge, notify_report_feedback,
    notify_report_ready, notify_registration_approved, notify_registration_rejected)
BASE_DIR = Path(__file__).parent
CFG = load_x1_config(BASE_DIR)
APP_VERSION = CFG.get('version', 'X4.6.3')
APP_PORT = int(CFG.get('port', 8082))
APP_HOST = CFG.get('host', '127.0.0.1')
ALLOWED_SETTINGS_BROWSE_ROOTS = [Path('/Users/fuwuqi').expanduser(), Path.home()]

LOG_ACTION_CATEGORY_MAP = {
    'login': '认证与会话',
    'login_failed': '认证与会话',
    'logout': '认证与会话',
    '导出报告': '报告记录治理',
    '删除记录': '报告记录治理',
    '批量删除记录': '报告记录治理',
    '作废记录': '报告记录治理',
    '重试飞书上传': '报告记录治理',
    '批量删除操作日志': '操作日志治理',
    '更新系统设置': '系统设置与运维',
    '执行路径巡检': '系统设置与运维',
    '创建系统设置目录': '系统设置与运维',
    '创建子目录': '系统设置与运维',
    '测试飞书配置': '系统设置与运维',
    '执行立即备份': '系统设置与运维',
    '更新角色权限': '权限与用户管理',
    '新增用户': '权限与用户管理',
    '编辑用户': '权限与用户管理',
    '删除用户': '权限与用户管理',
    '重置用户密码': '权限与用户管理',
    '注册模板': '模板注册与模板治理',
    '上传并注册模板': '模板注册与模板治理',
    '模板导出验证': '模板注册与模板治理',
    '删除模板注册': '模板注册与模板治理',
    '切换模板启停': '模板注册与模板治理',
    '验证模板': '模板注册与模板治理',
    '设置默认模板': '模板注册与模板治理',
    '加入模板候选': '模板注册与模板治理',
    '设置语义默认模板': '模板注册与模板治理',
    '加入语义模板候选': '模板注册与模板治理',
    '查看模板': '标准库/文档/查看类',
}

LOG_ACTION_CATEGORIES = [
    '认证与会话', '报告记录治理', '操作日志治理', '系统设置与运维',
    '权限与用户管理', '模板注册与模板治理', '标准库/文档/查看类', '其他/未分类'
]

TASK_TYPE_OPTIONS = [
    'inspection',
    'reinspection',
    'supplementary',
    'rectification',
]

TASK_STATUS_OPTIONS = [
    'pending_assign',
    'assigned',
    'accepted',
    'in_progress',
    'completed',
    'cancelled',
]

TASK_TYPE_LABELS = {
    'inspection': '常规检测',
    'reinspection': '复检任务',
    'supplementary': '补测任务',
    'rectification': '整改任务',
}

TASK_STATUS_LABELS = {
    'pending_assign': '待指派',
    'assigned': '已指派',
    'accepted': '已接单',
    'in_progress': '执行中',
    'completed': '已完成',
    'cancelled': '已取消',
}


def get_log_action_category(action: str) -> str:
    return LOG_ACTION_CATEGORY_MAP.get((action or '').strip(), '其他/未分类')


def _resolve_browse_path(path_str: str) -> Path:
    raw = (path_str or '').strip()
    candidate = Path(raw).expanduser().resolve() if raw else Path('/Users/fuwuqi').resolve()
    for root in ALLOWED_SETTINGS_BROWSE_ROOTS:
        try:
            candidate.relative_to(root.resolve())
            return candidate
        except Exception:
            continue
    return ALLOWED_SETTINGS_BROWSE_ROOTS[0].resolve()


# 模板基础路径：从配置文件读取，支持 ~ 展开
template_base_config = CFG.get('template_base', '~/公司资料/检测部/检测报告模板')
if template_base_config.startswith('~'):
    TEMPLATE_BASE = Path.home() / template_base_config[2:]  # 去掉 ~/
else:
    TEMPLATE_BASE = Path(template_base_config)
TEMPLATE_BASE = TEMPLATE_BASE.expanduser().resolve()

TEMPLATE_MAP_X1 = [
    ('hospital', 'operating_room', 'Ⅰ级', '医院洁净部/洁净手术部-百级手术室检测报告模板.docx'),
    ('hospital', 'operating_room', 'Ⅱ级', '医院洁净部/洁净手术部-千级手术室检测报告模板.docx'),
    ('hospital', 'operating_room', 'Ⅲ级', '医院洁净部/洁净手术部-万级手术室检测报告模板.docx'),
    ('hospital', 'operating_room', 'Ⅳ级', '医院洁净部/洁净手术部-十万级手术室检测报告模板.docx'),
]

PATHS = CFG.get('paths', {})
STATIC_DIR = BASE_DIR / PATHS.get('static', 'static')
TEMPLATES_DIR = BASE_DIR / PATHS.get('templates', 'templates')
RECORDS_DIR = BASE_DIR / PATHS.get('records', 'records_x1')
REPORTS_DIR = BASE_DIR / PATHS.get('reports', 'reports_x1')
LOGS_DIR = BASE_DIR / PATHS.get('logs', 'logs_x1')
CACHE_DIR = BASE_DIR / PATHS.get('cache', 'cache_x1')
TEMP_DIR = BASE_DIR / PATHS.get('temp', 'temp_x1')
UPLOADS_DIR = BASE_DIR / PATHS.get('uploads', 'uploads_x1')
ADAPTERS_DIR = BASE_DIR / PATHS.get('adapters', 'adapters')
DOCS_DIR = BASE_DIR / PATHS.get('docs', 'docs')
TEMPLATE_CONFIG_FILE = BASE_DIR / 'template_config.json'

FORMAL_RECORDS_BASE = Path('/Users/fuwuqi/公司资料/检测部/原始记录')
FORMAL_REPORTS_BASE = Path('/Users/fuwuqi/公司资料/检测部/检测报告')

def _formal_year_dir(base: Path, year: int) -> Path:
    target = base / str(year)
    target.mkdir(parents=True, exist_ok=True)
    return target

def _safe_filename_part(value: str, fallback: str = '未命名') -> str:
    text = str(value or '').strip()
    if not text:
        text = fallback
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(ch, '_')
    text = text.replace('\n', '_').replace('\r', '_').replace('\t', '_')
    return text[:120].strip() or fallback


def _copy_to_formal_dir(src: Path, base: Path, year: int, target_name=None):
    if not src or not src.exists():
        return {'success': False, 'error': '源文件不存在'}
    try:
        import shutil
        target_dir = _formal_year_dir(base, year)
        target = target_dir / (target_name or src.name)
        shutil.copy2(src, target)
        return {'success': True, 'path': str(target), 'filename': target.name}
    except Exception as e:
        return {'success': False, 'error': str(e)}

for p in [RECORDS_DIR, REPORTS_DIR, LOGS_DIR, CACHE_DIR, TEMP_DIR, UPLOADS_DIR, ADAPTERS_DIR, DOCS_DIR]:
    p.mkdir(parents=True, exist_ok=True)

SECRET_FILE = BASE_DIR / 'data' / 'flask_secret_key.txt'

def _load_or_create_secret_key():
    env_secret = os.getenv('X1_SECRET_KEY', '').strip()
    if env_secret:
        return env_secret
    if SECRET_FILE.exists():
        try:
            existing = SECRET_FILE.read_text(encoding='utf-8').strip()
            if existing:
                return existing
        except Exception:
            pass
    secret = secrets.token_urlsafe(48)
    SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    SECRET_FILE.write_text(secret, encoding='utf-8')
    return secret


def get_x1_data_conn():
    db_path = BASE_DIR / 'data' / 'x1_data.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_business_projects_table():
    conn = get_x1_data_conn()
    try:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS business_projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_name TEXT NOT NULL,
            client_name TEXT DEFAULT '',
            project_address TEXT DEFAULT '',
            contact_name TEXT DEFAULT '',
            contact_phone TEXT DEFAULT '',
            detection_domain TEXT DEFAULT '',
            detection_type TEXT DEFAULT '',
            expected_detection_date TEXT DEFAULT '',
            project_desc TEXT DEFAULT '',
            business_stage TEXT DEFAULT '',
            contract_status TEXT DEFAULT '',
            contract_amount REAL DEFAULT 0,
            inspection_stage TEXT DEFAULT '',
            report_status TEXT DEFAULT '',
            invoice_status TEXT DEFAULT '',
            payment_status TEXT DEFAULT '',
            owner TEXT DEFAULT '',
            remarks TEXT DEFAULT '',
            assigned_to TEXT DEFAULT '',
            assigned_at TEXT DEFAULT '',
            task_status TEXT DEFAULT '',
            created_at TEXT DEFAULT '',
            updated_at TEXT DEFAULT ''
        )
        """)
        # 增量迁移：项目编号字段
        try:
            conn.execute("ALTER TABLE business_projects ADD COLUMN project_no TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # 已存在
        # 增量迁移：已收款金额
        try:
            conn.execute("ALTER TABLE business_projects ADD COLUMN paid_amount REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
        # 增量迁移：报告文件路径（补录场景）
        try:
            conn.execute("ALTER TABLE business_projects ADD COLUMN report_file_path TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        conn.commit()
    finally:
        conn.close()


def _generate_project_no():
    """生成项目编号，格式：PJ-YYYY-NNNN"""
    year = datetime.now().strftime('%Y')
    prefix = f'PJ-{year}-'
    conn = get_x1_data_conn()
    try:
        row = conn.execute(
            "SELECT project_no FROM business_projects "
            "WHERE project_no LIKE ? ORDER BY project_no DESC LIMIT 1",
            (f'{prefix}%',)
        ).fetchone()
        if row and row['project_no']:
            try:
                last_seq = int(row['project_no'].replace(prefix, ''))
            except ValueError:
                last_seq = 0
        else:
            last_seq = 0
        return f'{prefix}{last_seq + 1:04d}'
    finally:
        conn.close()


def serialize_business_project(row):
    if not row:
        return None
    return {
        'id': row['id'],
        'project_no': row['project_no'] or '',
        'project_name': row['project_name'] or '',
        'client_name': row['client_name'] or '',
        'project_address': row['project_address'] or '',
        'contact_name': row['contact_name'] or '',
        'contact_phone': row['contact_phone'] or '',
        'detection_domain': row['detection_domain'] or '',
        'detection_type': row['detection_type'] or '',
        'expected_detection_date': row['expected_detection_date'] or '',
        'project_desc': row['project_desc'] or '',
        'business_stage': row['business_stage'] or '',
        'contract_status': row['contract_status'] or '',
        'contract_amount': row['contract_amount'] or 0,
        'paid_amount': row['paid_amount'] if 'paid_amount' in row.keys() else 0,
        'receivable_amount': round((row['contract_amount'] or 0) - (row['paid_amount'] if 'paid_amount' in row.keys() else 0), 2),
        'inspection_stage': row['inspection_stage'] or '',
        'report_status': row['report_status'] or '',
        'invoice_status': row['invoice_status'] or '',
        'payment_status': row['payment_status'] or '',
        'owner': row['owner'] or '',
        'remarks': row['remarks'] or '',
        'assigned_to': row['assigned_to'] or '',
        'assigned_at': row['assigned_at'] or '',
        'task_status': row['task_status'] or '',
        'created_at': row['created_at'] or '',
        'updated_at': row['updated_at'] or '',
        'source': row['source'] if 'source' in row.keys() else '',
        'has_urge': row['has_urge'] if 'has_urge' in row.keys() else '',
        'report_file_path': row['report_file_path'] if 'report_file_path' in row.keys() else '',
    }


def init_project_tasks_table():
    conn = get_x1_data_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS project_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                task_name TEXT NOT NULL,
                task_type TEXT NOT NULL DEFAULT 'inspection',
                assigned_to INTEGER,
                assigned_at TEXT,
                task_status TEXT NOT NULL DEFAULT 'pending_assign',
                expected_execute_date TEXT,
                started_at TEXT,
                completed_at TEXT,
                remarks TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        cur.execute("CREATE INDEX IF NOT EXISTS idx_project_tasks_project_id ON project_tasks(project_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_project_tasks_assigned_to ON project_tasks(assigned_to)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_project_tasks_status ON project_tasks(task_status)")
        conn.commit()
    finally:
        conn.close()


def _get_task_status_label(status):
    return TASK_STATUS_LABELS.get((status or '').strip(), (status or '').strip())


def _get_task_type_label(task_type):
    return TASK_TYPE_LABELS.get((task_type or '').strip(), (task_type or '').strip())


def _get_business_project_by_id(project_id):
    if not project_id:
        return None
    conn = get_x1_data_conn()
    try:
        return conn.execute("SELECT * FROM business_projects WHERE id=?", (project_id,)).fetchone()
    finally:
        conn.close()


def _get_user_display_name(user_id):
    if not user_id:
        return ''
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT user_id, display_name FROM users WHERE user_id=?",
                (str(user_id),)
            ).fetchone()
            if not row:
                return ''
            return row['display_name'] or row['user_id'] or ''
    except Exception:
        return ''


def serialize_project_task(row, project_row=None):
    if not row:
        return None
    project_name = ''
    client_name = ''
    if project_row:
        project_name = project_row['project_name'] or ''
        client_name = project_row['client_name'] or ''
    assigned_to = row['assigned_to']
    created_by = row['created_by']
    return {
        'id': row['id'],
        'project_id': row['project_id'],
        'project_name': project_name,
        'client_name': client_name,
        'task_name': row['task_name'] or '',
        'task_type': row['task_type'] or '',
        'task_type_label': _get_task_type_label(row['task_type']),
        'assigned_to': assigned_to,
        'assigned_to_name': _get_user_display_name(assigned_to),
        'assigned_at': row['assigned_at'] or '',
        'task_status': row['task_status'] or '',
        'task_status_label': _get_task_status_label(row['task_status']),
        'expected_execute_date': row['expected_execute_date'] or '',
        'started_at': row['started_at'] or '',
        'completed_at': row['completed_at'] or '',
        'remarks': row['remarks'] or '',
        'created_by': created_by,
        'created_by_name': _get_user_display_name(created_by),
        'created_at': row['created_at'] or '',
        'updated_at': row['updated_at'] or '',
    }


def _clean_project_task_payload(data):
    data = data or {}

    def s(key):
        value = data.get(key)
        if value is None:
            return None
        value = str(value).strip()
        return value or None

    def i(key):
        value = data.get(key)
        if value in (None, ''):
            return None
        try:
            return int(value)
        except Exception:
            return None

    payload = {
        'project_id': i('project_id'),
        'task_name': s('task_name'),
        'task_type': s('task_type') or 'inspection',
        'assigned_to': s('assigned_to'),
        'expected_execute_date': s('expected_execute_date'),
        'task_status': s('task_status'),
        'remarks': s('remarks'),
    }

    if payload['task_type'] not in TASK_TYPE_OPTIONS:
        payload['task_type'] = 'inspection'
    if payload['task_status'] and payload['task_status'] not in TASK_STATUS_OPTIONS:
        payload['task_status'] = None
    return payload


def refresh_project_task_summary(project_id):
    if not project_id:
        return
    conn = get_x1_data_conn()
    try:
        rows = conn.execute(
            """
            SELECT * FROM project_tasks
            WHERE project_id=?
            ORDER BY
                CASE task_status
                    WHEN 'in_progress' THEN 1
                    WHEN 'accepted' THEN 2
                    WHEN 'assigned' THEN 3
                    WHEN 'pending_assign' THEN 4
                    WHEN 'completed' THEN 5
                    WHEN 'cancelled' THEN 6
                    ELSE 99
                END,
                updated_at DESC,
                id DESC
            """,
            (project_id,)
        ).fetchall()
        chosen = next((row for row in rows if row['task_status'] != 'cancelled'), None)
        if chosen:
            conn.execute(
                """
                UPDATE business_projects
                SET assigned_to=?, assigned_at=?, task_status=?, updated_at=?
                WHERE id=?
                """,
                (
                    str(chosen['assigned_to'] or ''),
                    chosen['assigned_at'] or '',
                    chosen['task_status'] or '',
                    datetime.now().isoformat(timespec='seconds'),
                    project_id,
                )
            )
        else:
            conn.execute(
                """
                UPDATE business_projects
                SET assigned_to='', assigned_at='', task_status='', updated_at=?
                WHERE id=?
                """,
                (datetime.now().isoformat(timespec='seconds'), project_id)
            )
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 项目状态自动流转
# ============================================================

# 状态流转优先级（数值越大 = 越靠后）
_INSPECTION_STAGE_ORDER = {
    '未安排': 0, '': 0,
    '已排期': 1, '待进场': 2,
    '检测中': 3, '补测中': 3,
    '检测完成': 4, '已结束': 5,
    '检测异常': -1,  # 异常不自动流转
}
_REPORT_STATUS_ORDER = {
    '未开始': 0, '': 0,
    '编制中': 1, '审核中': 2, '待修改': 2, '待出具': 3,
    '已出具': 4, '待客户确认': 5, '客户已确认': 6, '已发送客户': 7,
}


def _auto_advance_project_stage(project_id, target_inspection=None, target_report=None):
    """自动推进项目状态，只前进不后退。
    
    规则：
    - 只在目标状态比当前状态“更靠后”时才更新
    - 异常状态不会被自动覆盖
    - 写操作日志
    """
    if not project_id:
        return
    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM business_projects WHERE id=?", (project_id,)).fetchone()
        if not row:
            return
        
        updates = []
        params = []
        current_ins = (row['inspection_stage'] or '').strip()
        current_rpt = (row['report_status'] or '').strip()
        
        if target_inspection:
            cur_order = _INSPECTION_STAGE_ORDER.get(current_ins, -99)
            tgt_order = _INSPECTION_STAGE_ORDER.get(target_inspection, -99)
            # 只前进，且不覆盖异常状态
            if cur_order >= 0 and tgt_order > cur_order:
                updates.append('inspection_stage=?')
                params.append(target_inspection)
        
        if target_report:
            cur_order = _REPORT_STATUS_ORDER.get(current_rpt, -99)
            tgt_order = _REPORT_STATUS_ORDER.get(target_report, -99)
            if cur_order >= 0 and tgt_order > cur_order:
                updates.append('report_status=?')
                params.append(target_report)
        
        if updates:
            updates.append('updated_at=?')
            params.append(datetime.now().isoformat(timespec='seconds'))
            params.append(project_id)
            conn.execute(
                f"UPDATE business_projects SET {', '.join(updates)} WHERE id=?",
                params
            )
            conn.commit()
            log_action(
                getattr(current_user, 'id', 'system') if hasattr(current_user, 'id') else 'system',
                '项目状态自动流转',
                f'project_id={project_id}',
                f'inspection_stage: {current_ins}→{target_inspection or "-"}, report_status: {current_rpt}→{target_report or "-"}'
            )
    except Exception:
        pass
    finally:
        conn.close()


def _clean_project_payload(data):
    def s(key):
        return str(data.get(key, '') or '').strip()

    raw_amount = data.get('contract_amount', 0)
    try:
        contract_amount = float(raw_amount or 0)
    except Exception:
        contract_amount = 0.0

    raw_paid = data.get('paid_amount', 0)
    try:
        paid_amount = float(raw_paid or 0)
    except Exception:
        paid_amount = 0.0

    return {
        'project_name': s('project_name'),
        'client_name': s('client_name'),
        'project_address': s('project_address'),
        'contact_name': s('contact_name'),
        'contact_phone': s('contact_phone'),
        'detection_domain': s('detection_domain'),
        'detection_type': s('detection_type'),
        'expected_detection_date': s('expected_detection_date'),
        'project_desc': s('project_desc'),
        'business_stage': s('business_stage'),
        'contract_status': s('contract_status'),
        'contract_amount': contract_amount,
        'paid_amount': paid_amount,
        'inspection_stage': s('inspection_stage'),
        'report_status': s('report_status'),
        'invoice_status': s('invoice_status'),
        'payment_status': s('payment_status'),
        'owner': s('owner'),
        'remarks': s('remarks'),
        'assigned_to': s('assigned_to'),
        'assigned_at': s('assigned_at'),
        'task_status': s('task_status'),
    }

app = Flask(__name__, template_folder=str(TEMPLATES_DIR), static_folder=str(STATIC_DIR))
app.secret_key = CFG.get('secret_key') or _load_or_create_secret_key()
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config['COMPRESS_MIMETYPES'] = ['text/html', 'text/css', 'application/json', 'application/javascript', 'text/javascript']
app.config['COMPRESS_MIN_SIZE'] = 500
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = bool(CFG.get('session_cookie_secure', False))
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB
Compress(app)

# 初始化认证系统
login_manager = init_login_manager(app)
init_business_projects_table()
init_project_tasks_table()

# 客户界面路由注册
from customer_routes import register_customer_routes, init_customer_tables
from customer_admin_routes import register_customer_admin_routes
init_customer_tables()
register_customer_routes(app)
register_customer_admin_routes(app)


@app.after_request
def add_no_cache_headers(response):
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


def _same_origin_request() -> bool:
    origin = request.headers.get('Origin', '').strip()
    referer = request.headers.get('Referer', '').strip()
    host_url = request.host_url.rstrip('/')
    if origin:
        return origin.rstrip('/') == host_url
    if referer:
        return referer.startswith(host_url + '/') or referer == host_url
    return bool(request.is_json)


@app.before_request
def enforce_csrf_for_authenticated_writes():
    if request.method not in ('POST', 'PUT', 'PATCH', 'DELETE'):
        return None
    if not current_user.is_authenticated:
        return None
    if request.endpoint in {'login_page', 'admin_api_open_file', 'admin_api_open_feishu_file'}:
        return None
    if not _same_origin_request():
        return jsonify({'success': False, 'error': 'CSRF 校验失败'}), 403
    return None




# ==================== 通知 API ====================

@app.route('/api/notifications')
@login_required
def api_notifications():
    """获取当前用户的通知列表"""
    limit = request.args.get('limit', 30, type=int)
    unread_only = request.args.get('unread_only', '') == '1'
    items = get_notifications(current_user.id, current_user.role, limit=limit, unread_only=unread_only)
    return jsonify({'success': True, 'items': items})


@app.route('/api/notifications/unread_count')
@login_required
def api_notifications_unread_count():
    """获取未读通知数"""
    count = get_unread_count(current_user.id, current_user.role)
    return jsonify({'success': True, 'count': count})


@app.route('/api/notifications/<int:nid>/read', methods=['POST'])
@login_required
def api_notification_mark_read(nid):
    """标记单条已读"""
    mark_read(nid, current_user.id)
    return jsonify({'success': True})


@app.route('/api/notifications/read_all', methods=['POST'])
@login_required
def api_notification_read_all():
    """全部标记已读"""
    mark_all_read(current_user.id, current_user.role)
    return jsonify({'success': True})

@app.route('/admin/api/registrations')
@login_required
@require_permission('admin.users.manage')
def admin_api_registrations():
    """获取客户注册申请列表"""
    from database import get_db
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


@app.route('/admin/api/registrations/<int:reg_id>/approve', methods=['POST'])
@login_required
@require_permission('admin.users.manage')
def admin_api_approve_registration(reg_id):
    """审核通过客户注册"""
    from database import get_db
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
    log_action(current_user.id, 'approve_registration', reg['username'], f"审核通过客户注册：{reg['company']} / {reg['contact_name']}")
    notify_registration_approved(reg['username'])
    return jsonify({'success': True, 'message': '已通过审核，客户可登录使用'})


@app.route('/admin/api/registrations/<int:reg_id>/reject', methods=['POST'])
@login_required
@require_permission('admin.users.manage')
def admin_api_reject_registration(reg_id):
    """驳回客户注册"""
    data = request.get_json(silent=True) or {}
    reason = (data.get('reason') or '').strip() or '未通过审核'
    from database import get_db
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


@app.route('/static/manifest.json')
def x_manifest():
    return jsonify({
        'name': CFG.get('app_name', 'X1 检测记录系统'),
        'short_name': 'X1',
        'display': 'standalone',
        'start_url': '/',
        'background_color': '#ffffff',
        'theme_color': '#667eea',
        'icons': []
    })


def _compute_record_asset_state(record: dict) -> dict:
    files = record.get('files') or []
    report_info = record.get('report_info') or {}
    export_info = record.get('export_info') or {}
    report_file = next((f for f in files if '.filled.' in f.get('name', '')), None) or next((f for f in files if '.bound.' in f.get('name', '')), None)
    raw_excel = next((f for f in files if f.get('name', '').lower().endswith('.xlsx')), None)
    feishu_report_url = record.get('feishu_report_url') or report_info.get('feishu_url') or record.get('feishu_report_open_url') or report_info.get('feishu_open_url') or ''
    feishu_export_url = record.get('feishu_export_url') or export_info.get('feishu_url') or record.get('feishu_export_open_url') or export_info.get('feishu_open_url') or ''
    local_report_ok = bool(report_file)
    local_record_ok = bool(raw_excel)
    feishu_report_ok = bool(feishu_report_url) and record.get('feishu_report_status') != 'failed'
    feishu_record_ok = bool(feishu_export_url) and record.get('feishu_export_status') != 'failed'
    report_ready = bool(record.get('report_success') or record.get('has_report') or report_info.get('filename') or feishu_report_url or local_report_ok)
    raw_ready = bool(record.get('raw_record_success') or record.get('has_export') or export_info.get('filename') or feishu_export_url or local_record_ok)
    issues = []
    if record.get('type') == 'export' and not local_report_ok and not feishu_report_ok:
        issues.append('report_missing')
    if record.get('type') == 'export' and not local_record_ok and not feishu_record_ok:
        issues.append('raw_record_missing')
    if record.get('feishu_report_status') == 'failed':
        issues.append('feishu_report_failed')
    if record.get('feishu_export_status') == 'failed':
        issues.append('feishu_record_failed')
    return {
        'report_file': report_file,
        'raw_excel': raw_excel,
        'local_report_ok': local_report_ok,
        'local_record_ok': local_record_ok,
        'feishu_report_ok': feishu_report_ok,
        'feishu_record_ok': feishu_record_ok,
        'report_ready': report_ready,
        'raw_ready': raw_ready,
        'issues': issues,
        'healthy': len(issues) == 0
    }



@app.route('/api/user')
def api_user_compat():
    if current_user.is_authenticated:
        return jsonify({
            'username': current_user.id,
            'display_name': current_user.display_name,
            'role': current_user.role,
            'department': current_user.department,
            'permissions': sorted(list(current_user.permissions or []))
        })
    return jsonify({
        'username': 'guest',
        'display_name': '访客'
    })


@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        # 支持JSON和表单两种方式
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form
        
        username = data.get('username')
        password = data.get('password')
        remember = data.get('remember', False)
        
        if verify_password(username, password):
            user = get_user(username)
            login_user(user, remember=remember)
            log_action(username, 'login', '', '登录成功')
            
            if request.is_json:
                return jsonify({'success': True, 'redirect': '/'})
            return redirect(url_for('index'))
        
        log_action(username or 'unknown', 'login_failed', '', '密码错误')
        if request.is_json:
            return jsonify({'success': False, 'error': '用户名或密码错误'}), 401
        flash('用户名或密码错误')
        return redirect(url_for('login_page'))
    
    return render_template('login.html', version=APP_VERSION)


@app.route('/register')
def register_page():
    """客户自助注册页面"""
    return render_template('register.html', version=APP_VERSION)


@app.route('/api/register', methods=['POST'])
def api_register():
    """客户自助注册 API：创建待审核客户账号"""
    data = request.get_json(silent=True) or {}
    company = (data.get('company') or '').strip()
    contact_name = (data.get('contact_name') or '').strip()
    phone = (data.get('phone') or '').strip()
    username = (data.get('username') or '').strip()
    password = (data.get('password') or '').strip()
    address = (data.get('address') or '').strip()

    # 校验
    if not company or not contact_name or not phone or not username or not password:
        return jsonify({'success': False, 'message': '请填写所有必填字段'})
    if len(username) < 3 or len(username) > 20:
        return jsonify({'success': False, 'message': '用户名需要3-20个字符'})
    import re as _re
    if not _re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'success': False, 'message': '用户名只能包含字母、数字、下划线'})
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少6位'})
    if not _re.match(r'^1[3-9]\d{9}$', phone):
        return jsonify({'success': False, 'message': '请输入正确的手机号'})

    from database import get_db
    from werkzeug.security import generate_password_hash
    try:
        with get_db() as conn:
            # 检查用户名是否已存在
            existing = conn.execute('SELECT user_id FROM users WHERE user_id = ?', [username]).fetchone()
            if existing:
                return jsonify({'success': False, 'message': '该用户名已被注册'})

            # 创建账号：is_active=0（待审核）
            conn.execute(
                """INSERT INTO users (user_id, display_name, password_hash, role, department, is_active, client_name, created_at)
                   VALUES (?, ?, ?, 'customer', ?, 0, ?, datetime('now', 'localtime'))""",
                [username, contact_name, generate_password_hash(password, method='pbkdf2:sha256'), company, company]
            )

            # 记录注册附加信息到 customer_registrations 表
            _ensure_registration_table(conn)
            conn.execute(
                """INSERT INTO customer_registrations (username, company, contact_name, phone, address, status, created_at)
                   VALUES (?, ?, ?, ?, ?, 'pending', datetime('now', 'localtime'))""",
                [username, company, contact_name, phone, address]
            )
            conn.commit()

        log_action(username, 'customer_register', '', f'客户自助注册：{company} / {contact_name} / {phone}')
        notify_new_registration(company, contact_name, username)
        return jsonify({'success': True, 'message': '注册成功，等待审核'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'注册失败：{str(e)}'})


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


@app.route('/logout')
@login_required
def logout():
    username = current_user.id
    log_action(username, 'logout', '', '登出')
    logout_user()
    return redirect(url_for('login_page'))


@app.route('/api/save', methods=['POST'])
@login_required
def api_save_compat():
    data = request.get_json(silent=True) or {}
    project = data.get('project') if isinstance(data, dict) else None
    if not isinstance(project, dict):
        project = data if isinstance(data, dict) else {}
    draft_id = ''
    if isinstance(data, dict):
        draft_id = (data.get('draft_id') or data.get('record_id') or project.get('record_id') or '').strip()
    # 第二层隔离：非本人草稿拒绝写入
    if draft_id:
        existing = _x_draft_path(draft_id)
        if existing.exists():
            try:
                old = json.loads(existing.read_text(encoding='utf-8'))
                old_inspector = (old.get('project') or {}).get('operator') or (old.get('project') or {}).get('inspector') or ''
                if old_inspector and old_inspector != current_user.id:
                    return jsonify({'success': False, 'error': '这是其他检测员的草稿，不能覆盖保存'}), 403
            except Exception:
                pass
    draft_kind = str(data.get('_draft_kind') or data.get('draft_kind') or '').strip().lower() or 'manual'
    payload = {
        'draft_id': draft_id or f"X1DRAFT_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'schema_version': APP_VERSION,
        'source': 'x1-compat-save',
        'saved_at': _x_now(),
        'draft_kind': draft_kind,
        'project': project,
    }
    payload['project']['record_id'] = payload['draft_id']
    target = _x_draft_path(payload['draft_id'])
    with open(target, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return jsonify({
        'success': True,
        'ok': True,
        'compat': True,
        'draft_id': payload['draft_id'],
        'record_id': payload['draft_id'],
        'saved_at': payload['saved_at'],
        'path': str(target)
    })


@app.route('/')
@login_required
def index():
    if current_user.role == 'customer':
        return redirect('/customer')
    return render_template('record_index.html', version=APP_VERSION, current_user=current_user)


@app.route('/admin')
@login_required
@require_permission('admin.access')
def admin():
    return render_template('admin.html', version=APP_VERSION)


@app.route('/api/system/health')
@login_required
@require_role('admin')
def api_system_health():
    """系统健康状态"""
    from monitor import get_error_logs, get_performance_stats
    
    health = get_system_health()
    recent_errors = get_error_logs(limit=10)
    export_stats = get_performance_stats('export_report', hours=24)
    
    return jsonify({
        'success': True,
        'health': health,
        'recent_errors': recent_errors,
        'performance': {
            'export_report': export_stats
        }
    })



def _settings_defs():
    return [
        {'key':'paths.template_base','label':'模板根目录','type':'path','group':'paths','default':str(TEMPLATE_BASE),'suggested':'~/公司资料/检测部/检测报告模板','requires_restart':1,'sensitive':1,'impact':'修改后可能导致检测报告模板命中失败、正式报告生成异常或模板巡检结果失真。','description':'用于检测报告模板定位；迁移服务器后通常需要重新确认。'},
        {'key':'paths.formal_report_archive','label':'正式检测报告归档目录','type':'path','group':'archive','default':'/Users/fuwuqi/公司资料/检测部/检测报告','suggested':'~/公司资料/检测部/检测报告','requires_restart':0,'sensitive':1,'impact':'修改后可能导致正式检测报告归档到错误目录，影响交付、查找与留档。','description':'检测报告最终正式归档位置；修改前请确认新目录可写。'},
        {'key':'paths.formal_raw_archive','label':'正式原始记录归档目录','type':'path','group':'archive','default':'/Users/fuwuqi/公司资料/检测部/原始记录','suggested':'~/公司资料/检测部/原始记录','requires_restart':0,'sensitive':1,'impact':'修改后可能导致原始记录归档错误，影响内部追溯、复核与年度存档。','description':'原始记录最终正式归档位置；迁移后应重新确认。'},
        {'key':'paths.backup_dir','label':'备份目录','type':'path','group':'paths','default':'/Users/fuwuqi/backups_x1','suggested':'~/backups_x1','requires_restart':0,'sensitive':0,'description':'系统整体备份输出目录；建议放到稳定位置。'},
        {'key':'paths.logs_dir','label':'日志目录','type':'path','group':'paths','default':str(LOGS_DIR),'suggested':'./logs_x1','requires_restart':1,'sensitive':0,'description':'守护与应用日志目录；迁移后建议保留独立日志位置。'},
        {'key':'paths.cache_dir','label':'缓存目录','type':'path','group':'paths','default':str(CACHE_DIR),'suggested':'./cache_x1','requires_restart':1,'sensitive':0,'description':'缓存与中间结果目录；异常时可作为清理对象。'},
        {'key':'paths.temp_dir','label':'临时目录','type':'path','group':'paths','default':str(BASE_DIR / 'tmp_x1'),'suggested':'./tmp_x1','requires_restart':1,'sensitive':0,'description':'中间处理临时目录；建议与正式归档目录分开。'},
        {'key':'export.enable_report_docx','label':'启用检测报告导出','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'description':'关闭后将停止检测报告 Word 导出链，仅用于特殊维护。'},
        {'key':'export.enable_raw_record','label':'启用原始记录导出','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'description':'关闭后将停止原始记录导出链，仅用于特殊维护。'},
        {'key':'template.enable_gate','label':'启用模板命中闸门','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'impact':'关闭后会放松正式检测报告模板约束，可能让未命中模板的报告继续流转，带来版式或对象映射风险。','description':'控制检测报告是否必须先命中合法模板，正式环境建议开启。'},
        {'key':'template.gate_mode','label':'模板命中模式','type':'string','group':'export','default':'strict','requires_restart':0,'sensitive':1,'impact':'从严格切到宽松后，可能放过口径不完整或模板映射异常的对象。','description':'严格模式要求符合模板规则；宽松模式仅用于排障。'},
        {'key':'template.allow_upload','label':'允许模板上传','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'impact':'开启模板上传会增加模板被替换风险；关闭则会限制后台模板维护能力。','description':'控制后台是否允许上传/替换模板；正式环境建议谨慎开启。'},
        {'key':'feishu.enabled','label':'启用飞书上传','type':'bool','group':'feishu','default':True,'requires_restart':0,'sensitive':1,'impact':'关闭后导出文件将不再自动上传飞书，可能影响客户交付与内部同步。','description':'控制是否执行飞书上传主链；迁移后应先确认配置状态。'},
        {'key':'feishu.app_id','label':'飞书 App ID','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'impact':'修改错误会导致飞书认证失败，自动上传链路中断。','description':'飞书开放平台应用 App ID；保存后不会在页面明文回显。'},
        {'key':'feishu.app_secret','label':'飞书 App Secret','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'impact':'修改错误会导致飞书 token 获取失败，自动上传完全不可用。','description':'飞书开放平台应用密钥；仅支持重新填写，不做明文展示。'},
        {'key':'feishu.folder_reports','label':'飞书检测报告目录 Token','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'description':'检测报告上传父目录 token；迁移后需重新核对。'},
        {'key':'feishu.folder_exports','label':'飞书原始记录目录 Token','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'description':'原始记录上传父目录 token；迁移后需重新核对。'},
        {'key':'feishu.auto_upload_report','label':'检测报告自动上传飞书','type':'bool','group':'feishu','default':True,'requires_restart':0,'sensitive':0,'description':'检测报告成功生成后是否自动上传到飞书。'},
        {'key':'feishu.auto_upload_raw','label':'原始记录自动上传飞书','type':'bool','group':'feishu','default':True,'requires_restart':0,'sensitive':0,'description':'原始记录成功生成后是否自动上传到飞书。'},
        {'key':'security.session_cookie_secure','label':'启用 Secure Cookie','type':'bool','group':'security','default':bool(CFG.get('session_cookie_secure', False)),'requires_restart':1,'sensitive':1,'impact':'在 HTTP 环境误开启可能导致会话异常；关闭则会降低 HTTPS 环境下的会话安全性。','description':'正式 HTTPS 部署建议开启；纯局域网 HTTP 环境需谨慎。'},
        {'key':'security.allow_delete_record','label':'允许删除记录','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':1,'impact':'开启后用户可删除记录；关闭则会影响后台治理效率但能保护正式数据。','description':'关闭后记录删除相关操作将被阻止，用于保护正式数据。'},
        {'key':'security.allow_cleanup_trash','label':'允许清空回收站','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':1,'impact':'开启后可能发生不可恢复删除；关闭则会阻止永久清理。','description':'关闭后将禁止永久清理回收站，降低不可恢复删除风险。'},
        {'key':'security.allow_file_preview','label':'允许文件预览','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':0,'description':'控制后台文件预览入口；关闭可缩小暴露面。'},
        {'key':'security.allow_file_download','label':'允许文件下载','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':0,'description':'控制本地文件下载能力；建议结合角色权限一起使用。'},
        {'key':'ops.log_retention_days','label':'日志保留天数','type':'int','group':'ops','default':30,'requires_restart':0,'sensitive':0,'description':'超过保留期的日志可纳入清理策略，避免长期堆积。'},
        {'key':'ops.trash_retention_days','label':'回收站保留天数','type':'int','group':'ops','default':30,'requires_restart':0,'sensitive':0,'description':'控制回收站默认保留时长，平衡恢复能力与磁盘占用。'},
    ]


def _setting_defs_map():
    return {item['key']: item for item in _settings_defs()}


def _cast_setting_value(value, value_type):
    if value_type == 'bool':
        return bool(value) if isinstance(value, bool) else str(value).strip().lower() in ('1','true','yes','on')
    if value_type == 'int':
        return int(value)
    return '' if value is None else str(value)


def _load_system_settings():
    defs = _settings_defs()
    values = {}
    feishu_cfg = get_feishu_config() or {}
    feishu_folders = feishu_cfg.get('folders', {}) if isinstance(feishu_cfg.get('folders'), dict) else {}
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM system_settings').fetchall()
    row_map = {row['setting_key']: row for row in rows}
    for item in defs:
        row = row_map.get(item['key'])
        raw_value = row['setting_value'] if row else item['default']
        if item['key'] == 'feishu.app_id':
            raw_value = feishu_cfg.get('app_id', '')
        elif item['key'] == 'feishu.app_secret':
            raw_value = '********' if feishu_cfg.get('app_secret') else ''
        elif item['key'] == 'feishu.folder_reports':
            raw_value = feishu_folders.get('reports', '')
        elif item['key'] == 'feishu.folder_exports':
            raw_value = feishu_folders.get('exports', '')
        if row and item['type'] == 'bool':
            try:
                raw_value = json.loads(raw_value)
            except Exception:
                pass
        values[item['key']] = {
            'key': item['key'],
            'label': item['label'],
            'group': item['group'],
            'type': item['type'],
            'value': _cast_setting_value(raw_value, item['type']),
            'default': item['default'],
            'suggested': item.get('suggested', ''),
            'requires_restart': bool(item['requires_restart']),
            'is_sensitive': bool(item['sensitive']),
            'description': item['description'],
            'impact': item.get('impact', ''),
            'updated_at': row['updated_at'] if row else '',
            'updated_by': row['updated_by'] if row else '',
        }
        if item['type'] == 'path':
            p = Path(str(values[item['key']]['value'])).expanduser()
            values[item['key']]['path_status'] = {
                'exists': p.exists(),
                'readable': os.access(p, os.R_OK) if p.exists() else False,
                'writable': os.access(p, os.W_OK) if p.exists() else False,
                'is_dir': p.is_dir() if p.exists() else False,
            }
    return values


def _setting_enabled(key, fallback=False):
    try:
        values = _load_system_settings()
        if key in values:
            return bool(values[key]['value'])
    except Exception:
        pass
    return fallback


def _save_feishu_config_from_settings(updates):
    if not any(k in updates for k in ('feishu.app_id', 'feishu.app_secret', 'feishu.folder_reports', 'feishu.folder_exports')):
        return
    config_path = BASE_DIR / 'feishu_config.json'
    current = get_feishu_config() or {}
    folders = current.get('folders', {}) if isinstance(current.get('folders'), dict) else {}
    app_secret = current.get('app_secret', '')
    if updates.get('feishu.app_secret') and str(updates.get('feishu.app_secret')).strip() != '********':
        app_secret = str(updates.get('feishu.app_secret')).strip()
    current.update({
        'app_id': str(updates.get('feishu.app_id', current.get('app_id', ''))).strip(),
        'app_secret': app_secret,
        'folders': {
            'reports': str(updates.get('feishu.folder_reports', folders.get('reports', ''))).strip(),
            'exports': str(updates.get('feishu.folder_exports', folders.get('exports', ''))).strip(),
        }
    })
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(current, f, ensure_ascii=False, indent=2)


@app.route('/admin/settings')
@login_required
@require_role('admin')
def admin_settings_page():
    return redirect('/admin')


@app.route('/admin/api/settings')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings():
    values = _load_system_settings()
    groups = {
        'basic': {'title':'基础信息','items':[]},
        'paths': {'title':'路径设置','items':[]},
        'archive': {'title':'正式归档设置','items':[]},
        'export': {'title':'模板与导出设置','items':[]},
        'template': {'title':'模板与导出设置','items':[]},
        'feishu': {'title':'飞书与外部集成设置','items':[]},
        'security': {'title':'权限与安全设置','items':[]},
        'ops': {'title':'运行与维护设置','items':[]},
    }
    for item in values.values():
        groups.setdefault(item['group'], {'title':item['group'], 'items':[]})['items'].append(item)
    basic_items = [
        {'label':'系统名称','value':CFG.get('app_name','X1 检测记录系统'),'description':'显示当前系统名称，仅用于确认当前实例身份。'},
        {'label':'当前版本','value':CFG.get('version','-'),'description':'显示当前系统版本，用于迁移后核对部署版本是否正确。'},
        {'label':'当前主机名','value':os.uname().nodename,'description':'显示当前 macOS 主机名，迁移新服务器后应首先核对。'},
        {'label':'当前访问地址','value':f'{APP_HOST}:{APP_PORT}','description':'显示当前服务监听地址与端口，用于确认浏览器访问入口。'},
        {'label':'配置文件路径','value':str(BASE_DIR / 'x1_config.json'),'description':'显示当前基础配置文件位置，便于排障和迁移核对。'},
        {'label':'飞书配置状态','value':'已配置' if get_feishu_config() else '未配置','description':'用于快速判断移机后飞书配置是否已落地。'},
        {'label':'部署形态','value':'固定 macOS 主机 + 浏览器访问','description':'当前正式主路线，不再以每人本地安装客户端作为主思路。'},
        {'label':'系统设置权限','value':'仅 admin 可查看和修改','description':'系统设置涉及高风险运行参数，当前已收紧为 admin 独占。'},
        {'label':'文档主入口','value':'X1 最终交付汇报摘要 / X1 交付总览入口（总监版）','description':'后台系统文档区优先阅读的两份 A 类活文档。'},
        {'label':'当前治理重点','value':'系统设置 V2 / 权限安全收口 / 统一部署迁移治理','description':'根据当前后台系统文档与近期执行面整理出的实时重点。'},
    ]
    groups['basic']['items'] = basic_items
    return jsonify({'success': True, 'groups': groups})


@app.route('/admin/api/settings', methods=['PUT'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_update():
    data = request.get_json(silent=True) or {}
    updates = data.get('updates') or {}
    defs = _setting_defs_map()
    now = datetime.now().isoformat()
    changed = []
    with get_db() as conn:
        for key, value in updates.items():
            if key not in defs:
                continue
            item = defs[key]
            casted = _cast_setting_value(value, item['type'])
            if key == 'feishu.app_secret' and str(casted).strip() == '********':
                continue
            conn.execute(
                '''INSERT INTO system_settings (setting_key, setting_value, value_type, group_name, description, requires_restart, is_sensitive, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value, value_type=excluded.value_type, group_name=excluded.group_name,
                   description=excluded.description, requires_restart=excluded.requires_restart, is_sensitive=excluded.is_sensitive, updated_at=excluded.updated_at, updated_by=excluded.updated_by''',
                (key, json.dumps(casted, ensure_ascii=False) if item['type']=='bool' else str(casted), item['type'], item['group'], item['description'], 1 if item['requires_restart'] else 0, 1 if item['sensitive'] else 0, now, current_user.id)
            )
            changed.append({'key': key, 'value': casted})
    if changed:
        _save_feishu_config_from_settings(updates)
        log_action(current_user.id, '更新系统设置', 'system_settings', json.dumps(changed, ensure_ascii=False))
    return jsonify({'success': True, 'changed': changed})


@app.route('/admin/api/settings/path_probe', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_path_probe():
    values = _load_system_settings()
    targets = [
        ('模板根目录', values['paths.template_base']['value']),
        ('正式检测报告归档目录', values['paths.formal_report_archive']['value']),
        ('正式原始记录归档目录', values['paths.formal_raw_archive']['value']),
        ('备份目录', values['paths.backup_dir']['value']),
        ('日志目录', values['paths.logs_dir']['value']),
        ('缓存目录', values['paths.cache_dir']['value']),
        ('临时目录', values['paths.temp_dir']['value']),
    ]
    result = []
    for label, path in targets:
        p = Path(str(path)).expanduser()
        result.append({'label': label, 'path': str(p), 'exists': p.exists(), 'readable': os.access(p, os.R_OK) if p.exists() else False, 'writable': os.access(p, os.W_OK) if p.exists() else False})
    log_action(current_user.id, '执行路径巡检', 'system_settings', json.dumps(result, ensure_ascii=False))
    return jsonify({'success': True, 'results': result})


@app.route('/admin/api/settings/ensure_path', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_ensure_path():
    data = request.get_json(silent=True) or {}
    key = str(data.get('key', '')).strip()
    values = _load_system_settings()
    item = values.get(key)
    if not item:
        return jsonify({'success': False, 'error': '配置项不存在'}), 404
    path = Path(str(item['value'])).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    log_action(current_user.id, '创建系统设置目录', key, str(path))
    return jsonify({'success': True, 'path': str(path)})


@app.route('/admin/api/settings/test_feishu', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_test_feishu():
    cfg = get_feishu_config() or {}
    token = get_feishu_token()
    reports_token = bool((cfg.get('folders') or {}).get('reports'))
    exports_token = bool((cfg.get('folders') or {}).get('exports'))
    reports_meta = get_feishu_folder_meta('reports') if token and reports_token else {'mode': 'missing'}
    exports_meta = get_feishu_folder_meta('exports') if token and exports_token else {'mode': 'missing'}
    reports_folder_ok = bool(reports_meta.get('resolved_token')) if token and reports_token else False
    exports_folder_ok = bool(exports_meta.get('resolved_token')) if token and exports_token else False

    warnings = []
    if reports_meta.get('mode') == 'year-root':
        warnings.append('检测报告目录当前仍为按年模式；如需按月自动切换，请将 token 指向月目录父目录。')
    if exports_meta.get('mode') == 'year-root':
        warnings.append('原始记录目录当前仍为按年模式；如需按月自动切换，请将 token 指向月目录父目录。')
    if reports_meta.get('mode') == 'month-root' and not reports_meta.get('month_matches'):
        warnings.append(f"检测报告目录尚未命中本月目录 {reports_meta.get('current_month')}，系统将在首次上传时自动创建。")
    if exports_meta.get('mode') == 'month-root' and not exports_meta.get('month_matches'):
        warnings.append(f"原始记录目录尚未命中本月目录 {exports_meta.get('current_month')}，系统将在首次上传时自动创建。")

    result = {
        'has_app_id': bool(cfg.get('app_id')),
        'has_app_secret': bool(cfg.get('app_secret')),
        'has_reports_folder': reports_token,
        'has_exports_folder': exports_token,
        'token_ok': bool(token),
        'reports_folder_ok': reports_folder_ok,
        'exports_folder_ok': exports_folder_ok,
        'reports_meta': reports_meta,
        'exports_meta': exports_meta,
        'warnings': warnings,
        'message': '飞书配置有效' if (token and reports_folder_ok and exports_folder_ok) else '飞书配置未完全通过，请检查凭证与目录 token'
    }
    log_action(current_user.id, '测试飞书配置', 'system_settings', json.dumps(result, ensure_ascii=False))
    return jsonify({'success': True, 'result': result})


@app.route('/admin/api/settings/browse_path')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings_browse_path():
    path = _resolve_browse_path(request.args.get('path', ''))
    parent = str(path.parent) if path != path.parent else str(path)
    entries = []
    try:
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.name.startswith('.'):
                continue
            if not child.is_dir():
                continue
            entries.append({'name': child.name, 'path': str(child), 'writable': os.access(child, os.W_OK)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': True, 'current_path': str(path), 'parent_path': parent, 'entries': entries, 'roots': [str(p) for p in ALLOWED_SETTINGS_BROWSE_ROOTS]})


@app.route('/admin/api/settings/native_choose_path', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_native_choose_path():
    script = 'POSIX path of (choose folder with prompt "请选择系统设置要使用的目录")'
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=120)
    except Exception as e:
        return jsonify({'success': False, 'error': f'原生路径选择器执行失败: {e}'}), 500
    if result.returncode != 0:
        stderr = (result.stderr or '').strip()
        if '-128' in stderr:
            return jsonify({'success': False, 'cancelled': True, 'error': '已取消选择'}), 400
        return jsonify({'success': False, 'error': stderr or '原生路径选择失败'}), 500
    selected = (result.stdout or '').strip()
    if not selected:
        return jsonify({'success': False, 'error': '未返回路径'}), 500
    resolved = _resolve_browse_path(selected)
    return jsonify({'success': True, 'path': str(resolved)})


@app.route('/admin/api/settings/create_subdir', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_create_subdir():
    data = request.get_json(silent=True) or {}
    base_path = _resolve_browse_path(data.get('base_path', ''))
    name = str(data.get('name', '')).strip()
    if not name or any(x in name for x in ('/', '\\', '..')):
        return jsonify({'success': False, 'error': '目录名称不合法'}), 400
    target = base_path / name
    target.mkdir(parents=False, exist_ok=True)
    log_action(current_user.id, '创建子目录', 'system_settings', str(target))
    return jsonify({'success': True, 'path': str(target)})


@app.route('/admin/api/settings/backup_now', methods=['POST'])
@login_required
@require_permission('admin.maintenance.run')
def admin_api_settings_backup_now():
    values = _load_system_settings()
    data = request.get_json(silent=True) or {}
    backup_dir = Path(str(values['paths.backup_dir']['value'])).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)

    version = str(CFG.get('version', APP_VERSION)).strip() or APP_VERSION
    version_updated = False
    if data.get('updateVersion'):
        new_version = str(data.get('version', '') or '').strip()
        if not new_version:
            return jsonify({'success': False, 'error': '版本号不能为空'}), 400
        CFG['version'] = new_version
        cfg_path = BASE_DIR / 'x1_config.json'
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(CFG, f, ensure_ascii=False, indent=2)
            version = new_version
            version_updated = True
        except Exception as e:
            return jsonify({'success': False, 'error': f'更新版本号失败: {e}'}), 500

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = str(data.get('backupName', '') or '').strip() if data.get('updateVersion') else ''
    if backup_name:
        safe_name = ''.join(ch if ch.isalnum() or ch in ('-','_') else '_' for ch in backup_name)
    else:
        safe_name = f'X1_{version}_manual_backup'
    backup_file = backup_dir / f'{safe_name}_{ts}.tar.gz'
    import tarfile
    with tarfile.open(backup_file, 'w:gz') as tar:
        tar.add(str(BASE_DIR), arcname=BASE_DIR.name)
    log_action(current_user.id, '执行立即备份', 'system_settings', str(backup_file))
    return jsonify({'success': True, 'backup_file': str(backup_file), 'size': backup_file.stat().st_size, 'version_updated': version_updated, 'version': version})


def _get_settings_backup_dir() -> Path:
    settings_values = _load_system_settings()
    return Path(str(settings_values.get('paths.backup_dir', {}).get('value', BASE_DIR / 'backups'))).expanduser()


def _is_allowed_backup_file(path: Path) -> bool:
    try:
        backup_dir = _get_settings_backup_dir().resolve()
        path.resolve().relative_to(backup_dir)
        return path.is_file() and path.name.endswith('.tar.gz')
    except Exception:
        return False


def _guess_backup_version(name: str) -> str:
    m = re.search(r'(X\d+(?:\.\d+)*)', name or '')
    return m.group(1) if m else ''


def _list_backup_files():
    backup_dir = _get_settings_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for fp in sorted(backup_dir.glob('*.tar.gz'), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            'name': fp.name,
            'path': str(fp),
            'size': fp.stat().st_size,
            'mtime': datetime.fromtimestamp(fp.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'version_guess': _guess_backup_version(fp.name),
            'restorable': True,
            'type': 'full_backup'
        })
    return items


def _extract_backup_summary(backup_path: Path):
    root_names = []
    has = {'app_x1.py': False, 'static/record.js': False, 'templates/record_index.html': False, 'x1_config.json': False}
    try:
        with tarfile.open(backup_path, 'r:gz') as tf:
            members = tf.getmembers()
            for m in members[:5000]:
                parts = [x for x in (m.name or '').split('/') if x]
                if parts:
                    root = parts[0]
                    if root not in root_names:
                        root_names.append(root)
                norm = '/'.join(parts[1:]) if len(parts) > 1 else (parts[0] if parts else '')
                if norm in has:
                    has[norm] = True
    except Exception as e:
        return {'ok': False, 'error': str(e), 'root_names': root_names, 'checks': has}
    return {'ok': True, 'root_names': root_names, 'checks': has}


def _safe_rmtree(path: Path):
    if path.exists():
        shutil.rmtree(path)


def _get_listener_pid(port: int):
    try:
        out = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'], capture_output=True, text=True, timeout=8)
        pid = (out.stdout or '').strip().splitlines()
        return pid[0].strip() if pid else ''
    except Exception:
        return ''


def _get_process_cwd(pid: str):
    if not pid:
        return ''
    try:
        out = subprocess.run(['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'], capture_output=True, text=True, timeout=8)
        for line in (out.stdout or '').splitlines():
            if line.startswith('n'):
                return line[1:].strip()
    except Exception:
        return ''
    return ''


def _health_json():
    try:
        return get_system_health() or {}
    except Exception:
        return {}


@app.route('/admin/api/settings/backups')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings_backups():
    return jsonify({'success': True, 'items': _list_backup_files(), 'backup_dir': str(_get_settings_backup_dir())})


@app.route('/admin/api/settings/backups/<path:name>')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings_backup_detail(name):
    backup_path = (_get_settings_backup_dir() / Path(name).name)
    if not _is_allowed_backup_file(backup_path):
        return jsonify({'success': False, 'error': '备份文件不存在或不在允许目录中'}), 404
    summary = _extract_backup_summary(backup_path)
    return jsonify({'success': True, 'name': backup_path.name, 'size': backup_path.stat().st_size, 'mtime': datetime.fromtimestamp(backup_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'), 'version_guess': _guess_backup_version(backup_path.name), 'summary': summary})


@app.route('/admin/api/settings/restore/full', methods=['POST'])
@login_required
@require_permission('admin.maintenance.run')
def admin_api_settings_restore_full():
    data = request.get_json(silent=True) or {}
    backup_name = Path(str(data.get('backup_name', '') or '').strip()).name
    confirm = str(data.get('confirm', '') or '').strip()
    if confirm != 'RESTORE':
        return jsonify({'success': False, 'error': '确认词不正确'}), 400
    if not backup_name:
        return jsonify({'success': False, 'error': '缺少备份名称'}), 400

    backup_path = _get_settings_backup_dir() / backup_name
    if not _is_allowed_backup_file(backup_path):
        return jsonify({'success': False, 'error': '备份文件不存在或不在允许目录中'}), 404

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    snapshot_dir = _get_settings_backup_dir() / f'pre_restore_snapshot_{ts}'
    renamed_dir = BASE_DIR.parent / f'{BASE_DIR.name}_before_restore_{ts}'
    temp_extract_dir = Path(tempfile.mkdtemp(prefix='x1_restore_', dir=str(_get_settings_backup_dir())))
    restore_log = LOGS_DIR / f'manual_restore_{ts}.log'
    kept_dirs = ['records_x1', 'reports_x1', 'uploads_x1', 'logs', 'logs_x1']
    rebuilt_dirs = ['cache_x1', 'temp_x1']

    def _w(line: str):
        restore_log.parent.mkdir(parents=True, exist_ok=True)
        with open(restore_log, 'a', encoding='utf-8') as f:
            f.write(line.rstrip() + '\n')

    try:
        _w(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] operator={current_user.id} backup={backup_path}')
        snapshot_dir.mkdir(parents=True, exist_ok=False)
        shutil.copytree(BASE_DIR, snapshot_dir / BASE_DIR.name)
        _w(f'snapshot={snapshot_dir / BASE_DIR.name}')

        with tarfile.open(backup_path, 'r:gz') as tf:
            tf.extractall(temp_extract_dir)
        roots = [p for p in temp_extract_dir.iterdir() if p.is_dir()]
        if not roots:
            raise RuntimeError('备份包解压后未找到项目目录')
        extracted_root = min(roots, key=lambda p: len(str(p)))

        for d in kept_dirs:
            src = BASE_DIR / d
            if src.exists():
                shutil.copytree(src, temp_extract_dir / '__kept__' / d)
        _w(f'kept_dirs={kept_dirs}')

        os.rename(BASE_DIR, renamed_dir)
        os.rename(extracted_root, BASE_DIR)
        _w(f'renamed_old={renamed_dir}')

        kept_root = temp_extract_dir / '__kept__'
        for d in kept_dirs:
            src = kept_root / d
            dst = BASE_DIR / d
            if dst.exists():
                _safe_rmtree(dst) if dst.is_dir() else dst.unlink()
            if src.exists():
                shutil.copytree(src, dst)
        for d in rebuilt_dirs:
            dst = BASE_DIR / d
            if dst.exists():
                _safe_rmtree(dst)
            dst.mkdir(parents=True, exist_ok=True)

        restart_script = BASE_DIR / 'restart_x1_daemon.sh'
        restart_proc = subprocess.run([str(restart_script)], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=180)
        listener_pid = _get_listener_pid(APP_PORT)
        listener_cwd = _get_process_cwd(listener_pid)
        health = _health_json()
        health_ok = bool(health.get('success'))
        cwd_ok = str(listener_cwd).strip() == str(BASE_DIR)
        restart_ok = restart_proc.returncode == 0
        _w(f'restart_rc={restart_proc.returncode}')
        if restart_proc.stdout:
            _w('restart_stdout_begin')
            _w(restart_proc.stdout)
            _w('restart_stdout_end')
        if restart_proc.stderr:
            _w('restart_stderr_begin')
            _w(restart_proc.stderr)
            _w('restart_stderr_end')
        _w(f'listener_pid={listener_pid}')
        _w(f'listener_cwd={listener_cwd}')
        _w(f'health_after_restore={json.dumps(health, ensure_ascii=False)}')

        result_payload = {
            'backup_name': backup_path.name,
            'snapshot_path': str(snapshot_dir / BASE_DIR.name),
            'renamed_dir': str(renamed_dir),
            'kept_dirs': kept_dirs,
            'rebuilt_dirs': rebuilt_dirs,
            'log_path': str(restore_log),
            'health': health,
            'version': load_x1_config(BASE_DIR).get('version', APP_VERSION),
            'restart_rc': restart_proc.returncode,
            'listener_pid': listener_pid,
            'listener_cwd': listener_cwd,
            'port': APP_PORT,
            'restart_stdout': (restart_proc.stdout or '')[-4000:]
        }

        if not restart_ok:
            log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'restart_failed'}, ensure_ascii=False))
            return jsonify({'success': False, 'error': '还原完成，但自动重启失败', **result_payload}), 500
        if not health_ok:
            log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'health_failed'}, ensure_ascii=False))
            return jsonify({'success': False, 'error': '还原完成，但健康检查失败', **result_payload}), 500
        if not cwd_ok:
            log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'cwd_mismatch'}, ensure_ascii=False))
            return jsonify({'success': False, 'error': '还原完成，但在线进程未切到新目录', **result_payload}), 500

        log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'success'}, ensure_ascii=False))
        return jsonify({'success': True, **result_payload})
    except Exception as e:
        _w(f'error={e}')
        return jsonify({'success': False, 'error': str(e), 'log_path': str(restore_log)}), 500
    finally:
        try:
            _safe_rmtree(temp_extract_dir)
        except Exception:
            pass


@app.route('/admin/templates')
@login_required
@require_permission('admin.templates.view')
def admin_templates():
    """模板管理页面"""
    return render_template('templates.html')


@app.route('/admin/standards')
@login_required
@require_permission('admin.standards.view')
def admin_standards():
    """标准数据库管理页面"""
    return render_template('standards.html')


@app.route('/admin/monitor')
@login_required
@require_permission('admin.stats.view')
def admin_monitor():
    """系统监控页面"""
    return render_template('monitor.html')


@app.route('/admin/api/docs/<doc_name>')
@login_required
@require_permission('admin.docs.view')
def admin_api_docs(doc_name):
    """读取文档内容"""
    import pathlib
    allowed = {'ARCHITECTURE': 'ARCHITECTURE.md', 'API': 'API.md'}
    if doc_name not in allowed:
        return jsonify({'error': '文档不存在'}), 404
    doc_path = pathlib.Path(__file__).parent / 'docs' / allowed[doc_name]
    if not doc_path.exists():
        return jsonify({'error': '文档文件不存在'}), 404
    return jsonify({'content': doc_path.read_text(encoding='utf-8')})


@app.route('/admin/api/workspace_doc')
@login_required
@require_permission('admin.docs.view')
def admin_api_workspace_doc():
    """读取 workspace 中已批准的交付/收口文档"""
    allowed = {
        'X1_系统当前版本说明.md',
        'X1_版本号管理规则.md',
        'X1_系统架构说明.md',
        'X1_系统接口说明.md',
        'X1_生产主链设计说明.md',
        'X1_代码统计.md',
        'X1 常见问题排障手册.md',
        'X1 运维启动-停止-验活说明.md',
        'X1 部署与迁移说明.md',
        'X1 飞书上传失败治理 SOP.md',
    }
    requested = request.args.get('path', '').strip()
    if not requested:
        return jsonify({'error': '缺少 path 参数'}), 400
    doc_path = Path(requested)
    if doc_path.name not in allowed:
        return jsonify({'error': '文档未授权'}), 403
    if not doc_path.exists() or not doc_path.is_file():
        return jsonify({'error': '文档不存在'}), 404
    return jsonify({'content': doc_path.read_text(encoding='utf-8')})



@app.route('/admin/api/business_projects')
@login_required
@require_permission('admin.projects.view')
def admin_api_business_projects():
    keyword = (request.args.get('keyword') or '').strip()
    business_stage = (request.args.get('business_stage') or '').strip()
    contract_status = (request.args.get('contract_status') or '').strip()
    inspection_stage = (request.args.get('inspection_stage') or '').strip()
    report_status = (request.args.get('report_status') or '').strip()
    invoice_status = (request.args.get('invoice_status') or '').strip()
    payment_status = (request.args.get('payment_status') or '').strip()
    owner = (request.args.get('owner') or '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except Exception:
        page = 1
    try:
        page_size = max(1, min(100, int(request.args.get('page_size', 20))))
    except Exception:
        page_size = 20
    where = ['1=1']
    params = []
    if keyword:
        kw = f'%{keyword}%'
        where.append('(project_name LIKE ? OR client_name LIKE ? OR owner LIKE ? OR remarks LIKE ?)')
        params.extend([kw, kw, kw, kw])
    if business_stage:
        where.append('business_stage = ?')
        params.append(business_stage)
    if contract_status:
        where.append('contract_status = ?')
        params.append(contract_status)
    if inspection_stage:
        where.append('inspection_stage = ?')
        params.append(inspection_stage)
    if report_status:
        where.append('report_status = ?')
        params.append(report_status)
    if invoice_status:
        where.append('invoice_status = ?')
        params.append(invoice_status)
    if payment_status:
        where.append('payment_status = ?')
        params.append(payment_status)
    if owner:
        where.append('owner LIKE ?')
        params.append(f'%{owner}%')
    where_sql = ' AND '.join(where)
    offset = (page - 1) * page_size
    conn = get_x1_data_conn()
    try:
        total = conn.execute(f'SELECT COUNT(*) AS c FROM business_projects WHERE {where_sql}', params).fetchone()['c']
        agg = conn.execute(
            f'SELECT COALESCE(SUM(contract_amount),0) AS sum_contract, COALESCE(SUM(paid_amount),0) AS sum_paid FROM business_projects WHERE {where_sql}',
            params
        ).fetchone()
        rows = conn.execute(
            f'''SELECT * FROM business_projects WHERE {where_sql} ORDER BY updated_at DESC, id DESC LIMIT ? OFFSET ?''',
            params + [page_size, offset]
        ).fetchall()
        sum_contract = round(agg['sum_contract'], 2)
        sum_paid = round(agg['sum_paid'], 2)
        return jsonify({
            'success': True,
            'items': [serialize_business_project(r) for r in rows],
            'total': total, 'page': page, 'page_size': page_size,
            'summary': {
                'contract_amount': sum_contract,
                'paid_amount': sum_paid,
                'receivable_amount': round(sum_contract - sum_paid, 2),
            }
        })
    finally:
        conn.close()


@app.route('/admin/api/business_projects/summary')
@login_required
@require_permission('admin.projects.view')
def admin_api_business_projects_summary():
    conn = get_x1_data_conn()
    try:
        total_projects = conn.execute("SELECT COUNT(*) AS c FROM business_projects").fetchone()['c']
        inspecting_projects = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE inspection_stage='检测中'").fetchone()['c']
        pending_reports = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE report_status IN ('编制中','审核中','待修改','待出具')").fetchone()['c']
        pending_invoices = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE invoice_status IN ('未开票','待开票','部分开票')").fetchone()['c']
        pending_payments = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE payment_status IN ('未回款','部分回款','逾期未回款')").fetchone()['c']
        contract_total_amount = conn.execute("SELECT COALESCE(SUM(contract_amount),0) AS s FROM business_projects").fetchone()['s']
        paid_total_amount = conn.execute("SELECT COALESCE(SUM(paid_amount),0) AS s FROM business_projects").fetchone()['s']
        completed_projects = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE business_stage='已完成'").fetchone()['c']
        return jsonify({'success': True, 'summary': {
            'total_projects': total_projects,
            'inspecting_projects': inspecting_projects,
            'pending_reports': pending_reports,
            'pending_invoices': pending_invoices,
            'pending_payments': pending_payments,
            'contract_total_amount': round(contract_total_amount, 2),
            'paid_total_amount': round(paid_total_amount, 2),
            'receivable_total_amount': round(contract_total_amount - paid_total_amount, 2),
            'completed_projects': completed_projects,
        }})
    finally:
        conn.close()


@app.route('/admin/api/business_projects/<int:project_id>')
@login_required
@require_permission('admin.projects.view')
def admin_api_business_project_detail(project_id):
    conn = get_x1_data_conn()
    try:
        row = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        return jsonify({'success': True, 'item': serialize_business_project(row)})
    finally:
        conn.close()


@app.route('/admin/api/business_projects/<int:project_id>/reports', methods=['GET'])
@login_required
@require_permission('admin.projects.view')
def admin_api_project_reports(project_id):
    """返回项目关联的所有导出报告"""
    conn = get_x1_data_conn()
    try:
        row = conn.execute('SELECT project_name, client_name FROM business_projects WHERE id=?', [project_id]).fetchone()
    finally:
        conn.close()
    if not row:
        return jsonify({'success': False, 'error': '项目不存在'}), 404

    pname = (row['project_name'] or '').strip()
    cname = (row['client_name'] or '').strip()
    results = []
    for jf in sorted(REPORTS_DIR.glob('X1EXPORT_*.json'), reverse=True):
        try:
            import json as _json
            with open(jf, 'r', encoding='utf-8') as f:
                data = _json.load(f)
            ep = data.get('export_payload', {}) or {}
            proj = ep.get('project', {}) or {}
            jp = (proj.get('project_name') or '').strip()
            jc = (proj.get('client_name') or '').strip()
            if jp == pname and (not cname or jc == cname):
                export_id = data.get('export_id', jf.stem)
                formal = data.get('formal_local', {}) or {}
                results.append({
                    'export_id': export_id,
                    'report_number': proj.get('report_number', ''),
                    'detection_date': proj.get('detection_date', ''),
                    'saved_at': data.get('saved_at', ''),
                    'detection_type': proj.get('detection_type_name', '') or proj.get('detection_type', ''),
                    'report_path': formal.get('report', {}).get('path', ''),
                    'export_path': formal.get('export', {}).get('path', ''),
                    'has_report_file': bool(formal.get('report', {}).get('success')),
                    'has_export_file': bool(formal.get('export', {}).get('success')),
                })
        except Exception:
            continue
    return jsonify({'success': True, 'project_id': project_id, 'items': results, 'total': len(results)})


@app.route('/admin/api/download_file', methods=['GET'])
@login_required
@require_permission('admin.files.download')
def admin_api_download_file():
    """管理员下载指定路径的报告/原始记录文件"""
    file_path = request.args.get('path', '')
    if not file_path:
        return jsonify({'success': False, 'error': '缺少path参数'}), 400
    p = Path(file_path)
    # 安全限制：只允许下载正式目录和 reports_x1 目录下的文件
    allowed_prefixes = [
        str(FORMAL_REPORTS_BASE), str(FORMAL_RECORDS_BASE), str(REPORTS_DIR)
    ]
    resolved = str(p.resolve())
    if not any(resolved.startswith(pfx) for pfx in allowed_prefixes):
        return jsonify({'success': False, 'error': '无权访问该路径'}), 403
    if not p.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    return send_file(str(p), as_attachment=True, download_name=p.name)



@app.route('/admin/api/business_projects', methods=['POST'])
@login_required
@require_permission('admin.projects.manage')
def admin_api_business_project_create():
    data = request.get_json(silent=True) or {}
    payload = _clean_project_payload(data)
    if not payload['project_name']:
        return jsonify({'success': False, 'error': '项目名称不能为空'}), 400
    now = datetime.now().isoformat(timespec='seconds')
    project_no = _generate_project_no()
    conn = get_x1_data_conn()
    try:
        cur = conn.execute('''
            INSERT INTO business_projects (
                project_no, project_name, client_name, project_address, contact_name, contact_phone,
                detection_domain, detection_type, expected_detection_date, project_desc,
                business_stage, contract_status, contract_amount, paid_amount, inspection_stage,
                report_status, invoice_status, payment_status, owner, remarks,
                assigned_to, assigned_at, task_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            project_no,
            payload['project_name'], payload['client_name'], payload['project_address'], payload['contact_name'], payload['contact_phone'],
            payload['detection_domain'], payload['detection_type'], payload['expected_detection_date'], payload['project_desc'],
            payload['business_stage'], payload['contract_status'], payload['contract_amount'], payload['paid_amount'], payload['inspection_stage'],
            payload['report_status'], payload['invoice_status'], payload['payment_status'], payload['owner'], payload['remarks'],
            payload['assigned_to'], payload['assigned_at'], payload['task_status'], now, now
        ])
        conn.commit()
        row = conn.execute('SELECT * FROM business_projects WHERE id=?', [cur.lastrowid]).fetchone()
        return jsonify({'success': True, 'item': serialize_business_project(row)})
    finally:
        conn.close()


@app.route('/admin/api/business_projects/<int:project_id>', methods=['PUT'])
@login_required
@require_permission('admin.projects.manage')
def admin_api_business_project_update(project_id):
    data = request.get_json(silent=True) or {}
    payload = _clean_project_payload(data)
    if not payload['project_name']:
        return jsonify({'success': False, 'error': '项目名称不能为空'}), 400
    now = datetime.now().isoformat(timespec='seconds')
    conn = get_x1_data_conn()
    try:
        exists = conn.execute('SELECT id FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not exists:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        conn.execute('''
            UPDATE business_projects SET
                project_name=?, client_name=?, project_address=?, contact_name=?, contact_phone=?,
                detection_domain=?, detection_type=?, expected_detection_date=?, project_desc=?,
                business_stage=?, contract_status=?, contract_amount=?, paid_amount=?, inspection_stage=?,
                report_status=?, invoice_status=?, payment_status=?, owner=?, remarks=?,
                assigned_to=?, assigned_at=?, task_status=?, updated_at=?
            WHERE id=?
        ''', [
            payload['project_name'], payload['client_name'], payload['project_address'], payload['contact_name'], payload['contact_phone'],
            payload['detection_domain'], payload['detection_type'], payload['expected_detection_date'], payload['project_desc'],
            payload['business_stage'], payload['contract_status'], payload['contract_amount'], payload['paid_amount'], payload['inspection_stage'],
            payload['report_status'], payload['invoice_status'], payload['payment_status'], payload['owner'], payload['remarks'],
            payload['assigned_to'], payload['assigned_at'], payload['task_status'], now, project_id
        ])
        conn.commit()
        row = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        return jsonify({'success': True, 'item': serialize_business_project(row)})
    finally:
        conn.close()


@app.route('/admin/api/business_projects/<int:project_id>', methods=['DELETE'])
@login_required
@require_permission('admin.projects.manage')
def admin_api_business_project_delete(project_id):
    conn = get_x1_data_conn()
    try:
        exists = conn.execute('SELECT id FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not exists:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        conn.execute('DELETE FROM business_projects WHERE id=?', [project_id])
        conn.commit()
        return jsonify({'success': True})
    finally:
        conn.close()


@app.route('/admin/api/business_projects/<int:project_id>/upload_report', methods=['POST'])
@login_required
@require_permission('admin.projects.upload_report')
def admin_api_upload_report(project_id):
    """上传报告文件（补录场景），支持 .docx / .pdf"""
    conn = get_x1_data_conn()
    try:
        project = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        f = request.files.get('report_file')
        if not f or not f.filename:
            return jsonify({'success': False, 'error': '请选择报告文件'}), 400

        ext = Path(f.filename).suffix.lower()
        if ext not in ('.docx', '.pdf', '.doc'):
            return jsonify({'success': False, 'error': '仅支持 .docx / .pdf / .doc 格式'}), 400

        upload_dir = BASE_DIR / 'uploaded_reports'
        upload_dir.mkdir(exist_ok=True)

        # 文件名：项目ID_时间戳.ext
        ts = datetime.now().strftime('%Y%m%d%H%M%S')
        safe_name = f"project_{project_id}_{ts}{ext}"
        save_path = upload_dir / safe_name
        f.save(str(save_path))

        # 如果上传的是 docx，同时生成 PDF 预览
        pdf_path = ''
        if ext == '.docx':
            try:
                from pdf_converter import convert_docx_to_pdf
                preview_dir = BASE_DIR / 'preview_pdf'
                preview_dir.mkdir(exist_ok=True)
                pdf_out = str(preview_dir / f"uploaded_{project_id}_{ts}.pdf")
                result = convert_docx_to_pdf(str(save_path), pdf_out)
                if result:
                    pdf_path = result
            except Exception:
                pass  # PDF 生成失败不影响主流程
        elif ext == '.pdf':
            # PDF 直接复制到预览目录
            preview_dir = BASE_DIR / 'preview_pdf'
            preview_dir.mkdir(exist_ok=True)
            pdf_dest = preview_dir / f"uploaded_{project_id}_{ts}.pdf"
            import shutil
            shutil.copy2(str(save_path), str(pdf_dest))
            pdf_path = str(pdf_dest)

        # 更新项目记录
        now = datetime.now().isoformat(timespec='seconds')
        updates = {'report_file_path': str(save_path), 'updated_at': now}
        # 如果 report_status 还是初始状态，自动推进到“已出具”
        current_rs = (project['report_status'] or '').strip()
        if current_rs in ('', '未开始', '编制中', '审核中', '待出具'):
            updates['report_status'] = '已出具'
            updates['inspection_stage'] = '检测完成'

        set_clause = ', '.join(f"{k}=?" for k in updates.keys())
        conn.execute(f'UPDATE business_projects SET {set_clause} WHERE id=?',
                     list(updates.values()) + [project_id])
        conn.commit()

        return jsonify({
            'success': True,
            'file_path': str(save_path),
            'pdf_path': pdf_path,
            'message': '报告上传成功' + ('，PDF 预览已生成' if pdf_path else '')
        })
    finally:
        conn.close()


@app.route('/admin/api/business_projects/<int:project_id>/download_report', methods=['GET'])
@login_required
@require_permission('admin.projects.view')
def admin_api_download_report(project_id):
    """下载项目报告文件（DOCX/PDF）"""
    conn = get_x1_data_conn()
    try:
        project = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        rfp = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
        if not rfp or not Path(rfp).exists():
            return jsonify({'success': False, 'error': '报告文件不存在'}), 404
        pname = project['project_name'] or '检测报告'
        ext = Path(rfp).suffix
        return send_file(rfp, as_attachment=True, download_name=f"{pname}{ext}")
    finally:
        conn.close()


# ============================================================
# 派单链 V1 — 后台管理侧任务接口
# ============================================================

@app.route('/admin/api/inspectors', methods=['GET'])
@login_required
@require_permission('admin.projects.view')
def admin_api_inspectors():
    """返回可派单人员列表（所有内部活跃用户）"""
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT user_id, display_name, role, department FROM users "
                "WHERE role != 'customer' AND is_active=1 "
                "ORDER BY CASE role WHEN 'inspector' THEN 1 WHEN 'supervisor' THEN 2 WHEN 'admin' THEN 3 ELSE 4 END, user_id"
            ).fetchall()
        items = [{'user_id': r['user_id'], 'display_name': r['display_name'], 'role': r['role'], 'department': r['department'] or ''} for r in rows]
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/customers')
@login_required
@require_permission('admin.customers.view')
def admin_api_customers():
    """返回客户账号列表（含 client_name 绑定）"""
    try:
        with get_db() as conn:
            cols = {r['name'] for r in conn.execute('PRAGMA table_info(users)').fetchall()}
            if 'client_name' not in cols:
                return jsonify({'success': True, 'items': []})
            rows = conn.execute(
                "SELECT user_id, display_name, client_name FROM users "
                "WHERE role='customer' AND is_active=1 AND client_name != '' "
                "ORDER BY client_name"
            ).fetchall()
        items = [{'user_id': r['user_id'], 'display_name': r['display_name'], 'client_name': r['client_name']} for r in rows]
        return jsonify({'success': True, 'items': items})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/api/project_tasks', methods=['POST'])
@login_required
@require_permission('admin.tasks.manage')
def create_project_task():
    data = request.get_json(silent=True) or {}
    payload = _clean_project_task_payload(data)

    if not payload.get('project_id'):
        return jsonify({'success': False, 'error': 'project_id 不能为空'}), 400

    project_row = _get_business_project_by_id(payload['project_id'])
    if not project_row:
        return jsonify({'success': False, 'error': '项目不存在'}), 404

    task_name = payload.get('task_name') or ''
    if not task_name:
        base_name = (project_row['project_name'] or '项目').strip()
        type_label = _get_task_type_label(payload.get('task_type') or 'inspection')
        task_name = f'{base_name}-{type_label}'

    now = _x_now()
    assigned_to = payload.get('assigned_to')
    task_type = payload.get('task_type') or 'inspection'

    if assigned_to:
        task_status = 'assigned'
        assigned_at = now
    else:
        task_status = 'pending_assign'
        assigned_at = None

    conn = get_x1_data_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO project_tasks "
            "(project_id, task_name, task_type, assigned_to, assigned_at, "
            " task_status, expected_execute_date, started_at, completed_at, "
            " remarks, created_by, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                payload['project_id'],
                task_name,
                task_type,
                assigned_to,
                assigned_at,
                task_status,
                payload.get('expected_execute_date'),
                None,
                None,
                payload.get('remarks'),
                getattr(current_user, 'id', None),
                now,
                now,
            ),
        )
        task_id = cur.lastrowid
        conn.commit()
    finally:
        conn.close()

    refresh_project_task_summary(payload['project_id'])
    # 自动流转：派单 → 已排期
    _auto_advance_project_stage(payload['project_id'], target_inspection='已排期')

    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    return jsonify({'success': True, 'item': serialize_project_task(row, project_row)})


@app.route('/admin/api/business_projects/<int:project_id>/tasks', methods=['GET'])
@login_required
@require_permission('admin.tasks.view')
def get_project_tasks(project_id):
    project_row = _get_business_project_by_id(project_id)
    if not project_row:
        return jsonify({'success': False, 'error': '项目不存在'}), 404

    conn = get_x1_data_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM project_tasks WHERE project_id=? "
            "ORDER BY updated_at DESC, id DESC",
            (project_id,),
        ).fetchall()
    finally:
        conn.close()

    items = [serialize_project_task(r, project_row) for r in rows]
    return jsonify({'success': True, 'items': items})


@app.route('/admin/api/project_tasks/<int:task_id>', methods=['GET'])
@login_required
@require_permission('admin.tasks.view')
def get_project_task_detail(task_id):
    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    project_row = _get_business_project_by_id(row['project_id'])
    return jsonify({'success': True, 'item': serialize_project_task(row, project_row)})


@app.route('/admin/api/project_tasks/<int:task_id>', methods=['PUT'])
@login_required
@require_permission('admin.tasks.manage')
def update_project_task(task_id):
    data = request.get_json(silent=True) or {}
    payload = _clean_project_task_payload(data)

    conn = get_x1_data_conn()
    try:
        old_row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    if not old_row:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    project_row = _get_business_project_by_id(old_row['project_id'])
    if not project_row:
        return jsonify({'success': False, 'error': '关联项目不存在'}), 404

    now = _x_now()

    new_task_name = payload.get('task_name') or old_row['task_name']
    new_task_type = payload.get('task_type') or old_row['task_type']
    new_expected = payload.get('expected_execute_date') if payload.get('expected_execute_date') is not None else old_row['expected_execute_date']
    new_remarks = payload.get('remarks') if payload.get('remarks') is not None else old_row['remarks']

    new_assigned_to = payload.get('assigned_to') if 'assigned_to' in data else old_row['assigned_to']
    new_assigned_at = old_row['assigned_at']
    if str(new_assigned_to or '') != str(old_row['assigned_to'] or ''):
        new_assigned_at = now if new_assigned_to else None

    new_status = payload.get('task_status') or old_row['task_status']

    new_started_at = old_row['started_at']
    new_completed_at = old_row['completed_at']
    if new_status == 'in_progress' and not new_started_at:
        new_started_at = now
    if new_status == 'completed' and not new_completed_at:
        new_completed_at = now

    conn = get_x1_data_conn()
    try:
        conn.execute(
            "UPDATE project_tasks SET "
            "task_name=?, task_type=?, assigned_to=?, assigned_at=?, "
            "task_status=?, expected_execute_date=?, started_at=?, completed_at=?, "
            "remarks=?, updated_at=? "
            "WHERE id=?",
            (
                new_task_name,
                new_task_type,
                new_assigned_to,
                new_assigned_at,
                new_status,
                new_expected,
                new_started_at,
                new_completed_at,
                new_remarks,
                now,
                task_id,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    refresh_project_task_summary(old_row['project_id'])

    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    return jsonify({'success': True, 'item': serialize_project_task(row, project_row)})


@app.route('/admin/api/project_tasks/<int:task_id>/cancel', methods=['POST'])
@login_required
@require_permission('admin.tasks.manage')
def cancel_project_task(task_id):
    data = request.get_json(silent=True) or {}

    conn = get_x1_data_conn()
    try:
        old_row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    if not old_row:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    if old_row['task_status'] == 'cancelled':
        return jsonify({'success': False, 'error': '任务已取消，无需重复操作'}), 400

    now = _x_now()
    cancel_note = str(data.get('remarks') or '').strip()

    remarks = (old_row['remarks'] or '').strip()
    if cancel_note:
        if remarks:
            remarks = remarks + '\n' + '取消原因：' + cancel_note
        else:
            remarks = '取消原因：' + cancel_note

    conn = get_x1_data_conn()
    try:
        conn.execute(
            "UPDATE project_tasks SET task_status='cancelled', "
            "remarks=?, updated_at=? WHERE id=?",
            (remarks, now, task_id),
        )
        conn.commit()
    finally:
        conn.close()

    refresh_project_task_summary(old_row['project_id'])

    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
        project_row = _get_business_project_by_id(old_row['project_id'])
    finally:
        conn.close()

    return jsonify({'success': True, 'item': serialize_project_task(row, project_row)})


# ============================================================
# 派单链 V1 — 检测员侧接口
# ============================================================

@app.route('/api/my_tasks', methods=['GET'])
@login_required
@require_permission('tasks.execute')
def api_my_tasks():
    """检测员查看分配给自己的任务"""
    user_id = current_user.id
    status_filter = request.args.get('status', '').strip()

    conn = get_x1_data_conn()
    try:
        if status_filter == 'all':
            rows = conn.execute(
                "SELECT * FROM project_tasks WHERE assigned_to=? "
                "ORDER BY updated_at DESC, id DESC",
                (user_id,)
            ).fetchall()
        elif status_filter == 'completed':
            rows = conn.execute(
                "SELECT * FROM project_tasks WHERE assigned_to=? AND task_status='completed' "
                "ORDER BY completed_at DESC, id DESC",
                (user_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM project_tasks WHERE assigned_to=? "
                "AND task_status IN ('assigned','accepted','in_progress') "
                "ORDER BY "
                "  CASE task_status WHEN 'in_progress' THEN 1 WHEN 'accepted' THEN 2 WHEN 'assigned' THEN 3 ELSE 9 END, "
                "  updated_at DESC, id DESC",
                (user_id,)
            ).fetchall()
    finally:
        conn.close()

    items = []
    for row in rows:
        project_row = _get_business_project_by_id(row['project_id'])
        items.append(serialize_project_task(row, project_row))

    return jsonify({'success': True, 'items': items})


@app.route('/api/project_tasks/<int:task_id>/accept', methods=['POST'])
@login_required
@require_permission('tasks.execute')
def api_task_accept(task_id):
    """检测员接单"""
    user_id = current_user.id
    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    if str(row['assigned_to'] or '') != user_id:
        return jsonify({'success': False, 'error': '该任务未分配给你'}), 403
    if row['task_status'] != 'assigned':
        return jsonify({'success': False, 'error': f"当前状态为{_get_task_status_label(row['task_status'])}，无法接单"}), 400

    now = _x_now()
    conn = get_x1_data_conn()
    try:
        conn.execute(
            "UPDATE project_tasks SET task_status='accepted', updated_at=? WHERE id=?",
            (now, task_id)
        )
        conn.commit()
    finally:
        conn.close()

    refresh_project_task_summary(row['project_id'])
    # 自动流转：接单 → 待进场
    _auto_advance_project_stage(row['project_id'], target_inspection='待进场')
    conn = get_x1_data_conn()
    try:
        updated = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
        project_row = _get_business_project_by_id(row['project_id'])
    finally:
        conn.close()
    return jsonify({'success': True, 'item': serialize_project_task(updated, project_row)})


@app.route('/api/project_tasks/<int:task_id>/start', methods=['POST'])
@login_required
@require_permission('tasks.execute')
def api_task_start(task_id):
    """检测员开始执行"""
    user_id = current_user.id
    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    if str(row['assigned_to'] or '') != user_id:
        return jsonify({'success': False, 'error': '该任务未分配给你'}), 403
    if row['task_status'] not in ('assigned', 'accepted'):
        return jsonify({'success': False, 'error': f"当前状态为{_get_task_status_label(row['task_status'])}，无法开始执行"}), 400

    now = _x_now()
    conn = get_x1_data_conn()
    try:
        conn.execute(
            "UPDATE project_tasks SET task_status='in_progress', started_at=?, updated_at=? WHERE id=?",
            (now, now, task_id)
        )
        conn.commit()
    finally:
        conn.close()

    refresh_project_task_summary(row['project_id'])
    # 自动流转：开始执行 → 检测中
    _auto_advance_project_stage(row['project_id'], target_inspection='检测中')
    conn = get_x1_data_conn()
    try:
        updated = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
        project_row = _get_business_project_by_id(row['project_id'])
    finally:
        conn.close()
    return jsonify({'success': True, 'item': serialize_project_task(updated, project_row)})


@app.route('/api/project_tasks/<int:task_id>/complete', methods=['POST'])
@login_required
@require_permission('tasks.execute')
def api_task_complete(task_id):
    """检测员完成任务"""
    user_id = current_user.id
    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    if str(row['assigned_to'] or '') != user_id:
        return jsonify({'success': False, 'error': '该任务未分配给你'}), 403
    if row['task_status'] not in ('accepted', 'in_progress'):
        return jsonify({'success': False, 'error': f"当前状态为{_get_task_status_label(row['task_status'])}，无法完成"}), 400

    now = _x_now()
    started_at = row['started_at'] or now
    conn = get_x1_data_conn()
    try:
        conn.execute(
            "UPDATE project_tasks SET task_status='completed', started_at=?, completed_at=?, updated_at=? WHERE id=?",
            (started_at, now, now, task_id)
        )
        conn.commit()
    finally:
        conn.close()

    refresh_project_task_summary(row['project_id'])
    # 自动流转：完成任务 → 检测完成 + 报告编制中
    _auto_advance_project_stage(row['project_id'], target_inspection='检测完成', target_report='编制中')
    conn = get_x1_data_conn()
    try:
        updated = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
        project_row = _get_business_project_by_id(row['project_id'])
    finally:
        conn.close()
    return jsonify({'success': True, 'item': serialize_project_task(updated, project_row)})


@app.route('/api/project_tasks/<int:task_id>/prefill', methods=['GET'])
@login_required
@require_permission('tasks.execute')
def api_task_prefill(task_id):
    """返回任务关联的项目基础信息，用于前端录入页自动填入"""
    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    if not row:
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    project_row = _get_business_project_by_id(row['project_id'])
    if not project_row:
        return jsonify({'success': False, 'error': '关联项目不存在'}), 404

    return jsonify({
        'success': True,
        'task_id': task_id,
        'project_id': row['project_id'],
        'prefill': {
            'project_name': project_row['project_name'] or '',
            'client_name': project_row['client_name'] or '',
            'project_address': project_row['project_address'] or '',
            'contact_name': project_row['contact_name'] or '',
            'contact_phone': project_row['contact_phone'] or '',
            'detection_domain': project_row['detection_domain'] or '',
            'detection_type': project_row['detection_type'] or '',
            'expected_detection_date': project_row['expected_detection_date'] or '',
            'project_no': project_row['project_no'] or '',
        }
    })


@app.route('/admin/api/stats')
@login_required
@require_permission('admin.stats.view')
def admin_api_stats():
    """数据统计 API"""
    from datetime import datetime
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


@app.route('/admin/api/records')
@login_required
@require_permission('admin.records.view')
def admin_api_records():
    """报告管理 - 记录列表"""
    records = []

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

    def _is_valid_export_record(export_id: str, proj: dict) -> bool:
        if not export_id.startswith('X1EXPORT_'):
            return False
        suffix = export_id[len('X1EXPORT_'):]
        if len(suffix) != 14 or not suffix.isdigit():
            return False
        if not isinstance(proj, dict):
            return False
        return any(str(proj.get(k, '')).strip() for k in ['project_name', 'client_name', 'report_number', 'detection_date'])
    
    # 读取所有草稿
    for draft_file in RECORDS_DIR.glob('*.json'):
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                project = data.get('project', {})
                if not _draft_has_visible_content(project, data):
                    continue
                save_time = data.get('updated_at', '') or data.get('created_at', '') or data.get('saved_at', '')
                room_count = len(project.get('rooms', []) if isinstance(project.get('rooms', []), list) else data.get('rooms', []))
                records.append({
                    'id': data.get('draft_id', draft_file.stem),
                    'type': 'draft',
                    'project_name': project.get('project_name', ''),
                    'report_number': project.get('report_number', ''),
                    'client_name': project.get('client_name', ''),
                    'operator': project.get('operator', '') or project.get('inspector', ''),
                    'detection_date': project.get('detection_date', ''),
                    'detection_state': project.get('detection_state', ''),
                    'domain': project.get('domain_name', '') or project.get('domain', ''),
                    'room_count': room_count,
                    'save_time': save_time,
                    'save_time_min': (save_time.replace('T',' ')[:16] if save_time else ''),
                    'created': data.get('created_at', '') or data.get('saved_at', ''),
                    'modified': data.get('updated_at', '') or data.get('saved_at', ''),
                    'status': 'draft',
                    'has_report': False,
                    'has_export': False,
                    'report_info': {},
                    'export_info': {},
                    'report_download_url': '',
                    'export_download_url': ''
                })
        except:
            pass
    
    # 读取标准导出记录（以标准 export json 为准）
    export_groups = {}
    for export_file in REPORTS_DIR.glob('X1EXPORT_*.json'):
        try:
            export_id = export_file.stem
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ep = data.get('export_payload', data)
                proj = ep.get('project', {}) or {}
                if not _is_valid_export_record(export_id, proj):
                    continue
                saved_at = data.get('saved_at', '') or proj.get('saved_at', '')
                feishu = data.get('feishu', {}) or {}

                report_info = {}
                export_info = {}
                report_status = 'missing'
                export_status = 'missing'
                report_error = ''
                export_error = ''
                if feishu.get('report'):
                    report_info = {
                        'feishu_url': feishu['report'].get('feishu_url', ''),
                        'feishu_open_url': feishu['report'].get('feishu_open_url', ''),
                        'feishu_open_kind': feishu['report'].get('feishu_open_kind', '')
                    }
                    report_status = 'success' if feishu['report'].get('success') else 'failed'
                    report_error = feishu['report'].get('error', '') or ''
                if feishu.get('export'):
                    export_info = {
                        'feishu_url': feishu['export'].get('feishu_url', ''),
                        'feishu_open_url': feishu['export'].get('feishu_open_url', ''),
                        'feishu_open_kind': feishu['export'].get('feishu_open_kind', '')
                    }
                    export_status = 'success' if feishu['export'].get('success') else 'failed'
                    export_error = feishu['export'].get('error', '') or ''

                export_groups[export_id] = {
                    'id': export_id,
                    'type': 'export',
                    'project_name': proj.get('project_name', ''),
                    'report_number': proj.get('report_number', ''),
                    'client_name': proj.get('client_name', ''),
                    'operator': proj.get('operator', '') or proj.get('inspector', ''),
                    'detection_date': proj.get('detection_date', ''),
                    'detection_state': proj.get('detection_state', ''),
                    'domain': proj.get('domain_name', '') or proj.get('domain', ''),
                    'room_count': len(ep.get('rooms', []) if isinstance(ep.get('rooms', []), list) else []),
                    'save_time': saved_at,
                    'save_time_min': (saved_at.replace('T',' ')[:16] if saved_at else ''),
                    'created': saved_at,
                    'modified': saved_at,
                    'status': 'generated',
                    'overall_status': data.get('overall_status'),
                    'report_success': data.get('report_success'),
                    'raw_record_success': data.get('raw_record_success'),
                    'report_status': data.get('report_status'),
                    'raw_record_status': data.get('raw_record_status'),
                    'template_ready': data.get('template_ready', None),
                    'has_report': bool(feishu.get('report')),
                    'has_export': bool(feishu.get('export')),
                    'report_info': report_info,
                    'export_info': export_info,
                    'files': [],
                    'feishu_report_url': feishu.get('report', {}).get('feishu_url', '') or feishu.get('report', {}).get('feishu_open_url', '') if feishu.get('report') else '',
                    'feishu_export_url': feishu.get('export', {}).get('feishu_url', '') or feishu.get('export', {}).get('feishu_open_url', '') if feishu.get('export') else '',
                    'feishu_report_open_url': feishu.get('report', {}).get('feishu_open_url', '') if feishu.get('report') else '',
                    'feishu_export_open_url': feishu.get('export', {}).get('feishu_open_url', '') if feishu.get('export') else '',
                    'feishu_report_status': report_status,
                    'feishu_export_status': export_status,
                    'feishu_report_error': report_error,
                    'feishu_export_error': export_error,
                    'voided': bool(data.get('voided')),
                    'voided_at': data.get('voided_at', ''),
                    'voided_by': data.get('voided_by', ''),
                    'void_reason': data.get('void_reason', '')
                }
        except:
            pass

    # 关联标准导出的文件
    for export_file in list(REPORTS_DIR.glob('X1EXPORT_*.docx')) + list(REPORTS_DIR.glob('X1EXPORT_*.xlsx')):
        export_id = export_file.stem.split('.')[0]
        if export_id in export_groups:
            export_groups[export_id]['files'].append({
                'name': export_file.name,
                'path': str(export_file)
            })
            if '.filled.' in export_file.name or '.bound.' in export_file.name:
                export_groups[export_id]['has_report'] = True
                if not export_groups[export_id]['report_info'].get('feishu_url'):
                    export_groups[export_id]['report_info']['filename'] = export_file.name
                    export_groups[export_id]['report_download_url'] = f'/download/{export_file.name}'
            elif export_file.name.endswith('.xlsx'):
                export_groups[export_id]['has_export'] = True
                if not export_groups[export_id]['export_info'].get('feishu_url'):
                    export_groups[export_id]['export_info']['filename'] = export_file.name
                    export_groups[export_id]['export_download_url'] = f'/download/{export_file.name}'

    records.extend(export_groups.values())

    records = [r for r in records if can_view_record(current_user, {'inspector_name': r.get('operator', '')})]

    for r in records:
        if r.get('type') == 'export':
            if r.get('report_success') is None:
                r['report_success'] = bool((r.get('report_info') or {}).get('feishu_url') or (r.get('report_info') or {}).get('filename'))
            if r.get('raw_record_success') is None:
                r['raw_record_success'] = bool((r.get('export_info') or {}).get('feishu_url') or (r.get('export_info') or {}).get('filename'))
            r['asset_state'] = _compute_record_asset_state(r)
            if not r.get('report_status'):
                r['report_status'] = 'success' if r['report_success'] else ('blocked_template_missing' if r.get('template_ready') is False and r['raw_record_success'] else 'missing')
            if not r.get('raw_record_status'):
                r['raw_record_status'] = 'success' if r['raw_record_success'] else 'missing'
            if not r.get('overall_status'):
                if r['report_success'] and r['raw_record_success']:
                    r['overall_status'] = 'success'
                elif r['raw_record_success'] and not r['report_success']:
                    r['overall_status'] = 'partial_success'
                else:
                    r['overall_status'] = 'failed'
            r['asset_state'] = _compute_record_asset_state(r)
    
    # --- 分页与筛选 ---
    # 按 save_time 倒序排序
    records.sort(key=lambda r: r.get('save_time', '') or '', reverse=True)
    
    # 收集所有领域（在筛选前）
    all_domains = sorted(set(r.get('domain', '') for r in records if r.get('domain', '')))
    
    # 筛选
    keyword = request.args.get('keyword', '').strip().lower()
    domain_filter = request.args.get('domain', '').strip()
    type_filter = request.args.get('type', '').strip()
    
    if domain_filter:
        records = [r for r in records if r.get('domain', '') == domain_filter]
    if type_filter:
        if type_filter == 'report':
            records = [r for r in records if r.get('type', '') == 'export' and (r.get('report_success') or r.get('has_report') or (r.get('report_info') or {}).get('filename') or (r.get('report_info') or {}).get('feishu_url'))]
        elif type_filter == 'draft':
            records = [r for r in records if r.get('type', '') == 'draft']
        elif type_filter == 'voided':
            records = [r for r in records if bool(r.get('voided'))]
        elif type_filter == 'all':
            pass
        else:
            records = [r for r in records if r.get('type', '') == type_filter]
    if keyword:
        parts = keyword.split()
        def match_keyword(r):
            s = ' '.join([
                r.get('project_name', ''),
                r.get('report_number', ''),
                r.get('client_name', ''),
                r.get('operator', '')
            ]).lower()
            return all(p in s for p in parts)
        records = [r for r in records if match_keyword(r)]
    
    # 分页
    total = len(records)
    page = max(1, int(request.args.get('page', 1)))
    page_size = max(1, min(200, int(request.args.get('page_size', 50))))
    total_pages = max(1, (total + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    paged_records = records[start:start + page_size]
    
    return jsonify({
        'records': paged_records,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'domains': all_domains
    })


# ============================================================
# 操作日志工具函数
# ============================================================

def _get_log_file(month=None):
    """获取日志文件路径，格式 YYYY-MM.jsonl"""
    from datetime import datetime
    if not month:
        month = datetime.now().strftime('%Y-%m')
    return LOGS_DIR / f'{month}.jsonl'

# ============================================================
# 用户管理工具函数
# ============================================================

def _get_users_file():
    return BASE_DIR / 'data' / 'users.json'

def _load_users():
    f = _get_users_file()
    if f.exists():
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                return json.load(fp)
        except Exception:
            return {}
    return {}

def _save_users(users):
    f = _get_users_file()
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, 'w', encoding='utf-8') as fp:
        json.dump(users, fp, ensure_ascii=False, indent=2)


def _soft_delete_record(record_id):
    """软删除记录（移到 trash 目录）"""
    import shutil
    trash_dir = BASE_DIR / 'trash'
    trash_dir.mkdir(exist_ok=True)
    # 草稿
    draft_file = RECORDS_DIR / f"{record_id}.json"
    if draft_file.exists():
        shutil.move(str(draft_file), str(trash_dir / draft_file.name))
        return True, '草稿已移至回收站'
    # 导出记录
    export_files = list(REPORTS_DIR.glob(f"{record_id}*"))
    if not export_files:
        return False, '记录不存在'
    for ef in export_files:
        shutil.move(str(ef), str(trash_dir / ef.name))
    return True, f'导出记录已移至回收站（{len(export_files)}个文件）'


def _record_data_for_access_check(record_id: str, file_path: Path):
    try:
        data = json.loads(file_path.read_text(encoding='utf-8'))
    except Exception:
        return {}
    project = data.get('project') if isinstance(data.get('project'), dict) else {}
    if project:
        return {'inspector_name': project.get('operator', '') or project.get('inspector', '')}
    ep = data.get('export_payload') if isinstance(data.get('export_payload'), dict) else {}
    proj = ep.get('project') if isinstance(ep.get('project'), dict) else {}
    return {'inspector_name': proj.get('operator', '') or proj.get('inspector', '')}


def _can_access_file_by_name(filename: str) -> bool:
    if current_user.role in ('admin', 'viewer'):
        return True
    stem = Path(filename).stem
    if stem.endswith('.filled'):
        stem = stem[:-7]
    elif stem.endswith('.bound'):
        stem = stem[:-6]
    sidecar_export = REPORTS_DIR / f'{stem}.json'
    sidecar_draft = RECORDS_DIR / f'{stem}.json'
    file_path = sidecar_export if sidecar_export.exists() else (sidecar_draft if sidecar_draft.exists() else None)
    if not file_path:
        return False
    record_data = _record_data_for_access_check(stem, file_path)
    return can_view_record(current_user, record_data)


@app.route('/admin/api/records/summary')
@login_required
@require_permission('admin.records.view')
def admin_api_records_summary():
    """报告管理 - 摘要统计（按当前筛选条件汇总，不受分页影响）"""
    records = []

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

    def _is_valid_export_record(export_id: str, proj: dict) -> bool:
        if not export_id.startswith('X1EXPORT_'):
            return False
        suffix = export_id[len('X1EXPORT_'):]
        if len(suffix) != 14 or not suffix.isdigit():
            return False
        if not isinstance(proj, dict):
            return False
        return any(str(proj.get(k, '')).strip() for k in ['project_name', 'client_name', 'report_number', 'detection_date'])

    for draft_file in RECORDS_DIR.glob('*.json'):
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                project = data.get('project', {})
                if not _draft_has_visible_content(project, data):
                    continue
                save_time = data.get('updated_at', '') or data.get('created_at', '') or data.get('saved_at', '')
                room_count = len(project.get('rooms', []) if isinstance(project.get('rooms', []), list) else data.get('rooms', []))
                records.append({
                    'id': data.get('draft_id', draft_file.stem),
                    'type': 'draft',
                    'project_name': project.get('project_name', ''),
                    'report_number': project.get('report_number', ''),
                    'client_name': project.get('client_name', ''),
                    'operator': project.get('operator', '') or project.get('inspector', ''),
                    'detection_date': project.get('detection_date', ''),
                    'detection_state': project.get('detection_state', ''),
                    'domain': project.get('domain_name', '') or project.get('domain', ''),
                    'room_count': room_count,
                    'save_time': save_time,
                    'created': data.get('created_at', '') or data.get('saved_at', ''),
                    'modified': data.get('updated_at', '') or data.get('saved_at', ''),
                    'status': 'draft',
                    'has_report': False,
                    'has_export': False,
                    'report_info': {},
                    'export_info': {},
                })
        except:
            pass

    export_groups = {}
    for export_file in REPORTS_DIR.glob('X1EXPORT_*.json'):
        try:
            export_id = export_file.stem
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ep = data.get('export_payload', data)
                proj = ep.get('project', {}) or {}
                if not _is_valid_export_record(export_id, proj):
                    continue
                saved_at = data.get('saved_at', '') or proj.get('saved_at', '')
                feishu = data.get('feishu', {}) or {}
                report_info = {}
                export_info = {}
                if feishu.get('report'):
                    report_info = {
                        'feishu_url': feishu['report'].get('feishu_url', ''),
                        'feishu_open_url': feishu['report'].get('feishu_open_url', ''),
                        'feishu_open_kind': feishu['report'].get('feishu_open_kind', '')
                    }
                if feishu.get('export'):
                    export_info = {
                        'feishu_url': feishu['export'].get('feishu_url', ''),
                        'feishu_open_url': feishu['export'].get('feishu_open_url', ''),
                        'feishu_open_kind': feishu['export'].get('feishu_open_kind', '')
                    }
                export_groups[export_id] = {
                    'id': export_id,
                    'type': 'export',
                    'project_name': proj.get('project_name', ''),
                    'report_number': proj.get('report_number', ''),
                    'client_name': proj.get('client_name', ''),
                    'operator': proj.get('operator', '') or proj.get('inspector', ''),
                    'detection_date': proj.get('detection_date', ''),
                    'detection_state': proj.get('detection_state', ''),
                    'domain': proj.get('domain_name', '') or proj.get('domain', ''),
                    'room_count': len(ep.get('rooms', []) if isinstance(ep.get('rooms', []), list) else []),
                    'save_time': saved_at,
                    'created': saved_at,
                    'modified': saved_at,
                    'status': 'generated',
                    'report_success': data.get('report_success'),
                    'raw_record_success': data.get('raw_record_success'),
                    'has_report': bool(feishu.get('report')),
                    'has_export': bool(feishu.get('export')),
                    'report_info': report_info,
                    'export_info': export_info,
                    'files': [],
                    'voided': bool(data.get('voided')),
                    'voided_at': data.get('voided_at', ''),
                    'voided_by': data.get('voided_by', ''),
                    'void_reason': data.get('void_reason', '')
                }
        except:
            pass

    for export_file in list(REPORTS_DIR.glob('X1EXPORT_*.docx')) + list(REPORTS_DIR.glob('X1EXPORT_*.xlsx')):
        export_id = export_file.stem.split('.')[0]
        if export_id in export_groups:
            export_groups[export_id]['files'].append({'name': export_file.name, 'path': str(export_file)})
            if '.filled.' in export_file.name or '.bound.' in export_file.name:
                export_groups[export_id]['has_report'] = True
                if not export_groups[export_id]['report_info'].get('feishu_url'):
                    export_groups[export_id]['report_info']['filename'] = export_file.name
            elif export_file.name.endswith('.xlsx'):
                export_groups[export_id]['has_export'] = True
                if not export_groups[export_id]['export_info'].get('feishu_url'):
                    export_groups[export_id]['export_info']['filename'] = export_file.name

    records.extend(export_groups.values())
    records = [r for r in records if can_view_record(current_user, {'inspector_name': r.get('operator', '')})]

    for r in records:
        if r.get('type') == 'export':
            if r.get('report_success') is None:
                r['report_success'] = bool((r.get('report_info') or {}).get('feishu_url') or (r.get('report_info') or {}).get('filename'))
            if r.get('raw_record_success') is None:
                r['raw_record_success'] = bool((r.get('export_info') or {}).get('feishu_url') or (r.get('export_info') or {}).get('filename'))
            r['asset_state'] = _compute_record_asset_state(r)

    keyword = request.args.get('keyword', '').strip().lower()
    domain_filter = request.args.get('domain', '').strip()
    type_filter = request.args.get('type', '').strip()

    if domain_filter:
        records = [r for r in records if r.get('domain', '') == domain_filter]
    if type_filter:
        if type_filter == 'report':
            records = [r for r in records if r.get('type', '') == 'export' and (r.get('report_success') or r.get('has_report') or (r.get('report_info') or {}).get('filename') or (r.get('report_info') or {}).get('feishu_url'))]
        elif type_filter == 'draft':
            records = [r for r in records if r.get('type', '') == 'draft']
        elif type_filter == 'voided':
            records = [r for r in records if bool(r.get('voided'))]
        elif type_filter == 'all':
            pass
        else:
            records = [r for r in records if r.get('type', '') == type_filter]
    if keyword:
        parts = keyword.split()
        def match_keyword(r):
            s = ' '.join([
                r.get('project_name', ''),
                r.get('report_number', ''),
                r.get('client_name', ''),
                r.get('operator', '')
            ]).lower()
            return all(p in s for p in parts)
        records = [r for r in records if match_keyword(r)]

    summary = {
        'total': len(records),
        'report_count': 0,
        'raw_record_count': 0,
        'export_count': 0,
        'draft_count': 0,
        'sync_issue_count': 0,
        'format_mismatch_count': 0,
        'feishu_failed_count': 0
    }

    for r in records:
        if r.get('type') == 'export':
            summary['export_count'] += 1
            has_report = bool(
                r.get('report_success') or r.get('has_report') or
                (r.get('report_info') or {}).get('filename') or
                (r.get('report_info') or {}).get('feishu_url')
            )
            has_raw = bool(
                r.get('raw_record_success') or r.get('has_export') or
                (r.get('export_info') or {}).get('filename') or
                (r.get('export_info') or {}).get('feishu_url')
            )
            if has_report:
                summary['report_count'] += 1
            if has_raw:
                summary['raw_record_count'] += 1
            asset_state = r.get('asset_state') or _compute_record_asset_state(r)
            if asset_state.get('issues'):
                summary['sync_issue_count'] += 1
            if 'raw_record_format_mismatch' in asset_state.get('issues', []):
                summary['format_mismatch_count'] += 1
            if 'feishu_report_failed' in asset_state.get('issues', []) or 'feishu_record_failed' in asset_state.get('issues', []):
                summary['feishu_failed_count'] += 1
        elif r.get('type') == 'draft':
            summary['draft_count'] += 1

    return jsonify({'success': True, 'summary': summary})

@app.route('/admin/api/records/<record_id>', methods=['DELETE'])
@login_required
@require_permission('admin.records.delete')
def admin_api_delete_record(record_id):
    """删除记录（软删除，移至 trash）"""
    if not _setting_enabled('security.allow_delete_record', True):
        return jsonify({'success': False, 'error': '系统设置已禁止删除记录'}), 403
    ok, msg = _soft_delete_record(record_id)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 404
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '删除记录', record_id, msg)
    return jsonify({'success': True, 'message': msg})


@app.route('/admin/api/records/<record_id>/retry_feishu', methods=['POST'])
@login_required
@require_permission('admin.feishu.retry')
def admin_api_retry_feishu(record_id):
    """重试飞书上传（基于现有导出文件）"""
    json_path = REPORTS_DIR / f"{record_id}.json"
    if not json_path.exists():
        return jsonify({'success': False, 'error': '导出记录不存在'}), 404

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        return jsonify({'success': False, 'error': f'读取导出记录失败: {e}'}), 500

    export_payload = data.get('export_payload') or {}
    project = export_payload.get('project') or {}
    detection_date = project.get('detection_date', '')
    year = int(detection_date[:4]) if detection_date and len(detection_date) >= 4 else datetime.now().year

    xlsx_target = REPORTS_DIR / f"{record_id}.xlsx"
    docx_target = REPORTS_DIR / f"{record_id}.docx"
    bound_docx_target = REPORTS_DIR / f"{record_id}.bound.docx"
    filled_docx_target = REPORTS_DIR / f"{record_id}.filled.docx"

    feishu_report = {}
    feishu_export = {}

    report_file = filled_docx_target if filled_docx_target.exists() else bound_docx_target
    if report_file.exists():
        reports_folder = resolve_feishu_upload_folder('reports', year)
        if reports_folder:
            feishu_report = upload_file_to_feishu(str(report_file), reports_folder)
        else:
            feishu_report = {'success': False, 'error': '未执行或未获得上传结果'}
    else:
        feishu_report = {'success': False, 'error': '报告文件不存在'}

    if xlsx_target.exists():
        exports_folder = resolve_feishu_upload_folder('exports', year)
        if exports_folder:
            feishu_export = upload_file_to_feishu(str(xlsx_target), exports_folder)
        else:
            feishu_export = {'success': False, 'error': '未执行或未获得上传结果'}
    else:
        feishu_export = {'success': False, 'error': '原始记录文件不存在'}

    data['feishu'] = {
        'report': feishu_report or {'success': False, 'error': '未执行或未获得上传结果'},
        'export': feishu_export or {'success': False, 'error': '未执行或未获得上传结果'}
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    log_action(current_user.id if current_user.is_authenticated else 'unknown', '重试飞书上传', record_id,
              f"report={'ok' if feishu_report.get('success') else 'fail'} export={'ok' if feishu_export.get('success') else 'fail'}")

    return jsonify({
        'success': True,
        'record_id': record_id,
        'feishu': data.get('feishu', {}),
        'report_success': feishu_report.get('success', False),
        'export_success': feishu_export.get('success', False)
    })


@app.route('/api/void_export/<record_id>', methods=['POST'])
@login_required
@require_permission('admin.records.void_export')
def api_void_export_record(record_id):
    json_path = REPORTS_DIR / f"{record_id}.json"
    if not json_path.exists():
        return jsonify({'success': False, 'error': '导出记录不存在'}), 404
    try:
        payload = request.get_json(silent=True) or {}
        reason = str(payload.get('reason', '') or '').strip()
        if not reason:
            return jsonify({'success': False, 'error': '必须填写作废理由'}), 400
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if data.get('voided'):
            return jsonify({'success': True, 'record_id': record_id, 'voided': True, 'message': '该记录已作废'})
        data['voided'] = True
        data['voided_at'] = _x_now()
        data['voided_by'] = current_user.id if current_user.is_authenticated else 'unknown'
        data['void_reason'] = reason
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log_action(current_user.id if current_user.is_authenticated else 'unknown', '作废记录', record_id, f'前台作废标记: {reason}')
        return jsonify({'success': True, 'record_id': record_id, 'voided': True, 'voided_at': data['voided_at'], 'voided_by': data['voided_by'], 'void_reason': data['void_reason']})
    except Exception as e:
        return jsonify({'success': False, 'error': f'作废失败: {e}'}), 500


@app.route('/admin/api/records/batch_delete', methods=['POST'])
@login_required
@require_permission('admin.records.batch_delete')
def admin_api_batch_delete_records():
    """批量删除记录（软删除，移至 trash）"""
    data = request.get_json(silent=True) or {}
    record_ids = data.get('record_ids', [])
    if not isinstance(record_ids, list) or not record_ids:
        return jsonify({'success': False, 'error': '请选择要删除的记录'}), 400
    deleted, failed = [], []
    for record_id in record_ids:
        ok, msg = _soft_delete_record(str(record_id))
        if ok:
            deleted.append(str(record_id))
            log_action(current_user.id if current_user.is_authenticated else 'unknown', '批量删除记录', str(record_id), msg)
        else:
            failed.append({'id': str(record_id), 'error': msg})
    return jsonify({'success': True, 'deleted_count': len(deleted), 'deleted_ids': deleted, 'failed': failed})

def cleanup_trash(days=30):
    """清理 trash 目录中超过指定天数的文件"""
    import time
    trash_dir = BASE_DIR / 'trash'
    if not trash_dir.exists():
        return {'deleted_count': 0, 'freed_bytes': 0}
    cutoff = time.time() - days * 86400
    deleted_count = 0
    freed_bytes = 0
    for f in list(trash_dir.rglob('*')):
        if f.is_file() and f.stat().st_mtime < cutoff:
            size = f.stat().st_size
            try:
                f.unlink()
                deleted_count += 1
                freed_bytes += size
                print(f'[trash-cleanup] 删除: {f.name} ({size} bytes)')
            except Exception as e:
                print(f'[trash-cleanup] 删除失败: {f.name} - {e}')
    # 清理空子目录
    for d in sorted(trash_dir.rglob('*'), reverse=True):
        if d.is_dir() and not list(d.iterdir()):
            try:
                d.rmdir()
            except Exception:
                pass
    print(f'[trash-cleanup] 完成: 删除 {deleted_count} 个文件, 释放 {freed_bytes/1024/1024:.2f} MB')
    return {'deleted_count': deleted_count, 'freed_bytes': freed_bytes}


@app.route('/admin/api/cleanup_trash', methods=['POST'])
@login_required
@require_permission('admin.trash.cleanup')
def admin_api_cleanup_trash():
    """清理过期的软删除文件"""
    if not _setting_enabled('security.allow_cleanup_trash', True):
        return jsonify({'success': False, 'error': '系统设置已禁止清空回收站'}), 403
    data = request.get_json(silent=True) or {}
    days = int(data.get('days', 30))
    result = cleanup_trash(days)
    log_action(session.get('username', 'admin'), '清理回收站', '',
              f"清理 {result['deleted_count']} 个文件，释放 {result['freed_bytes']/1024/1024:.2f} MB")
    return jsonify({'success': True, **result})


@app.route('/admin/api/trash_status')
@login_required
@require_permission('admin.trash.cleanup')
def admin_api_trash_status():
    """获取回收站状态"""
    trash_dir = BASE_DIR / 'trash'
    if not trash_dir.exists():
        return jsonify({'count': 0, 'size_bytes': 0, 'size_mb': '0.00'})
    files = list(trash_dir.rglob('*'))
    files = [f for f in files if f.is_file()]
    total_size = sum(f.stat().st_size for f in files)
    return jsonify({
        'count': len(files),
        'size_bytes': total_size,
        'size_mb': f'{total_size/1024/1024:.2f}'
    })


@app.route('/admin/api/permissions/roles')
@login_required
@require_permission('admin.permissions.view')
def admin_api_role_permissions():
    result = []
    with get_db() as conn:
        rows = conn.execute('SELECT role, permission_key, enabled FROM role_permissions ORDER BY role, permission_key').fetchall()
    custom_map = {}
    for row in rows:
        custom_map.setdefault(row['role'], {})[row['permission_key']] = bool(row['enabled'])
    for role, defaults in DEFAULT_ROLE_PERMISSIONS.items():
        effective = sorted(set(defaults) | {k for k, v in custom_map.get(role, {}).items() if v})
        disabled = sorted([k for k, v in custom_map.get(role, {}).items() if not v])
        result.append({
            'role': role,
            'default_permissions': sorted(defaults),
            'custom_permissions': custom_map.get(role, {}),
            'effective_permissions': effective,
            'disabled_permissions': disabled,
        })
    return jsonify({'success': True, 'roles': result})


@app.route('/admin/api/permissions/roles/<role>', methods=['PUT'])
@login_required
@require_permission('admin.permissions.manage')
def admin_api_role_permissions_update(role):
    if role == 'admin':
        return jsonify({'success': False, 'error': 'admin 角色权限不可修改'}), 403
    if role not in DEFAULT_ROLE_PERMISSIONS:
        return jsonify({'success': False, 'error': '角色不存在'}), 404
    data = request.get_json(silent=True) or {}
    custom_permissions = data.get('custom_permissions', {})
    if not isinstance(custom_permissions, dict):
        return jsonify({'success': False, 'error': 'custom_permissions 必须为对象'}), 400
    now = datetime.now().isoformat()
    with get_db() as conn:
        conn.execute('DELETE FROM role_permissions WHERE role = ?', (role,))
        for key, enabled in custom_permissions.items():
            key = str(key or '').strip()
            if not key:
                continue
            conn.execute(
                'INSERT INTO role_permissions (role, permission_key, enabled, updated_at) VALUES (?, ?, ?, ?)',
                (role, key, 1 if bool(enabled) else 0, now)
            )
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '更新角色权限', role, json.dumps(custom_permissions, ensure_ascii=False))
    return jsonify({'success': True, 'role': role, 'custom_permissions': custom_permissions})


@app.route('/admin/api/users')
@login_required
@require_permission('admin.users.view')
def admin_api_users():
    """用户列表（从数据库读取）"""
    from database import get_db
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


@app.route('/admin/api/users', methods=['POST'])
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


@app.route('/admin/api/users/<username>', methods=['PUT'])
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


@app.route('/admin/api/users/<username>', methods=['DELETE'])
@login_required
@require_permission('admin.users.manage')
def admin_api_users_delete(username):
    """删除用户（从数据库删除）"""
    from auth import delete_user
    from database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT display_name FROM users WHERE user_id = ?', (username,))
        row = cursor.fetchone()
        display_name = row['display_name'] if row else username
    ok, msg = delete_user(username)
    if not ok:
        status = 400 if username == 'admin' else 404
        return jsonify({'success': False, 'error': msg}), status
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '删除用户', username, f'姓名: {display_name}')
    return jsonify({'success': True, 'message': f'用户 {display_name} 已删除'})

@app.route('/admin/api/users/<username>/toggle_active', methods=['POST'])
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


@app.route('/admin/api/users/<username>/reset_password', methods=['POST'])
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
# 操作日志 API
# ============================================================

@app.route('/admin/api/logs')
@login_required
@require_permission('admin.logs.view')
def admin_api_logs():
    """操作日志列表（分页）"""
    from database import get_db

    month = (request.args.get('month') or datetime.now().strftime('%Y-%m')).strip()
    user_filter = (request.args.get('user') or '').strip()
    action_filter = (request.args.get('action') or '').strip()
    category_filter = (request.args.get('category') or '').strip()
    keyword = (request.args.get('keyword') or '').strip()
    page = max(1, int(request.args.get('page', 1)))
    page_size = max(1, min(500, int(request.args.get('page_size', 50))))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f'''
            SELECT id, time, user, action, target, detail
            FROM action_logs
            WHERE time LIKE ?
            ORDER BY id DESC
        ''', [f'{month}%'])
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




@app.route('/admin/api/logs/batch_delete', methods=['POST'])
@login_required
@require_permission('admin.logs.delete')
def admin_api_logs_batch_delete():
    """批量删除操作日志"""
    from database import get_db
    data = request.get_json(silent=True) or {}
    log_ids = data.get('log_ids', [])
    if not isinstance(log_ids, list) or not log_ids:
        return jsonify({'success': False, 'error': '请选择要删除的日志'}), 400
    ids = [int(x) for x in log_ids if str(x).isdigit()]
    if not ids:
        return jsonify({'success': False, 'error': '日志ID无效'}), 400
    placeholders = ','.join('?' for _ in ids)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(f'DELETE FROM action_logs WHERE id IN ({placeholders})', ids)
        deleted_count = cursor.rowcount
        conn.commit()
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '批量删除操作日志', '', f'删除 {deleted_count} 条日志')
    return jsonify({'success': True, 'deleted_count': deleted_count})

@app.route('/admin/api/logs/months')
@login_required
@require_permission('admin.logs.view')
def admin_api_logs_months():
    """日志月份列表"""
    from database import get_db
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT substr(time, 1, 7) as month 
            FROM action_logs 
            ORDER BY month DESC
        ''')
        months = [row['month'] for row in cursor.fetchall()]
    
    if not months:
        months = [datetime.now().strftime('%Y-%m')]
    return jsonify(months)



# ============================================================
# 标准数据库 API
# ============================================================

@app.route('/admin/api/standards')
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


@app.route('/admin/api/standards/<path:std_code>')
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



def _compute_operating_room_group_stats(group: str, overlay: dict) -> dict:
    from template_resources import get_semantic_template_mapping
    group = str(group or '').strip()
    group_prefix = f'hospital/operating_room/{group}/'
    semantic_prefix = f'hospital.operating_room.{group}.'
    semantic_keys = [
        'hospital.operating_room.main.level1',
        'hospital.operating_room.main.level2',
        'hospital.operating_room.main.level3',
        'hospital.operating_room.main.level4',
        'hospital.operating_room.eye.level1',
        'hospital.operating_room.eye.level2',
        'hospital.operating_room.eye.level3',
        'hospital.operating_room.eye.level4',
        'hospital.operating_room.aux.level1',
        'hospital.operating_room.aux.level2',
        'hospital.operating_room.aux.level3',
        'hospital.operating_room.aux.level4',
    ]
    target_keys = [k for k in semantic_keys if k.startswith(semantic_prefix)]
    stats = {
        'total': len(target_keys),
        'registered_keys': 0,
        'enabled_count': 0,
        'missing_count': 0,
        'exists': True,
        'ready': 0,
        'readyBasic': 0,
        'pending': 0,
        'risk': 0,
        'activated': 0,
        'registeredOnly': 0,
        'display_enabled_count': None,
    }
    seen = set()
    for semantic_key in target_keys:
        mapping = get_semantic_template_mapping(semantic_key)
        default_key = str(mapping.get('default_template_key', '')).strip()
        item = overlay.get(default_key) if default_key else None
        st = _compute_template_scene_state(mapping, item)
        code = str(st.get('code', 'unknown'))
        if code == 'verified_export':
            stats['ready'] += 1
        elif code == 'verified_basic':
            stats['readyBasic'] += 1
        elif code == 'registered':
            stats['registeredOnly'] += 1
        elif code == 'pending_config':
            stats['pending'] += 1
        else:
            stats['risk'] += 1
        if item and item.get('enabled', True) is not False:
            stats['activated'] += 1
        allowed_keys = list(mapping.get('allowed_template_keys', []) or [])
        if default_key and default_key not in allowed_keys:
            allowed_keys.append(default_key)
        for tk in allowed_keys:
            tk = str(tk or '').strip()
            if not tk or not tk.startswith(group_prefix) or tk in seen:
                continue
            seen.add(tk)
            stats['registered_keys'] += 1
            reg_item = overlay.get(tk) or {}
            if reg_item.get('enabled', True) is not False:
                stats['enabled_count'] += 1
            tpath = str(reg_item.get('template_path', '')).strip()
            if not tpath or not Path(tpath).exists():
                stats['missing_count'] += 1
    return stats


def _compute_template_home_stats(type_id: str, overlay: dict) -> dict:
    from template_resources import get_type_template_mapping, get_semantic_template_mapping
    semantic_options = [
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.a', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.b', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.c', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.d', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.a', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.b', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.c', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.d', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'food.food_workshop.grade.1', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.2', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.3', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.4', 'type_id': 'food_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.5', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.6', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.7', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.8', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.9', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'hospital.clean_function_room.icu', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.cssd', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.dialysis', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.general', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.operating_room.main.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'biosafety.animal_room.normal', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_main', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.isolation', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_storage', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.after_sterilization', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_corridor', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.dirty_corridor', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.buffer', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_2', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.cleaning_disinfection', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_1', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.bsl.p2', 'type_id': 'bsl'},
        {'semantic_key': 'biosafety.bsl.p3', 'type_id': 'bsl'},
    ]
    mapping = get_type_template_mapping(type_id)
    semantic_rows = [item for item in semantic_options if item.get('type_id') == type_id]
    scene_states = []
    stats = {
        'total': 1,
        'registered_keys': 0,
        'enabled_count': 0,
        'missing_count': 0,
        'ready': 0,
        'readyBasic': 0,
        'pending': 0,
        'risk': 0,
        'registeredOnly': 0,
        'display_enabled_count': 0,
    }
    if semantic_rows:
        stats['total'] = 0
        for opt in semantic_rows:
            semantic_mapping = get_semantic_template_mapping(opt.get('semantic_key', ''))
            st = _resolve_scene_state_for_home(semantic_mapping, overlay)
            scene_states.append(st)
            stats['total'] += 1
            code = str(st.get('code', 'unknown'))
            if code == 'verified_export':
                stats['ready'] += 1
            elif code == 'verified_basic':
                stats['readyBasic'] += 1
            elif code == 'registered':
                stats['registeredOnly'] += 1
            elif code == 'pending_config':
                stats['pending'] += 1
            else:
                stats['risk'] += 1
    else:
        st = _resolve_scene_state_for_home(mapping, overlay)
        scene_states.append(st)
        code = str(st.get('code', 'unknown'))
        if code == 'verified_export':
            stats['ready'] = 1
        elif code == 'verified_basic':
            stats['readyBasic'] = 1
        elif code == 'registered':
            stats['registeredOnly'] = 1
        elif code == 'pending_config':
            stats['pending'] = 1
        else:
            stats['risk'] = 1
    seen = set()
    for template_key, value in overlay.items():
        if not isinstance(value, dict) or value.get('type_id') != type_id:
            continue
        if template_key in seen:
            continue
        seen.add(template_key)
        stats['registered_keys'] += 1
        if value.get('enabled', True) is not False:
            stats['enabled_count'] += 1
        template_path = str(value.get('template_path', '')).strip()
        if not template_path or not Path(template_path).exists():
            stats['missing_count'] += 1
    stats['display_enabled_count'] = stats['enabled_count']
    home_state = _compute_home_flow_state(scene_states)
    return stats, home_state


@app.route('/admin/api/templates')
@login_required
@require_permission('admin.templates.view')
def admin_api_templates():
    from template_resources import TEMPLATE_MAP, list_registered_template_resources, get_type_template_mapping
    overlay = list_registered_template_resources()
    semantic_options = [
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.a', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.b', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.c', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.d', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.a', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.b', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.c', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.d', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'food.food_workshop.grade.1', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.2', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.3', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.4', 'type_id': 'food_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.5', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.6', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.7', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.8', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.9', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'hospital.clean_function_room.icu', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.cssd', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.dialysis', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.general', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.operating_room.main.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'biosafety.animal_room.normal', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_main', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.isolation', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_storage', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.after_sterilization', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_corridor', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.dirty_corridor', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.buffer', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_2', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.cleaning_disinfection', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_1', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.bsl.p2', 'type_id': 'bsl'},
        {'semantic_key': 'biosafety.bsl.p3', 'type_id': 'bsl'},
    ]
    result = []
    for tid, cfg in TEMPLATE_MAP.items():
        rel_path = str(cfg.get('path', '')).strip()
        abs_dir = TEMPLATE_BASE / rel_path if rel_path else TEMPLATE_BASE
        builtin_files = list(cfg.get('files', []) or [])
        files = []
        for fname in builtin_files:
            fpath = abs_dir / fname
            files.append({
                'name': fname,
                'exists': fpath.exists(),
                'size': fpath.stat().st_size if fpath.exists() else 0,
            })
        registered_pairs = [(k, v) for k, v in overlay.items() if isinstance(v, dict) and v.get('type_id') == tid]
        registered_pairs = sorted(registered_pairs, key=lambda kv: str((kv[1] or {}).get('last_verified_at', '')), reverse=True)
        mapping = get_type_template_mapping(tid)
        allowed_keys = list(mapping.get('allowed_template_keys', []) or [])
        default_template_key = mapping.get('default_template_key', '') or ''
        last_verified_at = ''
        last_verify_result = ''
        version = ''
        enabled = True
        if registered_pairs:
            _, latest = registered_pairs[0]
            last_verified_at = latest.get('last_verified_at', '')
            last_verify_result = latest.get('last_verify_result', '')
            version = latest.get('version', '')
        if default_template_key:
            default_item = overlay.get(default_template_key) or {}
            enabled = default_item.get('enabled', True)
            if not version:
                version = default_item.get('version', '')
            if not last_verified_at:
                last_verified_at = default_item.get('last_verified_at', '')
            if not last_verify_result:
                last_verify_result = default_item.get('last_verify_result', '')
        enabled_count = sum(1 for _, v in registered_pairs if (v or {}).get('enabled', True))
        missing_count = sum(1 for _, v in registered_pairs if not Path(str((v or {}).get('template_path', ''))).exists())

        stats, home_state = _compute_template_home_stats(tid, overlay)

        row = {
            'id': tid,
            'name': cfg.get('name', tid),
            'domain': cfg.get('domain', ''),
            'path': rel_path,
            'template_count': len(files),
            'valid_count': sum(1 for f in files if f.get('exists')),
            'exists': abs_dir.exists(),
            'registered_keys': len(registered_pairs),
            'candidate_count': len(allowed_keys),
            'enabled_count': enabled_count,
            'missing_count': missing_count,
            'source': '内置模板+注册配置' if registered_pairs else '内置模板',
            'version': version or '—',
            'last_verified_at': last_verified_at,
            'last_verify_result': _human_verify_result(last_verify_result or 'unverified'),
            'default_template_key': default_template_key,
            'enabled': enabled,
            'default_warning': (
                'missing' if default_template_key and (not overlay.get(default_template_key) or not Path(str((overlay.get(default_template_key) or {}).get('template_path', '')).strip()).exists())
                else 'disabled' if default_template_key and overlay.get(default_template_key) and (overlay.get(default_template_key) or {}).get('enabled', True) is False
                else 'unset' if not default_template_key
                else ''
            ),
            'home_status_code': home_state.get('code', 'error'),
            'home_status_text': home_state.get('text', '异常'),
            'home_status_level': home_state.get('level', 'danger'),
            'total': stats.get('total', 1),
            'ready': stats.get('ready', 0),
            'readyBasic': stats.get('readyBasic', 0),
            'pending': stats.get('pending', 0),
            'risk': stats.get('risk', 0),
            'registeredOnly': stats.get('registeredOnly', 0),
            'display_enabled_count': stats.get('display_enabled_count', enabled_count),
        }
        if tid == 'operating_room':
            row['group_stats'] = {
                'main': _compute_operating_room_group_stats('main', overlay),
                'eye': _compute_operating_room_group_stats('eye', overlay),
                'aux': _compute_operating_room_group_stats('aux', overlay),
            }
        result.append(row)
    return jsonify({'templates': result, 'total': len(result), 'overlay_total': len(overlay)})


@app.route('/admin/api/template-registry/options')
@login_required
@require_permission('admin.templates.view')
def admin_api_template_registry_options():
    import template_resources as tr
    objects = getattr(tr, 'TEMPLATE_OBJECT_OPTIONS', None)
    if not isinstance(objects, dict) or not objects:
        template_map = getattr(tr, 'TEMPLATE_MAP', {}) or {}
        objects = {}
        for type_id, cfg in template_map.items():
            if not isinstance(cfg, dict):
                continue
            objects[type_id] = {
                'name': cfg.get('name', type_id),
                'label': cfg.get('name', type_id),
                'domain': cfg.get('domain', ''),
                'path': cfg.get('path', ''),
                'keyBase': type_id,
            }
    else:
        normalized = {}
        for type_id, cfg in objects.items():
            if not isinstance(cfg, dict):
                continue
            normalized[type_id] = {
                **cfg,
                'label': cfg.get('label') or cfg.get('name') or type_id,
                'keyBase': cfg.get('keyBase') or type_id,
            }
        objects = normalized
    semantic_options = [
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.a', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / A级'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.b', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / B级'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.c', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / C级'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.d', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / D级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.a', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / A级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.b', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / B级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.c', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / C级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.d', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / D级'},
        {'semantic_key': 'food.food_workshop.grade.1', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅰ级'},
        {'semantic_key': 'food.food_workshop.grade.2', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅱ级'},
        {'semantic_key': 'food.food_workshop.grade.3', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅲ级'},
        {'semantic_key': 'food.food_workshop.grade.4', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅳ级'},
        {'semantic_key': 'electronics.electronics_workshop.iso.5', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 5'},
        {'semantic_key': 'electronics.electronics_workshop.iso.6', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 6'},
        {'semantic_key': 'electronics.electronics_workshop.iso.7', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 7'},
        {'semantic_key': 'electronics.electronics_workshop.iso.8', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 8'},
        {'semantic_key': 'electronics.electronics_workshop.iso.9', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 9'},
        {'semantic_key': 'hospital.clean_function_room.icu', 'type_id': 'clean_function_room', 'label': '洁净功能房 / ICU'},
        {'semantic_key': 'hospital.clean_function_room.cssd', 'type_id': 'clean_function_room', 'label': '洁净功能房 / 消毒供应中心'},
        {'semantic_key': 'hospital.clean_function_room.dialysis', 'type_id': 'clean_function_room', 'label': '洁净功能房 / 透析室'},
        {'semantic_key': 'hospital.clean_function_room.general', 'type_id': 'clean_function_room', 'label': '洁净功能房 / 通用洁净功能房'},
        {'semantic_key': 'hospital.operating_room.main.level1', 'type_id': 'operating_room', 'label': '手术部 / 百级手术室'},
        {'semantic_key': 'hospital.operating_room.main.level2', 'type_id': 'operating_room', 'label': '手术部 / 千级手术室'},
        {'semantic_key': 'hospital.operating_room.main.level3', 'type_id': 'operating_room', 'label': '手术部 / 万级手术室'},
        {'semantic_key': 'hospital.operating_room.main.level4', 'type_id': 'operating_room', 'label': '手术部 / 十万级手术室'},
        {'semantic_key': 'hospital.operating_room.eye.level1', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 百级'},
        {'semantic_key': 'hospital.operating_room.eye.level2', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 千级'},
        {'semantic_key': 'hospital.operating_room.eye.level3', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 万级'},
        {'semantic_key': 'hospital.operating_room.eye.level4', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 十万级'},
        {'semantic_key': 'hospital.operating_room.aux.level1', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 局5周6'},
        {'semantic_key': 'hospital.operating_room.aux.level2', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 ISO 7'},
        {'semantic_key': 'hospital.operating_room.aux.level3', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 ISO 8'},
        {'semantic_key': 'hospital.operating_room.aux.level4', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 ISO 8.5'},
        {'semantic_key': 'biosafety.animal_room.normal', 'type_id': 'animal_room', 'label': '动物房 / 普通环境'},
        {'semantic_key': 'biosafety.animal_room.barrier_main', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境主房间'},
        {'semantic_key': 'biosafety.animal_room.isolation', 'type_id': 'animal_room', 'label': '动物房 / 隔离环境'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_storage', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境洁物储存室'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.after_sterilization', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境灭菌后室区'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_corridor', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境洁净走廊'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.dirty_corridor', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境污物走廊'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.buffer', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境缓冲间'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_2', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境二更'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.cleaning_disinfection', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境清洗消毒室'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_1', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境一更'},
        {'semantic_key': 'biosafety.bsl.p2', 'type_id': 'bsl', 'label': '生物安全实验室 / P2'},
        {'semantic_key': 'biosafety.bsl.p3', 'type_id': 'bsl', 'label': '生物安全实验室 / P3'},
    ]
    semantic_by_type = {}
    for item in semantic_options:
        semantic_by_type.setdefault(item['type_id'], []).append(item)
    for type_id, cfg in objects.items():
        if isinstance(cfg, dict):
            cfg['semanticOptions'] = semantic_by_type.get(type_id, [])
    registry_keys = []
    try:
        registry_keys = sorted(list((tr.list_registered_template_resources() or {}).keys()))
    except Exception:
        registry_keys = []
    return jsonify({'success': True, 'objects': objects, 'template_base': str(TEMPLATE_BASE), 'registry_keys': registry_keys})


@app.route('/admin/api/template-registry/register', methods=['POST'])
@login_required
@require_permission('admin.templates.registry.manage')
def admin_api_template_registry_register():
    data = request.get_json(silent=True) or {}
    type_id = str(data.get('type_id', '')).strip()
    template_key = str(data.get('template_key', '')).strip()
    template_name = str(data.get('template_name', '')).strip()
    path_mode = str(data.get('path_mode', 'relative')).strip() or 'relative'
    relative_dir = str(data.get('relative_dir', '')).strip().strip('/')
    relative_path = str(data.get('relative_path', '')).strip().strip('/')
    absolute_path = str(data.get('absolute_path', '')).strip()
    resource_note = str(data.get('resource_note', '')).strip()
    attach_to_type = bool(data.get('attach_to_type', True))
    set_as_default = bool(data.get('set_as_default', False))
    semantic_key = str(data.get('semantic_key', '')).strip()
    attach_to_semantic = bool(data.get('attach_to_semantic', False))
    set_as_semantic_default = bool(data.get('set_as_semantic_default', False))

    if not type_id or not template_key or not template_name:
        return jsonify({'success': False, 'error': 'type_id / template_key / template_name 不能为空'}), 400
    key_error = _validate_template_key(template_key)
    if key_error:
        return jsonify({'success': False, 'error': key_error, 'template_key': template_key}), 400

    if path_mode == 'absolute':
        template_path = absolute_path
    else:
        parts = [p for p in [relative_dir, relative_path or template_name] if p]
        template_path = str(TEMPLATE_BASE / '/'.join(parts)) if parts else str(TEMPLATE_BASE / template_name)

    # 路径穿越防护
    resolved = Path(template_path).resolve()
    template_base_resolved = TEMPLATE_BASE.resolve()
    if not str(resolved).startswith(str(template_base_resolved)):
        return jsonify({'success': False, 'error': '模板路径不允许超出模板基础目录'}), 400

    inspect = _inspect_template_docx(template_path)
    exists = inspect['exists']
    valid = inspect['valid']
    parse_error = inspect['parse_error']

    if exists and not valid:
        return jsonify({
            'success': False,
            'error': parse_error or '模板文件校验失败，请确认是有效 docx',
            'template_key': template_key,
            'template_path': template_path,
            'exists': exists,
            'valid': valid,
            'size': inspect['size'],
        }), 400

    from template_resources import register_template_resource, attach_template_key_to_type, set_type_default_template, attach_template_key_to_semantic, set_semantic_default_template, list_registered_template_resources
    existing = list_registered_template_resources() or {}
    if template_key in existing:
        return jsonify({'success': False, 'error': 'template key 已存在，请使用系统自动生成的唯一 key 或更换 key', 'template_key': template_key}), 400
    payload = {
        'template_path': template_path,
        'template_name': template_name,
        'resource_status': 'confirmed' if (exists and valid) else 'missing',
        'resource_note': resource_note or f'后台注册模板：{type_id}',
        'registered_at': _x_now(),
        'registered_by': getattr(current_user, 'id', 'unknown'),
        'type_id': type_id,
    }
    register_template_resource(template_key, payload)
    mapping = None
    semantic_mapping = None
    if attach_to_type:
        mapping = attach_template_key_to_type(type_id, template_key, updated_by=getattr(current_user, 'id', 'unknown'))
    if set_as_default:
        mapping = set_type_default_template(type_id, template_key, updated_by=getattr(current_user, 'id', 'unknown'), updated_at=_x_now())
    if semantic_key and attach_to_semantic:
        semantic_mapping = attach_template_key_to_semantic(semantic_key, template_key, updated_by=getattr(current_user, 'id', 'unknown'))
    if semantic_key and set_as_semantic_default:
        semantic_mapping = set_semantic_default_template(semantic_key, template_key, updated_by=getattr(current_user, 'id', 'unknown'), updated_at=_x_now())
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '注册模板', template_key, template_name)
    return jsonify({'success': True, 'template_key': template_key, 'template_path': template_path, 'exists': exists, 'valid': valid, 'parse_error': parse_error, 'mapping': mapping, 'semantic_mapping': semantic_mapping, 'attach_to_type': attach_to_type, 'set_as_default': set_as_default, 'semantic_key': semantic_key, 'attach_to_semantic': attach_to_semantic, 'set_as_semantic_default': set_as_semantic_default})




@app.route('/admin/api/template-registry/upload-and-register', methods=['POST'])
@login_required
@require_permission('admin.templates.registry.manage')
def admin_api_template_registry_upload_and_register():
    type_id = str(request.form.get('type_id', '')).strip()
    template_key = str(request.form.get('template_key', '')).strip()
    relative_dir = str(request.form.get('relative_dir', '')).strip().strip('/')
    resource_note = str(request.form.get('resource_note', '')).strip()
    version = str(request.form.get('version', 'v1')).strip() or 'v1'
    enabled = str(request.form.get('enabled', 'true')).strip().lower() != 'false'
    attach_to_type = str(request.form.get('attach_to_type', 'true')).strip().lower() != 'false'
    set_as_default = str(request.form.get('set_as_default', 'false')).strip().lower() == 'true'
    semantic_key = str(request.form.get('semantic_key', '')).strip()
    attach_to_semantic = str(request.form.get('attach_to_semantic', 'false')).strip().lower() == 'true'
    set_as_semantic_default = str(request.form.get('set_as_semantic_default', 'false')).strip().lower() == 'true'
    if not type_id or not template_key:
        return jsonify({'success': False, 'error': 'type_id / template_key 不能为空'}), 400
    key_error = _validate_template_key(template_key)
    if key_error:
        return jsonify({'success': False, 'error': key_error, 'template_key': template_key}), 400
    file = request.files.get('file')
    if not file or not file.filename:
        return jsonify({'success': False, 'error': '未选择模板文件'}), 400
    if not file.filename.lower().endswith('.docx'):
        return jsonify({'success': False, 'error': '仅支持 .docx 格式'}), 400

    from template_resources import TEMPLATE_OBJECT_OPTIONS, register_template_resource, attach_template_key_to_type, set_type_default_template, attach_template_key_to_semantic, set_semantic_default_template, list_registered_template_resources
    existing = list_registered_template_resources() or {}
    if template_key in existing:
        return jsonify({'success': False, 'error': 'template key 已存在，请使用系统自动生成的唯一 key 或更换 key', 'template_key': template_key}), 400
    obj = TEMPLATE_OBJECT_OPTIONS.get(type_id, {})
    if not relative_dir:
        relative_dir = str(obj.get('path', '')).strip().strip('/')
    if not relative_dir:
        return jsonify({'success': False, 'error': '无法确定模板保存目录'}), 400

    safe_name = Path(file.filename).name
    target_dir = TEMPLATE_BASE / relative_dir
    # 路径穿越防护
    if not str(target_dir.resolve()).startswith(str(TEMPLATE_BASE.resolve())):
        return jsonify({'success': False, 'error': '相对目录不允许超出模板基础目录'}), 400
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / safe_name
    file.save(str(target_path))

    inspect = _inspect_template_docx(target_path)
    exists = inspect['exists']
    valid = inspect['valid']
    parse_error = inspect['parse_error']

    if exists and not valid:
        try:
            target_path.unlink(missing_ok=True)
        except Exception:
            pass
        return jsonify({
            'success': False,
            'error': parse_error or '上传的模板不是有效 docx，已拒绝入库',
            'template_key': template_key,
            'template_path': str(target_path),
            'exists': exists,
            'valid': valid,
            'size': inspect['size'],
        }), 400

    payload = {
        'template_path': str(target_path),
        'template_name': safe_name,
        'resource_status': 'confirmed' if (exists and valid) else 'missing',
        'resource_note': resource_note or f'后台上传注册模板：{type_id}',
        'registered_at': _x_now(),
        'registered_by': getattr(current_user, 'id', 'unknown'),
        'type_id': type_id,
        'enabled': enabled,
        'version': version,
        'last_verified_at': _x_now(),
        'last_verify_result': 'success' if valid else 'failed',
        'last_verify_error': parse_error,
    }
    register_template_resource(template_key, payload)
    mapping = None
    semantic_mapping = None
    if attach_to_type:
        mapping = attach_template_key_to_type(type_id, template_key, updated_by=getattr(current_user, 'id', 'unknown'))
    if set_as_default:
        mapping = set_type_default_template(type_id, template_key, updated_by=getattr(current_user, 'id', 'unknown'), updated_at=_x_now())
    if semantic_key and attach_to_semantic:
        semantic_mapping = attach_template_key_to_semantic(semantic_key, template_key, updated_by=getattr(current_user, 'id', 'unknown'))
    if semantic_key and set_as_semantic_default:
        semantic_mapping = set_semantic_default_template(semantic_key, template_key, updated_by=getattr(current_user, 'id', 'unknown'), updated_at=_x_now())
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '上传并注册模板', template_key, safe_name)
    return jsonify({
        'success': True,
        'upload_success': exists,
        'register_success': True,
        'template_key': template_key,
        'template_path': str(target_path),
        'template_name': safe_name,
        'exists': exists,
        'valid': valid,
        'enabled': enabled,
        'version': version,
        'parse_error': parse_error,
        'mapping': mapping,
        'semantic_mapping': semantic_mapping,
        'attach_to_type': attach_to_type,
        'set_as_default': set_as_default,
        'semantic_key': semantic_key,
        'attach_to_semantic': attach_to_semantic,
        'set_as_semantic_default': set_as_semantic_default,
    })


@app.route('/admin/api/template-registry/smoke-export', methods=['POST'])
@login_required
@require_permission('admin.templates.smoke_export')
def admin_api_template_registry_smoke_export():
    data = request.get_json(silent=True) or {}
    template_key = str(data.get('template_key', '')).strip()
    type_id = str(data.get('type_id', '')).strip()
    if not template_key or not type_id:
        return jsonify({'success': False, 'error': 'template_key / type_id 不能为空'}), 400
    from template_resources import list_registered_template_resources, update_template_resource
    overlay = list_registered_template_resources()
    item = overlay.get(template_key)
    if not item:
        return jsonify({'success': False, 'error': '未找到注册模板'}), 404
    if _verify_stage(item.get('last_verify_result', '')) < 2:
        return jsonify({'success': False, 'error': '请先完成基础验证，通过后才能做试导出验证'}), 400

    template_path = str(item.get('template_path', '')).strip()
    exists = bool(template_path and Path(template_path).exists())
    valid = False
    smoke_error = ''
    if exists:
        try:
            from docx import Document
            Document(template_path)
            valid = True
        except Exception as e:
            smoke_error = str(e)
    else:
        smoke_error = '模板文件不存在'

    current = update_template_resource(template_key, {
        'resource_status': 'confirmed' if exists else 'missing',
        'last_verified_at': _x_now(),
        'last_verify_result': 'smoke_success' if valid else 'smoke_failed',
        'last_verify_error': smoke_error,
    })
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '模板导出验证', template_key, current.get('template_name', ''))
    return jsonify({
        'success': valid,
        'template_key': template_key,
        'type_id': type_id,
        'template_name': current.get('template_name', ''),
        'template_path': current.get('template_path', ''),
        'enabled': current.get('enabled', True),
        'version': current.get('version', 'v1'),
        'last_verified_at': current.get('last_verified_at', ''),
        'last_verify_result': current.get('last_verify_result', ''),
        'last_verify_result_label': _human_verify_result(current.get('last_verify_result', '')),
        'last_verify_error': current.get('last_verify_error', ''),
    })


@app.route('/admin/api/template-registry/delete', methods=['POST'])
@login_required
@require_permission('admin.templates.delete')
def admin_api_template_registry_delete():
    data = request.get_json(silent=True) or {}
    template_key = str(data.get('template_key', '')).strip()
    if not template_key:
        return jsonify({'success': False, 'error': 'template_key 不能为空'}), 400
    from template_resources import list_registered_template_resources, _save_registry_overlay, _load_type_mappings, _save_type_mappings, _load_semantic_mappings, _save_semantic_mappings
    overlay = list_registered_template_resources()
    item = overlay.get(template_key)
    if not item:
        return jsonify({'success': False, 'error': '未找到注册模板'}), 404
    removed = overlay.pop(template_key, None)
    _save_registry_overlay(overlay)
    # 清理 type_mappings 中的引用
    tm_warnings = []
    tm = _load_type_mappings()
    for tid, cfg in tm.items():
        if cfg.get('default_template_key') == template_key:
            cfg['default_template_key'] = ''
            tm_warnings.append(f'{tid} 的默认模板已清除')
        allowed = cfg.get('allowed_template_keys', [])
        if template_key in allowed:
            allowed.remove(template_key)
    if tm_warnings:
        _save_type_mappings(tm)
    # 清理 semantic_mappings 中的引用
    sm = _load_semantic_mappings()
    sm_warnings = []
    for sk, cfg in sm.items():
        if cfg.get('default_template_key') == template_key:
            cfg['default_template_key'] = ''
            sm_warnings.append(f'{sk} 的默认模板已清除')
        allowed = cfg.get('allowed_template_keys', [])
        if template_key in allowed:
            allowed.remove(template_key)
    if sm_warnings:
        _save_semantic_mappings(sm)
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '删除模板注册', template_key, (removed or {}).get('template_name', ''))
    warnings = tm_warnings + sm_warnings
    result = {'success': True, 'template_key': template_key, 'template_name': (removed or {}).get('template_name', '')}
    if warnings:
        result['warnings'] = warnings
    return jsonify(result)


@app.route('/admin/api/template-registry/toggle', methods=['POST'])
@login_required
@require_permission('admin.templates.toggle')
def admin_api_template_registry_toggle():
    data = request.get_json(silent=True) or {}
    template_key = str(data.get('template_key', '')).strip()
    enabled = bool(data.get('enabled', False))
    if not template_key:
        return jsonify({'success': False, 'error': 'template_key 不能为空'}), 400
    from template_resources import update_template_resource, _load_type_mappings, _load_semantic_mappings
    # 停用时检查是否是默认模板
    warning = ''
    if not enabled:
        tm = _load_type_mappings()
        sm = _load_semantic_mappings()
        affected = []
        for tid, cfg in tm.items():
            if cfg.get('default_template_key') == template_key:
                affected.append(f'对象 {tid} 的默认模板')
        for sk, cfg in sm.items():
            if cfg.get('default_template_key') == template_key:
                affected.append(f'场景 {sk} 的默认模板')
        if affected:
            warning = f'警告：该模板当前是{", ".join(affected)}，停用后导出功能将受影响'
    current = update_template_resource(template_key, {'enabled': enabled})
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '切换模板启停', template_key, f'enabled={enabled}')
    result = {'success': True, 'template_key': template_key, 'enabled': current.get('enabled', True)}
    if warning:
        result['warning'] = warning
    return jsonify(result)


def _verify_stage(value: str) -> int:
    v = str(value or '').strip().lower()
    if v in ('smoke_success',):
        return 3
    if v in ('success', 'passed', 'ok'):
        return 2
    if v in ('', 'unverified'):
        return 1
    return 0


def _flow_rank_from_scene_code(code: str) -> int:
    v = str(code or '').strip().lower()
    if v == 'registered':
        return 1
    if v == 'verified_basic':
        return 2
    if v == 'verified_export':
        return 3
    if v == 'enabled':
        return 4
    return 0


def _is_scene_error_code(code: str) -> bool:
    v = str(code or '').strip().lower()
    return v in (
        'pending_config',
        'missing_binding',
        'disabled',
        'missing_file',
        'file_invalid',
        'verify_failed',
        'unknown',
    )


def _compute_home_flow_state(scene_states) -> dict:
    rows = [s for s in (scene_states or []) if isinstance(s, dict)]
    if not rows:
        return {
            'code': 'error',
            'text': '异常',
            'level': 'danger',
            'reason': 'no_scene_state',
        }

    codes = [str((row or {}).get('code', '')).strip() for row in rows]
    if any(_is_scene_error_code(code) for code in codes):
        return {
            'code': 'error',
            'text': '异常',
            'level': 'danger',
            'reason': 'scene_error',
        }

    normalized = []
    for code in codes:
        raw = str(code or '').strip().lower()
        if raw in ('registered', 'verified_basic', 'verified_export', 'enabled'):
            normalized.append(raw)

    if not normalized:
        return {
            'code': 'error',
            'text': '异常',
            'level': 'danger',
            'reason': 'no_flow_state',
        }

    if len(set(normalized)) > 1:
        # 如果所有场景都在 registered / verified_basic / verified_export / enabled 中，
        # 且没有 pending 或 error，则按最低流程位判定状态，而不是笔笼统判 mixed
        flow_order = ['registered', 'verified_basic', 'verified_export', 'enabled']
        lowest = min(normalized, key=lambda c: flow_order.index(c) if c in flow_order else -1)
        if lowest == 'registered':
            return {
                'code': 'registered',
                'text': '已注册',
                'level': 'warning',
                'reason': 'min_flow_registered',
            }
        elif lowest == 'verified_basic':
            return {
                'code': 'verified_basic',
                'text': '基础验证通过',
                'level': 'info',
                'reason': 'min_flow_basic',
            }
        else:
            return {
                'code': 'verified_export',
                'text': '正常',
                'level': 'success',
                'reason': 'min_flow_export',
            }

    code = normalized[0]
    text_map = {
        'registered': '已注册',
        'verified_basic': '基础验证通过',
        'verified_export': '正常',
        'enabled': '正常',
    }
    level_map = {
        'registered': 'warning',
        'verified_basic': 'info',
        'verified_export': 'success',
        'enabled': 'success',
    }
    return {
        'code': code,
        'text': text_map.get(code, '异常'),
        'level': level_map.get(code, 'danger'),
        'reason': 'uniform_flow_stage',
    }



def _resolve_scene_state_for_home(mapping, overlay) -> dict:
    mapping = mapping or {}
    overlay = overlay or {}
    default_key = str(mapping.get('default_template_key', '')).strip()
    default_item = overlay.get(default_key) if default_key else None
    st = _compute_template_scene_state(mapping, default_item)
    if st.get('code') not in ('missing_binding', 'pending_config'):
        return st

    allowed_keys = list(mapping.get('allowed_template_keys', []) or [])
    for key in allowed_keys:
        item = overlay.get(key)
        if not isinstance(item, dict):
            continue
        fallback_mapping = dict(mapping)
        fallback_mapping['default_template_key'] = key
        fallback_state = _compute_template_scene_state(fallback_mapping, item)
        if fallback_state.get('code') in ('registered', 'verified_basic', 'verified_export', 'enabled'):
            return fallback_state
    return st



def _human_verify_result(value: str) -> str:
    v = str(value or '').strip().lower()
    if v in ('', 'unverified'):
        return '未做验证记录'
    if v in ('success', 'passed', 'ok'):
        return '基础验证通过'
    if v in ('smoke_success',):
        return '试导出验证通过'
    if v in ('failed', 'error'):
        return '基础验证失败'
    if v in ('smoke_failed',):
        return '试导出验证失败'
    return value or '未做验证记录'


def _validate_template_key(template_key: str) -> str:
    key = str(template_key or '').strip()
    if not key:
        return 'template key 不能为空'
    if re.search(r'\s', key):
        return 'template key 不能包含空格'
    if re.search(r'[A-Z]', key):
        return 'template key 必须使用小写'
    if re.search(r'[\u4e00-\u9fff]', key):
        return 'template key 不能包含中文'
    if not re.match(r'^[a-z0-9_\/-]+$', key):
        return 'template key 仅允许小写字母、数字、下划线、中划线和斜杠'
    if len(key) > 128:
        return 'template key 过长（最多 128 字符）'
    if key.count('/') > 6:
        return 'template key 层级过深（最多 6 层）'
    if '/' not in key:
        return 'template key 必须使用分层结构，不能只写临时短名'
    legacy_names = {'icu', 'hood', 'putong', 'pass-box', 'operating roon'}
    if key in legacy_names:
        return 'template key 含历史别名，请使用系统自动生成的规范 key'
    if 'electronic shop' in key or 'v2verify' in key or '/test/' in key or '/temp/' in key:
        return 'template key 含非规范命名痕迹，请使用系统自动生成的规范 key'
    return ''


def _inspect_template_docx(path_like) -> dict:
    path_obj = Path(str(path_like or '').strip()) if path_like else None
    exists = bool(path_obj and path_obj.exists())
    size = path_obj.stat().st_size if exists else 0
    valid = False
    parse_error = ''
    if exists and size >= 1024:
        try:
            from docx import Document
            Document(str(path_obj))
            valid = True
        except Exception as e:
            parse_error = str(e)
    elif exists and size > 0:
        parse_error = f'模板文件过小（{size} bytes），疑似无效 docx 或测试占位文件'
    elif exists and size == 0:
        parse_error = '模板文件为空（0 bytes）'
    elif not exists:
        parse_error = '模板文件不存在'
    return {
        'path': str(path_obj) if path_obj else '',
        'exists': exists,
        'size': size,
        'valid': valid,
        'parse_error': parse_error,
    }


def _compute_template_scene_state(mapping, item) -> dict:
    mapping = mapping or {}
    item = item or None
    default_key = str(mapping.get('default_template_key', '')).strip()
    if not default_key:
        return {
            'code': 'pending_config',
            'text': '待配置',
            'hint': '请选择一个模板作为当前模板',
            'level': 'warning',
        }
    if not item:
        return {
            'code': 'missing_binding',
            'text': '模板缺失',
            'hint': '默认模板未在候选项中命中，请切换模板或重新挂接',
            'level': 'error',
        }
    if item.get('enabled', True) is False:
        return {
            'code': 'disabled',
            'text': '模板已停用',
            'hint': '请切换模板，或先到下方模板池重新启用',
            'level': 'error',
        }

    template_path = str(item.get('template_path', '')).strip()
    path_obj = Path(template_path) if template_path else None
    exists = bool(path_obj and path_obj.exists())
    size = path_obj.stat().st_size if exists else 0
    verify_raw = str(item.get('last_verify_result', '') or '').strip().lower()

    if not exists:
        return {
            'code': 'missing_file',
            'text': '模板缺失',
            'hint': '当前默认模板文件不存在，请补齐文件或切换模板',
            'level': 'error',
        }
    if size > 0 and size < 1024:
        return {
            'code': 'file_invalid',
            'text': '模板异常',
            'hint': '当前默认模板文件体积异常，疑似不是有效 docx，请重新上传',
            'level': 'error',
        }
    if verify_raw in ('failed', 'error', 'smoke_failed'):
        return {
            'code': 'verify_failed',
            'text': '验证异常',
            'hint': '当前默认模板最近检查失败，请先修复或切换模板',
            'level': 'error',
        }
    if verify_raw in ('', 'unverified'):
        return {
            'code': 'registered',
            'text': '已注册',
            'hint': '当前模板已注册，下一步请先做基础验证',
            'level': 'warning',
        }
    if verify_raw in ('success', 'passed', 'ok'):
        return {
            'code': 'verified_basic',
            'text': '基础验证通过',
            'hint': '当前模板已通过基础验证，下一步请做试导出验证',
            'level': 'info',
        }
    if verify_raw == 'smoke_success':
        return {
            'code': 'verified_export',
            'text': '试导出验证通过',
            'hint': '当前模板已通过试导出验证，下一步可启用为当前模板',
            'level': 'success',
        }
    return {
        'code': 'unknown',
        'text': '状态未归类',
        'hint': f'当前模板存在未归类状态：{verify_raw or "unknown"}',
        'level': 'warning',
    }


@app.route('/admin/api/template-registry/verify', methods=['POST'])
@login_required
@require_permission('admin.templates.verify')
def admin_api_template_registry_verify():
    data = request.get_json(silent=True) or {}
    template_key = str(data.get('template_key', '')).strip()
    if not template_key:
        return jsonify({'success': False, 'error': 'template_key 不能为空'}), 400
    from template_resources import list_registered_template_resources, update_template_resource
    overlay = list_registered_template_resources()
    item = overlay.get(template_key)
    if not item:
        return jsonify({'success': False, 'error': '未找到注册模板'}), 404

    template_path = str(item.get('template_path', '')).strip()
    exists = bool(template_path and Path(template_path).exists())
    valid = False
    verify_error = ''
    if exists:
        try:
            from docx import Document
            Document(template_path)
            valid = True
        except Exception as e:
            verify_error = str(e)
    else:
        verify_error = '模板文件不存在'

    patch = {
        'resource_status': 'confirmed' if exists else 'missing',
        'last_verified_at': _x_now(),
        'last_verify_result': 'success' if valid else 'failed',
        'last_verify_error': verify_error,
    }
    current = update_template_resource(template_key, patch)
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '验证模板', template_key, current.get('template_name', ''))
    return jsonify({
        'success': True,
        'template_key': template_key,
        'template_name': current.get('template_name', ''),
        'template_path': current.get('template_path', ''),
        'resource_status': current.get('resource_status', 'missing'),
        'last_verified_at': current.get('last_verified_at', ''),
        'last_verify_result': current.get('last_verify_result', ''),
        'last_verify_result_label': _human_verify_result(current.get('last_verify_result', '')),
        'last_verify_error': current.get('last_verify_error', ''),
    })


@app.route('/admin/api/template-type-mappings/<type_id>')
@login_required
@require_permission('admin.templates.view')
def admin_api_template_type_mapping_detail(type_id):
    from template_resources import get_type_template_mapping, list_registered_template_resources
    mapping = get_type_template_mapping(type_id)
    overlay = list_registered_template_resources()
    items = []
    for key, value in overlay.items():
        if isinstance(value, dict) and value.get('type_id') == type_id:
            items.append({
                'template_key': key,
                'template_name': value.get('template_name', ''),
                'enabled': value.get('enabled', True),
                'version': value.get('version', 'v1'),
                'last_verified_at': value.get('last_verified_at', ''),
                'last_verify_result': value.get('last_verify_result', ''),
                'is_default': key == mapping.get('default_template_key', ''),
                'is_allowed': key in (mapping.get('allowed_template_keys', []) or []),
            })
    return jsonify({'success': True, 'type_id': type_id, 'mapping': mapping, 'items': items})


@app.route('/admin/api/template-type-mappings/set-default', methods=['POST'])
@login_required
@require_permission('admin.templates.default.set')
def admin_api_template_type_mapping_set_default():
    data = request.get_json(silent=True) or {}
    type_id = str(data.get('type_id', '')).strip()
    template_key = str(data.get('template_key', '')).strip()
    if not type_id or not template_key:
        return jsonify({'success': False, 'error': 'type_id / template_key 不能为空'}), 400
    from template_resources import list_registered_template_resources, set_type_default_template, update_template_resource
    overlay = list_registered_template_resources()
    current = overlay.get(template_key)
    if not isinstance(current, dict) or current.get('type_id') != type_id:
        return jsonify({'success': False, 'error': '该模板不属于指定检测类型或尚未注册'}), 400
    if _verify_stage(current.get('last_verify_result', '')) < 3:
        return jsonify({'success': False, 'error': '请先完成试导出验证，通过后才能启用为当前模板'}), 400
    # 检查模板文件是否存在
    tpath = current.get('template_path', '')
    if tpath and not Path(tpath).exists():
        return jsonify({'success': False, 'error': f'模板文件不存在：{Path(tpath).name}，请先上传模板文件'}), 400
    update_template_resource(template_key, {'enabled': True})
    mapping = set_type_default_template(type_id, template_key, updated_by=getattr(current_user, 'id', 'unknown'), updated_at=_x_now())
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '设置默认模板', type_id, template_key)
    return jsonify({'success': True, 'type_id': type_id, 'template_key': template_key, 'mapping': mapping})


@app.route('/admin/api/template-type-mappings/attach', methods=['POST'])
@login_required
@require_permission('admin.templates.mapping.type_manage')
def admin_api_template_type_mapping_attach():
    data = request.get_json(silent=True) or {}
    type_id = str(data.get('type_id', '')).strip()
    template_key = str(data.get('template_key', '')).strip()
    if not type_id or not template_key:
        return jsonify({'success': False, 'error': 'type_id / template_key 不能为空'}), 400
    from template_resources import list_registered_template_resources, attach_template_key_to_type
    overlay = list_registered_template_resources()
    current = overlay.get(template_key)
    if not isinstance(current, dict) or current.get('type_id') != type_id:
        return jsonify({'success': False, 'error': '该模板不属于指定检测类型或尚未注册'}), 400
    mapping = attach_template_key_to_type(type_id, template_key, updated_by=getattr(current_user, 'id', 'unknown'))
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '加入模板候选', type_id, template_key)
    return jsonify({'success': True, 'type_id': type_id, 'template_key': template_key, 'mapping': mapping})


@app.route('/admin/api/template-semantic-mappings/options')
@login_required
@require_permission('admin.templates.view')
def admin_api_template_semantic_mapping_options():
    options = [
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.a', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / A级'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.b', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / B级'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.c', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / C级'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.d', 'type_id': 'veterinary_gmp_workshop', 'label': '兽药GMP车间 / D级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.a', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / A级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.b', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / B级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.c', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / C级'},
        {'semantic_key': 'pharma.gmp_workshop.grade.d', 'type_id': 'gmp_workshop', 'label': 'GMP车间 / D级'},
        {'semantic_key': 'food.food_workshop.grade.1', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅰ级'},
        {'semantic_key': 'food.food_workshop.grade.2', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅱ级'},
        {'semantic_key': 'food.food_workshop.grade.3', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅲ级'},
        {'semantic_key': 'food.food_workshop.grade.4', 'type_id': 'food_workshop', 'label': '食品车间 / Ⅳ级'},
        {'semantic_key': 'electronics.electronics_workshop.iso.5', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 5'},
        {'semantic_key': 'electronics.electronics_workshop.iso.6', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 6'},
        {'semantic_key': 'electronics.electronics_workshop.iso.7', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 7'},
        {'semantic_key': 'electronics.electronics_workshop.iso.8', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 8'},
        {'semantic_key': 'electronics.electronics_workshop.iso.9', 'type_id': 'electronics_workshop', 'label': '电子车间 / ISO 9'},
        {'semantic_key': 'hospital.clean_function_room.icu', 'type_id': 'clean_function_room', 'label': '洁净功能房 / ICU'},
        {'semantic_key': 'hospital.clean_function_room.cssd', 'type_id': 'clean_function_room', 'label': '洁净功能房 / 消毒供应中心'},
        {'semantic_key': 'hospital.clean_function_room.dialysis', 'type_id': 'clean_function_room', 'label': '洁净功能房 / 透析室'},
        {'semantic_key': 'hospital.clean_function_room.general', 'type_id': 'clean_function_room', 'label': '洁净功能房 / 通用洁净功能房'},
        {'semantic_key': 'hospital.operating_room.main.level1', 'type_id': 'operating_room', 'label': '手术部 / 百级手术室'},
        {'semantic_key': 'hospital.operating_room.main.level2', 'type_id': 'operating_room', 'label': '手术部 / 千级手术室'},
        {'semantic_key': 'hospital.operating_room.main.level3', 'type_id': 'operating_room', 'label': '手术部 / 万级手术室'},
        {'semantic_key': 'hospital.operating_room.main.level4', 'type_id': 'operating_room', 'label': '手术部 / 十万级手术室'},
        {'semantic_key': 'hospital.operating_room.eye.level1', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 百级'},
        {'semantic_key': 'hospital.operating_room.eye.level2', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 千级'},
        {'semantic_key': 'hospital.operating_room.eye.level3', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 万级'},
        {'semantic_key': 'hospital.operating_room.eye.level4', 'type_id': 'operating_room', 'label': '手术部 / 眼科手术室 十万级'},
        {'semantic_key': 'hospital.operating_room.aux.level1', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 局5周6'},
        {'semantic_key': 'hospital.operating_room.aux.level2', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 ISO 7'},
        {'semantic_key': 'hospital.operating_room.aux.level3', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 ISO 8'},
        {'semantic_key': 'hospital.operating_room.aux.level4', 'type_id': 'operating_room', 'label': '手术部 / 洁净辅房 ISO 8.5'},
        {'semantic_key': 'biosafety.animal_room.normal', 'type_id': 'animal_room', 'label': '动物房 / 普通环境'},
        {'semantic_key': 'biosafety.animal_room.barrier_main', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境主房间'},
        {'semantic_key': 'biosafety.animal_room.isolation', 'type_id': 'animal_room', 'label': '动物房 / 隔离环境'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_storage', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境洁物储存室'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.after_sterilization', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境灭菌后室区'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_corridor', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境洁净走廊'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.dirty_corridor', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境污物走廊'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.buffer', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境缓冲间'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_2', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境二更'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.cleaning_disinfection', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境清洗消毒室'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_1', 'type_id': 'animal_room', 'label': '动物房 / 屏障环境一更'},
        {'semantic_key': 'biosafety.bsl.p2', 'type_id': 'bsl', 'label': '生物安全实验室 / P2'},
        {'semantic_key': 'biosafety.bsl.p3', 'type_id': 'bsl', 'label': '生物安全实验室 / P3'},
    ]
    return jsonify({'success': True, 'options': options})


@app.route('/admin/api/template-semantic-mappings/<path:semantic_key>')
@login_required
@require_permission('admin.templates.view')
def admin_api_template_semantic_mapping_detail(semantic_key):
    import re
    if not re.match(r'^[a-zA-Z0-9_.\-/]+$', semantic_key) or len(semantic_key) > 128:
        return jsonify({'success': False, 'error': 'semantic_key 格式无效'}), 400
    from pathlib import Path
    from template_resources import get_semantic_template_mapping, list_registered_template_resources
    mapping = get_semantic_template_mapping(semantic_key)
    overlay = list_registered_template_resources()
    type_id = str(request.args.get('type_id', '')).strip()
    items = []
    allowed_keys = set(mapping.get('allowed_template_keys', []) or [])
    default_key = str(mapping.get('default_template_key', '')).strip()
    default_item = None
    for key, value in overlay.items():
        if not isinstance(value, dict):
            continue
        if type_id and value.get('type_id') != type_id:
            continue
        if (not type_id) and key not in allowed_keys:
            continue
        template_path = str(value.get('template_path', '')).strip()
        path_obj = Path(template_path) if template_path else None
        exists = bool(path_obj and path_obj.exists())
        size = path_obj.stat().st_size if exists else 0
        row = {
            'template_key': key,
            'template_name': value.get('template_name', ''),
            'template_path': template_path,
            'exists': exists,
            'size': size,
            'enabled': value.get('enabled', True),
            'version': value.get('version', 'v1'),
            'last_verified_at': value.get('last_verified_at', ''),
            'last_verify_result': value.get('last_verify_result', ''),
            'last_verify_result_label': _human_verify_result(value.get('last_verify_result', '')),
            'is_default': key == default_key,
            'is_allowed': key in allowed_keys,
        }
        items.append(row)
        if key == default_key:
            default_item = row
    scene_state = _compute_template_scene_state(mapping, default_item)
    return jsonify({
        'success': True,
        'semantic_key': semantic_key,
        'mapping': mapping,
        'items': items,
        'scene_state': scene_state,
    })


@app.route('/admin/api/template-semantic-mappings/set-default', methods=['POST'])
@login_required
@require_permission('admin.templates.default.set')
def admin_api_template_semantic_mapping_set_default():
    data = request.get_json(silent=True) or {}
    semantic_key = str(data.get('semantic_key', '')).strip()
    template_key = str(data.get('template_key', '')).strip()
    if not semantic_key or not template_key:
        return jsonify({'success': False, 'error': 'semantic_key / template_key 不能为空'}), 400
    from template_resources import list_registered_template_resources, set_semantic_default_template, update_template_resource
    overlay = list_registered_template_resources()
    current = overlay.get(template_key)
    if not isinstance(current, dict):
        return jsonify({'success': False, 'error': '该模板尚未注册'}), 400
    if _verify_stage(current.get('last_verify_result', '')) < 3:
        return jsonify({'success': False, 'error': '请先完成试导出验证，通过后才能启用为当前模板'}), 400
    # 检查模板文件是否存在
    tpath = current.get('template_path', '')
    if tpath and not Path(tpath).exists():
        return jsonify({'success': False, 'error': f'模板文件不存在：{Path(tpath).name}，请先上传模板文件'}), 400
    # 校验模板 type_id 与 semantic_key 对应的对象类型是否匹配
    template_type_id = current.get('type_id', '')
    # semantic_key 格式: domain.type_id.xxx → 提取第二段
    sk_parts = semantic_key.split('.')
    expected_type_id = sk_parts[1] if len(sk_parts) >= 2 else ''
    if template_type_id and expected_type_id and template_type_id != expected_type_id:
        return jsonify({'success': False, 'error': f'模板类型({template_type_id})与场景对象({expected_type_id})不匹配'}), 400
    update_template_resource(template_key, {'enabled': True})
    mapping = set_semantic_default_template(semantic_key, template_key, updated_by=getattr(current_user, 'id', 'unknown'), updated_at=_x_now())
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '设置语义默认模板', semantic_key, template_key)
    return jsonify({'success': True, 'semantic_key': semantic_key, 'template_key': template_key, 'mapping': mapping})


@app.route('/admin/api/template-semantic-mappings/attach', methods=['POST'])
@login_required
@require_permission('admin.templates.mapping.semantic_manage')
def admin_api_template_semantic_mapping_attach():
    data = request.get_json(silent=True) or {}
    semantic_key = str(data.get('semantic_key', '')).strip()
    template_key = str(data.get('template_key', '')).strip()
    if not semantic_key or not template_key:
        return jsonify({'success': False, 'error': 'semantic_key / template_key 不能为空'}), 400
    from template_resources import list_registered_template_resources, attach_template_key_to_semantic
    overlay = list_registered_template_resources()
    current = overlay.get(template_key)
    if not isinstance(current, dict):
        return jsonify({'success': False, 'error': '该模板尚未注册'}), 400
    # 校验 type_id 匹配
    template_type_id = current.get('type_id', '')
    sk_parts = semantic_key.split('.')
    expected_type_id = sk_parts[1] if len(sk_parts) >= 2 else ''
    if template_type_id and expected_type_id and template_type_id != expected_type_id:
        return jsonify({'success': False, 'error': f'模板类型({template_type_id})与场景对象({expected_type_id})不匹配'}), 400
    mapping = attach_template_key_to_semantic(semantic_key, template_key, updated_by=getattr(current_user, 'id', 'unknown'))
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '加入语义模板候选', semantic_key, template_key)
    return jsonify({'success': True, 'semantic_key': semantic_key, 'template_key': template_key, 'mapping': mapping})


def _summarize_template_detail_rows(files, group: str = '') -> dict:
    def _label_stage(label: str) -> int:
        text = str(label or '')
        if '试导出验证通过' in text or '导出验证通过' in text:
            return 3
        if '基础验证通过' in text or '验证通过' in text:
            return 2
        if text and '未做验证' not in text and '未验证' not in text:
            return 1
        return 1 if text else 0
    rows = files if isinstance(files, list) else []
    prefix = f'hospital/operating_room/{group}/' if group else ''
    summary = {
        'total': 0,
        'registered': 0,
        'basic': 0,
        'exportReady': 0,
        'current': 0,
        'enabled': 0,
        'missing': 0,
        'error': 0,
    }
    for row in rows:
        if not isinstance(row, dict):
            continue
        template_key = str(row.get('template_key', '')).strip()
        if not template_key:
            continue
        if prefix and not template_key.startswith(prefix):
            continue
        summary['total'] += 1
        verify_label = str(row.get('last_verify_result', '') or '')
        stage = _label_stage(verify_label)
        if stage >= 1:
            summary['registered'] += 1
        if stage >= 2:
            summary['basic'] += 1
        if stage >= 3:
            summary['exportReady'] += 1
        if row.get('is_default'):
            summary['current'] += 1
        if row.get('enabled', True) is not False:
            summary['enabled'] += 1
        if not row.get('exists'):
            summary['missing'] += 1
        if '失败' in verify_label:
            summary['error'] += 1
    return summary


@app.route('/admin/api/templates/<template_id>')
@login_required
@require_permission('admin.templates.view')
def admin_api_template_detail(template_id):
    """模板详情 API"""
    from template_resources import TEMPLATE_MAP, list_registered_template_resources, get_type_template_mapping
    template_map = TEMPLATE_MAP
    if template_id not in template_map:
        return jsonify({'error': '模板不存在'}), 404

    info = template_map[template_id]
    dir_path = TEMPLATE_BASE / info['path']
    overlay = list_registered_template_resources()
    mapping = get_type_template_mapping(template_id)
    default_template_key = mapping.get('default_template_key', '')
    allowed_template_keys = set(mapping.get('allowed_template_keys', []) or [])
    files = []
    builtin_names = set(info.get('files', []) or [])

    for fname in info.get('files', []) or []:
        fpath = dir_path / fname
        matched_items = [
            (k, v) for k, v in overlay.items()
            if isinstance(v, dict) and v.get('type_id') == template_id and v.get('template_name') == fname
        ]
        if matched_items:
            for matched_key, matched_item in matched_items:
                files.append({
                    'name': fname,
                    'path': str(fpath),
                    'exists': fpath.exists(),
                    'size': fpath.stat().st_size if fpath.exists() else 0,
                    'template_key': matched_key,
                    'source': '注册配置',
                    'enabled': (matched_item or {}).get('enabled', True),
                    'version': (matched_item or {}).get('version', '—') if matched_item else '—',
                    'last_verified_at': (matched_item or {}).get('last_verified_at', ''),
                    'last_verify_result': _human_verify_result((matched_item or {}).get('last_verify_result', 'unverified')) if matched_item else '未做验证',
                    'is_default': matched_key == default_template_key,
                    'is_allowed': matched_key in allowed_template_keys,
                })
        elif fpath.exists():
            files.append({
                'name': fname,
                'path': str(fpath),
                'exists': True,
                'size': fpath.stat().st_size if fpath.exists() else 0,
                'template_key': '',
                'source': '内置模板',
                'enabled': True,
                'version': '—',
                'last_verified_at': '',
                'last_verify_result': '未做验证',
                'is_default': False,
                'is_allowed': False,
            })

    for matched_key, matched_item in overlay.items():
        if not isinstance(matched_item, dict) or matched_item.get('type_id') != template_id:
            continue
        template_name = str(matched_item.get('template_name', '')).strip()
        if template_name in builtin_names:
            continue
        template_path = str(matched_item.get('template_path', '')).strip()
        fpath = Path(template_path) if template_path else (dir_path / template_name if template_name else dir_path)
        files.append({
            'name': template_name or matched_key,
            'path': str(fpath),
            'exists': fpath.exists(),
            'size': fpath.stat().st_size if fpath.exists() else 0,
            'template_key': matched_key,
            'source': '注册配置',
            'enabled': matched_item.get('enabled', True),
            'version': matched_item.get('version', '—') or '—',
            'last_verified_at': matched_item.get('last_verified_at', ''),
            'last_verify_result': _human_verify_result(matched_item.get('last_verify_result', 'unverified')) or '未做验证',
            'is_default': matched_key == default_template_key,
            'is_allowed': matched_key in allowed_template_keys,
        })

    files = sorted(
        files,
        key=lambda x: (
            0 if x.get('template_key') else 1,
            str(x.get('name', '')),
            str(x.get('template_key', '')),
        )
    )

    detail_stats = {
        'all': _summarize_template_detail_rows(files),
        'main': _summarize_template_detail_rows(files, 'main') if template_id == 'operating_room' else None,
        'eye': _summarize_template_detail_rows(files, 'eye') if template_id == 'operating_room' else None,
        'aux': _summarize_template_detail_rows(files, 'aux') if template_id == 'operating_room' else None,
    }

    log_action(current_user.id if current_user.is_authenticated else 'unknown', '查看模板', template_id, info['name'])
    return jsonify({
        'id': template_id,
        'name': info.get('name', template_id),
        'domain': info.get('domain', ''),
        'path': str(dir_path),
        'files': files,
        'stats': detail_stats,
        'template_base': str(TEMPLATE_BASE),
        'mapping': mapping,
        'default_warning': (
            'missing' if default_template_key and not any((f.get('template_key') == default_template_key and f.get('exists')) for f in files)
            else 'disabled' if default_template_key and any((f.get('template_key') == default_template_key and f.get('enabled') is False) for f in files)
            else 'unset' if not default_template_key
            else ''
        ),
    })


@app.route('/api/x/health')
def api_x_health():
    # 本地守护/诊断探针允许免登录；其他来源仍需登录
    remote = (request.headers.get('X-Forwarded-For') or request.remote_addr or '').split(',')[0].strip()
    if remote not in {'127.0.0.1', '::1', 'localhost'} and not current_user.is_authenticated:
        return redirect(url_for('login', next=request.url))
    # 获取系统资源信息
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        system_info = {
            'cpu_percent': round(cpu_percent, 1),
            'memory_percent': round(memory.percent, 1),
            'memory_used_gb': round(memory.used / (1024**3), 2),
            'memory_total_gb': round(memory.total / (1024**3), 2),
            'disk_percent': round(disk.percent, 1),
            'disk_used_gb': round(disk.used / (1024**3), 2),
            'disk_total_gb': round(disk.total / (1024**3), 2),
        }
    except:
        system_info = {}
    
    settings_values = _load_system_settings()
    backup_dir_path = Path(str(settings_values.get('paths.backup_dir', {}).get('value', BASE_DIR / 'backups'))).expanduser()
    return jsonify({
        'success': True,
        'app': 'X1',
        'version': APP_VERSION,
        'host': APP_HOST,
        'port': APP_PORT,
        'base_dir': str(BASE_DIR),
        'template_base': str(TEMPLATE_BASE),
        'records_dir': str(RECORDS_DIR),
        'reports_dir': str(REPORTS_DIR),
        'logs_dir': str(LOGS_DIR),
        'cache_dir': str(CACHE_DIR),
        'temp_dir': str(TEMP_DIR),
        'uploads_dir': str(UPLOADS_DIR),
        'template_config': str(TEMPLATE_CONFIG_FILE),
        'backup_dir': str(backup_dir_path),
        'backup_latest': _get_latest_backup(backup_dir_path),
        'system': system_info,
        'isolation': {
            'shares_v_runtime': False,
            'shares_t_runtime': False,
            'api_prefix': '/api/x/*',
        },
    })






def _get_latest_backup(parent_dir):
    import glob
    import os
    parent_dir = Path(parent_dir).expanduser()
    patterns = [
        str(parent_dir / 'X1_*_manual_backup_*.tar.gz'),
        str(parent_dir / '检测报告生成系统_X*_backup_*.tar.gz'),
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    if files:
        # 按修改时间排序，最新的在前
        files = sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
        f = files[0]
        size_mb = round(os.path.getsize(f) / (1024*1024), 1)
        return f'{os.path.basename(f)}  ({size_mb} MB)'
    return '暂无备份'

def _x_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _x_draft_path(draft_id: str) -> Path:
    return RECORDS_DIR / f"{draft_id}.json"


def _resolve_active_draft_id(data: dict, project: dict) -> str:
    candidate = ''
    if isinstance(data, dict):
        candidate = str(data.get('draft_id') or data.get('record_id') or '').strip()
    if not candidate and isinstance(project, dict):
        candidate = str(project.get('record_id') or '').strip()
    return candidate if candidate.startswith('X1DRAFT_') else ''


def _delete_draft_file_if_exists(draft_id: str) -> bool:
    if not draft_id:
        return False
    target = _x_draft_path(draft_id)
    if target.exists():
        try:
            target.unlink()
            return True
        except Exception:
            return False
    return False


@app.route('/api/x/inspectors')
@login_required
def api_x_inspectors():
    """返回可转让的检测员列表（不含当前用户）"""
    from database import get_db
    result = []
    with get_db() as conn:
        columns = {row['name'] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        has_is_active = 'is_active' in columns
        if has_is_active:
            rows = conn.execute('SELECT user_id, display_name, is_active FROM users ORDER BY user_id').fetchall()
        else:
            rows = conn.execute('SELECT user_id, display_name FROM users ORDER BY user_id').fetchall()
        for row in rows:
            uid = row['user_id']
            if uid == current_user.id:
                continue
            if has_is_active and not row['is_active']:
                continue
            result.append({'username': uid, 'display_name': row['display_name'] or uid})
    return jsonify({'success': True, 'inspectors': result})


@app.route('/api/x/transfer_draft', methods=['POST'])
@login_required
@require_permission('draft.transfer')
def api_x_transfer_draft():
    """转让草稿给其他检测员：修改草稿的 inspector，转让后原主人不再能编辑"""
    data = request.get_json(silent=True) or {}
    draft_id = str(data.get('draft_id') or '').strip()
    target_user = str(data.get('target_user') or '').strip()
    if not draft_id or not target_user:
        return jsonify({'success': False, 'error': '缺少 draft_id 或 target_user'}), 400
    target = _x_draft_path(draft_id)
    if not target.exists():
        return jsonify({'success': False, 'error': '草稿不存在'}), 404
    try:
        draft_data = json.loads(target.read_text(encoding='utf-8'))
    except Exception:
        return jsonify({'success': False, 'error': '草稿文件读取失败'}), 500
    project = draft_data.get('project') or {}
    old_inspector = project.get('operator') or project.get('inspector') or ''
    # 只有草稿本人或 inspector 为空时才能转让
    if old_inspector and old_inspector != current_user.id:
        return jsonify({'success': False, 'error': '只有草稿创建者才能转让'}), 403
    if target_user == current_user.id:
        return jsonify({'success': False, 'error': '不能转让给自己'}), 400
    # 执行转让：修改 inspector / operator
    project['inspector'] = target_user
    project['operator'] = target_user
    draft_data['project'] = project
    draft_data['transferred_from'] = current_user.id
    draft_data['transferred_at'] = _x_now()
    with open(target, 'w', encoding='utf-8') as f:
        json.dump(draft_data, f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'draft_id': draft_id, 'transferred_to': target_user})


@app.route('/api/x/save_draft', methods=['POST'])
@login_required
@require_permission('draft.write')
def api_x_save_draft():
    data = request.get_json(silent=True) or {}
    project = data.get('project') if isinstance(data.get('project'), dict) else data
    project = normalize_project_payload(project, source='draft')
    draft_id = data.get('draft_id') or f"X1DRAFT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    # 第二层隔离：非本人草稿拒绝写入
    existing = _x_draft_path(draft_id)
    if existing.exists():
        try:
            old = json.loads(existing.read_text(encoding='utf-8'))
            old_inspector = (old.get('project') or {}).get('operator') or (old.get('project') or {}).get('inspector') or ''
            if old_inspector and old_inspector != current_user.id:
                return jsonify({'success': False, 'error': '这是其他检测员的草稿，不能覆盖保存'}), 403
        except Exception:
            pass
    payload = {
        'draft_id': draft_id,
        'schema_version': project.get('schema_version', '1.1'),
        'record_version': project.get('record_version', '1'),
        'trace_id': project.get('trace_id', ''),
        'normalized_at': project.get('normalized_at', ''),
        'source': 'x1',
        'saved_at': _x_now(),
        'draft_kind': str(data.get('_draft_kind') or data.get('draft_kind') or '').strip().lower() or 'manual',
        'project': project,
    }
    target = _x_draft_path(draft_id)
    with open(target, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return jsonify({'success': True, 'draft_id': draft_id, 'saved_at': payload['saved_at'], 'path': str(target)})


@app.route('/api/x/list_drafts')
@login_required
@require_permission('draft.read')
def api_x_list_drafts():
    drafts = []
    auto_cutoff = datetime.now().timestamp() - 7 * 24 * 60 * 60
    for fp in sorted(RECORDS_DIR.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(fp.read_text(encoding='utf-8'))
            project = data.get('project') or {}
            inspector_name = project.get('operator') or project.get('inspector') or ''
            if not can_view_record(current_user, {'inspector_name': inspector_name}):
                continue
            draft_kind = str(data.get('draft_kind') or '').strip().lower() or 'manual'
            saved_at = data.get('saved_at') or ''
            if draft_kind == 'auto':
                try:
                    if datetime.fromisoformat(saved_at.replace('Z', '+00:00')).timestamp() < auto_cutoff:
                        continue
                except Exception:
                    pass
            drafts.append({
                'draft_id': data.get('draft_id') or fp.stem,
                'saved_at': saved_at,
                'draft_kind': draft_kind,
                'project_name': project.get('project_name') or '',
                'client_name': project.get('client_name') or '',
                'domain_name': project.get('domain_name') or '',
                'room_count': len(project.get('rooms') or []),
            })
        except Exception:
            continue
    return jsonify({'success': True, 'drafts': drafts})


@app.route('/api/x/load_draft/<draft_id>')
@login_required
@require_permission('draft.read')
def api_x_load_draft(draft_id):
    target = _x_draft_path(draft_id)
    if not target.exists():
        return jsonify({'success': False, 'error': 'draft not found'}), 404
    data = json.loads(target.read_text(encoding='utf-8'))
    project = data.get('project', {}) or {}
    normalized_project = normalize_project_payload(project, source='draft-load')
    if not can_view_record(current_user, {'inspector_name': normalized_project.get('operator', '') or normalized_project.get('inspector', '')}):
        return jsonify({'success': False, 'error': '无权访问该草稿'}), 403
    data['project'] = normalized_project
    return jsonify({'success': True, 'draft': data})


@app.route('/api/save_draft', methods=['POST'])
@login_required
def api_save_draft_compat():
    """旧客户端兼容草稿保存接口，复用 /api/x/save_draft。"""
    response = api_x_save_draft()
    if isinstance(response, tuple):
        body, status = response
        if hasattr(body, 'get_json'):
            payload = body.get_json(silent=True) or {}
            if isinstance(payload, dict):
                payload.setdefault('compat', True)
                payload.setdefault('compat_route', '/api/save_draft')
            return jsonify(payload), status
        return response
    payload = response.get_json(silent=True) or {}
    if isinstance(payload, dict):
        payload.setdefault('compat', True)
        payload.setdefault('compat_route', '/api/save_draft')
    return jsonify(payload)


@app.route('/api/load_draft/<draft_id>')
@login_required
def api_load_draft_compat(draft_id):
    """旧客户端兼容草稿读取接口。"""
    target = _x_draft_path(draft_id)
    if not target.exists():
        return jsonify({'success': False, 'error': 'draft not found'}), 404
    data = json.loads(target.read_text(encoding='utf-8'))
    project = normalize_project_payload(data.get('project', {}) or {}, source='draft-load-compat')
    if not can_view_record(current_user, {'inspector_name': project.get('operator', '') or project.get('inspector', '')}):
        return jsonify({'success': False, 'error': '无权访问该草稿'}), 403
    project['record_id'] = data.get('draft_id', draft_id)
    return jsonify(project)


@app.route('/api/get/<record_id>')
@login_required
def api_get_record_compat(record_id):
    """旧客户端兼容记录加载接口，映射到 /api/x/load_draft。"""
    # 尝试作为草稿ID加载
    target = _x_draft_path(record_id)
    if target.exists():
        data = json.loads(target.read_text(encoding='utf-8'))
        normalized_project = normalize_project_payload(data.get('project', data) or {}, source='record-load-compat')
        if not can_view_record(current_user, {'inspector_name': normalized_project.get('operator', '') or normalized_project.get('inspector', '')}):
            return jsonify({'success': False, 'error': '无权访问该记录'}), 403
        normalized_project['record_id'] = data.get('draft_id', record_id)
        return jsonify({'success': True, 'record': normalized_project})
    
    # 如果不是草稿，可能是导出记录ID
    export_target = _x_export_path(record_id)
    if export_target.exists():
        data = json.loads(export_target.read_text(encoding='utf-8'))
        ep = data.get('export_payload', {})
        proj = ep.get('project', {})
        if not can_view_record(current_user, {'inspector_name': proj.get('operator', '') or proj.get('inspector', '')}):
            return jsonify({'success': False, 'error': '无权访问该记录'}), 403
        # X1 导出格式：优先从 project.rooms 取多房间，否则回退单房间
        if proj.get('rooms') and isinstance(proj['rooms'], list) and len(proj['rooms']) > 0:
            pass  # 已有完整的 rooms
        else:
            room = ep.get('room', {})
            if room:
                proj['rooms'] = [room]
            else:
                proj['rooms'] = []
        proj['record_id'] = record_id
        normalized_project = normalize_project_payload(proj, source='export-record-load')
        normalized_project['record_id'] = record_id
        return jsonify({'success': True, 'record': normalized_project})
    
    return jsonify({'success': False, 'error': 'record not found'}), 404


def _x_export_path(export_id: str) -> Path:
    return REPORTS_DIR / f"{export_id}.json"


def _x_select_template(domain: str, level_name: str = '', type_id: str = ''):
    if type_id:
        for d, t, kw, tpl in TEMPLATE_MAP_X1:
            if d == domain and t == type_id and kw and kw in level_name:
                path = TEMPLATE_BASE / tpl
                if path.exists():
                    return path
        for d, t, kw, tpl in TEMPLATE_MAP_X1:
            if d == domain and t == type_id and not kw:
                path = TEMPLATE_BASE / tpl
                if path.exists():
                    return path
    return None


def _build_single_room_export(project: dict, room: dict, room_index: int = 0) -> dict:
    """对单个房间做判定 + 模板匹配，返回该房间的导出数据。"""
    room_context = room.get('context', {}) or {}
    room_summary = dict(room.get('summary', {}) or {})

    # 确保 params 中每个项有 value 字段（判定引擎需要）
    _params = room.get('params', []) or []
    if isinstance(_params, list):
        for _p in _params:
            if isinstance(_p, dict) and 'value' not in _p:
                _data = _p.get('data', {}) or {}
                if isinstance(_data, dict) and _data.get('total') is not None:
                    _p['value'] = _data['total']
                elif _p.get('result'):
                    _p['value'] = _p['result']

    room_judgement = judge_room(project, room)
    if room_judgement:
        room_summary['input_result_state'] = room_summary.get('result_state', '')
        room_summary['result_state'] = room_judgement.get('result_state', room_summary.get('result_state', ''))
        room_summary['judgement_engine'] = room_judgement.get('engine', '')
        room_summary['judgement_reason'] = room_judgement.get('reason', '')
        room_summary['judgement_overridden'] = room_summary.get('input_result_state', '') != room_summary.get('result_state', '')
    else:
        room_summary['input_result_state'] = room_summary.get('result_state', '')
        room_summary['judgement_engine'] = room_summary.get('judgement_engine', '') or 'unmatched_or_insufficient_params'
        room_summary['judgement_reason'] = room_summary.get('judgement_reason', '') or '判定引擎未命中：对象缺少可判定参数、等级/上下文字段不足，或当前样本仅满足导出不满足自动判定。'
        room_summary['judgement_overridden'] = False
    room = dict(room)
    room['summary'] = room_summary

    # 构建以该房间为 rooms[0] 的虚拟 project，供 resolve_template_rule 使用
    room_project = dict(project)
    room_project['rooms'] = [room]
    clean_class_semantics = build_clean_class_semantics(room_project)
    template_rule = resolve_template_rule(room_project)
    template_rule = apply_semantic_default_template(room_project, template_rule)
    template_rule = apply_type_default_template(template_rule)
    template_resource = resolve_template_resource(template_rule)
    report_context = build_report_context(room_project, template_rule)

    room_type = room.get('type_id', '')
    export_room = {
        'room_id': room.get('room_id', ''),
        'room_name': room.get('room_name', ''),
        'type_id': room.get('type_id', ''),
        'type_name': room.get('type_name', ''),
        'level_name': room.get('level_name', ''),
        'clean_class': room.get('clean_class', ''),
        'basis': room.get('basis', []),
        'judgement': room.get('judgement', []),
        'summary': room_summary,
        'params': room.get('params', []),
        'context': room_context,
        'length': room.get('length', ''),
        'width': room.get('width', ''),
        'height': room.get('height', ''),
    }
    if room_type == 'operating_room':
        normalized_or = _normalize_operating_room_context(room)
        room_context['surgery_room_type'] = room_context.get('surgery_room_type') or normalized_or.get('surgery_room_type', '')
        room_context['surgery_aux_clean_class'] = room_context.get('surgery_aux_clean_class') or normalized_or.get('surgery_aux_clean_class', '')
        aux_clean_class = room_context.get('surgery_aux_clean_class', '')
        branch = room_context.get('surgery_room_type', '')
        export_room['business_context'] = {
            'room_branch': branch,
            'aux_room_name': room_context.get('surgery_aux_room', ''),
            'aux_clean_class': aux_clean_class,
            'context_mode': 'operating-room-minimal',
        }
        if branch:
            export_room['business_context']['branch_mode'] = (
                'auxiliary-room'
                if branch in ('洁净辅房', '辅房')
                else 'main-operating-room'
            )
        if aux_clean_class:
            export_room['business_context']['aux_clean_rule'] = {
                'source': 't-business-logic-extracted',
                'clean_override_key': aux_clean_class,
            }
        if branch in ('洁净辅房', '辅房'):
            export_room['business_context']['parameter_strategy'] = 'aux-clean-override'
        else:
            export_room['business_context']['parameter_strategy'] = 'main-clean-class'
    return {
        'room': export_room,
        'clean_class_semantics': clean_class_semantics,
        'template_rule': template_rule,
        'template_resource': template_resource,
        'report_context': report_context,
        'judgement_result': room_judgement,
        'room_index': room_index,
    }


def _build_export_payload(project: dict) -> dict:
    project = normalize_project_payload(project, source=project.get('source', 'runtime'))
    rooms = project.get('rooms') or []
    if not rooms:
        rooms = [{}]

    # 对每个房间独立做判定 + 模板匹配
    rooms_export = []
    for i, room in enumerate(rooms):
        rooms_export.append(_build_single_room_export(project, room, room_index=i))

    # 主房间（第一个）的数据作为顶层兼容字段
    primary = rooms_export[0]
    room = primary['room']
    room_type = room.get('type_id', '')
    clean_class_semantics = primary['clean_class_semantics']
    template_rule = primary['template_rule']
    template_resource = primary['template_resource']
    report_context = primary['report_context']
    return {
        'export_version': 'X4.7',
        'export_type': room_type,
        'generated_at': _x_now(),
        'project': {
            'project_name': project.get('project_name', ''),
            'report_number': project.get('report_number', ''),
            'client_name': project.get('client_name', ''),
            'contact_info': project.get('contact_info', ''),
            'project_address': project.get('project_address', ''),
            'inspection_area': project.get('inspection_area', ''),
            'detection_date': project.get('detection_date', ''),
            'domain': project.get('domain', ''),
            'domain_name': project.get('domain_name', ''),
            'detection_state': project.get('detection_state', ''),
            'weather': project.get('weather', {}),
            'rooms': project.get('rooms', []),
            'inspector': project.get('inspector', '') or project.get('operator', ''),
        },
        'room': room,
        'rooms_export': rooms_export,
        'clean_class_semantics': clean_class_semantics,
        'template_rule': template_rule,
        'template_resource': template_resource,
        'report_context': report_context,
        'judgement_result': primary['judgement_result'],
        'source': 'x1-canonical-model'
    }


@app.route('/record/api/export_excel', methods=['POST'])
@login_required
@require_permission('record.export')
def api_record_export_excel():
    """导出原始记录(Excel)，前端 record.js exportRecordExcel() 调用。"""
    data = request.get_json(silent=True) or {}
    project = data if isinstance(data, dict) else {}
    project = normalize_project_payload(project, source='export_excel')
    validation_error = validate_normalized_project(project)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    export_payload = _build_export_payload(project)
    export_id = f"X1EXCEL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    xlsx_target = REPORTS_DIR / f"{export_id}.xlsx"
    try:
        build_canonical_excel_report(export_payload, str(xlsx_target))
    except Exception as e:
        log_error('export_excel', str(e), f'export_id={export_id}')
        return jsonify({'success': False, 'error': str(e)}), 500
    if not xlsx_target.exists():
        return jsonify({'success': False, 'error': 'Excel 文件生成失败'}), 500
    log_action(current_user.id, '导出原始记录', export_id,
               f"{export_payload.get('project', {}).get('project_name', '')} - Excel")
    return jsonify({
        'success': True,
        'export_id': export_id,
        'filename': xlsx_target.name,
        'download_url': f'/download/{xlsx_target.name}'
    })


@app.route('/api/x/build_export', methods=['POST'])
@login_required
@require_permission('record.export')
def api_x_build_export():
    data = request.get_json(silent=True) or {}
    project = data.get('project') if isinstance(data.get('project'), dict) else data
    project = normalize_project_payload(project, source='build_export')
    validation_error = validate_normalized_project(project)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    payload = _build_export_payload(project)
    return jsonify({'success': True, 'export_payload': payload})


@app.route('/api/submit_and_export', methods=['POST'])
@login_required
@require_permission('admin.records.export')
def api_submit_and_export_compat():
    """旧客户端兼容导出接口，复用 X1 正式导出逻辑。"""
    response = api_x_submit_export()
    if isinstance(response, tuple):
        body, status = response
        if hasattr(body, 'get_json'):
            payload = body.get_json(silent=True) or {}
            if isinstance(payload, dict):
                payload.setdefault('compat', True)
                payload.setdefault('compat_route', '/api/submit_and_export')
            return jsonify(payload), status
        return response
    payload = response.get_json(silent=True) or {}
    if isinstance(payload, dict):
        payload.setdefault('compat', True)
        payload.setdefault('compat_route', '/api/submit_and_export')
    return jsonify(payload)


@app.route('/api/list')
@login_required
def api_list_compat():
    """旧客户端兼容列表接口，返回草稿和导出记录。"""
    records = []

    def _draft_has_visible_content(project: dict, data: dict) -> bool:
        if not isinstance(project, dict):
            return False
        project_name = str(project.get('project_name', '') or '').strip()
        client_name = str(project.get('client_name', '') or '').strip()
        # 默认隐藏自动化测试草稿，避免前台列表被大量测试记录淹没
        if project_name.startswith('全变体测试-'):
            return False
        if client_name == '边界测试单位':
            return False
        if project_name and ('_low_' in project_name or '_high_' in project_name or project_name.startswith(('or_', 'bsl_', 'elec_', 'gmp_', 'food_'))):
            return False
        rooms = project.get('rooms') or []
        strong_fields = [
            project_name,
            client_name,
            project.get('contact_info', ''),
            project.get('project_address', ''),
            project.get('inspection_area', ''),
            project.get('detection_type', ''),
            project.get('detection_type_name', ''),
            project.get('remarks', ''),
        ]
        if any(str(v).strip() for v in strong_fields if v is not None):
            return True
        # 仅有日期或 rooms 的弱内容草稿不展示，避免空白卡片
        return False

    def _is_valid_export_record(export_id: str, proj: dict) -> bool:
        if not export_id.startswith('X1EXPORT_'):
            return False
        suffix = export_id[len('X1EXPORT_'):]
        if len(suffix) != 14 or not suffix.isdigit():
            return False
        if not isinstance(proj, dict):
            return False
        return any(str(proj.get(k, '')).strip() for k in ['project_name', 'client_name', 'report_number', 'detection_date'])
    
    # 1. 读取所有草稿
    auto_cutoff = datetime.now().timestamp() - 7 * 24 * 60 * 60
    for draft_file in RECORDS_DIR.glob('*.json'):
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                project = data.get('project', {})
                if not _draft_has_visible_content(project, data):
                    continue
                draft_kind = str(data.get('draft_kind') or '').strip().lower() or 'manual'
                saved_at = data.get('updated_at', '') or data.get('created_at', '') or data.get('saved_at', '')
                if draft_kind == 'auto':
                    try:
                        if datetime.fromisoformat(saved_at.replace('Z', '+00:00')).timestamp() < auto_cutoff:
                            continue
                    except Exception:
                        pass
                records.append({
                    'record_id': data.get('draft_id', draft_file.stem),
                    'project_name': project.get('project_name', ''),
                    'client_name': project.get('client_name', ''),
                    'report_number': project.get('report_number', ''),
                    'detection_date': project.get('detection_date', ''),
                    'detection_type': project.get('detection_type', ''),
                    'detection_type_name': project.get('detection_type_name', ''),
                    'rooms': project.get('rooms', []) if isinstance(project.get('rooms', []), list) else [],
                    'room_count': len(project.get('rooms', []) if isinstance(project.get('rooms', []), list) else []),
                    'voided': bool(data.get('voided')),
                    'voided_at': data.get('voided_at', ''),
                    'voided_by': data.get('voided_by', ''),
                    'void_reason': data.get('void_reason', ''),
                    'inspector': project.get('operator', '') or project.get('inspector', ''),
                    'domain_name': project.get('domain_name', '') or project.get('domain', ''),
                    'schema_version': project.get('schema_version', '') or data.get('schema_version', ''),
                    'record_version': project.get('record_version', '') or data.get('record_version', ''),
                    'trace_id': project.get('trace_id', '') or data.get('trace_id', ''),
                    'normalized_at': project.get('normalized_at', '') or data.get('normalized_at', ''),
                    'status': 'draft',
                    'draft_kind': draft_kind,
                    'save_time': saved_at,
                    'export_info': None,
                    'report_info': None
                })
        except:
            pass
    
    # 2. 读取标准正式导出记录（以标准 export json 为准）
    for export_file in sorted(REPORTS_DIR.glob('X1EXPORT_*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            export_id = export_file.stem
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                ep = data.get('export_payload', data)
                proj = ep.get('project', {}) or {}
                room_from_export = ep.get('room', {}) if isinstance(ep.get('room', {}), dict) else {}
                rooms_from_project = proj.get('rooms', []) if isinstance(proj.get('rooms', []), list) else []
                normalized_rooms = rooms_from_project if rooms_from_project else ([room_from_export] if room_from_export else [])
                detection_type = proj.get('detection_type', '') or ep.get('export_type', '') or room_from_export.get('type_id', '')
                detection_type_name = proj.get('detection_type_name', '') or room_from_export.get('type_name', '')
                if not _is_valid_export_record(export_id, proj):
                    continue

                main_xlsx = REPORTS_DIR / f'{export_id}.xlsx'
                main_docx = REPORTS_DIR / f'{export_id}.docx'
                filled_docx = REPORTS_DIR / f'{export_id}.filled.docx'
                bound_docx = REPORTS_DIR / f'{export_id}.bound.docx'
                feishu = data.get('feishu', {}) or {}

                export_info = None
                report_info = None
                export_feishu_url = str((feishu.get('export', {}) or {}).get('feishu_url', '') or '').strip()
                report_feishu_url = str((feishu.get('report', {}) or {}).get('feishu_url', '') or '').strip()
                if export_feishu_url:
                    export_info = {
                        'feishu_url': export_feishu_url
                    }
                elif main_xlsx.exists():
                    export_info = {
                        'filename': main_xlsx.name,
                        'path': str(main_xlsx),
                    }
                elif main_docx.exists():
                    export_info = {
                        'filename': main_docx.name,
                        'path': str(main_docx),
                    }

                report_filename = filled_docx if filled_docx.exists() else (bound_docx if bound_docx.exists() else None)
                if report_feishu_url:
                    report_info = {
                        'feishu_url': report_feishu_url
                    }
                elif report_filename:
                    report_info = {
                        'filename': report_filename.name,
                        'path': str(report_filename),
                    }

                overall_status = data.get('overall_status')
                report_success = data.get('report_success')
                raw_record_success = data.get('raw_record_success')
                report_status = data.get('report_status')
                raw_record_status = data.get('raw_record_status')
                template_ready_value = data.get('template_ready', None)

                if report_success is None:
                    report_success = bool(report_info)
                if raw_record_success is None:
                    raw_record_success = bool(export_info)
                if report_status is None:
                    report_status = 'success' if report_success else ('blocked_template_missing' if template_ready_value is False and raw_record_success else 'missing')
                if raw_record_status is None:
                    raw_record_status = 'success' if raw_record_success else 'missing'
                if overall_status is None:
                    if report_success and raw_record_success:
                        overall_status = 'success'
                    elif raw_record_success and not report_success:
                        overall_status = 'partial_success'
                    else:
                        overall_status = 'failed'

                records.append({
                    'record_id': export_id,
                    'project_name': proj.get('project_name', ''),
                    'client_name': proj.get('client_name', ''),
                    'report_number': proj.get('report_number', ''),
                    'detection_date': proj.get('detection_date', ''),
                    'detection_type': detection_type,
                    'detection_type_name': detection_type_name,
                    'rooms': normalized_rooms,
                    'room_count': len(normalized_rooms),
                    'voided': bool(data.get('voided')),
                    'voided_at': data.get('voided_at', ''),
                    'voided_by': data.get('voided_by', ''),
                    'void_reason': data.get('void_reason', ''),
                    'inspector': proj.get('operator', '') or proj.get('inspector', ''),
                    'domain_name': proj.get('domain_name', '') or proj.get('domain', ''),
                    'schema_version': proj.get('schema_version', '') or data.get('schema_version', ''),
                    'record_version': proj.get('record_version', '') or data.get('record_version', ''),
                    'trace_id': proj.get('trace_id', '') or data.get('trace_id', ''),
                    'normalized_at': proj.get('normalized_at', '') or data.get('normalized_at', ''),
                    'status': 'completed',
                    'overall_status': overall_status,
                    'report_success': report_success,
                    'raw_record_success': raw_record_success,
                    'report_status': report_status,
                    'raw_record_status': raw_record_status,
                    'template_ready': template_ready_value,
                    'save_time': data.get('saved_at', '') or proj.get('saved_at', ''),
                    'export_info': export_info,
                    'report_info': report_info,
                })
        except:
            pass

    records = [r for r in records if can_view_record(current_user, {'inspector_name': r.get('inspector', '')})]
    # 统一规则：暂存记录与报告记录一律按 save_time 倒序返回（最新在最前）
    records.sort(key=lambda r: r.get('save_time') or '', reverse=True)
    
    return jsonify({
        'success': True,
        'compat': True,
        'compat_route': '/api/list',
        'exports': [
            {
                'name': r['export_info']['filename'],
                'path': r['export_info']['path'],
                'suffix': Path(r['export_info']['filename']).suffix.lower() if r['export_info'].get('filename') else ''
            }
            for r in records if r.get('export_info') and r['export_info'].get('filename')
        ],
        'records': records,
    })



def _try_advance_on_export(export_payload):
    """导出报告成功后，尝试推进已存在项目的状态到 检测完成 + 待客户确认。"""
    try:
        project_info = export_payload.get('project', {}) or {}
        project_name = (project_info.get('project_name') or '').strip()
        client_name = (project_info.get('client_name') or '').strip()
        if not project_name:
            return
        conn = get_x1_data_conn()
        try:
            row = conn.execute(
                "SELECT id FROM business_projects WHERE project_name=? AND client_name=?",
                (project_name, client_name)
            ).fetchone()
        finally:
            conn.close()
        if row:
            _auto_advance_project_stage(
                row['id'],
                target_inspection='检测完成',
                target_report='待客户确认'
            )
    except Exception:
        pass


def _auto_sync_project_and_task(export_payload, export_id):
    """导出报告时自动同步项目信息到后台项目管理。
    规则：按项目名 + 客户名查重，不存在则自动创建，已存在则跳过。
    """
    try:
        project_info = export_payload.get('project', {}) or {}
        project_name = (project_info.get('project_name') or '').strip()
        client_name = (project_info.get('client_name') or '').strip()
        if not project_name:
            return

        conn = get_x1_data_conn()
        try:
            existing = conn.execute(
                "SELECT id FROM business_projects WHERE project_name=? AND client_name=?",
                (project_name, client_name)
            ).fetchone()
            if existing:
                return  # 已存在，不覆盖人工维护的经营字段

            now = datetime.now().isoformat(timespec='seconds')
            inspector_id = getattr(current_user, 'id', '') or ''

            detection_domain = (project_info.get('detection_domain') or
                                project_info.get('inspection_area') or '').strip()
            detection_type = (project_info.get('detection_type') or
                              project_info.get('detection_type_name') or '').strip()

            cur = conn.cursor()
            project_no = _generate_project_no()
            cur.execute(
                "INSERT INTO business_projects "
                "(project_no, project_name, client_name, project_address, contact_name, contact_phone, "
                " detection_domain, detection_type, expected_detection_date, project_desc, "
                " business_stage, inspection_stage, report_status, owner, "
                " assigned_to, assigned_at, task_status, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    project_no,
                    project_name,
                    client_name,
                    (project_info.get('project_address') or '').strip(),
                    (project_info.get('contact_name') or project_info.get('contact_person') or '').strip(),
                    (project_info.get('contact_phone') or project_info.get('contact_info') or '').strip(),
                    detection_domain,
                    detection_type,
                    (project_info.get('detection_date') or '').strip(),
                    '',
                    '检测中',
                    '检测中',
                    '未开始',
                    inspector_id,
                    inspector_id,
                    now,
                    'in_progress',
                    now,
                    now,
                )
            )
            project_id = cur.lastrowid

            cur.execute(
                "INSERT INTO project_tasks "
                "(project_id, task_name, task_type, assigned_to, assigned_at, "
                " task_status, expected_execute_date, remarks, created_by, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    project_id,
                    f'{project_name}-常规检测',
                    'inspection',
                    inspector_id,
                    now,
                    'in_progress',
                    (project_info.get('detection_date') or '').strip(),
                    f'自动创建（来源：导出 {export_id}）',
                    inspector_id,
                    now,
                    now,
                )
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:
        print(f'[auto_sync_project] 警告：自动同步项目失败 - {e}')


@app.route('/api/x/submit_export', methods=['POST'])
@login_required
@require_permission('record.export')
@monitor_performance('export_report')
def api_x_submit_export():
    data = request.get_json(silent=True) or {}
    project = data.get('project') if isinstance(data.get('project'), dict) else data
    project = normalize_project_payload(project, source='submit_export')
    source_draft_id = _resolve_active_draft_id(data, project)
    validation_error = validate_normalized_project(project)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    export_payload = _build_export_payload(project)
    if export_payload.get('export_type') != (project.get('rooms') or [{}])[0].get('type_id'):
        return jsonify({'success': False, 'error': 'export_type 与 room.type_id 不一致'}), 400
    export_id = f"X1EXPORT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    json_target = _x_export_path(export_id)
    xlsx_target = REPORTS_DIR / f"{export_id}.xlsx"
    docx_target = REPORTS_DIR / f"{export_id}.docx"
    bound_docx_target = REPORTS_DIR / f"{export_id}.bound.docx"
    filled_docx_target = REPORTS_DIR / f"{export_id}.filled.docx"
    template_resource = export_payload.get('template_resource', {}) or {}
    template_ready = bool(template_resource.get('template_found')) and template_resource.get('resource_status') == 'confirmed'
    report_export_enabled = _setting_enabled('export.enable_report_docx', True)
    raw_export_enabled = _setting_enabled('export.enable_raw_record', True)
    template_gate_enabled = _setting_enabled('template.enable_gate', True)
    template_gate_mode = _load_system_settings().get('template.gate_mode', {}).get('value', 'strict')
    final_payload = {
        'export_id': export_id,
        'saved_at': _x_now(),
        'schema_version': project.get('schema_version', '1.1'),
        'record_version': project.get('record_version', '1'),
        'trace_id': project.get('trace_id', ''),
        'normalized_at': project.get('normalized_at', ''),
        'export_payload': export_payload,
        'template_ready': template_ready,
    }
    
    try:
        with open(json_target, 'w', encoding='utf-8') as f:
            json.dump(final_payload, f, ensure_ascii=False, indent=2)
        build_canonical_excel_report(export_payload, str(xlsx_target)) if raw_export_enabled else None
        build_canonical_object_report(export_payload, str(docx_target)) if report_export_enabled else None
        build_template_bound_docx(export_payload, str(bound_docx_target)) if report_export_enabled else None
        filled_docx_path = build_mixed_report_docx(export_payload, str(filled_docx_target)) if (report_export_enabled and template_ready) else ''
        
        # 记录操作日志
        project_name = export_payload.get('project', {}).get('project_name', '')
        type_name = export_payload.get('room', {}).get('type_name', '')
        log_action(current_user.id, '导出报告', export_id, f'{project_name} - {type_name}')
        
    except Exception as e:
        log_error('export_report', str(e), f'export_id={export_id}')
        return jsonify({'success': False, 'error': str(e)}), 500
    
    # 检测报告模板命中闸门：模板未命中时，原始记录可生成，但正式检测报告不允许按成功件返回
    # 这里明确区分双链结果：xlsx 允许成功产出，docx 视为正式检测报告失败。
    if template_gate_enabled and template_gate_mode == 'strict' and report_export_enabled and not template_ready:
        return jsonify({
            'success': True,
            'report_success': False,
            'raw_record_success': bool(xlsx_target.exists()),
            'overall_status': 'partial_success' if xlsx_target.exists() else 'failed',
            'report_status': 'blocked_template_missing',
            'raw_record_status': 'success' if xlsx_target.exists() else 'failed',
            'error': '检测报告模板未命中，禁止生成正式检测报告；请先修正对象类型/等级/子类型口径或模板资源映射。',
            'export_id': export_id,
            'saved_at': final_payload['saved_at'],
            'json_path': str(json_target),
            'xlsx_path': str(xlsx_target) if xlsx_target.exists() else '',
            'template_ready': template_ready,
            'template_key': template_resource.get('template_key', ''),
            'template_name': template_resource.get('template_name', ''),
            'template_found': template_resource.get('template_found', False),
            'template_path': template_resource.get('template_path', ''),
            'export_stage': 'template-resource-missing',
            'export_payload': export_payload,
            'dual_chain': {
                'report': {'success': False, 'status': 'blocked_template_missing', 'blocked_by_template_gate': True},
                'raw_record': {'success': bool(xlsx_target.exists()), 'status': 'success' if xlsx_target.exists() else 'failed'}
            }
        }), 200

    # 飞书上传 + PDF 转换 + 正式目录落地：异步执行，不阻塞导出主流程
    import threading

    def _async_post_export():
        """后台线程：飞书上传 + PDF 转换 + 正式目录落地"""
        try:
            feishu_report = {}
            feishu_export = {}
            feishu_enabled = _setting_enabled('feishu.enabled', True)
            detection_date = export_payload.get('project', {}).get('detection_date', '')
            year = int(detection_date[:4]) if detection_date and len(detection_date) >= 4 else datetime.now().year

            report_file = filled_docx_target if filled_docx_path else bound_docx_target
            if feishu_enabled and report_file.exists():
                reports_folder = resolve_feishu_upload_folder('reports', year)
                if reports_folder:
                    feishu_report = upload_file_to_feishu(str(report_file), reports_folder)
                    if feishu_report.get('success'):
                        print(f"✅ 检测报告已上传飞书: {feishu_report.get('feishu_url', '')}")

            if feishu_enabled and xlsx_target.exists():
                exports_folder = resolve_feishu_upload_folder('exports', year)
                if exports_folder:
                    feishu_export = upload_file_to_feishu(str(xlsx_target), exports_folder)
                    if feishu_export.get('success'):
                        print(f"✅ 原始记录已上传飞书: {feishu_export.get('feishu_url', '')}")

            # 正式目录双落地
            project_info = export_payload.get('project', {}) or {}
            cn = _safe_filename_part(project_info.get('client_name', ''), '未知委托单位')
            pn = _safe_filename_part(project_info.get('project_name', ''), '未命名项目')
            rn = _safe_filename_part(project_info.get('report_number', ''), export_id)
            formal_export_name = f"原始记录_{cn}_{pn}.xlsx"
            report_source = Path(filled_docx_path) if filled_docx_path else (bound_docx_target if bound_docx_target.exists() else docx_target)
            formal_report_name = f"{rn}_{cn}{report_source.suffix or '.docx'}"
            formal_export = _copy_to_formal_dir(xlsx_target, FORMAL_RECORDS_BASE, year, formal_export_name)
            formal_report = _copy_to_formal_dir(report_source, FORMAL_REPORTS_BASE, year, formal_report_name)

            # PDF 转换
            pdf_preview_path = ''
            try:
                from pdf_converter import convert_docx_to_pdf
                pdf_dir = BASE_DIR / 'preview_pdf'
                pdf_dir.mkdir(exist_ok=True)
                docx_for_pdf = Path(filled_docx_path) if filled_docx_path else (bound_docx_target if bound_docx_target.exists() else None)
                if docx_for_pdf and docx_for_pdf.exists():
                    pdf_out = pdf_dir / f"{export_id}.pdf"
                    pdf_preview_path = convert_docx_to_pdf(str(docx_for_pdf), str(pdf_out))
            except Exception as e:
                print(f"[async_post_export] PDF 转换跳过: {e}")

            # 回写完整结果到 JSON
            final_payload['feishu'] = {
                'report': feishu_report or {'success': False, 'error': '未执行或未获得上传结果'},
                'export': feishu_export or {'success': False, 'error': '未执行或未获得上传结果'}
            }
            final_payload['formal_local'] = {'report': formal_report, 'export': formal_export}
            final_payload['pdf_preview'] = pdf_preview_path
            with open(json_target, 'w', encoding='utf-8') as f:
                json.dump(final_payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[async_post_export] 后台任务异常: {e}")

    # 启动后台线程
    threading.Thread(target=_async_post_export, daemon=True).start()

    # 主流程立即返回（不等飞书/PDF）
    final_payload['feishu'] = {'report': {'success': False, 'error': '异步上传中'}, 'export': {'success': False, 'error': '异步上传中'}}
    final_payload['formal_local'] = {'report': '', 'export': ''}
    final_payload['pdf_preview'] = ''
    with open(json_target, 'w', encoding='utf-8') as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)
    draft_deleted = _delete_draft_file_if_exists(source_draft_id)

    # 自动同步项目信息到后台项目管理
    _auto_sync_project_and_task(export_payload, export_id)

    # 自动流转：导出报告成功 → 检测完成 + 已出具
    _try_advance_on_export(export_payload)

    return jsonify({
        'success': True,
        'report_success': True,
        'raw_record_success': True,
        'overall_status': 'success',
        'report_status': 'success',
        'raw_record_status': 'success',
        'export_id': export_id,
        'saved_at': final_payload['saved_at'],
        'json_path': str(json_target),
        'xlsx_path': str(xlsx_target),
        'docx_path': str(docx_target),
        'bound_docx_path': str(bound_docx_target),
        'filled_docx_path': filled_docx_path,
        'template_ready': template_ready,
        'template_key': template_resource.get('template_key', ''),
        'template_name': template_resource.get('template_name', ''),
        'template_found': template_resource.get('template_found', False),
        'template_path': template_resource.get('template_path', ''),
        'export_stage': 'template-bound-ready' if template_ready else 'template-resource-missing',
        'export_payload': export_payload,
        'feishu': final_payload.get('feishu', {}),
        'formal_local': final_payload.get('formal_local', {}),
        'dual_chain': {
            'report': {'success': True, 'status': 'success', 'path': filled_docx_path or str(bound_docx_target)},
            'raw_record': {'success': True, 'status': 'success', 'path': str(xlsx_target)}
        },
        'source_draft_deleted': draft_deleted
    })



@app.route('/api/x/template_probe', methods=['POST'])
@login_required
@require_permission('record.export')
def api_x_template_probe():
    data = request.get_json(silent=True) or {}
    project = normalize_project_payload(data.get('project', data) or {}, source='template_probe')
    validation_error = validate_normalized_project(project)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    payload = _build_export_payload(project)
    room = payload.get('room', {}) or {}
    template_path = _x_select_template(
        payload.get('project', {}).get('domain', ''),
        room.get('level_name', '') or room.get('clean_class', ''),
        room.get('type_id', ''),
    )
    return jsonify({
        'success': True,
        'template_found': bool(template_path),
        'template_path': str(template_path) if template_path else '',
        'type_id': room.get('type_id', ''),
        'level_name': room.get('level_name', '') or room.get('clean_class', ''),
        'domain': payload.get('project', {}).get('domain', ''),
    })


@app.route('/api/x/list_exports')
@login_required
@require_permission('admin.records.view')
def api_x_list_exports():
    exports = []
    for fp in sorted(REPORTS_DIR.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True):
        exports.append({
            'name': fp.name,
            'path': str(fp),
            'suffix': fp.suffix,
        })
    return jsonify({'success': True, 'exports': exports})

@app.route('/api/x/passbox-sample')
def api_x_passbox_sample():
    return jsonify({
        'success': True,
        'sample': {
            'room_id': 'r1',
            'type_id': 'pass_box',
            'type_name': '传递窗',
            'domain': 'pharma',
            'room_name': 'X1传递窗样板',
            'level_name': '无等级要求',
            'clean_class': '无等级要求',
            'basis': ['GB 50591-2010'],
            'judgement': ['JG/T 382-2012', 'GB 50591-2010'],
            'params': [],
            'summary': {
                'result_state': '',
                'judgement_active': ['JG/T 382-2012'],
                'basis_primary': 'GB 50591-2010',
                'judgement_primary': 'JG/T 382-2012'
            },
            'context': {}
        }
    })

@app.route('/api/x/meta')
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



@app.route('/admin/api/templates/<template_id>/upload', methods=['POST'])
@login_required
@require_permission('admin.templates.registry.manage')
def admin_api_template_upload(template_id):
    """上传/替换模板文件"""
    if not _setting_enabled('template.allow_upload', True):
        return jsonify({'success': False, 'error': '系统设置已禁止模板上传'}), 403
    from template_resources import TEMPLATE_MAP
    if template_id not in TEMPLATE_MAP:
        return jsonify({'success': False, 'error': '模板不存在'}), 404
    
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '未选择文件'}), 400
    
    file = request.files['file']
    if not file.filename:
        return jsonify({'success': False, 'error': '文件名为空'}), 400
    
    if not file.filename.endswith('.docx'):
        return jsonify({'success': False, 'error': '仅支持 .docx 格式'}), 400
    
    info = TEMPLATE_MAP[template_id]
    dir_path = TEMPLATE_BASE / info['path']
    dir_path.mkdir(parents=True, exist_ok=True)
    
    # 备份旧文件（版本历史）
    backup_dir = dir_path / '.backup'
    backup_dir.mkdir(exist_ok=True)
    
    safe_name = Path(file.filename).name
    target_path = dir_path / safe_name
    if target_path.exists():
        from datetime import datetime
        backup_name = f"{target_path.stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}{target_path.suffix}"
        import shutil
        shutil.copy2(str(target_path), str(backup_dir / backup_name))
    
    # 保存新文件
    file.save(str(target_path))
    
    # 校验文件完整性
    try:
        from docx import Document
        Document(str(target_path))
        valid = True
    except:
        valid = False
    
    log_action(current_user.id if current_user.is_authenticated else 'unknown', 
               '上传模板', template_id, f'{info["name"]} - {file.filename}')
    
    return jsonify({
        'success': True,
        'message': f'模板文件 {file.filename} 上传成功',
        'valid': valid,
        'path': str(target_path)
    })


@app.route('/admin/api/templates/<template_id>/versions')
@login_required
@require_permission('admin.templates.view')
def admin_api_template_versions(template_id):
    """模板版本历史"""
    from template_resources import TEMPLATE_MAP
    if template_id not in TEMPLATE_MAP:
        return jsonify({'success': False, 'error': '模板不存在'}), 404
    
    info = TEMPLATE_MAP[template_id]
    dir_path = TEMPLATE_BASE / info['path']
    backup_dir = dir_path / '.backup'
    
    versions = []
    if backup_dir.exists():
        for f in sorted(backup_dir.glob('*.docx'), key=lambda x: x.stat().st_mtime, reverse=True):
            versions.append({
                'name': f.name,
                'size': f.stat().st_size,
                'mtime': f.stat().st_mtime,
                'mtime_str': datetime.fromtimestamp(f.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S')
            })
    
    return jsonify({
        'template_id': template_id,
        'template_name': info['name'],
        'versions': versions,
        'total': len(versions)
    })


# ============================================================
# 文件下载与在线预览
# ============================================================

@app.route('/download/<filename>')
@login_required
@require_permission('files.download.own')
def download_file(filename):
    """下载导出的报告文件"""
    if not _setting_enabled('security.allow_file_download', True):
        return jsonify({'success': False, 'error': '系统设置已禁止文件下载'}), 403
    import re
    # 安全检查：只允许合法文件名
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': '非法文件名'}), 400
    if not _can_access_file_by_name(filename):
        return jsonify({'success': False, 'error': '无权访问该文件'}), 403
    
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        # 也在 records 目录中找
        file_path = RECORDS_DIR / filename
    if not file_path.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    
    return send_file(str(file_path), as_attachment=True, download_name=filename)


@app.route('/admin/api/open_file/<filename>', methods=['POST'])
@login_required
@require_permission('admin.records.open_local')
def admin_api_open_file(filename):
    """在服务器本机优先用 Word/Excel 打开文件"""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': '非法文件名'}), 400
    if not _can_access_file_by_name(filename):
        return jsonify({'success': False, 'error': '无权访问该文件'}), 403

    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        file_path = RECORDS_DIR / filename
    if not file_path.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    try:
        import subprocess
        suffix = file_path.suffix.lower()
        app_name = 'WPS Office'
        if suffix in ('.docx', '.doc', '.xlsx', '.xls', '.csv', '.pptx', '.ppt'):
            subprocess.Popen(['open', '-a', 'wpsoffice', str(file_path)])
        else:
            app_name = '系统默认软件'
            subprocess.Popen(['open', str(file_path)])
        return jsonify({'success': True, 'message': f'已调用 {app_name} 打开文件', 'app_name': app_name, 'filename': filename, 'path': str(file_path)})
    except Exception as e:
        return jsonify({'success': False, 'error': f'打开文件失败: {e}'}), 500


@app.route('/admin/api/download_feishu_file')
@login_required
@require_permission('admin.records.open_feishu')
def admin_api_download_feishu_file():
    """从飞书云盘下载文件并返回给当前浏览器（多人多端场景）
    
    action=open 时使用 inline 模式，让手机系统弹出“用什么 App 打开”选择器。
    默认 attachment 模式，直接下载到设备。
    """
    file_token = (request.args.get('file_token') or '').strip()
    if not file_token:
        return jsonify({'success': False, 'error': '缺少 file_token'}), 400
    result = download_file_content_from_feishu(file_token)
    if not result.get('success'):
        return jsonify({'success': False, 'error': result.get('error', '飞书下载失败')}), 500
    filename = result['filename']
    content = result['content']
    content_type = result.get('content_type') or 'application/octet-stream'
    # 根据扩展名设置正确的 MIME type，因为飞书可能返回 octet-stream
    _suffix = Path(filename).suffix.lower()
    _mime_map = {
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.doc': 'application/msword',
        '.xls': 'application/vnd.ms-excel',
        '.pdf': 'application/pdf',
    }
    content_type = _mime_map.get(_suffix, content_type)
    action = (request.args.get('action') or '').strip().lower()
    as_attachment = (action != 'open')  # open = inline, 其他 = attachment
    from io import BytesIO
    return send_file(
        BytesIO(content),
        mimetype=content_type,
        as_attachment=as_attachment,
        download_name=filename,
        max_age=0
    )


@app.route('/admin/api/open_feishu_file', methods=['POST'])
@login_required
@require_permission('admin.records.open_feishu')
def admin_api_open_feishu_file():
    """从飞书云盘下载文件并用 WPS 打开"""
    data = request.get_json(silent=True) or {}
    file_token = data.get('file_token', '').strip()
    if not file_token:
        return jsonify({'success': False, 'error': '缺少 file_token'}), 400
    result = download_file_from_feishu(file_token)
    if not result.get('success'):
        return jsonify({'success': False, 'error': result.get('error', '飞书下载失败')}), 500
    file_path = result['path']
    try:
        import subprocess
        subprocess.Popen(['open', '-a', 'wpsoffice', file_path])
        return jsonify({'success': True, 'message': f'已从飞书下载并用 WPS 打开: {result["filename"]}', 'filename': result['filename'], 'size': result['size']})
    except Exception as e:
        return jsonify({'success': False, 'error': f'打开失败: {e}'}), 500


@app.route('/api/preview/<filename>')
@login_required
@require_permission('files.preview.own')
def preview_file(filename):
    """在线预览 docx/xlsx 文件（返回 HTML）"""
    if not _setting_enabled('security.allow_file_preview', True):
        return jsonify({'success': False, 'error': '系统设置已禁止文件预览'}), 403
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'success': False, 'error': '非法文件名'}), 400
    if not _can_access_file_by_name(filename):
        return jsonify({'success': False, 'error': '无权访问该文件'}), 403
    
    file_path = REPORTS_DIR / filename
    if not file_path.exists():
        file_path = RECORDS_DIR / filename
    if not file_path.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    
    suffix = file_path.suffix.lower()
    try:
        if suffix == '.docx':
            import mammoth
            with open(str(file_path), 'rb') as f:
                result = mammoth.convert_to_html(f)
                html_content = result.value
            return jsonify({
                'success': True,
                'html': html_content,
                'filename': filename,
                'file_size': file_path.stat().st_size,
                'type': 'docx'
            })
        elif suffix in ('.xlsx', '.xls'):
            import html
            import openpyxl
            wb = openpyxl.load_workbook(str(file_path), data_only=True)
            html_parts = []
            for sheet_name in wb.sheetnames:
                ws = wb[sheet_name]
                html_parts.append(f'<h3 style="margin:16px 0 8px;color:#1890ff">{html.escape(str(sheet_name))}</h3>')
                html_parts.append('<table style="border-collapse:collapse;width:100%;margin-bottom:16px">')
                for row in ws.iter_rows(values_only=False):
                    html_parts.append('<tr>')
                    for cell in row:
                        val = cell.value if cell.value is not None else ''
                        safe_val = html.escape(str(val))
                        # 处理合并单元格
                        style = 'border:1px solid #d9d9d9;padding:6px 8px;font-size:13px'
                        if isinstance(val, (int, float)):
                            style += ';text-align:right'
                        html_parts.append(f'<td style="{style}">{safe_val}</td>')
                    html_parts.append('</tr>')
                html_parts.append('</table>')
            wb.close()
            return jsonify({
                'success': True,
                'html': ''.join(html_parts),
                'filename': filename,
                'file_size': file_path.stat().st_size,
                'type': 'xlsx'
            })
        else:
            return jsonify({'success': False, 'error': f'不支持预览 {suffix} 格式'}), 400
    except ImportError as e:
        return jsonify({'success': False, 'error': f'缺少依赖库: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': f'预览失败: {str(e)}'}), 500


@app.route('/admin/api/templates/<template_id>/preview')
@login_required
@require_permission('admin.templates.preview')
def admin_api_template_preview(template_id):
    """模板预览（返回完整 HTML）"""
    from template_resources import TEMPLATE_MAP
    if template_id not in TEMPLATE_MAP:
        return jsonify({'success': False, 'error': '模板不存在'}), 404
    
    filename = request.args.get('file')
    if not filename or '..' in filename or '/' in filename or chr(92) in filename:
        return jsonify({'success': False, 'error': '非法文件名'}), 400
    
    info = TEMPLATE_MAP[template_id]
    file_path = TEMPLATE_BASE / info['path'] / filename
    
    if not file_path.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    
    try:
        import mammoth
        with open(str(file_path), 'rb') as f:
            result = mammoth.convert_to_html(f)
            html_content = result.value
        
        return jsonify({
            'success': True,
            'html': html_content,
            'filename': filename,
            'file_size': file_path.stat().st_size
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'预览失败: {str(e)}'}), 500
@app.route('/admin/api/templates/<template_id>/variables')
@login_required
@require_permission('admin.templates.variables')
def admin_api_template_variables(template_id):
    """提取模板填写项（表格标签 + 关键段落关键词）"""
    from template_resources import TEMPLATE_MAP
    import re
    if template_id not in TEMPLATE_MAP:
        return jsonify({'success': False, 'error': '模板不存在'}), 404

    filename = request.args.get('file')
    if not filename or '..' in filename or '/' in filename or chr(92) in filename:
        return jsonify({'success': False, 'error': '非法文件名'}), 400

    info = TEMPLATE_MAP[template_id]
    file_path = TEMPLATE_BASE / info['path'] / filename
    if not file_path.exists():
        return jsonify({'success': False, 'error': '文件不存在'}), 404

    try:
        from docx import Document
        doc = Document(str(file_path))
        variables = []
        seen = set()

        # 1. 扫描段落：提取 {{...}} 或 【...】 占位符
        for i, para in enumerate(doc.paragraphs):
            for m in re.findall(r'\{\{([^}]+)\}\}|【([^】]+)】', para.text):
                name = m[0] or m[1]
                if name and name not in seen:
                    seen.add(name)
                    variables.append({'name': name, 'type': 'placeholder', 'location': f'段落 {i+1}'})

        # 2. 扫描表格：左列标签 → 右列为空或待填写
        for ti, table in enumerate(doc.tables):
            for ri, row in enumerate(table.rows):
                cells = [c.text.strip() for c in row.cells]
                if len(cells) < 2:
                    continue
                # 左列有内容（标签），且列数为偶数（label-value 对）
                for ci in range(0, len(cells)-1, 2):
                    label = cells[ci].strip('：: ').strip()
                    value = cells[ci+1] if ci+1 < len(cells) else ''
                    # 标签有意义（非纯数字/符号）且值为空或为占位符
                    if label and len(label) > 1 and not label.isdigit():
                        if label not in seen:
                            seen.add(label)
                            variables.append({
                                'name': label,
                                'type': 'table_field',
                                'location': f'表{ti+1} 第{ri+1}行'
                            })

        # 按类型分组输出
        return jsonify({
            'success': True,
            'variables': variables,
            'total': len(variables),
            'summary': {
                'placeholder': sum(1 for v in variables if v['type']=='placeholder'),
                'table_field': sum(1 for v in variables if v['type']=='table_field'),
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': f'解析失败: {str(e)}'}), 500

if __name__ == '__main__':
    print(f"🚀 X1 skeleton running at http://{APP_HOST}:{APP_PORT}")
    app.run(host=APP_HOST, port=APP_PORT, debug=False)

