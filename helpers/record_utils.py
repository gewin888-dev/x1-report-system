"""
record_utils.py - 记录/草稿相关辅助函数
从 app_x1.py 提取，保持原有逻辑不变。
"""

import json
import shutil
import time
from datetime import datetime
from pathlib import Path

from flask_login import current_user

from config_loader import load_x1_config
from auth import can_view_record

# ---------- 路径配置 ----------
BASE_DIR = Path(__file__).parent.parent
_CFG = load_x1_config(BASE_DIR)
_PATHS = _CFG.get('paths', {})
RECORDS_DIR = BASE_DIR / _PATHS.get('records', 'records_x1')
REPORTS_DIR = BASE_DIR / _PATHS.get('reports', 'reports_x1')


# ---------- 资产状态计算 ----------

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


# ---------- 软删除 ----------

def _soft_delete_record(record_id):
    """软删除记录（移到 trash 目录）"""
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


# ---------- 访问控制辅助 ----------

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


# ---------- 回收站清理 ----------

def cleanup_trash(days=30):
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


# ---------- 草稿工具函数 ----------

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
