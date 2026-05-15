"""
客户管理后台 API —— 给 admin 面板用的客户管理接口
"""
from flask import request, jsonify
from flask_login import current_user, login_required
from auth import require_permission
from datetime import datetime
import sqlite3, json
from pathlib import Path

BASE_DIR = Path(__file__).parent


# _admin_required 已废弃，统一使用 require_permission


def _get_x1_conn():
    db_path = BASE_DIR / 'data' / 'x1_data.db'
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _get_user_conn():
    from database import get_db
    return get_db()


def register_customer_admin_routes(app):
    """注册客户管理后台路由"""

    # ──────────────────────────────────────────────
    # 1. 客户列表（聚合视图）
    # ──────────────────────────────────────────────
    @app.route('/admin/api/customer_management/list')
    @login_required
    @require_permission('admin.customers.view')
    def customer_mgmt_list():
        """
        聚合客户信息：
        - 从 business_projects 提取所有不重复的 client_name
        - 关联 client_profiles 的开票/收件信息
        - 关联 users 的客户账号
        - 统计项目数、合同总额、已收款、应收款、催单数、反馈数
        """
        conn = _get_x1_conn()
        try:
            # 获取所有有项目的客户
            rows = conn.execute("""
                SELECT client_name,
                       COUNT(*) as project_count,
                       SUM(COALESCE(contract_amount, 0)) as total_contract,
                       SUM(COALESCE(paid_amount, 0)) as total_paid,
                       MAX(created_at) as last_project_date,
                       GROUP_CONCAT(DISTINCT detection_domain) as domains
                FROM business_projects
                WHERE client_name IS NOT NULL AND client_name != ''
                GROUP BY client_name
                ORDER BY last_project_date DESC
            """).fetchall()

            # 获取 client_profiles
            profiles = {}
            for r in conn.execute("SELECT * FROM client_profiles").fetchall():
                profiles[r['client_name']] = dict(r)

            # 获取催单统计
            urge_stats = {}
            for r in conn.execute("""
                SELECT client_name, COUNT(*) as cnt
                FROM project_urge_logs
                GROUP BY client_name
            """).fetchall():
                urge_stats[r['client_name']] = r['cnt']

            # 获取反馈统计
            feedback_stats = {}
            pending_feedback = {}
            for r in conn.execute("""
                SELECT client_name,
                       COUNT(*) as total,
                       SUM(CASE WHEN status='待处理' THEN 1 ELSE 0 END) as pending
                FROM client_feedback
                GROUP BY client_name
            """).fetchall():
                feedback_stats[r['client_name']] = r['total']
                pending_feedback[r['client_name']] = r['pending']

            # 获取客户账号
            try:
                with _get_user_conn() as uconn:
                    user_map = {}
                    ucols = {r['name'] for r in uconn.execute("PRAGMA table_info(users)").fetchall()}
                    if 'client_name' in ucols:
                        for r in uconn.execute(
                            "SELECT user_id, display_name, client_name FROM users WHERE role='customer' AND client_name != ''"
                        ).fetchall():
                            user_map[r['client_name']] = {
                                'user_id': r['user_id'],
                                'display_name': r['display_name']
                            }
            except Exception:
                user_map = {}

            # 也收集 profiles 中有但没有项目的客户
            profile_only_names = set(profiles.keys()) - {r['client_name'] for r in rows}

            items = []
            for r in rows:
                cn = r['client_name']
                receivable = round((r['total_contract'] or 0) - (r['total_paid'] or 0), 2)
                profile = profiles.get(cn, {})
                items.append({
                    'client_name': cn,
                    'project_count': r['project_count'],
                    'total_contract': r['total_contract'] or 0,
                    'total_paid': r['total_paid'] or 0,
                    'receivable': receivable,
                    'last_project_date': (r['last_project_date'] or '')[:10],
                    'domains': r['domains'] or '',
                    'contact_name': profile.get('recipient_name', ''),
                    'contact_phone': profile.get('recipient_phone', ''),
                    'contact_address': profile.get('recipient_address', ''),
                    'has_account': cn in user_map,
                    'account_info': user_map.get(cn),
                    'urge_count': urge_stats.get(cn, 0),
                    'feedback_count': feedback_stats.get(cn, 0),
                    'pending_feedback': pending_feedback.get(cn, 0),
                    'has_profile': cn in profiles,
                })

            # 追加只有 profile 没有项目的客户
            for cn in profile_only_names:
                profile = profiles[cn]
                items.append({
                    'client_name': cn,
                    'project_count': 0,
                    'total_contract': 0,
                    'total_paid': 0,
                    'receivable': 0,
                    'last_project_date': '',
                    'domains': '',
                    'contact_name': profile.get('recipient_name', ''),
                    'contact_phone': profile.get('recipient_phone', ''),
                    'contact_address': profile.get('recipient_address', ''),
                    'has_account': cn in user_map,
                    'account_info': user_map.get(cn),
                    'urge_count': urge_stats.get(cn, 0),
                    'feedback_count': feedback_stats.get(cn, 0),
                    'pending_feedback': pending_feedback.get(cn, 0),
                    'has_profile': True,
                })

            # 汇总
            summary = {
                'total': len(items),
                'with_projects': sum(1 for x in items if x['project_count'] > 0),
                'pending_urge': sum(x['urge_count'] for x in items),
                'pending_feedback': sum(x['pending_feedback'] for x in items),
                'receivable_clients': sum(1 for x in items if x['receivable'] > 0),
            }

            return jsonify({'success': True, 'items': items, 'summary': summary})
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 2. 客户详情
    # ──────────────────────────────────────────────
    @app.route('/admin/api/customer_management/detail')
    @login_required
    @require_permission('admin.customers.view')
    def customer_mgmt_detail():
        client_name = request.args.get('client_name', '').strip()
        if not client_name:
            return jsonify({'success': False, 'error': '缺少客户名称'}), 400

        conn = _get_x1_conn()
        try:
            # 基本信息 from client_profiles
            profile_row = conn.execute(
                "SELECT * FROM client_profiles WHERE client_name = ?", (client_name,)
            ).fetchone()
            profile = dict(profile_row) if profile_row else {
                'client_name': client_name,
                'invoice_company': '', 'invoice_tax_no': '',
                'invoice_address_phone': '', 'invoice_bank': '', 'invoice_bank_account': '',
                'recipient_name': '', 'recipient_phone': '', 'recipient_address': '',
            }

            # 项目列表
            projects = []
            for r in conn.execute(
                "SELECT id, project_no, project_name, detection_domain, detection_type, "
                "inspection_stage, report_status, invoice_status, contract_amount, paid_amount, "
                "has_urge, created_at, updated_at, source "
                "FROM business_projects WHERE client_name = ? ORDER BY updated_at DESC",
                (client_name,)
            ).fetchall():
                projects.append(dict(r))

            # 催单记录
            urge_logs = []
            for r in conn.execute(
                "SELECT * FROM project_urge_logs WHERE client_name = ? ORDER BY created_at DESC LIMIT 20",
                (client_name,)
            ).fetchall():
                urge_logs.append(dict(r))

            # 反馈记录
            feedbacks = []
            for r in conn.execute(
                "SELECT * FROM client_feedback WHERE client_name = ? ORDER BY created_at DESC",
                (client_name,)
            ).fetchall():
                feedbacks.append(dict(r))

            # 报告记录（扫描 reports_x1）
            reports = []
            reports_dir = BASE_DIR / 'reports_x1'
            if reports_dir.exists():
                for fp in sorted(reports_dir.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True):
                    try:
                        data = json.loads(fp.read_text(encoding='utf-8'))
                        ep = data.get('export_payload', {})
                        proj = ep.get('project', {})
                        if proj.get('client_name') == client_name:
                            reports.append({
                                'filename': fp.name,
                                'project_name': proj.get('name', ''),
                                'detection_type': ep.get('type_label', ''),
                                'report_no': proj.get('report_no', ''),
                                'export_time': data.get('export_time', ''),
                                'feishu_url': data.get('feishu_report_url', ''),
                            })
                    except Exception:
                        pass

            # 账号信息
            account = None
            try:
                with _get_user_conn() as uconn:
                    ucols = {r['name'] for r in uconn.execute("PRAGMA table_info(users)").fetchall()}
                    if 'client_name' in ucols:
                        arow = uconn.execute(
                            "SELECT user_id, display_name, is_active, last_login FROM users WHERE role='customer' AND client_name=?",
                            (client_name,)
                        ).fetchone()
                        if arow:
                            account = dict(arow)
            except Exception:
                pass

            return jsonify({
                'success': True,
                'profile': profile,
                'projects': projects,
                'urge_logs': urge_logs,
                'feedbacks': feedbacks,
                'reports': reports,
                'account': account,
            })
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 3. 更新客户信息（后台编辑 profile）
    # ──────────────────────────────────────────────
    @app.route('/admin/api/customer_management/profile', methods=['PUT'])
    @login_required
    @require_permission('admin.customers.manage')
    def customer_mgmt_update_profile():
        data = request.get_json() or {}
        client_name = data.get('client_name', '').strip()
        if not client_name:
            return jsonify({'success': False, 'error': '缺少客户名称'}), 400

        conn = _get_x1_conn()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            existing = conn.execute(
                "SELECT id FROM client_profiles WHERE client_name = ?", (client_name,)
            ).fetchone()

            fields = {
                'invoice_company': data.get('invoice_company', ''),
                'invoice_tax_no': data.get('invoice_tax_no', ''),
                'invoice_address_phone': data.get('invoice_address_phone', ''),
                'invoice_bank': data.get('invoice_bank', ''),
                'invoice_bank_account': data.get('invoice_bank_account', ''),
                'recipient_name': data.get('recipient_name', ''),
                'recipient_phone': data.get('recipient_phone', ''),
                'recipient_address': data.get('recipient_address', ''),
            }

            if existing:
                sets = ', '.join(f"{k} = ?" for k in fields)
                conn.execute(
                    f"UPDATE client_profiles SET {sets}, updated_at = ? WHERE client_name = ?",
                    list(fields.values()) + [now, client_name]
                )
            else:
                cols = ', '.join(['client_name'] + list(fields.keys()) + ['updated_at'])
                phs = ', '.join(['?'] * (len(fields) + 2))
                conn.execute(
                    f"INSERT INTO client_profiles ({cols}) VALUES ({phs})",
                    [client_name] + list(fields.values()) + [now]
                )
            conn.commit()
            return jsonify({'success': True, 'message': '客户信息已更新'})
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 4. 回复客户反馈
    # ──────────────────────────────────────────────
    @app.route('/admin/api/customer_management/feedback/<int:feedback_id>/reply', methods=['PUT'])
    @login_required
    @require_permission('admin.customers.manage')
    def customer_mgmt_reply_feedback(feedback_id):
        data = request.get_json() or {}
        reply = data.get('reply', '').strip()
        status = data.get('status', '已处理')
        if not reply:
            return jsonify({'success': False, 'error': '回复内容不能为空'}), 400

        conn = _get_x1_conn()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            conn.execute(
                "UPDATE client_feedback SET reply = ?, status = ?, updated_at = ? WHERE id = ?",
                (reply, status, now, feedback_id)
            )
            conn.commit()
            return jsonify({'success': True, 'message': '已回复'})
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 5. 新增客户（后台手动创建 profile）
    # ──────────────────────────────────────────────
    @app.route('/admin/api/customer_management/create', methods=['POST'])
    @login_required
    @require_permission('admin.customers.manage')
    def customer_mgmt_create():
        data = request.get_json() or {}
        client_name = data.get('client_name', '').strip()
        if not client_name:
            return jsonify({'success': False, 'error': '客户名称不能为空'}), 400

        conn = _get_x1_conn()
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            existing = conn.execute(
                "SELECT id FROM client_profiles WHERE client_name = ?", (client_name,)
            ).fetchone()
            if existing:
                return jsonify({'success': False, 'error': '该客户已存在'}), 400

            conn.execute(
                "INSERT INTO client_profiles (client_name, recipient_name, recipient_phone, recipient_address, updated_at) VALUES (?, ?, ?, ?, ?)",
                (client_name,
                 data.get('recipient_name', ''),
                 data.get('recipient_phone', ''),
                 data.get('recipient_address', ''),
                 now)
            )
            conn.commit()
            return jsonify({'success': True, 'message': f'客户 {client_name} 已创建'})
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 6. 清除催单标记
    # ──────────────────────────────────────────────
    @app.route('/admin/api/customer_management/clear_urge/<int:project_id>', methods=['POST'])
    @login_required
    @require_permission('admin.customers.manage')
    def customer_mgmt_clear_urge(project_id):
        conn = _get_x1_conn()
        try:
            conn.execute("UPDATE business_projects SET has_urge = '' WHERE id = ?", (project_id,))
            conn.commit()
            return jsonify({'success': True, 'message': '催单标记已清除'})
        finally:
            conn.close()

    # ──────────────────────────────────────────────
    # 7. 删除客户
    # ──────────────────────────────────────────────
    @app.route('/admin/api/customer_management/delete', methods=['POST'])
    @login_required
    @require_permission('admin.customers.manage')
    def customer_mgmt_delete():
        data = request.get_json() or {}
        client_name = data.get('client_name', '').strip()
        if not client_name:
            return jsonify({'success': False, 'error': '缺少客户名称'}), 400

        conn = _get_x1_conn()
        try:
            # 检查是否有关联项目
            row = conn.execute(
                "SELECT COUNT(*) as cnt FROM business_projects WHERE client_name = ?",
                (client_name,)
            ).fetchone()
            project_count = row['cnt'] if row else 0

            if project_count > 0:
                return jsonify({
                    'success': False,
                    'error': f'该客户关联 {project_count} 个项目，不能直接删除。请先处理关联项目。'
                }), 400

            # 删除 profile
            conn.execute("DELETE FROM client_profiles WHERE client_name = ?", (client_name,))
            # 删除催单记录
            conn.execute("DELETE FROM project_urge_logs WHERE client_name = ?", (client_name,))
            # 删除反馈记录
            conn.execute("DELETE FROM client_feedback WHERE client_name = ?", (client_name,))
            conn.commit()
            return jsonify({'success': True, 'message': f'客户 {client_name} 已删除'})
        finally:
            conn.close()
