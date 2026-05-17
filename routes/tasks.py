# routes/tasks.py
"""派单管理 Blueprint — 管理端 + 检测员侧接口"""

from datetime import datetime

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user

from auth import require_permission
from helpers.db import get_x1_data_conn
from helpers.project_utils import (
    serialize_project_task,
    _clean_project_task_payload,
    refresh_project_task_summary,
    _auto_advance_project_stage,
    _get_business_project_by_id,
    _get_task_type_label,
    _get_task_status_label,
    TASK_TYPE_OPTIONS,
    TASK_STATUS_OPTIONS,
)
from notifications import create_notification

tasks_bp = Blueprint('tasks', __name__)


def _x_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ============================================================
# 管理端接口
# ============================================================

@tasks_bp.route('/admin/api/project_tasks', methods=['POST'])
@login_required
@require_permission('admin.tasks.create')
def create_project_task():
    data = request.get_json(silent=True) or {}
    payload = _clean_project_task_payload(data)

    if not payload.get('project_id'):
        return jsonify({'success': False, 'error': 'project_id 不能为空'}), 400

    project_row = _get_business_project_by_id(payload['project_id'])
    if not project_row:
        return jsonify({'success': False, 'error': '项目不存在'}), 404

    # ── 派单可用性检查 ──
    stage = project_row['inspection_stage'] or ''
    rpt_st = project_row['report_status'] or ''
    done_stages = ('已完结', '已关闭')
    done_reports = ('客户已确认', '已发送客户')
    if stage in done_stages and rpt_st in done_reports:
        return jsonify({'success': False, 'error': '项目已完结，无法继续派单'}), 400

    task_type_req = payload.get('task_type') or 'inspection'
    conn_chk = get_x1_data_conn()
    try:
        active_tasks = conn_chk.execute(
            "SELECT COUNT(*) as cnt FROM project_tasks "
            "WHERE project_id=? AND task_type=? AND task_status IN ('pending_assign','assigned','accepted','in_progress')",
            (payload['project_id'], task_type_req)
        ).fetchone()
        if active_tasks and active_tasks['cnt'] > 0:
            return jsonify({'success': False, 'error': f'该项目已有进行中的同类任务（{active_tasks["cnt"]}个），请等现有任务完成或取消后再派单'}), 400
    finally:
        conn_chk.close()

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

    # 通知被派单人员
    if assigned_to:
        try:
            project_name = project_row['project_name'] or str(payload['project_id'])
            type_label = _get_task_type_label(task_type)
            create_notification(
                title='新任务派单',
                content=f'您被指派了「{project_name}」的{type_label}任务',
                category='dispatch',
                target_role=None,
                target_user=assigned_to,
                link='tasks'
            )
        except Exception:
            pass

    conn = get_x1_data_conn()
    try:
        row = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
    finally:
        conn.close()

    return jsonify({'success': True, 'item': serialize_project_task(row, project_row)})


@tasks_bp.route('/admin/api/business_projects/<int:project_id>/tasks', methods=['GET'])
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


@tasks_bp.route('/admin/api/project_tasks/<int:task_id>', methods=['GET'])
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


@tasks_bp.route('/admin/api/project_tasks/<int:task_id>', methods=['PUT'])
@login_required
@require_permission('admin.tasks.update')
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


@tasks_bp.route('/admin/api/project_tasks/<int:task_id>/cancel', methods=['POST'])
@login_required
@require_permission('admin.tasks.delete')
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

@tasks_bp.route('/api/my_tasks', methods=['GET'])
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


@tasks_bp.route('/api/my_tasks/pending_count')
@login_required
def api_my_tasks_pending_count():
    """返回当前用户待处理任务数（assigned + accepted + in_progress）"""
    user_id = current_user.id
    conn = get_x1_data_conn()
    try:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM project_tasks "
            "WHERE assigned_to=? AND task_status IN ('assigned','accepted','in_progress')",
            (user_id,)
        ).fetchone()
    finally:
        conn.close()
    return jsonify({'success': True, 'count': row['cnt'] if row else 0})


@tasks_bp.route('/api/project_tasks/<int:task_id>/accept', methods=['POST'])
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
    # 自动流转：接单 → 已排期
    _auto_advance_project_stage(row['project_id'], target_inspection='已排期')
    conn = get_x1_data_conn()
    try:
        updated = conn.execute("SELECT * FROM project_tasks WHERE id=?", (task_id,)).fetchone()
        project_row = _get_business_project_by_id(row['project_id'])
    finally:
        conn.close()
    return jsonify({'success': True, 'item': serialize_project_task(updated, project_row)})


@tasks_bp.route('/api/project_tasks/<int:task_id>/start', methods=['POST'])
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


@tasks_bp.route('/api/project_tasks/<int:task_id>/complete', methods=['POST'])
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


@tasks_bp.route('/api/project_tasks/<int:task_id>/prefill', methods=['GET'])
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
