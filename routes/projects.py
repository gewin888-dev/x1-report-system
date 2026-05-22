"""
X1 项目管理路由 Blueprint
"""

import json
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request, send_file
from flask_login import login_required, current_user

from auth import require_role, require_permission
from database import get_db
from notifications import notify_project_report_uploaded, notify_project_status_change
from monitor import log_action
from config_loader import load_x1_config
from helpers.db import get_x1_data_conn
from helpers.project_utils import (
    _generate_project_no, serialize_business_project,
    _get_business_project_by_id, _get_user_display_name,
    _clean_project_payload, refresh_project_task_summary,
)
from customer_routes import _serialize_report_feedback_attachments

# ============================================================
# Blueprint 定义
# ============================================================

projects_bp = Blueprint('projects', __name__)

# ============================================================
# 路径常量（与 app_x1.py 保持一致）
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CFG = load_x1_config(BASE_DIR)
PATHS = CFG.get('paths', {})
REPORTS_DIR = BASE_DIR / PATHS.get('reports', 'reports_x1')
FORMAL_RECORDS_BASE = Path(os.path.expanduser(str((CFG.get('archive') or {}).get('formal_raw_archive') or PATHS.get('formal_raw_archive') or '~/公司资料/检测部/原始记录'))).resolve()
FORMAL_REPORTS_BASE = Path(os.path.expanduser(str((CFG.get('archive') or {}).get('formal_report_archive') or PATHS.get('formal_report_archive') or '~/公司资料/检测部/检测报告'))).resolve()


# ============================================================
# 项目列表
# ============================================================

@projects_bp.route('/admin/api/business_projects')
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


# ============================================================
# 项目汇总
# ============================================================

@projects_bp.route('/admin/api/business_projects/summary')
@login_required
@require_permission('admin.projects.view')
def admin_api_business_projects_summary():
    conn = get_x1_data_conn()
    try:
        total_projects = conn.execute("SELECT COUNT(*) AS c FROM business_projects").fetchone()['c']
        inspecting_projects = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE inspection_stage='检测中'").fetchone()['c']
        pending_reports = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE report_status IN ('编制中','审核中','待修改','待出具')").fetchone()['c']
        pending_invoices = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE invoice_status IN ('未开票','部分开票')").fetchone()['c']
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


# ============================================================
# 项目详情
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>')
@login_required
@require_permission('admin.projects.view')
def admin_api_business_project_detail(project_id):
    conn = get_x1_data_conn()
    try:
        row = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        feedback_rows = conn.execute(
            "SELECT * FROM report_feedback WHERE project_id=? ORDER BY created_at DESC, id DESC",
            (project_id,)
        ).fetchall()
        report_feedbacks = []
        for fb in feedback_rows:
            # 管理员专用附件序列化：使用管理员下载路径
            att_rows = conn.execute(
                "SELECT id, report_feedback_id, original_name, stored_name, file_ext, mime_type, file_size, relative_path, created_at FROM report_feedback_attachments WHERE report_feedback_id=? ORDER BY id ASC",
                (fb['id'],)
            ).fetchall()
            attachments = []
            for att in att_rows:
                attachments.append({
                    'id': att['id'],
                    'report_feedback_id': att['report_feedback_id'],
                    'original_name': att['original_name'] or '',
                    'stored_name': att['stored_name'] or '',
                    'file_ext': att['file_ext'] or '',
                    'mime_type': att['mime_type'] or '',
                    'file_size': att['file_size'] or 0,
                    'relative_path': att['relative_path'] or '',
                    'download_url': '/admin/api/report_feedback/attachments/%s/download' % att['id'],
                    'created_at': att['created_at'] or '',
                })
            report_feedbacks.append({
                'id': fb['id'],
                'project_id': fb['project_id'],
                'client_name': fb['client_name'] or '',
                'action': fb['action'] or '',
                'content': fb['content'] or '',
                'created_at': fb['created_at'] or '',
                'attachments': attachments,
            })
        return jsonify({'success': True, 'item': serialize_business_project(row), 'report_feedbacks': report_feedbacks})
    finally:
        conn.close()


# ============================================================
# 项目关联报告
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>/reports', methods=['GET'])
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


# ============================================================
# 文件下载
# ============================================================

@projects_bp.route('/admin/api/download_file', methods=['GET'])
@login_required
@require_permission('admin.files.download')
def admin_api_download_file():
    """管理员下载指定路径的报告/原始记录文件"""
    file_path = request.args.get('path', '')
    if not file_path:
        return jsonify({'success': False, 'error': '缺少path参数'}), 400
    try:
        p = Path(file_path).expanduser().resolve(strict=False)
    except Exception:
        return jsonify({'success': False, 'error': '路径非法'}), 400
    # 安全限制：仅允许正式目录和 reports_x1 目录下的真实文件，使用 canonical containment 校验
    allowed_roots = [
        FORMAL_REPORTS_BASE.resolve(),
        FORMAL_RECORDS_BASE.resolve(),
        REPORTS_DIR.resolve(),
    ]
    allowed = False
    for root in allowed_roots:
        try:
            p.relative_to(root)
            allowed = True
            break
        except Exception:
            continue
    if not allowed:
        return jsonify({'success': False, 'error': '无权访问该路径'}), 403
    if not p.exists() or not p.is_file():
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    return send_file(str(p), as_attachment=True, download_name=p.name)


# ============================================================
# 管理员下载客户报告修正反馈附件
# ============================================================

@projects_bp.route('/admin/api/report_feedback/attachments/<int:attachment_id>/download', methods=['GET'])
@login_required
@require_permission('admin.projects.view')
def admin_api_download_report_feedback_attachment(attachment_id):
    """管理员下载报告修正反馈附件（不受 client_name 过滤限制）"""
    conn = get_x1_data_conn()
    try:
        row = conn.execute(
            """
            SELECT a.*, f.project_id
            FROM report_feedback_attachments a
            JOIN report_feedback f ON f.id = a.report_feedback_id
            WHERE a.id=?
            """,
            (attachment_id,)
        ).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '附件不存在或关联反馈已失效'}), 404
        if not row['project_id']:
            return jsonify({'success': False, 'error': '附件关联项目无效'}), 404
        uploads_root = (BASE_DIR / 'uploads_x1').resolve()
        try:
            file_path = (uploads_root / (row['relative_path'] or '')).resolve(strict=False)
            file_path.relative_to(uploads_root)
        except Exception:
            return jsonify({'success': False, 'error': '附件路径非法'}), 400
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'success': False, 'error': '附件文件不存在'}), 404
        return send_file(str(file_path), as_attachment=True, download_name=row['original_name'] or row['stored_name'])
    finally:
        conn.close()


# ============================================================
# 创建项目
# ============================================================

@projects_bp.route('/admin/api/business_projects', methods=['POST'])
@login_required
@require_permission('admin.projects.create')
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
                assigned_to, assigned_at, task_status, created_at, updated_at, version, updated_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', [
            project_no,
            payload['project_name'], payload['client_name'], payload['project_address'], payload['contact_name'], payload['contact_phone'],
            payload['detection_domain'], payload['detection_type'], payload['expected_detection_date'], payload['project_desc'],
            payload['business_stage'], payload['contract_status'], payload['contract_amount'], payload['paid_amount'], payload['inspection_stage'],
            payload['report_status'], payload['invoice_status'], payload['payment_status'], payload['owner'], payload['remarks'],
            payload['assigned_to'], payload['assigned_at'], payload['task_status'], now, now, 1, getattr(current_user, 'id', None)
        ])
        conn.commit()
        row = conn.execute('SELECT * FROM business_projects WHERE id=?', [cur.lastrowid]).fetchone()
        try:
            log_action(
                getattr(current_user, 'id', 'system'),
                '创建项目',
                f'business_project:{cur.lastrowid}',
                json.dumps({
                    'project_id': cur.lastrowid,
                    'project_no': project_no,
                    'project_name': payload['project_name'],
                    'client_name': payload['client_name'],
                    'inspection_stage': payload['inspection_stage'],
                    'report_status': payload['report_status'],
                }, ensure_ascii=False)
            )
        except Exception:
            pass
        return jsonify({'success': True, 'item': serialize_business_project(row)})
    finally:
        conn.close()


# ============================================================
# 更新项目
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>', methods=['PUT'])
@login_required
@require_permission('admin.projects.update')
def admin_api_business_project_update(project_id):
    data = request.get_json(silent=True) or {}
    now = datetime.now().isoformat(timespec='seconds')
    conn = get_x1_data_conn()
    try:
        row = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not row:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        # 合并：以现有数据为底，用请求数据覆盖（部分更新）
        existing = dict(row)
        expected_version = data.get('version', None)
        if expected_version is not None:
            try:
                expected_version = int(expected_version)
            except (TypeError, ValueError):
                return jsonify({'success': False, 'error': 'version 参数非法'}), 400
        current_version = int(existing.get('version') or 1)
        if expected_version is not None and expected_version != current_version:
            return jsonify({'success': False, 'error': '项目数据已被其他人修改，请刷新后重试', 'code': 'version_conflict', 'current_version': current_version}), 409

        merged = {k: data[k] if k in data else existing.get(k, '') for k in [
            'project_name', 'client_name', 'project_address', 'contact_name', 'contact_phone',
            'detection_domain', 'detection_type', 'expected_detection_date', 'project_desc',
            'business_stage', 'contract_status', 'contract_amount', 'paid_amount', 'inspection_stage',
            'report_status', 'invoice_status', 'payment_status', 'owner', 'remarks',
            'assigned_to', 'assigned_at', 'task_status'
        ]}
        if not merged.get('project_name'):
            return jsonify({'success': False, 'error': '项目名称不能为空'}), 400

        params = [
            merged['project_name'], merged['client_name'], merged['project_address'], merged['contact_name'], merged['contact_phone'],
            merged['detection_domain'], merged['detection_type'], merged['expected_detection_date'], merged['project_desc'],
            merged['business_stage'], merged['contract_status'], merged.get('contract_amount', 0), merged.get('paid_amount', 0), merged.get('inspection_stage', ''),
            merged.get('report_status', ''), merged.get('invoice_status', ''), merged.get('payment_status', ''), merged.get('owner', ''), merged.get('remarks', ''),
            merged.get('assigned_to', ''), merged.get('assigned_at', ''), merged.get('task_status', ''), now, getattr(current_user, 'id', None), current_version + 1,
            project_id,
        ]
        update_sql = '''
            UPDATE business_projects SET
                project_name=?, client_name=?, project_address=?, contact_name=?, contact_phone=?,
                detection_domain=?, detection_type=?, expected_detection_date=?, project_desc=?,
                business_stage=?, contract_status=?, contract_amount=?, paid_amount=?, inspection_stage=?,
                report_status=?, invoice_status=?, payment_status=?, owner=?, remarks=?,
                assigned_to=?, assigned_at=?, task_status=?, updated_at=?, updated_by=?, version=?
            WHERE id=?
        '''
        if expected_version is not None:
            update_sql += ' AND COALESCE(version, 1)=?'
            params.append(expected_version)

        cur = conn.execute(update_sql, params)
        if cur.rowcount == 0:
            return jsonify({'success': False, 'error': '项目数据已被其他人修改，请刷新后重试', 'code': 'version_conflict'}), 409
        conn.commit()

        try:
            changes = {}
            for k in ['project_name','client_name','inspection_stage','report_status','invoice_status','payment_status','owner','remarks']:
                old_v = existing.get(k, '')
                new_v = merged.get(k, '')
                if str(old_v) != str(new_v):
                    changes[k] = {'old': old_v, 'new': new_v}
            log_action(
                getattr(current_user, 'id', 'system'),
                '更新项目',
                f'business_project:{project_id}',
                json.dumps({'project_id': project_id, 'changes': changes}, ensure_ascii=False)
            )
        except Exception:
            pass

        # 检测阶段或报告状态变更时通知客户
        try:
            old_stage = existing.get('inspection_stage', '')
            new_stage = merged.get('inspection_stage', '')
            if new_stage and new_stage != old_stage:
                notify_project_status_change(merged['project_name'], merged['client_name'], old_stage, new_stage)
        except Exception:
            pass

        row = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        return jsonify({'success': True, 'item': serialize_business_project(row)})
    finally:
        conn.close()


# ============================================================
# 删除项目
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>', methods=['DELETE'])
@login_required
@require_permission('admin.projects.delete')
def admin_api_business_project_delete(project_id):
    inspect_only = request.args.get('inspect_only', '').strip() in ('1', 'true', 'yes')
    conn = get_x1_data_conn()
    try:
        project = conn.execute('SELECT id, project_name, client_name, report_file_path FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        task_row = conn.execute('SELECT COUNT(*) AS cnt FROM project_tasks WHERE project_id=?', [project_id]).fetchone()
        feedback_row = conn.execute('SELECT COUNT(*) AS cnt FROM report_feedback WHERE project_id=?', [project_id]).fetchone()
        urge_row = conn.execute('SELECT COUNT(*) AS cnt FROM project_urge_logs WHERE project_id=?', [project_id]).fetchone()
        cfb_row = conn.execute('SELECT COUNT(*) AS cnt FROM client_feedback WHERE project_id=?', [project_id]).fetchone()
        attachment_count = len(_parse_report_file_list((project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''))
        impact = {
            'project_name': project['project_name'] or '',
            'client_name': project['client_name'] or '',
            'task_count': task_row['cnt'] if task_row else 0,
            'feedback_count': feedback_row['cnt'] if feedback_row else 0,
            'urge_count': urge_row['cnt'] if urge_row else 0,
            'client_feedback_count': cfb_row['cnt'] if cfb_row else 0,
            'attachment_count': attachment_count,
        }
        if inspect_only:
            return jsonify({'success': True, 'impact': impact})
        conn.execute('DELETE FROM project_tasks WHERE project_id=?', [project_id])
        conn.execute('DELETE FROM project_urge_logs WHERE project_id=?', [project_id])
        conn.execute('DELETE FROM report_feedback WHERE project_id=?', [project_id])
        conn.execute('DELETE FROM client_feedback WHERE project_id=?', [project_id])
        conn.execute('DELETE FROM business_projects WHERE id=?', [project_id])
        conn.commit()
        try:
            log_action(
                getattr(current_user, 'id', 'system'),
                '删除项目',
                f'business_project:{project_id}',
                json.dumps(impact, ensure_ascii=False)
            )
        except Exception:
            pass
        return jsonify({'success': True, 'impact': impact})
    finally:
        conn.close()


# ============================================================
# 上传报告
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>/upload_report', methods=['POST'])
@login_required
@require_permission('admin.projects.upload_report')
def admin_api_upload_report(project_id):
    """上传报告附件（支持多文件 + 压缩包）。
    根据当前 report_status 自动判断附件类型：
    - 报告编制中 → 上传审核稿(draft)，状态推进到"待客户确认"
    - 客户已确认 → 上传最终盖章版(final)，状态推进到"已出报告"
    - 其他状态 → 按 file_type 参数或默认 draft
    """
    ALLOWED_EXTS = {'.docx', '.pdf', '.doc', '.zip', '.rar', '.7z', '.tar', '.gz', '.xlsx', '.xls'}
    conn = get_x1_data_conn()
    try:
        project = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        files = request.files.getlist('report_file')
        if not files or not any(f.filename for f in files):
            return jsonify({'success': False, 'error': '请选择报告文件'}), 400

        # 根据当前状态判断附件类型和目标状态
        current_rs = (project['report_status'] or '').strip()
        # 允许前端显式指定 file_type（可选），但必须受业务状态约束
        explicit_type = ''
        if request.content_type and 'multipart' in request.content_type:
            explicit_type = (request.form.get('file_type') or '').strip()

        # 严格业务规则：
        # 1) 只有“客户已确认”后，才允许上传最终稿(final)
        # 2) 客户未确认前（包括反馈打回后再次上传），一律只能上传审核稿(draft)
        if explicit_type == 'final' and current_rs != '客户已确认':
            try:
                log_action(
                    getattr(current_user, 'id', 'system'),
                    '上传项目报告-非法最终稿尝试',
                    f'business_project:{project_id}',
                    json.dumps({
                        'project_id': project_id,
                        'project_name': project['project_name'],
                        'client_name': project['client_name'],
                        'current_report_status': current_rs,
                        'explicit_type': explicit_type,
                    }, ensure_ascii=False)
                )
            except Exception:
                pass
            return jsonify({'success': False, 'error': '客户未确认前只能上传审核稿，不能上传最终稿'}), 400

        if current_rs == '客户已确认':
            file_type = 'final'
        else:
            file_type = 'draft'

        # 目标状态推进
        if file_type == 'draft':
            target_status = '待客户确认'
        else:
            target_status = '已出报告'

        upload_dir = BASE_DIR / 'uploaded_reports'
        upload_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d%H%M%S')

        # 读取已有附件列表
        existing_raw = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
        existing_files = _parse_report_file_list(existing_raw)

        saved_files = []
        saved_file_paths = []
        pdf_paths = []
        errors = []

        for idx, f in enumerate(files):
            if not f or not f.filename:
                continue
            ext = Path(f.filename).suffix.lower()
            if ext not in ALLOWED_EXTS:
                errors.append(f"{f.filename}: 不支持的格式({ext})")
                continue

            orig_stem = re.sub(r'[^\w\u4e00-\u9fff\-.]', '_', Path(f.filename).stem)[:50]
            safe_name = f"project_{project_id}_{ts}_{idx}_{orig_stem}{ext}"
            save_path = upload_dir / safe_name
            f.save(str(save_path))
            saved_file_paths.append(str(save_path))
            saved_files.append({
                'path': str(save_path),
                'name': f.filename,
                'size': save_path.stat().st_size,
                'file_type': file_type,
                'uploaded_at': datetime.now().isoformat(timespec='seconds')
            })

            # PDF 预览生成
            if ext == '.docx':
                try:
                    from pdf_converter import convert_docx_to_pdf
                    preview_dir = BASE_DIR / 'preview_pdf'
                    preview_dir.mkdir(exist_ok=True)
                    pdf_out = str(preview_dir / f"uploaded_{project_id}_{ts}_{idx}.pdf")
                    result = convert_docx_to_pdf(str(save_path), pdf_out)
                    if result:
                        pdf_paths.append(result)
                except Exception:
                    pass
            elif ext == '.pdf':
                preview_dir = BASE_DIR / 'preview_pdf'
                preview_dir.mkdir(exist_ok=True)
                pdf_dest = preview_dir / f"uploaded_{project_id}_{ts}_{idx}.pdf"
                shutil.copy2(str(save_path), str(pdf_dest))
                pdf_paths.append(str(pdf_dest))

        if not saved_files:
            error_msg = '; '.join(errors) if errors else '没有有效文件'
            return jsonify({'success': False, 'error': error_msg}), 400

        # 如果上传最终版，清除旧的审核稿对客户的可见性（保留文件但标记隐藏）
        if file_type == 'final':
            for item in existing_files:
                if item.get('file_type') == 'draft':
                    item['hidden'] = True

        # 合并附件列表
        all_files = existing_files + saved_files
        file_list_json = json.dumps(all_files, ensure_ascii=False)

        # 更新项目记录
        now = datetime.now().isoformat(timespec='seconds')
        updates = {'report_file_path': file_list_json, 'updated_at': now, 'updated_by': getattr(current_user, 'id', None)}

        # 状态推进（只前进不后退，除非是从编制中到待确认）
        if file_type == 'draft' and current_rs in ('', '未开始', '编制中', '报告编制中', '审核中', '待修改', '待出具'):
            updates['report_status'] = '待客户确认'
            if not (project['inspection_stage'] or '').strip() or (project['inspection_stage'] or '').strip() in ('未安排', '已排期', '检测中'):
                updates['inspection_stage'] = '检测完成'
        elif file_type == 'final' and current_rs in ('客户已确认',):
            updates['report_status'] = '已出报告'

        try:
            current_version = int(project['version']) if 'version' in project.keys() and project['version'] else 1
            updates['version'] = current_version + 1
            set_clause = ', '.join(f"{k}=?" for k in updates.keys())
            conn.execute(f'UPDATE business_projects SET {set_clause} WHERE id=?',
                         list(updates.values()) + [project_id])
            conn.commit()
        except Exception:
            conn.rollback()
            for fp in saved_file_paths:
                try:
                    Path(fp).unlink(missing_ok=True)
                except Exception:
                    pass
            for fp in pdf_paths:
                try:
                    Path(fp).unlink(missing_ok=True)
                except Exception:
                    pass
            raise

        # 通知客户
        try:
            if file_type == 'draft':
                notify_project_report_uploaded(project['project_name'], project['client_name'])
        except Exception:
            pass

        try:
            log_action(
                getattr(current_user, 'id', 'system'),
                '上传项目报告',
                f'business_project:{project_id}',
                json.dumps({
                    'project_id': project_id,
                    'project_name': project['project_name'],
                    'client_name': project['client_name'],
                    'file_type': file_type,
                    'file_count': len(saved_files),
                    'target_status': target_status,
                    'errors': len(errors),
                }, ensure_ascii=False)
            )
        except Exception:
            pass

        count = len(saved_files)
        type_label = '审核稿' if file_type == 'draft' else '正式报告'
        msg = f'{count}个{type_label}上传成功'
        if pdf_paths:
            msg += f'，{len(pdf_paths)}个PDF预览已生成'
        if errors:
            msg += f'（{len(errors)}个文件被跳过）'
        msg += f'，状态已更新为"{target_status}"'

        return jsonify({
            'success': True,
            'files': [{'name': f['name'], 'size': f['size'], 'file_type': f['file_type']} for f in saved_files],
            'file_type': file_type,
            'target_status': target_status,
            'pdf_paths': pdf_paths,
            'errors': errors,
            'total_attachments': len([f for f in all_files if not f.get('hidden')]),
            'message': msg
        })
    finally:
        conn.close()


def _parse_report_file_list(raw: str) -> list:
    """解析 report_file_path 字段：
    - 新格式：JSON 数组，每项是 {path, name, file_type, ...} 对象
    - 旧格式：JSON 数组的纯路径字符串列表
    - 最旧格式：单个路径字符串
    返回统一的对象列表。
    """
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith('['):
        try:
            items = json.loads(raw)
            result = []
            for item in items:
                if isinstance(item, dict):
                    if item.get('path') and Path(item['path']).exists():
                        result.append(item)
                elif isinstance(item, str) and item and Path(item).exists():
                    # 旧格式纯路径，转为对象
                    result.append({
                        'path': item,
                        'name': Path(item).name,
                        'file_type': 'draft',
                        'size': Path(item).stat().st_size
                    })
            return result
        except (json.JSONDecodeError, TypeError):
            return []
    # 最旧格式：单个路径
    if Path(raw).exists():
        return [{'path': raw, 'name': Path(raw).name, 'file_type': 'draft', 'size': Path(raw).stat().st_size}]
    return []


def _parse_report_file_paths(raw: str) -> list:
    """向后兼容：返回纯路径列表（供 download 等接口使用）"""
    items = _parse_report_file_list(raw)
    return [item['path'] for item in items if not item.get('hidden')]


# ============================================================
# 下载项目报告
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>/report_files', methods=['GET'])
@login_required
@require_permission('admin.projects.view')
def admin_api_list_report_files(project_id):
    """列出项目所有报告附件（含 file_type 标记）"""
    conn = get_x1_data_conn()
    try:
        project = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        raw = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
        items = _parse_report_file_list(raw)
        files = []
        for i, item in enumerate(items):
            if item.get('hidden'):
                continue
            pp = Path(item['path'])
            files.append({
                'index': i,
                'name': item.get('name') or pp.name,
                'ext': pp.suffix.lower(),
                'size': item.get('size') or (pp.stat().st_size if pp.exists() else 0),
                'file_type': item.get('file_type', 'draft'),
                'uploaded_at': item.get('uploaded_at', ''),
                'download_url': f'/admin/api/business_projects/{project_id}/download_report?idx={i}'
            })
        return jsonify({'success': True, 'files': files, 'total': len(files)})
    finally:
        conn.close()


@projects_bp.route('/admin/api/business_projects/<int:project_id>/download_report', methods=['GET'])
@login_required
@require_permission('admin.projects.view')
def admin_api_download_report(project_id):
    """下载项目报告文件，支持 ?idx=N 指定附件索引（默认第一个）"""
    conn = get_x1_data_conn()
    try:
        project = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        raw = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
        paths = _parse_report_file_paths(raw)
        if not paths:
            return jsonify({'success': False, 'error': '报告文件不存在'}), 404
        idx = request.args.get('idx', 0, type=int)
        if idx < 0 or idx >= len(paths):
            return jsonify({'success': False, 'error': f'附件索引无效(0~{len(paths)-1})'}), 400
        file_path = Path(paths[idx]).expanduser().resolve(strict=False)
        allowed_roots = [
            (BASE_DIR / 'uploaded_reports').resolve(),
            REPORTS_DIR.resolve(),
            FORMAL_REPORTS_BASE.resolve(),
        ]
        allowed = False
        for root in allowed_roots:
            try:
                file_path.relative_to(root)
                allowed = True
                break
            except Exception:
                continue
        if not allowed:
            return jsonify({'success': False, 'error': '文件路径非法'}), 400
        if not file_path.exists() or not file_path.is_file():
            return jsonify({'success': False, 'error': '文件已被移除'}), 404
        return send_file(str(file_path), as_attachment=True, download_name=file_path.name)
    finally:
        conn.close()


@projects_bp.route('/admin/api/business_projects/<int:project_id>/delete_report_file', methods=['POST'])
@login_required
@require_permission('admin.projects.update')
def admin_api_delete_report_file(project_id):
    """删除项目的某个报告附件，保持新格式对象数组，不回退成旧路径数组。"""
    conn = get_x1_data_conn()
    try:
        project = conn.execute('SELECT * FROM business_projects WHERE id=?', [project_id]).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404
        data = request.get_json(silent=True) or {}
        idx = data.get('index', -1)
        raw = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
        items = _parse_report_file_list(raw)
        if idx < 0 or idx >= len(items):
            return jsonify({'success': False, 'error': '附件索引无效'}), 400

        removed_item = items.pop(idx)
        removed_path = Path(removed_item.get('path') or '').expanduser().resolve(strict=False) if isinstance(removed_item, dict) and (removed_item.get('path') or '').strip() else None
        if removed_path is not None:
            allowed_roots = [
                (BASE_DIR / 'uploaded_reports').resolve(),
                REPORTS_DIR.resolve(),
                FORMAL_REPORTS_BASE.resolve(),
            ]
            allowed = False
            for root in allowed_roots:
                try:
                    removed_path.relative_to(root)
                    allowed = True
                    break
                except Exception:
                    continue
            if not allowed:
                return jsonify({'success': False, 'error': '附件路径非法'}), 400
            if removed_path.exists() and removed_path.is_file():
                removed_path.unlink()

        now = datetime.now().isoformat(timespec='seconds')
        current_version = int(project['version']) if 'version' in project.keys() and project['version'] else 1
        new_json = json.dumps(items, ensure_ascii=False) if items else ''
        conn.execute(
            'UPDATE business_projects SET report_file_path=?, updated_at=?, updated_by=?, version=? WHERE id=?',
            [new_json, now, getattr(current_user, 'id', None), current_version + 1, project_id]
        )
        conn.commit()
        return jsonify({'success': True, 'remaining': len([x for x in items if not x.get("hidden")]), 'message': '附件已删除'})
    finally:
        conn.close()


# ============================================================
# 检测人员列表
# ============================================================

@projects_bp.route('/admin/api/inspectors', methods=['GET'])
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


# ============================================================
# 客户列表
# ============================================================

@projects_bp.route('/admin/api/customers')
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
