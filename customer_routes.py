"""
客户界面后端路由模块
提供客户门户的 API：个人信息、历史记录、项目管理、催单、投诉建议
"""

from flask import Blueprint, render_template, request, jsonify
from auth import require_permission
from notifications import notify_customer_urge, notify_report_feedback, notify_report_ready
from flask_login import current_user, login_required
from pathlib import Path
from datetime import datetime, timedelta
import json
import sqlite3
from functools import wraps

BASE_DIR = Path(__file__).resolve().parent

customer_bp = Blueprint("customer", __name__)


def customer_required(f):
    """装饰器：要求登录且角色为 customer 或 admin"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role not in ('customer', 'admin'):
            from flask import redirect
            if '/api/' in request.path:
                return jsonify({'success': False, 'error': '无权访问，请登录客户账号'}), 403
            return redirect('/customer/login')
        return f(*args, **kwargs)
    return decorated


def _get_client_name():
    """获取当前客户绑定的委托单位名"""
    # admin 预览模式：通过 ?as_client=xxx 模拟指定客户
    if current_user.role == 'admin':
        as_client = request.args.get('as_client', '').strip()
        return as_client  # 空串表示未指定
    from database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT client_name FROM users WHERE user_id = ?",
            (current_user.id,)
        ).fetchone()
    return row['client_name'] if row and row['client_name'] else ''


def _get_x1_data_conn():
    """获取业务数据库连接（避免循环引用）"""
    db_path = BASE_DIR / 'data' / 'x1_data.db'
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def init_customer_tables():
    """创建客户相关表（在 data/x1_data.db 中）并执行增量迁移"""
    conn = _get_x1_data_conn()
    try:
        # client_profiles 表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS client_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT UNIQUE NOT NULL,
                invoice_company TEXT DEFAULT '',
                invoice_tax_no TEXT DEFAULT '',
                invoice_address_phone TEXT DEFAULT '',
                invoice_bank TEXT DEFAULT '',
                invoice_bank_account TEXT DEFAULT '',
                recipient_name TEXT DEFAULT '',
                recipient_phone TEXT DEFAULT '',
                recipient_address TEXT DEFAULT '',
                updated_at TEXT DEFAULT ''
            )
        """)

        # project_urge_logs 表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS project_urge_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                client_name TEXT NOT NULL,
                urge_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        # client_feedback 表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS client_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                feedback_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT DEFAULT '',
                contact TEXT DEFAULT '',
                status TEXT DEFAULT '待处理',
                reply TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT DEFAULT ''
            )
        """)

        # report_feedback 表（客户报告反馈/确认）
        conn.execute("""
            CREATE TABLE IF NOT EXISTS report_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                client_name TEXT NOT NULL,
                action TEXT NOT NULL,
                content TEXT DEFAULT '',
                created_at TEXT NOT NULL
            )
        """)

        # 增量迁移：business_projects 增加 source 字段
        try:
            conn.execute("ALTER TABLE business_projects ADD COLUMN source TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # 已存在

        # 增量迁移：business_projects 增加 has_urge 字段
        try:
            conn.execute("ALTER TABLE business_projects ADD COLUMN has_urge TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # 已存在

        conn.commit()
    finally:
        conn.close()

    # 增量迁移：users 表增加 client_name 字段（在根目录 x1_data.db 中）
    from database import get_db
    with get_db() as user_conn:
        try:
            user_conn.execute("ALTER TABLE users ADD COLUMN client_name TEXT DEFAULT ''")
            user_conn.commit()
        except sqlite3.OperationalError:
            pass  # 已存在



# ==================== 页面路由 ====================

@customer_bp.route('/customer')
@customer_required
def customer_page():
    return render_template('customer.html')

# ==================== 客户信息 API ====================

@customer_bp.route('/customer/api/profile', methods=['GET'])
@customer_required
def customer_get_profile():
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': True, 'data': {'client_name': '', 'invoice_company': '', 'invoice_tax_no': '', 'invoice_address_phone': '', 'invoice_bank': '', 'invoice_bank_account': '', 'recipient_name': '', 'recipient_phone': '', 'recipient_address': ''}})

    conn = _get_x1_data_conn()
    try:
        row = conn.execute(
            "SELECT * FROM client_profiles WHERE client_name = ?",
            (client_name,)
        ).fetchone()

        if row:
            profile = {
                'client_name': row['client_name'],
                'invoice_company': row['invoice_company'] or '',
                'invoice_tax_no': row['invoice_tax_no'] or '',
                'invoice_address_phone': row['invoice_address_phone'] or '',
                'invoice_bank': row['invoice_bank'] or '',
                'invoice_bank_account': row['invoice_bank_account'] or '',
                'recipient_name': row['recipient_name'] or '',
                'recipient_phone': row['recipient_phone'] or '',
                'recipient_address': row['recipient_address'] or '',
                'updated_at': row['updated_at'] or '',
            }
        else:
            profile = {
                'client_name': client_name,
                'invoice_company': '',
                'invoice_tax_no': '',
                'invoice_address_phone': '',
                'invoice_bank': '',
                'invoice_bank_account': '',
                'recipient_name': '',
                'recipient_phone': '',
                'recipient_address': '',
                'updated_at': '',
            }

        return jsonify({'success': True, 'data': profile})
    finally:
        conn.close()

@customer_bp.route('/customer/api/profile', methods=['PUT'])
@customer_required
def customer_update_profile():
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': False, 'message': '未绑定客户单位'}), 400

    data = request.get_json() or {}
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = _get_x1_data_conn()
    try:
        existing = conn.execute(
            "SELECT id FROM client_profiles WHERE client_name = ?",
            (client_name,)
        ).fetchone()

        if existing:
            conn.execute("""
                UPDATE client_profiles SET
                    invoice_company = ?,
                    invoice_tax_no = ?,
                    invoice_address_phone = ?,
                    invoice_bank = ?,
                    invoice_bank_account = ?,
                    recipient_name = ?,
                    recipient_phone = ?,
                    recipient_address = ?,
                    updated_at = ?
                WHERE client_name = ?
            """, (
                data.get('invoice_company', ''),
                data.get('invoice_tax_no', ''),
                data.get('invoice_address_phone', ''),
                data.get('invoice_bank', ''),
                data.get('invoice_bank_account', ''),
                data.get('recipient_name', ''),
                data.get('recipient_phone', ''),
                data.get('recipient_address', ''),
                now,
                client_name,
            ))
        else:
            conn.execute("""
                INSERT INTO client_profiles
                    (client_name, invoice_company, invoice_tax_no, invoice_address_phone,
                     invoice_bank, invoice_bank_account, recipient_name, recipient_phone,
                     recipient_address, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                client_name,
                data.get('invoice_company', ''),
                data.get('invoice_tax_no', ''),
                data.get('invoice_address_phone', ''),
                data.get('invoice_bank', ''),
                data.get('invoice_bank_account', ''),
                data.get('recipient_name', ''),
                data.get('recipient_phone', ''),
                data.get('recipient_address', ''),
                now,
            ))

        conn.commit()
        return jsonify({'success': True, 'message': '信息已更新'})
    finally:
        conn.close()

# ==================== 历史记录 API ====================

@customer_bp.route('/customer/api/history', methods=['GET'])
@customer_required
def customer_get_history():
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': True, 'items': []})

    results = []
    seen_projects = set()  # 用于去重

    # 数据源1：已确认的项目（从 business_projects 表）
    conn = _get_x1_data_conn()
    try:
        confirmed_rows = conn.execute(
            "SELECT * FROM business_projects WHERE client_name=? AND report_status IN ('客户已确认','已发送客户','已出报告') ORDER BY updated_at DESC",
            (client_name,)
        ).fetchall()
        for row in confirmed_rows:
            pname = row['project_name'] or ''
            seen_projects.add(pname)
            results.append({
                'export_id': '',
                'project_id': row['id'],
                'project_name': pname,
                'detection_object': row['detection_type'] or '',
                'detection_type': row['detection_type'] or '',
                'detection_date': row['expected_detection_date'] or (row['updated_at'] or '')[:10],
                'report_number': row['project_no'] or '',
                'report_no': row['project_no'] or '',
                'project_address': row['project_address'] or '',
                'contact_name': row['contact_name'] or '',
                'contact_phone': row['contact_phone'] or '',
                'client_name': row['client_name'] or '',
                'status': '已出报告' if row['report_status'] == '已出报告' else ('客户已确认' if row['report_status'] == '客户已确认' else '已完成'),
                'feishu_report_url': '',
                'feishu_export_url': '',
                'can_preview_pdf': True,
            })
    finally:
        conn.close()

    # 数据源2：导出记录（从 reports_x1/*.json）
    reports_dir = BASE_DIR / 'reports_x1'
    if reports_dir.exists():
        for json_file in sorted(reports_dir.glob('*.json'), reverse=True):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                export_payload = data.get('export_payload', {})
                project = export_payload.get('project', {})
                file_client_name = project.get('client_name', '')

                if file_client_name != client_name:
                    continue

                pname = project.get('project_name', '')
                if pname in seen_projects:
                    continue  # 已经从确认项目源取到，跳过重复
                seen_projects.add(pname)

                feishu = data.get('feishu', {})
                feishu_report = feishu.get('report', {})
                feishu_export = feishu.get('export', {})

                results.append({
                    'export_id': data.get('export_id', ''),
                    'project_name': pname,
                    'detection_object': project.get('inspection_area', ''),
                    'detection_date': project.get('detection_date', ''),
                    'report_number': project.get('report_number', ''),
                    'status': '已出具' if feishu_report.get('success') else '生成中',
                    'feishu_report_url': feishu_report.get('feishu_url', ''),
                    'feishu_export_url': feishu_export.get('feishu_url', ''),
                })
            except (json.JSONDecodeError, KeyError, IOError):
                continue

    return jsonify({'success': True, 'items': results})

# ==================== 检测项目 API ====================

@customer_bp.route('/customer/api/projects', methods=['GET'])
@customer_required
def customer_get_projects():
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': True, 'items': []})

    conn = _get_x1_data_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM business_projects WHERE client_name = ? ORDER BY updated_at DESC, id DESC",
            (client_name,)
        ).fetchall()

        # 查询催单冷却状态（4小时内是否催过）
        cooldown_time = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
        urge_logs = conn.execute(
            "SELECT project_id, urge_type FROM project_urge_logs WHERE client_name=? AND created_at > ?",
            (client_name, cooldown_time)
        ).fetchall()
        # 构建 {project_id: set(urge_types)} 映射
        urge_cooling = {}
        for log in urge_logs:
            pid = log['project_id']
            if pid not in urge_cooling:
                urge_cooling[pid] = set()
            urge_cooling[pid].add(log['urge_type'])

        projects = []
        for row in rows:
            pid = row['id']
            cooling = urge_cooling.get(pid, set())
            rs = (row['report_status'] or '').strip()
            # 已确认/已出报告的项目不在进行中列表显示（转历史记录）
            if rs in ('客户已确认', '已发送客户', '已出报告'):
                continue
            projects.append({
                'id': pid,
                'project_no': row['project_no'] or '',
                'project_name': row['project_name'] or '',
                'client_name': row['client_name'] or '',
                'project_address': row['project_address'] or '',
                'contact_name': row['contact_name'] or '',
                'contact_phone': row['contact_phone'] or '',
                'detection_type': row['detection_type'] or '',
                'expected_detection_date': row['expected_detection_date'] or '',
                'project_desc': row['project_desc'] or '',
                'business_stage': row['business_stage'] or '',
                'inspection_stage': row['inspection_stage'] or '',
                'report_status': rs,
                'invoice_status': row['invoice_status'] or '',
                'payment_status': row['payment_status'] or '',
                'has_urge': row['has_urge'] if 'has_urge' in row.keys() else '',
                'urge_cooling_report': 'report' in cooling,
                'urge_cooling_invoice': 'invoice' in cooling,
                'created_at': row['created_at'] or '',
                'updated_at': row['updated_at'] or '',
            })

        return jsonify({'success': True, 'items': projects})
    finally:
        conn.close()

@customer_bp.route('/customer/api/projects', methods=['POST'])
@customer_required
@require_permission('customer.projects')
def customer_create_project():
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': False, 'message': '未绑定客户单位'}), 400

    data = request.get_json() or {}

    required_fields = ['project_name', 'detection_type']
    for field in required_fields:
        if not data.get(field, '').strip():
            return jsonify({'success': False, 'message': f'缺少必填字段: {field}'}), 400

    # 局部 import 避免循环引用
    from app_x1 import _generate_project_no

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    project_no = _generate_project_no()

    conn = _get_x1_data_conn()
    try:
        cur = conn.execute("""
            INSERT INTO business_projects
                (project_no, project_name, client_name, detection_type, project_address,
                 contact_name, contact_phone, expected_detection_date, project_desc,
                 source, business_stage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project_no,
            data.get('project_name', '').strip(),
            client_name,
            data.get('detection_type', '').strip(),
            data.get('project_address', '').strip(),
            data.get('contact_name', '').strip(),
            data.get('contact_phone', '').strip(),
            data.get('expected_detection_date', '').strip(),
            data.get('project_desc', '').strip(),
            '客户需求',
            '待确认',
            now,
            now,
        ))
        conn.commit()
        return jsonify({
            'success': True,
            'message': '项目已提交',
            'project_id': cur.lastrowid,
            'project_no': project_no
        })
    finally:
        conn.close()

# ==================== 催单 API ====================

@customer_bp.route('/customer/api/projects/<int:project_id>/urge', methods=['POST'])
@customer_required
@require_permission('customer.urge')
def customer_urge_project(project_id):
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': False, 'message': '未绑定客户单位'}), 400

    data = request.get_json() or {}
    urge_type = data.get('type', '')
    if urge_type not in ('report', 'invoice'):
        return jsonify({'success': False, 'message': '催单类型无效，需为 report 或 invoice'}), 400

    conn = _get_x1_data_conn()
    try:
        # 验证项目属于当前客户
        project = conn.execute(
            "SELECT id, client_name, has_urge FROM business_projects WHERE id = ?",
            (project_id,)
        ).fetchone()

        if not project or project['client_name'] != client_name:
            return jsonify({'success': False, 'message': '项目不存在或无权操作'}), 404

        # 冷却期检查：4小时内同一项目同一类型不能重复催单
        cooldown_time = (datetime.now() - timedelta(hours=4)).strftime('%Y-%m-%d %H:%M:%S')
        recent = conn.execute(
            "SELECT id FROM project_urge_logs WHERE project_id = ? AND urge_type = ? AND created_at > ?",
            (project_id, urge_type, cooldown_time)
        ).fetchone()

        if recent:
            return jsonify({
                'success': False,
                'message': '正在处理您的请求，请4小时后再试。'
            }), 429

        # 写入催单记录
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "INSERT INTO project_urge_logs (project_id, client_name, urge_type, created_at) VALUES (?, ?, ?, ?)",
            (project_id, client_name, urge_type, now)
        )

        # 标记 has_urge
        existing_urge = project['has_urge'] or ''
        urge_tags = set(existing_urge.split(',')) if existing_urge else set()
        urge_tags.discard('')
        urge_tags.add(urge_type)
        conn.execute(
            "UPDATE business_projects SET has_urge = ? WHERE id = ?",
            (','.join(urge_tags), project_id)
        )

        conn.commit()

        # 返回提示文案
        if urge_type == 'report':
            message = '感谢您的信任，普迪公司总经理已经收到您的催单，他会根据报告进度尽快处理。'
        else:
            message = '普迪公司财务会尽快开具发票。'

        try:
            notify_customer_urge(client_name, project.get('project_name') or str(project_id))
        except Exception:
            pass
        return jsonify({'success': True, 'message': message})
    finally:
        conn.close()

# ==================== 投诉建议 API ====================

@customer_bp.route('/customer/api/feedback', methods=['GET'])
@customer_required
def customer_get_feedback():
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': True, 'items': []})

    conn = _get_x1_data_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM client_feedback WHERE client_name = ? ORDER BY created_at DESC",
            (client_name,)
        ).fetchall()

        feedbacks = []
        for row in rows:
            feedbacks.append({
                'id': row['id'],
                'feedback_type': row['feedback_type'] or '',
                'title': row['title'] or '',
                'content': row['content'] or '',
                'contact': row['contact'] or '',
                'status': row['status'] or '待处理',
                'reply': row['reply'] or '',
                'created_at': row['created_at'] or '',
                'updated_at': row['updated_at'] or '',
            })

        return jsonify({'success': True, 'items': feedbacks})
    finally:
        conn.close()

@customer_bp.route('/customer/api/feedback', methods=['POST'])
@customer_required
@require_permission('customer.feedback')
def customer_create_feedback():
    client_name = _get_client_name()
    if not client_name:
        return jsonify({'success': False, 'message': '未绑定客户单位'}), 400

    data = request.get_json() or {}

    feedback_type = data.get('feedback_type', '').strip()
    title = data.get('title', '').strip()

    if not feedback_type or feedback_type not in ('投诉', '建议', '其他'):
        return jsonify({'success': False, 'message': '反馈类型无效'}), 400
    if not title:
        return jsonify({'success': False, 'message': '标题不能为空'}), 400

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    conn = _get_x1_data_conn()
    try:
        conn.execute("""
            INSERT INTO client_feedback
                (client_name, feedback_type, title, content, contact, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            client_name,
            feedback_type,
            title,
            data.get('content', '').strip(),
            data.get('contact', '').strip(),
            '待处理',
            now,
            now,
        ))
        conn.commit()
        return jsonify({'success': True, 'message': '反馈已提交，感谢您的宝贵意见'})
    finally:
        conn.close()

# ============================================================
# 报告反馈 & 确认
# ============================================================

@customer_bp.route('/customer/api/projects/<int:project_id>/report_feedback', methods=['GET'])
@customer_required
def customer_get_report_feedback(project_id):
    """获取某项目的报告反馈历史"""
    client_name = _get_client_name()
    conn = _get_x1_data_conn()
    try:
        # 校验项目归属
        project = conn.execute(
            "SELECT * FROM business_projects WHERE id=? AND client_name=?",
            (project_id, client_name)
        ).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        rows = conn.execute(
            "SELECT * FROM report_feedback WHERE project_id=? AND client_name=? ORDER BY created_at DESC",
            (project_id, client_name)
        ).fetchall()
        items = [{
            'id': r['id'],
            'action': r['action'],
            'content': r['content'],
            'created_at': r['created_at'],
        } for r in rows]
        return jsonify({'success': True, 'items': items, 'report_status': project['report_status'] or ''})
    finally:
        conn.close()

@customer_bp.route('/customer/api/projects/<int:project_id>/report_feedback', methods=['POST'])
@customer_required
@require_permission('customer.feedback')
def customer_submit_report_feedback(project_id):
    """客户提交报告修正意见，状态回退到“报告编制中”"""
    client_name = _get_client_name()
    data = request.get_json(silent=True) or {}
    content = (data.get('content') or '').strip()
    if not content:
        return jsonify({'success': False, 'error': '请填写反馈内容'}), 400

    conn = _get_x1_data_conn()
    try:
        project = conn.execute(
            "SELECT * FROM business_projects WHERE id=? AND client_name=?",
            (project_id, client_name)
        ).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        rs = (project['report_status'] or '').strip()
        if rs not in ('已出具', '待客户确认', '已发送客户'):
            return jsonify({'success': False, 'error': '当前状态不允许反馈'}), 400

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            "INSERT INTO report_feedback (project_id, client_name, action, content, created_at) VALUES (?,?,?,?,?)",
            (project_id, client_name, 'feedback', content, now)
        )
        # 状态回退到“报告编制中”——管理员修改后重新上传审核稿
        conn.execute(
            "UPDATE business_projects SET report_status=?, updated_at=? WHERE id=?",
            ('报告编制中', now, project_id)
        )
        conn.commit()

        from monitor import log_action
        log_action(client_name, '客户报告反馈', f'project_id={project_id}', content[:100])

        try:
            notify_report_feedback(client_name, str(project_id))
        except Exception:
            pass
        return jsonify({'success': True, 'message': '反馈已提交，报告将进入修改流程'})
    finally:
        conn.close()

@customer_bp.route('/customer/api/projects/<int:project_id>/confirm_report', methods=['POST'])
@customer_required
@require_permission('customer.confirm')
def customer_confirm_report(project_id):
    """客户确认报告无误，同意出具正式报告"""
    client_name = _get_client_name()
    data = request.get_json(silent=True) or {}
    remark = (data.get('remark') or '').strip()
    conn = _get_x1_data_conn()
    try:
        project = conn.execute(
            "SELECT * FROM business_projects WHERE id=? AND client_name=?",
            (project_id, client_name)
        ).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        rs = (project['report_status'] or '').strip()
        if rs not in ('已出具', '待客户确认', '已发送客户'):
            return jsonify({'success': False, 'error': '当前状态不允许确认'}), 400

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        confirm_content = '客户确认报告无误，同意出具正式报告'
        if remark:
            confirm_content += f'\n附言：{remark}'
        conn.execute(
            "INSERT INTO report_feedback (project_id, client_name, action, content, created_at) VALUES (?,?,?,?,?)",
            (project_id, client_name, 'confirm', confirm_content, now)
        )
        # 状态推进到“客户已确认”
        conn.execute(
            "UPDATE business_projects SET report_status=?, updated_at=? WHERE id=?",
            ('客户已确认', now, project_id)
        )
        conn.commit()

        from monitor import log_action
        log_action(client_name, '客户确认报告', f'project_id={project_id}', remark[:200])

        return jsonify({'success': True, 'message': '报告已确认，将安排打印出具正式报告'})
    finally:
        conn.close()

# ============================================================
# 报告 PDF 预览
# ============================================================

@customer_bp.route('/customer/api/projects/<int:project_id>/preview_pdf', methods=['GET'])
@customer_required
@require_permission('customer.report.preview')
def customer_preview_pdf(project_id):
    """客户预览报告PDF。
    - 待客户确认/客户已确认 → 预览审核稿
    - 已出报告 → 预览正式报告
    """
    from flask import send_file as _send_file
    client_name = _get_client_name()
    conn = _get_x1_data_conn()
    try:
        project = conn.execute(
            "SELECT * FROM business_projects WHERE id=? AND client_name=?",
            (project_id, client_name)
        ).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        rs = (project['report_status'] or '').strip()
        allowed = ('待客户确认', '客户已确认', '已出报告', '已出具', '已发送客户')
        if rs not in allowed:
            return jsonify({'success': False, 'error': '报告尚未出具，无法预览'}), 400

        project_name = (project['project_name'] or '').strip()
        report_file_raw = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
    finally:
        conn.close()

    # 根据状态获取客户可见的附件
    file_list = _parse_customer_report_files(report_file_raw, rs)
    preview_dir = BASE_DIR / 'preview_pdf'
    pdf_path = None

    # 从客户可见附件中找 PDF
    for item in file_list:
        fp = Path(item['path'])
        if fp.suffix.lower() == '.pdf' and fp.exists():
            pdf_path = fp
            break

    # 如果没有直接的 PDF，尝试从 preview_pdf 目录找已生成的
    if not pdf_path and preview_dir.exists():
        for candidate in sorted(preview_dir.glob(f'uploaded_{project_id}_*.pdf'), reverse=True):
            if candidate.stat().st_size > 0:
                pdf_path = candidate
                break

    # 如果还没有，尝试从 docx 实时转换
    if not pdf_path:
        for item in file_list:
            fp = Path(item['path'])
            if fp.suffix.lower() == '.docx' and fp.exists():
                try:
                    from pdf_converter import convert_docx_to_pdf
                    preview_dir.mkdir(exist_ok=True)
                    ts = datetime.now().strftime('%Y%m%d%H%M%S')
                    pdf_out = str(preview_dir / f"preview_{project_id}_{ts}.pdf")
                    result = convert_docx_to_pdf(str(fp), pdf_out)
                    if result:
                        pdf_path = Path(result)
                        break
                except Exception:
                    pass

    if not pdf_path or not pdf_path.exists():
        return jsonify({'success': False, 'error': 'PDF 预览文件尚未生成，请稍后重试或联系检测中心'}), 404

    label = '正式报告' if rs in ('已出报告', '已出具', '已发送客户') else '检测报告(审核稿)'
    return _send_file(
        str(pdf_path),
        mimetype='application/pdf',
        as_attachment=False,
        download_name=f"{label}_{project_name}.pdf"
    )

@customer_bp.route('/customer/api/projects/<int:project_id>/download_report', methods=['GET'])
@customer_required
@require_permission('customer.report.download')
def customer_download_report(project_id):
    """客户下载报告文件。
    - 待客户确认/客户已确认 → 返回审核稿(draft)
    - 已出报告 → 返回正式报告(final)，审核稿不可见
    """
    from flask import send_file as _send_file
    client_name = _get_client_name()
    conn = _get_x1_data_conn()
    try:
        project = conn.execute(
            "SELECT * FROM business_projects WHERE id=? AND client_name=?",
            (project_id, client_name)
        ).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        rs = (project['report_status'] or '').strip()
        allowed = ('待客户确认', '客户已确认', '已出报告', '已出具', '已发送客户')
        if rs not in allowed:
            return jsonify({'success': False, 'error': '报告尚未出具，无法下载'}), 400

        project_name = (project['project_name'] or '').strip()
        report_file_raw = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
    finally:
        conn.close()

    # 解析附件列表
    file_list = _parse_customer_report_files(report_file_raw, rs)

    idx = request.args.get('idx', 0, type=int)
    if not file_list:
        return jsonify({'success': False, 'error': '报告文件不存在，请联系检测中心'}), 404
    if idx < 0 or idx >= len(file_list):
        idx = 0

    target = Path(file_list[idx]['path'])
    if not target.exists():
        return jsonify({'success': False, 'error': '文件已被移除，请联系检测中心'}), 404

    file_type_label = '正式报告' if file_list[idx].get('file_type') == 'final' else '检测报告'
    mime = 'application/pdf' if target.suffix.lower() == '.pdf' else 'application/octet-stream'
    return _send_file(str(target), mimetype=mime, as_attachment=True,
                      download_name=f"{file_type_label}_{project_name}{target.suffix}")


@customer_bp.route('/customer/api/projects/<int:project_id>/report_files', methods=['GET'])
@customer_required
@require_permission('customer.report.download')
def customer_list_report_files(project_id):
    """客户查看可下载的报告附件列表（根据状态过滤 draft/final）"""
    client_name = _get_client_name()
    conn = _get_x1_data_conn()
    try:
        project = conn.execute(
            "SELECT * FROM business_projects WHERE id=? AND client_name=?",
            (project_id, client_name)
        ).fetchone()
        if not project:
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        rs = (project['report_status'] or '').strip()
        allowed = ('待客户确认', '客户已确认', '已出报告', '已出具', '已发送客户')
        if rs not in allowed:
            return jsonify({'success': True, 'files': [], 'total': 0})

        report_file_raw = (project['report_file_path'] if 'report_file_path' in project.keys() else '') or ''
    finally:
        conn.close()

    file_list = _parse_customer_report_files(report_file_raw, rs)
    files = []
    for i, item in enumerate(file_list):
        pp = Path(item['path'])
        files.append({
            'index': i,
            'name': item.get('name') or pp.name,
            'ext': pp.suffix.lower(),
            'size': item.get('size') or (pp.stat().st_size if pp.exists() else 0),
            'file_type': item.get('file_type', 'draft'),
            'download_url': f'/customer/api/projects/{project_id}/download_report?idx={i}'
        })
    return jsonify({'success': True, 'files': files, 'total': len(files)})


def _parse_customer_report_files(raw: str, report_status: str) -> list:
    """根据项目状态，返回客户可见的附件列表。
    - 已出报告 → 只返回 final 类型
    - 待客户确认/客户已确认 → 只返回 draft 类型（未 hidden 的）
    """
    if not raw:
        return []
    raw = raw.strip()
    items = []
    if raw.startswith('['):
        try:
            parsed = json.loads(raw)
            for item in parsed:
                if isinstance(item, dict):
                    if item.get('path') and Path(item['path']).exists() and not item.get('hidden'):
                        items.append(item)
                elif isinstance(item, str) and item and Path(item).exists():
                    items.append({'path': item, 'name': Path(item).name, 'file_type': 'draft'})
        except (json.JSONDecodeError, TypeError):
            pass
    elif Path(raw).exists():
        items.append({'path': raw, 'name': Path(raw).name, 'file_type': 'draft'})

    # 根据状态过滤
    if report_status in ('已出报告', '已出具', '已发送客户'):
        # 最终状态：只展示 final
        final_files = [f for f in items if f.get('file_type') == 'final']
        if final_files:
            return final_files
        # 如果没有 final 标记的（旧数据兼容），返回所有
        return items
    else:
        # 待确认/已确认：只展示 draft
        return [f for f in items if f.get('file_type') == 'draft']


# ============================================================
# 客户修改密码
# ============================================================
@customer_bp.route('/customer/api/change_password', methods=['POST'])
@login_required
@customer_required
def customer_change_password():
    """客户修改自己的密码"""
    data = request.get_json(silent=True) or {}
    old_password = (data.get('old_password') or '').strip()
    new_password = (data.get('new_password') or '').strip()

    if not old_password or not new_password:
        return jsonify({'success': False, 'error': '请填写原密码和新密码'}), 400
    if len(new_password) < 6:
        return jsonify({'success': False, 'error': '新密码至少6位'}), 400

    from werkzeug.security import check_password_hash, generate_password_hash
    from database import get_db

    try:
        with get_db() as conn:
            row = conn.execute('SELECT password_hash FROM users WHERE user_id = ?', [current_user.id]).fetchone()
            if not row:
                return jsonify({'success': False, 'error': '用户不存在'}), 404
            if not check_password_hash(row['password_hash'], old_password):
                return jsonify({'success': False, 'error': '原密码错误'}), 400
            conn.execute('UPDATE users SET password_hash = ? WHERE user_id = ?',
                         [generate_password_hash(new_password, method='pbkdf2:sha256'), current_user.id])
            conn.commit()
        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': f'修改失败：{str(e)}'}), 500
