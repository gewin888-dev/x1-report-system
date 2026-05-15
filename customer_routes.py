"""
客户界面后端路由模块
提供客户门户的 API：个人信息、历史记录、项目管理、催单、投诉建议
"""

from flask import render_template, request, jsonify
from flask_login import current_user, login_required
from pathlib import Path
from datetime import datetime, timedelta
import json
import sqlite3
from functools import wraps

BASE_DIR = Path(__file__).resolve().parent


def customer_required(f):
    """装饰器：要求登录且角色为 customer 或 admin"""
    @wraps(f)
    @login_required
    def decorated(*args, **kwargs):
        if not hasattr(current_user, 'role') or current_user.role not in ('customer', 'admin'):
            return jsonify({'success': False, 'message': '无权访问'}), 403
        return f(*args, **kwargs)
    return decorated


def _get_client_name():
    """获取当前客户绑定的委托单位名"""
    if current_user.role == 'admin':
        return ''  # admin 预览模式，无绑定
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


def register_customer_routes(app):
    """注册客户界面路由"""

    # 初始化表
    init_customer_tables()

    # ==================== 页面路由 ====================

    @app.route('/customer')
    @customer_required
    def customer_page():
        return render_template('customer.html')

    # ==================== 客户信息 API ====================

    @app.route('/customer/api/profile', methods=['GET'])
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

    @app.route('/customer/api/profile', methods=['PUT'])
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

    @app.route('/customer/api/history', methods=['GET'])
    @customer_required
    def customer_get_history():
        client_name = _get_client_name()
        if not client_name:
            return jsonify({'success': True, 'items': []})

        reports_dir = BASE_DIR / 'reports_x1'
        results = []

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

                    feishu = data.get('feishu', {})
                    feishu_report = feishu.get('report', {})
                    feishu_export = feishu.get('export', {})

                    results.append({
                        'export_id': data.get('export_id', ''),
                        'project_name': project.get('project_name', ''),
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

    @app.route('/customer/api/projects', methods=['GET'])
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

            projects = []
            for row in rows:
                projects.append({
                    'id': row['id'],
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
                    'report_status': row['report_status'] or '',
                    'invoice_status': row['invoice_status'] or '',
                    'payment_status': row['payment_status'] or '',
                    'has_urge': row['has_urge'] if 'has_urge' in row.keys() else '',
                    'created_at': row['created_at'] or '',
                    'updated_at': row['updated_at'] or '',
                })

            return jsonify({'success': True, 'items': projects})
        finally:
            conn.close()

    @app.route('/customer/api/projects', methods=['POST'])
    @customer_required
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

    @app.route('/customer/api/projects/<int:project_id>/urge', methods=['POST'])
    @customer_required
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

            # 冷却期检查：24小时内同一项目同一类型不能重复催单
            cooldown_time = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
            recent = conn.execute(
                "SELECT id FROM project_urge_logs WHERE project_id = ? AND urge_type = ? AND created_at > ?",
                (project_id, urge_type, cooldown_time)
            ).fetchone()

            if recent:
                return jsonify({
                    'success': False,
                    'message': '您已在24小时内催过单，请耐心等待处理。'
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

            return jsonify({'success': True, 'message': message})
        finally:
            conn.close()

    # ==================== 投诉建议 API ====================

    @app.route('/customer/api/feedback', methods=['GET'])
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

    @app.route('/customer/api/feedback', methods=['POST'])
    @customer_required
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
