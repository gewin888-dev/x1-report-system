"""
routes/records.py - 记录管理相关路由 Blueprint
从 app_x1.py 提取，保持原有逻辑不变。
"""

import json
import os
import time
from pathlib import Path
from datetime import datetime

from flask import Blueprint, jsonify, request, session as flask_session
from flask_login import login_required, current_user

from auth import require_role, require_permission, can_view_record
from database import get_db
from monitor import log_action
from config_loader import load_x1_config
from feishu_utils import resolve_feishu_upload_folder, upload_file_to_feishu
from helpers.record_utils import (
    _compute_record_asset_state, _soft_delete_record,
    _record_data_for_access_check, _can_access_file_by_name,
    cleanup_trash
)
from helpers.settings_utils import _setting_enabled

records_bp = Blueprint('records', __name__)

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent.parent
_CFG = load_x1_config(BASE_DIR)
_PATHS = _CFG.get('paths', {})
RECORDS_DIR = BASE_DIR / _PATHS.get('records', 'records_x1')
REPORTS_DIR = BASE_DIR / _PATHS.get('reports', 'reports_x1')


def _x_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _setting_enabled(key, fallback=False):
    """检查系统设置是否启用"""
    import sqlite3
    db_path = BASE_DIR / _PATHS.get('database', 'x1_data.db')
    if not db_path.exists():
        return fallback
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT value FROM system_settings WHERE key=?", (key,)).fetchone()
        conn.close()
        if row:
            import json as _json
            v = _json.loads(row['value']) if isinstance(row['value'], str) else row['value']
            if isinstance(v, dict):
                return bool(v.get('value', fallback))
            return bool(v)
    except Exception:
        pass
    return fallback


def _cleanup_trash(days=30):
    """清理 trash 目录中超过指定天数的文件"""
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
            except Exception:
                pass
    for d in sorted(trash_dir.rglob('*'), reverse=True):
        if d.is_dir() and not list(d.iterdir()):
            try:
                d.rmdir()
            except Exception:
                pass
    return {'deleted_count': deleted_count, 'freed_bytes': freed_bytes}


# ========== 记录列表 ==========

@records_bp.route('/admin/api/records')
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



# ========== 记录摘要统计 ==========

@records_bp.route('/admin/api/records/summary')
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



# ========== 删除/作废/批量操作 ==========

def admin_api_delete_record(record_id):
    """删除记录（软删除，移至 trash）"""
    if not _setting_enabled('security.allow_delete_record', True):
        return jsonify({'success': False, 'error': '系统设置已禁止删除记录'}), 403
    ok, msg = _soft_delete_record(record_id)
    if not ok:
        return jsonify({'success': False, 'error': msg}), 404
    log_action(current_user.id if current_user.is_authenticated else 'unknown', '删除记录', record_id, msg)
    return jsonify({'success': True, 'message': msg})



@records_bp.route('/admin/api/records/<record_id>/retry_feishu', methods=['POST'])
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


@records_bp.route('/api/void_export/<record_id>', methods=['POST'])
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


@records_bp.route('/admin/api/records/batch_delete', methods=['POST'])
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


@records_bp.route('/admin/api/trash_status')
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
