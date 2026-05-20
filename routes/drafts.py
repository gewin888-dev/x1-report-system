"""
X1 草稿管理路由 Blueprint
"""

import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user

from auth import require_permission, can_view_record
from database import get_db
from monitor import log_action
from config_loader import load_x1_config
from payload_normalizer import normalize_project_payload
from helpers.record_utils import (
    _x_now,
    _x_draft_path,
    _resolve_active_draft_id,
    _delete_draft_file_if_exists,
)

# ============================================================
# Blueprint 定义
# ============================================================

drafts_bp = Blueprint('drafts', __name__)

# ============================================================
# 路径常量（与 app_x1.py 保持一致）
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CFG = load_x1_config(BASE_DIR)
PATHS = CFG.get('paths', {})
RECORDS_DIR = BASE_DIR / PATHS.get('records', 'records_x1')
REPORTS_DIR = BASE_DIR / PATHS.get('reports', 'reports_x1')


def _x_export_path(export_id: str) -> Path:
    """导出记录路径"""
    return REPORTS_DIR / f"{export_id}.json"


# ============================================================
# /api/x/transfer_draft - 转让草稿
# ============================================================

@drafts_bp.route('/api/x/transfer_draft', methods=['POST'])
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


# ============================================================
# /api/x/save_draft - 保存草稿
# ============================================================

@drafts_bp.route('/api/x/save_draft', methods=['POST'])
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


# ============================================================
# /api/x/list_drafts - 列出草稿
# ============================================================

@drafts_bp.route('/api/x/list_drafts')
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


# ============================================================
# /api/x/load_draft/<draft_id> - 加载草稿
# ============================================================

@drafts_bp.route('/api/x/load_draft/<draft_id>')
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


# ============================================================
# /api/save_draft - 兼容旧客户端保存
# ============================================================

@drafts_bp.route('/api/save_draft', methods=['POST'])
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


# ============================================================
# /api/load_draft/<draft_id> - 兼容旧客户端加载
# ============================================================

@drafts_bp.route('/api/load_draft/<draft_id>')
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


# ============================================================
# /api/get/<record_id> - 兼容旧客户端记录加载
# ============================================================

@drafts_bp.route('/api/get/<record_id>')
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
