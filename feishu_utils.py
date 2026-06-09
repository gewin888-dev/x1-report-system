"""
飞书云盘集成模块
"""
import json
import re
import time
import requests
from pathlib import Path
from datetime import datetime
from functools import wraps

# 飞书目录缓存 {prefix_key: folder_token}
_feishu_folder_cache = {}
_MONTH_RE = re.compile(r'^\d{4}-\d{2}$')
_YEAR_RE = re.compile(r'^\d{4}$')

# Token 缓存
_token_cache = {'token': None, 'expires_at': 0}
# 目录解析缓存 {key: (folder_token, expire_time)}
_folder_resolve_cache = {}


def get_feishu_config():
    """读取飞书配置"""
    config_path = Path(__file__).parent / 'feishu_config.json'
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return None


def get_feishu_token():
    """获取飞书 tenant_access_token（带缓存，有效期内不重复请求）"""
    global _token_cache
    now = time.time()
    if _token_cache['token'] and now < _token_cache['expires_at']:
        return _token_cache['token']
    config = get_feishu_config()
    if not config:
        return None
    try:
        resp = requests.post(
            'https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal',
            json={'app_id': config['app_id'], 'app_secret': config['app_secret']},
            timeout=10
        )
        data = resp.json()
        if data.get('code') == 0:
            token = data.get('tenant_access_token')
            expire = data.get('expire', 7200)
            # 提前 5 分钟过期，避免边缘情况
            _token_cache = {'token': token, 'expires_at': now + expire - 300}
            return token
    except Exception:
        pass
    return None


def _list_feishu_folder_entries(folder_token, token=None, page_size=50):
    """列出飞书目录下的子项"""
    if not token:
        token = get_feishu_token()
    if not token or not folder_token:
        return []
    try:
        resp = requests.get(
            'https://open.feishu.cn/open-apis/drive/v1/files',
            headers={'Authorization': f'Bearer {token}'},
            params={'folder_token': folder_token, 'page_size': page_size},
            timeout=15
        )
        data = resp.json()
        if data.get('code') == 0:
            return data.get('data', {}).get('files', []) or []
    except Exception:
        pass
    return []


def _infer_folder_mode(entries):
    """根据目录内容推断配置 token 的目录模式。"""
    if not entries:
        return 'unknown'
    folder_names = [str(entry.get('name') or '') for entry in entries if entry.get('type') == 'folder']
    if any(_MONTH_RE.fullmatch(name) for name in folder_names):
        return 'month-root'
    if any(_YEAR_RE.fullmatch(name) for name in folder_names):
        return 'year-root'
    has_file = any(entry.get('type') == 'file' for entry in entries)
    if has_file:
        return 'direct'
    return 'direct'


def _current_month_label(now=None):
    if now is None:
        now = datetime.now()
    return now.strftime('%Y-%m')


def get_feishu_monthly_folder(prefix, year=None, month=None, token=None, parent_token=None, parent_entries=None):
    """获取或创建飞书按月份命名的子文件夹（YYYY-MM）。"""
    now = datetime.now()
    if year is None:
        year = now.year
    if month is None:
        month = now.month
    folder_name = f'{int(year):04d}-{int(month):02d}'
    cache_key = f'{prefix}_{folder_name}'

    config = get_feishu_config()
    if not config:
        return None
    if not parent_token:
        parent_token = (config.get('folders') or {}).get(prefix)
    if not parent_token:
        return None
    if cache_key in _feishu_folder_cache:
        return _feishu_folder_cache[cache_key]
    if not token:
        token = get_feishu_token()
    if not token:
        return None

    try:
        entries = parent_entries if parent_entries is not None else _list_feishu_folder_entries(parent_token, token=token)
        for f in entries:
            if f.get('name') == folder_name and f.get('type') == 'folder':
                _feishu_folder_cache[cache_key] = f['token']
                return f['token']
        resp = requests.post(
            'https://open.feishu.cn/open-apis/drive/v1/files/create_folder',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'name': folder_name, 'folder_token': parent_token},
            timeout=15
        )
        data = resp.json()
        if data.get('code') == 0:
            new_token = data.get('data', {}).get('token', '')
            if new_token:
                _feishu_folder_cache[cache_key] = new_token
                print(f"✅ 飞书创建月份文件夹: {prefix}/{folder_name} -> {new_token}")
                return new_token
        print(f"❌ 飞书创建月份文件夹失败: {data.get('msg', '')}")
    except Exception as e:
        print(f"❌ 飞书月份文件夹操作失败: {e}")
    return None


def get_feishu_yearly_folder(prefix, year=None, token=None, parent_token=None, parent_entries=None):
    """获取或创建飞书按年份命名的子文件夹。"""
    if year is None:
        year = datetime.now().year
    cache_key = f"{prefix}_{year}"
    folder_name = str(year)

    config = get_feishu_config()
    if not config:
        return None

    if not parent_token:
        parent_token = (config.get('folders') or {}).get(prefix)
    if not parent_token:
        return None

    if cache_key in _feishu_folder_cache:
        return _feishu_folder_cache[cache_key]

    if not token:
        token = get_feishu_token()
    if not token:
        return None

    try:
        entries = parent_entries if parent_entries is not None else _list_feishu_folder_entries(parent_token, token=token)
        for f in entries:
            if f.get('name') == folder_name and f.get('type') == 'folder':
                _feishu_folder_cache[cache_key] = f['token']
                return f['token']

        resp = requests.post(
            'https://open.feishu.cn/open-apis/drive/v1/files/create_folder',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'name': folder_name, 'folder_token': parent_token},
            timeout=15
        )
        data = resp.json()
        if data.get('code') == 0:
            new_token = data.get('data', {}).get('token', '')
            if new_token:
                _feishu_folder_cache[cache_key] = new_token
                print(f"✅ 飞书创建年份文件夹: {prefix}/{folder_name} -> {new_token}")
                return new_token
        print(f"❌ 飞书创建年份文件夹失败: {data.get('msg', '')}")
    except Exception as e:
        print(f"❌ 飞书年份文件夹操作失败: {e}")

    return None


def resolve_feishu_upload_folder(prefix, year=None, now=None):
    """解析飞书上传目标目录（带 10 分钟缓存）。"""
    if now is None:
        now = datetime.now()
    if year is None:
        year = now.year
    cache_key = f"{prefix}_{year}_{now.month}"
    cached = _folder_resolve_cache.get(cache_key)
    if cached:
        folder_token, expire_time = cached
        if time.time() < expire_time:
            return folder_token

    config = get_feishu_config()
    if not config:
        return None
    parent_token = (config.get('folders') or {}).get(prefix)
    if not parent_token:
        return None
    token = get_feishu_token()
    if not token:
        return None

    entries = _list_feishu_folder_entries(parent_token, token=token)
    mode = _infer_folder_mode(entries)
    if mode == 'direct':
        result = parent_token
    elif mode == 'month-root':
        result = get_feishu_monthly_folder(prefix, year=now.year, month=now.month, token=token, parent_token=parent_token, parent_entries=entries)
    else:
        result = get_feishu_yearly_folder(prefix, year, token=token, parent_token=parent_token, parent_entries=entries)

    if result:
        _folder_resolve_cache[cache_key] = (result, time.time() + 600)  # 缓存 10 分钟
    return result


def get_feishu_folder_meta(prefix, year=None, now=None):
    """返回飞书目录配置的模式、解析结果与月份匹配信息。"""
    if now is None:
        now = datetime.now()
    if year is None:
        year = now.year
    month_label = _current_month_label(now)
    config = get_feishu_config() or {}
    configured_token = (config.get('folders') or {}).get(prefix, '')
    token = get_feishu_token()
    entries = _list_feishu_folder_entries(configured_token, token=token) if (token and configured_token) else []
    mode = _infer_folder_mode(entries) if configured_token else 'missing'
    resolved_token = resolve_feishu_upload_folder(prefix, year=year, now=now) if (token and configured_token) else None

    folder_names = [str(entry.get('name') or '') for entry in entries if entry.get('type') == 'folder']
    month_child_exists = month_label in folder_names
    month_matches = False
    if mode == 'direct':
        month_matches = True
    elif mode == 'month-root':
        month_matches = month_child_exists

    return {
        'configured_token': configured_token,
        'resolved_token': resolved_token,
        'mode': mode,
        'current_month': month_label,
        'month_child_exists': month_child_exists,
        'month_matches': month_matches,
        'entries_count': len(entries),
    }


def retry(max_attempts=3, delay=1, backoff=2):
    """重试装饰器，支持指数退避。只在函数抛异常时重试。"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts:
                        print(f"⚠️ 飞书上传重试（第 {attempt} 次）: {e}")
                        time.sleep(delay * (backoff ** (attempt - 1)))
            return {'success': False, 'error': f'上传失败（已重试{max_attempts}次）: {last_error}'}
        return wrapper
    return decorator


def build_feishu_open_url(file_token, file_name=''):
    """根据文件扩展名构造更贴近原格式的飞书打开链接。"""
    if not file_token:
        return ''
    return f'https://pudi-test.feishu.cn/drive/file/{file_token}'


@retry()
def upload_file_to_feishu(file_path, folder_token):
    """上传文件到飞书云盘"""
    token = get_feishu_token()
    if not token:
        return {'success': False, 'error': '无法获取飞书token'}
    file_path = Path(file_path)
    with open(file_path, 'rb') as f:
        resp = requests.post(
            'https://open.feishu.cn/open-apis/drive/v1/files/upload_all',
            headers={'Authorization': f'Bearer {token}'},
            data={
                'file_name': file_path.name,
                'parent_type': 'explorer',
                'parent_node': folder_token,
                'size': str(file_path.stat().st_size)
            },
            files={'file': (file_path.name, f)},
            timeout=30
        )
    data = resp.json()
    if data.get('code') == 0:
        file_token = data.get('data', {}).get('file_token', '')
        feishu_url = f'https://pudi-test.feishu.cn/drive/file/{file_token}' if file_token else ''
        feishu_open_url = build_feishu_open_url(file_token, file_path.name)
        return {
            'success': True,
            'file_token': file_token,
            'feishu_url': feishu_url,
            'feishu_open_url': feishu_open_url,
            'feishu_open_kind': Path(file_path.name).suffix.lower().lstrip('.')
        }
    raise RuntimeError(f"飞书API错误 code={data.get('code')} msg={data.get('msg', '上传失败')}")


def download_file_content_from_feishu(file_token):
    """从飞书云盘下载文件内容到内存，供浏览器下载流返回。"""
    token = get_feishu_token()
    if not token:
        return {'success': False, 'error': '无法获取飞书token'}
    try:
        resp = requests.get(
            f'https://open.feishu.cn/open-apis/drive/v1/files/{file_token}/download',
            headers={'Authorization': f'Bearer {token}'},
            timeout=60
        )
        if resp.status_code != 200:
            return {'success': False, 'error': f'飞书下载失败: HTTP {resp.status_code}'}
        cd = resp.headers.get('Content-Disposition', '')
        filename = ''
        if 'filename=' in cd:
            import re
            m = re.search(r'filename[*]?=(?:UTF-8\'\')?(.*?)(?:;|$)', cd)
            if m:
                from urllib.parse import unquote
                filename = unquote(m.group(1).strip('"'))
        if not filename:
            filename = f'feishu_{file_token}'
        return {
            'success': True,
            'filename': filename,
            'size': len(resp.content),
            'content': resp.content,
            'content_type': resp.headers.get('Content-Type', 'application/octet-stream')
        }
    except Exception as e:
        return {'success': False, 'error': f'飞书下载异常: {e}'}


def download_file_from_feishu(file_token, save_dir=None):
    """从飞书云盘下载文件到本地临时目录"""
    token = get_feishu_token()
    if not token:
        return {'success': False, 'error': '无法获取飞书token'}
    try:
        resp = requests.get(
            f'https://open.feishu.cn/open-apis/drive/v1/files/{file_token}/download',
            headers={'Authorization': f'Bearer {token}'},
            timeout=60
        )
        if resp.status_code != 200:
            return {'success': False, 'error': f'飞书下载失败: HTTP {resp.status_code}'}
        # 从 Content-Disposition 获取文件名
        cd = resp.headers.get('Content-Disposition', '')
        filename = ''
        if 'filename=' in cd:
            import re
            m = re.search(r'filename[*]?=(?:UTF-8\'\')?(.*?)(?:;|$)', cd)
            if m:
                from urllib.parse import unquote
                filename = unquote(m.group(1).strip('"'))
        if not filename:
            filename = f'feishu_{file_token}'
        if save_dir is None:
            import tempfile
            save_dir = tempfile.mkdtemp(prefix='x1_feishu_')
        save_path = Path(save_dir) / filename
        save_path.write_bytes(resp.content)
        return {'success': True, 'path': str(save_path), 'filename': filename, 'size': len(resp.content)}
    except Exception as e:
        return {'success': False, 'error': f'飞书下载异常: {e}'}
