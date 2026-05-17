"""
settings_utils.py - 系统设置相关辅助函数

从 app_x1.py 提取，保持原有逻辑不变。
"""

import glob
import json
import os
import re
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

from config_loader import load_x1_config
from database import get_db
from feishu_utils import get_feishu_config
from monitor import get_system_health

# ---------------------------------------------------------------------------
# 全局变量占位 - 由调用方或初始化时注入
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CFG = load_x1_config(BASE_DIR)
APP_VERSION = CFG.get('version', 'UNKNOWN_VERSION')

TEMPLATE_BASE = Path(CFG.get('template_base', BASE_DIR / 'templates_report')).expanduser()
LOGS_DIR = Path(CFG.get('logs_dir', BASE_DIR / 'logs_x1')).expanduser()
CACHE_DIR = Path(CFG.get('cache_dir', BASE_DIR / 'cache_x1')).expanduser()
DEFAULT_ARCHIVE_ROOT = Path.home() / '公司资料' / '检测部'


# ---------------------------------------------------------------------------
# 设置定义
# ---------------------------------------------------------------------------

def _settings_defs():
    return [
        {'key':'paths.template_base','label':'模板根目录','type':'path','group':'paths','default':str(TEMPLATE_BASE),'suggested':'~/公司资料/检测部/检测报告模板','requires_restart':1,'sensitive':1,'impact':'修改后可能导致检测报告模板命中失败、正式报告生成异常或模板巡检结果失真。','description':'用于检测报告模板定位；迁移服务器后通常需要重新确认。'},
        {'key':'runtime.host_mode','label':'运行模式','type':'string','group':'basic','default':str(CFG.get('host_mode', 'desktop')),'requires_restart':1,'sensitive':0,'impact':'切换到 server 模式后，将禁用本机打开文件与部分桌面集成功能；切回 desktop 模式前需确认宿主机具备 GUI/WPS/Pages 能力。','description':'desktop=桌面办公机模式；server=服务器模式。迁移到无 GUI 主机时建议设为 server。'},
        {'key':'paths.formal_report_archive','label':'正式检测报告归档目录','type':'path','group':'archive','default':str(Path(os.path.expanduser(str((CFG.get('archive') or {}).get('formal_report_archive') or DEFAULT_ARCHIVE_ROOT / '检测报告')))),'suggested':'~/公司资料/检测部/检测报告','requires_restart':0,'sensitive':1,'impact':'修改后可能导致正式检测报告归档到错误目录，影响交付、查找与留档。','description':'检测报告最终正式归档位置；修改前请确认新目录可写。'},
        {'key':'paths.formal_raw_archive','label':'正式原始记录归档目录','type':'path','group':'archive','default':str(Path(os.path.expanduser(str((CFG.get('archive') or {}).get('formal_raw_archive') or DEFAULT_ARCHIVE_ROOT / '原始记录')))),'suggested':'~/公司资料/检测部/原始记录','requires_restart':0,'sensitive':1,'impact':'修改后可能导致原始记录归档错误，影响内部追溯、复核与年度存档。','description':'原始记录最终正式归档位置；迁移后应重新确认。'},
        {'key':'paths.backup_dir','label':'备份目录','type':'path','group':'paths','default':str(Path(os.path.expanduser('~/backups_x1'))),'suggested':'~/backups_x1','requires_restart':0,'sensitive':0,'description':'系统整体备份输出目录；建议放到稳定位置。'},
        {'key':'paths.logs_dir','label':'日志目录','type':'path','group':'paths','default':str(LOGS_DIR),'suggested':'./logs_x1','requires_restart':1,'sensitive':0,'description':'守护与应用日志目录；迁移后建议保留独立日志位置。'},
        {'key':'paths.cache_dir','label':'缓存目录','type':'path','group':'paths','default':str(CACHE_DIR),'suggested':'./cache_x1','requires_restart':1,'sensitive':0,'description':'缓存与中间结果目录；异常时可作为清理对象。'},
        {'key':'paths.temp_dir','label':'临时目录','type':'path','group':'paths','default':str(BASE_DIR / 'tmp_x1'),'suggested':'./tmp_x1','requires_restart':1,'sensitive':0,'description':'中间处理临时目录；建议与正式归档目录分开。'},
        {'key':'export.enable_report_docx','label':'启用检测报告导出','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'description':'关闭后将停止检测报告 Word 导出链，仅用于特殊维护。'},
        {'key':'export.enable_raw_record','label':'启用原始记录导出','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'description':'关闭后将停止原始记录导出链，仅用于特殊维护。'},
        {'key':'template.enable_gate','label':'启用模板命中闸门','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'impact':'关闭后会放松正式检测报告模板约束，可能让未命中模板的报告继续流转，带来版式或对象映射风险。','description':'控制检测报告是否必须先命中合法模板，正式环境建议开启。'},
        {'key':'template.gate_mode','label':'模板命中模式','type':'string','group':'export','default':'strict','requires_restart':0,'sensitive':1,'impact':'从严格切到宽松后，可能放过口径不完整或模板映射异常的对象。','description':'严格模式要求符合模板规则；宽松模式仅用于排障。'},
        {'key':'template.allow_upload','label':'允许模板上传','type':'bool','group':'export','default':True,'requires_restart':0,'sensitive':1,'impact':'开启模板上传会增加模板被替换风险；关闭则会限制后台模板维护能力。','description':'控制后台是否允许上传/替换模板；正式环境建议谨慎开启。'},
        {'key':'feishu.enabled','label':'启用飞书上传','type':'bool','group':'feishu','default':True,'requires_restart':0,'sensitive':1,'impact':'关闭后导出文件将不再自动上传飞书，可能影响客户交付与内部同步。','description':'控制是否执行飞书上传主链；迁移后应先确认配置状态。'},
        {'key':'feishu.app_id','label':'飞书 App ID','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'impact':'修改错误会导致飞书认证失败，自动上传链路中断。','description':'飞书开放平台应用 App ID；保存后不会在页面明文回显。'},
        {'key':'feishu.app_secret','label':'飞书 App Secret','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'impact':'修改错误会导致飞书 token 获取失败，自动上传完全不可用。','description':'飞书开放平台应用密钥；仅支持重新填写，不做明文展示。'},
        {'key':'feishu.folder_reports','label':'飞书检测报告目录 Token','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'description':'检测报告上传父目录 token；迁移后需重新核对。'},
        {'key':'feishu.folder_exports','label':'飞书原始记录目录 Token','type':'string','group':'feishu','default':'','requires_restart':0,'sensitive':1,'description':'原始记录上传父目录 token；迁移后需重新核对。'},
        {'key':'feishu.auto_upload_report','label':'检测报告自动上传飞书','type':'bool','group':'feishu','default':True,'requires_restart':0,'sensitive':0,'description':'检测报告成功生成后是否自动上传到飞书。'},
        {'key':'feishu.auto_upload_raw','label':'原始记录自动上传飞书','type':'bool','group':'feishu','default':True,'requires_restart':0,'sensitive':0,'description':'原始记录成功生成后是否自动上传到飞书。'},
        {'key':'security.session_cookie_secure','label':'启用 Secure Cookie','type':'bool','group':'security','default':bool(CFG.get('session_cookie_secure', False)),'requires_restart':1,'sensitive':1,'impact':'在 HTTP 环境误开启可能导致会话异常；关闭则会降低 HTTPS 环境下的会话安全性。','description':'正式 HTTPS 部署建议开启；纯局域网 HTTP 环境需谨慎。'},
        {'key':'security.allow_delete_record','label':'允许删除记录','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':1,'impact':'开启后用户可删除记录；关闭则会影响后台治理效率但能保护正式数据。','description':'关闭后记录删除相关操作将被阻止，用于保护正式数据。'},
        {'key':'security.allow_cleanup_trash','label':'允许清空回收站','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':1,'impact':'开启后可能发生不可恢复删除；关闭则会阻止永久清理。','description':'关闭后将禁止永久清理回收站，降低不可恢复删除风险。'},
        {'key':'security.allow_file_preview','label':'允许文件预览','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':0,'description':'控制后台文件预览入口；关闭可缩小暴露面。'},
        {'key':'security.allow_file_download','label':'允许文件下载','type':'bool','group':'security','default':True,'requires_restart':0,'sensitive':0,'description':'控制本地文件下载能力；建议结合角色权限一起使用。'},
        {'key':'ops.log_retention_days','label':'日志保留天数','type':'int','group':'ops','default':30,'requires_restart':0,'sensitive':0,'description':'超过保留期的日志可纳入清理策略，避免长期堆积。'},
        {'key':'ops.trash_retention_days','label':'回收站保留天数','type':'int','group':'ops','default':30,'requires_restart':0,'sensitive':0,'description':'控制回收站默认保留时长，平衡恢复能力与磁盘占用。'},
    ]


def _setting_defs_map():
    return {item['key']: item for item in _settings_defs()}


def _cast_setting_value(value, value_type):
    if value_type == 'bool':
        return bool(value) if isinstance(value, bool) else str(value).strip().lower() in ('1','true','yes','on')
    if value_type == 'int':
        return int(value)
    return '' if value is None else str(value)


def _load_system_settings():
    defs = _settings_defs()
    values = {}
    feishu_cfg = get_feishu_config() or {}
    feishu_folders = feishu_cfg.get('folders', {}) if isinstance(feishu_cfg.get('folders'), dict) else {}
    with get_db() as conn:
        rows = conn.execute('SELECT * FROM system_settings').fetchall()
    row_map = {row['setting_key']: row for row in rows}
    for item in defs:
        row = row_map.get(item['key'])
        raw_value = row['setting_value'] if row else item['default']
        if item['key'] == 'feishu.app_id':
            raw_value = feishu_cfg.get('app_id', '')
        elif item['key'] == 'feishu.app_secret':
            raw_value = '********' if feishu_cfg.get('app_secret') else ''
        elif item['key'] == 'feishu.folder_reports':
            raw_value = feishu_folders.get('reports', '')
        elif item['key'] == 'feishu.folder_exports':
            raw_value = feishu_folders.get('exports', '')
        if row and item['type'] == 'bool':
            try:
                raw_value = json.loads(raw_value)
            except Exception:
                pass
        values[item['key']] = {
            'key': item['key'],
            'label': item['label'],
            'group': item['group'],
            'type': item['type'],
            'value': _cast_setting_value(raw_value, item['type']),
            'default': item['default'],
            'suggested': item.get('suggested', ''),
            'requires_restart': bool(item['requires_restart']),
            'is_sensitive': bool(item['sensitive']),
            'description': item['description'],
            'impact': item.get('impact', ''),
            'updated_at': row['updated_at'] if row else '',
            'updated_by': row['updated_by'] if row else '',
        }
        if item['type'] == 'path':
            p = Path(str(values[item['key']]['value'])).expanduser()
            values[item['key']]['path_status'] = {
                'exists': p.exists(),
                'readable': os.access(p, os.R_OK) if p.exists() else False,
                'writable': os.access(p, os.W_OK) if p.exists() else False,
                'is_dir': p.is_dir() if p.exists() else False,
            }
    return values


def _setting_enabled(key, fallback=False):
    try:
        values = _load_system_settings()
        if key in values:
            return bool(values[key]['value'])
    except Exception:
        pass
    return fallback


def _save_feishu_config_from_settings(updates):
    if not any(k in updates for k in ('feishu.app_id', 'feishu.app_secret', 'feishu.folder_reports', 'feishu.folder_exports')):
        return
    config_path = BASE_DIR / 'feishu_config.json'
    current = get_feishu_config() or {}
    folders = current.get('folders', {}) if isinstance(current.get('folders'), dict) else {}
    app_secret = current.get('app_secret', '')
    if updates.get('feishu.app_secret') and str(updates.get('feishu.app_secret')).strip() != '********':
        app_secret = str(updates.get('feishu.app_secret')).strip()
    current.update({
        'app_id': str(updates.get('feishu.app_id', current.get('app_id', ''))).strip(),
        'app_secret': app_secret,
        'folders': {
            'reports': str(updates.get('feishu.folder_reports', folders.get('reports', ''))).strip(),
            'exports': str(updates.get('feishu.folder_exports', folders.get('exports', ''))).strip(),
        }
    })
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(current, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# 备份相关
# ---------------------------------------------------------------------------

def _get_settings_backup_dir() -> Path:
    settings_values = _load_system_settings()
    return Path(str(settings_values.get('paths.backup_dir', {}).get('value', BASE_DIR / 'backups'))).expanduser()


def _is_allowed_backup_file(path: Path) -> bool:
    try:
        backup_dir = _get_settings_backup_dir().resolve()
        path.resolve().relative_to(backup_dir)
        return path.is_file() and path.name.endswith('.tar.gz')
    except Exception:
        return False


def _guess_backup_version(name: str) -> str:
    m = re.search(r'(X\d+(?:\.\d+)*)', name or '')
    return m.group(1) if m else ''


def _list_backup_files():
    backup_dir = _get_settings_backup_dir()
    backup_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for fp in sorted(backup_dir.glob('*.tar.gz'), key=lambda p: p.stat().st_mtime, reverse=True):
        items.append({
            'name': fp.name,
            'path': str(fp),
            'size': fp.stat().st_size,
            'mtime': datetime.fromtimestamp(fp.stat().st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
            'version_guess': _guess_backup_version(fp.name),
            'restorable': True,
            'type': 'full_backup'
        })
    return items


def _extract_backup_summary(backup_path: Path):
    root_names = []
    has = {'app_x1.py': False, 'static/record.js': False, 'templates/record_index.html': False, 'x1_config.json': False}
    try:
        with tarfile.open(backup_path, 'r:gz') as tf:
            members = tf.getmembers()
            for m in members[:5000]:
                parts = [x for x in (m.name or '').split('/') if x]
                if parts:
                    root = parts[0]
                    if root not in root_names:
                        root_names.append(root)
                norm = '/'.join(parts[1:]) if len(parts) > 1 else (parts[0] if parts else '')
                if norm in has:
                    has[norm] = True
    except Exception as e:
        return {'ok': False, 'error': str(e), 'root_names': root_names, 'checks': has}
    return {'ok': True, 'root_names': root_names, 'checks': has}


def _safe_rmtree(path: Path):
    if path.exists():
        shutil.rmtree(path)


# ---------------------------------------------------------------------------
# 进程与健康检查
# ---------------------------------------------------------------------------

def _get_listener_pid(port: int):
    try:
        out = subprocess.run(['lsof', '-nP', f'-iTCP:{port}', '-sTCP:LISTEN', '-t'], capture_output=True, text=True, timeout=8)
        pid = (out.stdout or '').strip().splitlines()
        return pid[0].strip() if pid else ''
    except Exception:
        return ''


def _get_process_cwd(pid: str):
    if not pid:
        return ''
    try:
        out = subprocess.run(['lsof', '-a', '-p', str(pid), '-d', 'cwd', '-Fn'], capture_output=True, text=True, timeout=8)
        for line in (out.stdout or '').splitlines():
            if line.startswith('n'):
                return line[1:].strip()
    except Exception:
        return ''
    return ''


def _health_json():
    try:
        return get_system_health() or {}
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# 最新备份查询
# ---------------------------------------------------------------------------

def _get_latest_backup(parent_dir):
    parent_dir = Path(parent_dir).expanduser()
    patterns = [
        str(parent_dir / 'X1_*_manual_backup_*.tar.gz'),
        str(parent_dir / 'X1_auto_*.tar.gz'),
        str(parent_dir / '检测报告生成系统_X*_backup_*.tar.gz'),
    ]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(pattern))
    if files:
        # 按修改时间排序，最新的在前
        files = sorted(files, key=lambda x: os.path.getmtime(x), reverse=True)
        f = files[0]
        size_mb = round(os.path.getsize(f) / (1024*1024), 1)
        return f'{os.path.basename(f)}  ({size_mb} MB)'
    return '暂无备份'
