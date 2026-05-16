"""
X1 项目管理路由 Blueprint
"""

import json
import os
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
        return jsonify({'success': True, 'item': serialize_business_project(row)})
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


# ============================================================
# 创建项目
# ============================================================

@projects_bp.route('/admin/api/business_projects', methods=['POST'])
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


# ============================================================
# 更新项目
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>', methods=['PUT'])
@login_required
@require_permission('admin.projects.manage')
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
        merged = {k: data[k] if k in data else existing.get(k, '') for k in [
            'project_name', 'client_name', 'project_address', 'contact_name', 'contact_phone',
            'detection_domain', 'detection_type', 'expected_detection_date', 'project_desc',
            'business_stage', 'contract_status', 'contract_amount', 'paid_amount', 'inspection_stage',
            'report_status', 'invoice_status', 'payment_status', 'owner', 'remarks',
            'assigned_to', 'assigned_at', 'task_status'
        ]}
        if not merged.get('project_name'):
            return jsonify({'success': False, 'error': '项目名称不能为空'}), 400
        conn.execute('''
            UPDATE business_projects SET
                project_name=?, client_name=?, project_address=?, contact_name=?, contact_phone=?,
                detection_domain=?, detection_type=?, expected_detection_date=?, project_desc=?,
                business_stage=?, contract_status=?, contract_amount=?, paid_amount=?, inspection_stage=?,
                report_status=?, invoice_status=?, payment_status=?, owner=?, remarks=?,
                assigned_to=?, assigned_at=?, task_status=?, updated_at=?
            WHERE id=?
        ''', [
            merged['project_name'], merged['client_name'], merged['project_address'], merged['contact_name'], merged['contact_phone'],
            merged['detection_domain'], merged['detection_type'], merged['expected_detection_date'], merged['project_desc'],
            merged['business_stage'], merged['contract_status'], merged.get('contract_amount', 0), merged.get('paid_amount', 0), merged.get('inspection_stage', ''),
            merged.get('report_status', ''), merged.get('invoice_status', ''), merged.get('payment_status', ''), merged.get('owner', ''), merged.get('remarks', ''),
            merged.get('assigned_to', ''), merged.get('assigned_at', ''), merged.get('task_status', ''), now, project_id
        ])
        conn.commit()

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


# ============================================================
# 上传报告
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>/upload_report', methods=['POST'])
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
            shutil.copy2(str(save_path), str(pdf_dest))
            pdf_path = str(pdf_dest)

        # 更新项目记录
        now = datetime.now().isoformat(timespec='seconds')
        updates = {'report_file_path': str(save_path), 'updated_at': now}
        # 如果 report_status 还是初始状态，自动推进到"已出具"
        current_rs = (project['report_status'] or '').strip()
        if current_rs in ('', '未开始', '编制中', '审核中', '待出具'):
            updates['report_status'] = '已出具'
            updates['inspection_stage'] = '检测完成'

        set_clause = ', '.join(f"{k}=?" for k in updates.keys())
        conn.execute(f'UPDATE business_projects SET {set_clause} WHERE id=?',
                     list(updates.values()) + [project_id])
        conn.commit()

        # 通知客户报告已出具
        try:
            notify_project_report_uploaded(project['project_name'], project['client_name'])
        except Exception:
            pass

        return jsonify({
            'success': True,
            'file_path': str(save_path),
            'pdf_path': pdf_path,
            'message': '报告上传成功' + ('，PDF 预览已生成' if pdf_path else '')
        })
    finally:
        conn.close()


# ============================================================
# 下载项目报告
# ============================================================

@projects_bp.route('/admin/api/business_projects/<int:project_id>/download_report', methods=['GET'])
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
