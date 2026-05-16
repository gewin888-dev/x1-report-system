import json
from datetime import datetime
from helpers.db import get_x1_data_conn
from database import get_db
from monitor import log_action
from flask_login import current_user


# ============================================================
# 常量
# ============================================================

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
    'assigned': '已派单',
    'accepted': '已接单',
    'in_progress': '执行中',
    'completed': '已完成',
    'cancelled': '已取消',
}

_INSPECTION_STAGE_ORDER = {
    '未安排': 0, '': 0,
    '已排期': 1,
    '检测中': 2,
    '检测完成': 3,
    '检测异常': -1,  # 异常不自动流转
}
_REPORT_STATUS_ORDER = {
    '未开始': 0, '': 0,
    '编制中': 1, '审核中': 2, '待修改': 2, '待出具': 3,
    '已出具': 4, '待客户确认': 5, '客户已确认': 6, '已发送客户': 7,
}


# ============================================================
# 项目编号生成
# ============================================================

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


# ============================================================
# 序列化
# ============================================================

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


# ============================================================
# 任务状态/类型标签
# ============================================================

def _get_task_status_label(status):
    return TASK_STATUS_LABELS.get((status or '').strip(), (status or '').strip())


def _get_task_type_label(task_type):
    return TASK_TYPE_LABELS.get((task_type or '').strip(), (task_type or '').strip())


# ============================================================
# 查询辅助
# ============================================================

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


# ============================================================
# 任务序列化
# ============================================================

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


# ============================================================
# 任务数据清洗
# ============================================================

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


# ============================================================
# 项目任务摘要刷新
# ============================================================

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

def _auto_advance_project_stage(project_id, target_inspection=None, target_report=None):
    """自动推进项目状态，只前进不后退。
    
    规则：
    - 只在目标状态比当前状态"更靠后"时才更新
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


# ============================================================
# 项目数据清洗
# ============================================================

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
        'contract_status': s('contract_status') or '未签',
        'contract_amount': contract_amount,
        'paid_amount': paid_amount,
        'inspection_stage': s('inspection_stage') or '未安排',
        'report_status': s('report_status') or '未开始',
        'invoice_status': s('invoice_status') or '未开票',
        'payment_status': s('payment_status') or '未回款',
        'owner': s('owner'),
        'remarks': s('remarks'),
        'assigned_to': s('assigned_to'),
        'assigned_at': s('assigned_at'),
        'task_status': s('task_status'),
    }


# ============================================================
# 导出时自动同步项目和任务
# ============================================================

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
