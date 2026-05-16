"""
routes/settings.py - 系统设置相关路由 Blueprint

从 app_x1.py 提取，保持原有逻辑不变。
"""

import json
import os
import shutil
import subprocess
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, redirect, current_app
from flask_login import login_required, current_user

from auth import require_role, require_permission
from config_loader import load_x1_config
from database import get_db
from feishu_utils import get_feishu_config, get_feishu_token, get_feishu_folder_meta
from monitor import log_action, get_system_health
from helpers.settings_utils import (
    _settings_defs, _setting_defs_map, _cast_setting_value,
    _load_system_settings, _setting_enabled, _save_feishu_config_from_settings,
    _get_settings_backup_dir, _is_allowed_backup_file, _guess_backup_version,
    _list_backup_files, _extract_backup_summary, _safe_rmtree,
    _get_listener_pid, _get_process_cwd, _health_json, _get_latest_backup
)

settings_bp = Blueprint('settings', __name__)

# ---------------------------------------------------------------------------
# 模块级变量 - 从项目配置加载
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CFG = load_x1_config(BASE_DIR)
APP_VERSION = CFG.get('version', 'UNKNOWN_VERSION')
APP_PORT = int(CFG.get('port', 8082))
APP_HOST = CFG.get('host', '127.0.0.1')
HOST_MODE = str(CFG.get('host_mode', 'desktop') or 'desktop').strip().lower()
ALLOWED_SETTINGS_BROWSE_ROOTS = [Path(BASE_DIR), Path.home()]

PATHS = CFG.get('paths', {})
LOGS_DIR = BASE_DIR / PATHS.get('logs', 'logs_x1')


def _resolve_browse_path(path_str: str) -> Path:
    raw = (path_str or '').strip()
    candidate = Path(raw).expanduser().resolve() if raw else BASE_DIR.resolve()
    for root in ALLOWED_SETTINGS_BROWSE_ROOTS:
        try:
            candidate.relative_to(root.resolve())
            return candidate
        except Exception:
            continue
    return ALLOWED_SETTINGS_BROWSE_ROOTS[0].resolve()


def _is_desktop_mode() -> bool:
    return HOST_MODE == 'desktop'


# ---------------------------------------------------------------------------
# 路由
# ---------------------------------------------------------------------------

@settings_bp.route('/admin/settings')
@login_required
@require_role('admin')
def admin_settings_page():
    return redirect('/admin')


@settings_bp.route('/admin/api/settings')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings():
    values = _load_system_settings()
    groups = {
        'basic': {'title':'基础信息','items':[]},
        'paths': {'title':'路径设置','items':[]},
        'archive': {'title':'正式归档设置','items':[]},
        'export': {'title':'模板与导出设置','items':[]},
        'template': {'title':'模板与导出设置','items':[]},
        'feishu': {'title':'飞书与外部集成设置','items':[]},
        'security': {'title':'权限与安全设置','items':[]},
        'ops': {'title':'运行与维护设置','items':[]},
    }
    for item in values.values():
        groups.setdefault(item['group'], {'title':item['group'], 'items':[]})['items'].append(item)
    basic_items = [
        {'label':'系统名称','value':CFG.get('app_name','X1 检测记录系统'),'description':'显示当前系统名称，仅用于确认当前实例身份。'},
        {'label':'当前版本','value':CFG.get('version','-'),'description':'显示当前系统版本，用于迁移后核对部署版本是否正确。'},
        {'label':'当前主机名','value':os.uname().nodename,'description':'显示当前 macOS 主机名，迁移新服务器后应首先核对。'},
        {'label':'当前访问地址','value':f'{APP_HOST}:{APP_PORT}','description':'显示当前服务监听地址与端口，用于确认浏览器访问入口。'},
        {'label':'配置文件路径','value':str(BASE_DIR / 'x1_config.json'),'description':'显示当前基础配置文件位置，便于排障和迁移核对。'},
        {'label':'飞书配置状态','value':'已配置' if get_feishu_config() else '未配置','description':'用于快速判断移机后飞书配置是否已落地。'},
        {'label':'部署形态','value':'固定 macOS 主机 + 浏览器访问','description':'当前正式主路线，不再以每人本地安装客户端作为主思路。'},
        {'label':'系统设置权限','value':'仅 admin 可查看和修改','description':'系统设置涉及高风险运行参数，当前已收紧为 admin 独占。'},
        {'label':'文档主入口','value':'X1 最终交付汇报摘要 / X1 交付总览入口（总监版）','description':'后台系统文档区优先阅读的两份 A 类活文档。'},
        {'label':'当前治理重点','value':'系统设置 V2 / 权限安全收口 / 统一部署迁移治理','description':'根据当前后台系统文档与近期执行面整理出的实时重点。'},
    ]
    groups['basic']['items'] = basic_items
    return jsonify({'success': True, 'groups': groups})


@settings_bp.route('/admin/api/settings', methods=['PUT'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_update():
    data = request.get_json(silent=True) or {}
    updates = data.get('updates') or {}
    defs = _setting_defs_map()
    now = datetime.now().isoformat()
    changed = []
    with get_db() as conn:
        for key, value in updates.items():
            if key not in defs:
                continue
            item = defs[key]
            casted = _cast_setting_value(value, item['type'])
            if key == 'feishu.app_secret' and str(casted).strip() == '********':
                continue
            conn.execute(
                '''INSERT INTO system_settings (setting_key, setting_value, value_type, group_name, description, requires_restart, is_sensitive, updated_at, updated_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(setting_key) DO UPDATE SET setting_value=excluded.setting_value, value_type=excluded.value_type, group_name=excluded.group_name,
                   description=excluded.description, requires_restart=excluded.requires_restart, is_sensitive=excluded.is_sensitive, updated_at=excluded.updated_at, updated_by=excluded.updated_by''',
                (key, json.dumps(casted, ensure_ascii=False) if item['type']=='bool' else str(casted), item['type'], item['group'], item['description'], 1 if item['requires_restart'] else 0, 1 if item['sensitive'] else 0, now, current_user.id)
            )
            changed.append({'key': key, 'value': casted})
    if changed:
        _save_feishu_config_from_settings(updates)
        log_action(current_user.id, '更新系统设置', 'system_settings', json.dumps(changed, ensure_ascii=False))
    return jsonify({'success': True, 'changed': changed})


@settings_bp.route('/admin/api/settings/path_probe', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_path_probe():
    values = _load_system_settings()
    targets = [
        ('模板根目录', values['paths.template_base']['value']),
        ('正式检测报告归档目录', values['paths.formal_report_archive']['value']),
        ('正式原始记录归档目录', values['paths.formal_raw_archive']['value']),
        ('备份目录', values['paths.backup_dir']['value']),
        ('日志目录', values['paths.logs_dir']['value']),
        ('缓存目录', values['paths.cache_dir']['value']),
        ('临时目录', values['paths.temp_dir']['value']),
    ]
    result = []
    for label, path in targets:
        p = Path(str(path)).expanduser()
        result.append({'label': label, 'path': str(p), 'exists': p.exists(), 'readable': os.access(p, os.R_OK) if p.exists() else False, 'writable': os.access(p, os.W_OK) if p.exists() else False})
    log_action(current_user.id, '执行路径巡检', 'system_settings', json.dumps(result, ensure_ascii=False))
    return jsonify({'success': True, 'results': result})


@settings_bp.route('/admin/api/settings/ensure_path', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_ensure_path():
    data = request.get_json(silent=True) or {}
    key = str(data.get('key', '')).strip()
    values = _load_system_settings()
    item = values.get(key)
    if not item:
        return jsonify({'success': False, 'error': '配置项不存在'}), 404
    path = Path(str(item['value'])).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    log_action(current_user.id, '创建系统设置目录', key, str(path))
    return jsonify({'success': True, 'path': str(path)})


@settings_bp.route('/admin/api/settings/test_feishu', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_test_feishu():
    cfg = get_feishu_config() or {}
    token = get_feishu_token()
    reports_token = bool((cfg.get('folders') or {}).get('reports'))
    exports_token = bool((cfg.get('folders') or {}).get('exports'))
    reports_meta = get_feishu_folder_meta('reports') if token and reports_token else {'mode': 'missing'}
    exports_meta = get_feishu_folder_meta('exports') if token and exports_token else {'mode': 'missing'}
    reports_folder_ok = bool(reports_meta.get('resolved_token')) if token and reports_token else False
    exports_folder_ok = bool(exports_meta.get('resolved_token')) if token and exports_token else False

    warnings = []
    if reports_meta.get('mode') == 'year-root':
        warnings.append('检测报告目录当前仍为按年模式；如需按月自动切换，请将 token 指向月目录父目录。')
    if exports_meta.get('mode') == 'year-root':
        warnings.append('原始记录目录当前仍为按年模式；如需按月自动切换，请将 token 指向月目录父目录。')
    if reports_meta.get('mode') == 'month-root' and not reports_meta.get('month_matches'):
        warnings.append(f"检测报告目录尚未命中本月目录 {reports_meta.get('current_month')}，系统将在首次上传时自动创建。")
    if exports_meta.get('mode') == 'month-root' and not exports_meta.get('month_matches'):
        warnings.append(f"原始记录目录尚未命中本月目录 {exports_meta.get('current_month')}，系统将在首次上传时自动创建。")

    result = {
        'has_app_id': bool(cfg.get('app_id')),
        'has_app_secret': bool(cfg.get('app_secret')),
        'has_reports_folder': reports_token,
        'has_exports_folder': exports_token,
        'token_ok': bool(token),
        'reports_folder_ok': reports_folder_ok,
        'exports_folder_ok': exports_folder_ok,
        'reports_meta': reports_meta,
        'exports_meta': exports_meta,
        'warnings': warnings,
        'message': '飞书配置有效' if (token and reports_folder_ok and exports_folder_ok) else '飞书配置未完全通过，请检查凭证与目录 token'
    }
    log_action(current_user.id, '测试飞书配置', 'system_settings', json.dumps(result, ensure_ascii=False))
    return jsonify({'success': True, 'result': result})


@settings_bp.route('/admin/api/settings/browse_path')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings_browse_path():
    path = _resolve_browse_path(request.args.get('path', ''))
    parent = str(path.parent) if path != path.parent else str(path)
    entries = []
    try:
        for child in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            if child.name.startswith('.'):
                continue
            if not child.is_dir():
                continue
            entries.append({'name': child.name, 'path': str(child), 'writable': os.access(child, os.W_OK)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    return jsonify({'success': True, 'current_path': str(path), 'parent_path': parent, 'entries': entries, 'roots': [str(p) for p in ALLOWED_SETTINGS_BROWSE_ROOTS]})


@settings_bp.route('/admin/api/settings/native_choose_path', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_native_choose_path():
    if not _is_desktop_mode():
        return jsonify({'success': False, 'error': '当前为 server 模式，已禁用原生目录选择器；请改用手动填写或路径浏览器'}), 409
    script = 'POSIX path of (choose folder with prompt "请选择系统设置要使用的目录")'
    try:
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True, timeout=120)
    except Exception as e:
        return jsonify({'success': False, 'error': f'原生路径选择器执行失败: {e}'}), 500
    if result.returncode != 0:
        stderr = (result.stderr or '').strip()
        if '-128' in stderr:
            return jsonify({'success': False, 'cancelled': True, 'error': '已取消选择'}), 400
        return jsonify({'success': False, 'error': stderr or '原生路径选择失败'}), 500
    selected = (result.stdout or '').strip()
    if not selected:
        return jsonify({'success': False, 'error': '未返回路径'}), 500
    resolved = _resolve_browse_path(selected)
    return jsonify({'success': True, 'path': str(resolved)})


@settings_bp.route('/admin/api/settings/create_subdir', methods=['POST'])
@login_required
@require_permission('admin.settings.edit')
def admin_api_settings_create_subdir():
    data = request.get_json(silent=True) or {}
    base_path = _resolve_browse_path(data.get('base_path', ''))
    name = str(data.get('name', '')).strip()
    if not name or any(x in name for x in ('/', '\\', '..')):
        return jsonify({'success': False, 'error': '目录名称不合法'}), 400
    target = base_path / name
    target.mkdir(parents=False, exist_ok=True)
    log_action(current_user.id, '创建子目录', 'system_settings', str(target))
    return jsonify({'success': True, 'path': str(target)})


@settings_bp.route('/admin/api/settings/backup_now', methods=['POST'])
@login_required
@require_permission('admin.maintenance.run')
def admin_api_settings_backup_now():
    values = _load_system_settings()
    data = request.get_json(silent=True) or {}
    backup_dir = Path(str(values['paths.backup_dir']['value'])).expanduser()
    backup_dir.mkdir(parents=True, exist_ok=True)

    version = str(CFG.get('version', APP_VERSION)).strip() or APP_VERSION
    version_updated = False
    if data.get('updateVersion'):
        new_version = str(data.get('version', '') or '').strip()
        if not new_version:
            return jsonify({'success': False, 'error': '版本号不能为空'}), 400
        CFG['version'] = new_version
        cfg_path = BASE_DIR / 'x1_config.json'
        try:
            with open(cfg_path, 'w', encoding='utf-8') as f:
                json.dump(CFG, f, ensure_ascii=False, indent=2)
            version = new_version
            version_updated = True
        except Exception as e:
            return jsonify({'success': False, 'error': f'更新版本号失败: {e}'}), 500

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = str(data.get('backupName', '') or '').strip() if data.get('updateVersion') else ''
    if backup_name:
        safe_name = ''.join(ch if ch.isalnum() or ch in ('-','_') else '_' for ch in backup_name)
    else:
        safe_name = f'X1_{version}_manual_backup'
    backup_file = backup_dir / f'{safe_name}_{ts}.tar.gz'
    import tarfile as _tarfile
    with _tarfile.open(backup_file, 'w:gz') as tar:
        tar.add(str(BASE_DIR), arcname=BASE_DIR.name)
    log_action(current_user.id, '执行立即备份', 'system_settings', str(backup_file))
    return jsonify({'success': True, 'backup_file': str(backup_file), 'size': backup_file.stat().st_size, 'version_updated': version_updated, 'version': version})


@settings_bp.route('/admin/api/settings/backups')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings_backups():
    return jsonify({'success': True, 'items': _list_backup_files(), 'backup_dir': str(_get_settings_backup_dir())})


@settings_bp.route('/admin/api/settings/backups/<path:name>')
@login_required
@require_permission('admin.settings.view')
def admin_api_settings_backup_detail(name):
    backup_path = (_get_settings_backup_dir() / Path(name).name)
    if not _is_allowed_backup_file(backup_path):
        return jsonify({'success': False, 'error': '备份文件不存在或不在允许目录中'}), 404
    summary = _extract_backup_summary(backup_path)
    return jsonify({'success': True, 'name': backup_path.name, 'size': backup_path.stat().st_size, 'mtime': datetime.fromtimestamp(backup_path.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'), 'version_guess': _guess_backup_version(backup_path.name), 'summary': summary})


@settings_bp.route('/admin/api/settings/restore/full', methods=['POST'])
@login_required
@require_permission('admin.maintenance.run')
def admin_api_settings_restore_full():
    data = request.get_json(silent=True) or {}
    backup_name = Path(str(data.get('backup_name', '') or '').strip()).name
    confirm = str(data.get('confirm', '') or '').strip()
    if confirm != 'RESTORE':
        return jsonify({'success': False, 'error': '确认词不正确'}), 400
    if not backup_name:
        return jsonify({'success': False, 'error': '缺少备份名称'}), 400

    backup_path = _get_settings_backup_dir() / backup_name
    if not _is_allowed_backup_file(backup_path):
        return jsonify({'success': False, 'error': '备份文件不存在或不在允许目录中'}), 404

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    snapshot_dir = _get_settings_backup_dir() / f'pre_restore_snapshot_{ts}'
    renamed_dir = BASE_DIR.parent / f'{BASE_DIR.name}_before_restore_{ts}'
    temp_extract_dir = Path(tempfile.mkdtemp(prefix='x1_restore_', dir=str(_get_settings_backup_dir())))
    restore_log = LOGS_DIR / f'manual_restore_{ts}.log'
    kept_dirs = ['records_x1', 'reports_x1', 'uploads_x1', 'logs', 'logs_x1']
    rebuilt_dirs = ['cache_x1', 'temp_x1']

    def _w(line: str):
        restore_log.parent.mkdir(parents=True, exist_ok=True)
        with open(restore_log, 'a', encoding='utf-8') as f:
            f.write(line.rstrip() + '\n')

    try:
        _w(f'[{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}] operator={current_user.id} backup={backup_path}')
        snapshot_dir.mkdir(parents=True, exist_ok=False)
        shutil.copytree(BASE_DIR, snapshot_dir / BASE_DIR.name)
        _w(f'snapshot={snapshot_dir / BASE_DIR.name}')

        with tarfile.open(backup_path, 'r:gz') as tf:
            tf.extractall(temp_extract_dir)
        roots = [p for p in temp_extract_dir.iterdir() if p.is_dir()]
        if not roots:
            raise RuntimeError('备份包解压后未找到项目目录')
        extracted_root = min(roots, key=lambda p: len(str(p)))

        for d in kept_dirs:
            src = BASE_DIR / d
            if src.exists():
                shutil.copytree(src, temp_extract_dir / '__kept__' / d)
        _w(f'kept_dirs={kept_dirs}')

        os.rename(BASE_DIR, renamed_dir)
        os.rename(extracted_root, BASE_DIR)
        _w(f'renamed_old={renamed_dir}')

        kept_root = temp_extract_dir / '__kept__'
        for d in kept_dirs:
            src = kept_root / d
            dst = BASE_DIR / d
            if dst.exists():
                _safe_rmtree(dst) if dst.is_dir() else dst.unlink()
            if src.exists():
                shutil.copytree(src, dst)
        for d in rebuilt_dirs:
            dst = BASE_DIR / d
            if dst.exists():
                _safe_rmtree(dst)
            dst.mkdir(parents=True, exist_ok=True)

        restart_script = BASE_DIR / 'restart_x1_daemon.sh'
        restart_proc = subprocess.run([str(restart_script)], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=180)
        listener_pid = _get_listener_pid(APP_PORT)
        listener_cwd = _get_process_cwd(listener_pid)
        health = _health_json()
        health_ok = bool(health.get('success'))
        cwd_ok = str(listener_cwd).strip() == str(BASE_DIR)
        restart_ok = restart_proc.returncode == 0
        _w(f'restart_rc={restart_proc.returncode}')
        if restart_proc.stdout:
            _w('restart_stdout_begin')
            _w(restart_proc.stdout)
            _w('restart_stdout_end')
        if restart_proc.stderr:
            _w('restart_stderr_begin')
            _w(restart_proc.stderr)
            _w('restart_stderr_end')
        _w(f'listener_pid={listener_pid}')
        _w(f'listener_cwd={listener_cwd}')
        _w(f'health_after_restore={json.dumps(health, ensure_ascii=False)}')

        result_payload = {
            'backup_name': backup_path.name,
            'snapshot_path': str(snapshot_dir / BASE_DIR.name),
            'renamed_dir': str(renamed_dir),
            'kept_dirs': kept_dirs,
            'rebuilt_dirs': rebuilt_dirs,
            'log_path': str(restore_log),
            'health': health,
            'version': load_x1_config(BASE_DIR).get('version', APP_VERSION),
            'restart_rc': restart_proc.returncode,
            'listener_pid': listener_pid,
            'listener_cwd': listener_cwd,
            'port': APP_PORT,
            'restart_stdout': (restart_proc.stdout or '')[-4000:]
        }

        if not restart_ok:
            log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'restart_failed'}, ensure_ascii=False))
            return jsonify({'success': False, 'error': '还原完成，但自动重启失败', **result_payload}), 500
        if not health_ok:
            log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'health_failed'}, ensure_ascii=False))
            return jsonify({'success': False, 'error': '还原完成，但健康检查失败', **result_payload}), 500
        if not cwd_ok:
            log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'cwd_mismatch'}, ensure_ascii=False))
            return jsonify({'success': False, 'error': '还原完成，但在线进程未切到新目录', **result_payload}), 500

        log_action(current_user.id, '执行整体还原', 'system_settings', json.dumps({**result_payload, 'result': 'success'}, ensure_ascii=False))
        return jsonify({'success': True, **result_payload})
    except Exception as e:
        _w(f'error={e}')
        return jsonify({'success': False, 'error': str(e), 'log_path': str(restore_log)}), 500
    finally:
        try:
            _safe_rmtree(temp_extract_dir)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# 系统健康检查 (放在 settings blueprint 中)
# ---------------------------------------------------------------------------

@settings_bp.route('/api/system/health')
@login_required
@require_role('admin')
def api_system_health():
    """系统健康状态"""
    from monitor import get_error_logs, get_performance_stats

    health = get_system_health()
    recent_errors = get_error_logs(limit=10)
    export_stats = get_performance_stats('export_report', hours=24)

    return jsonify({
        'success': True,
        'health': health,
        'recent_errors': recent_errors,
        'performance': {
            'export_report': export_stats
        }
    })
