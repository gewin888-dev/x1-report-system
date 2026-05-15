#!/usr/bin/env python3
"""
X1 模板管理每日巡检脚本
- JSON 完整性校验（三张配置表）
- 关键 key 存在性校验
- 文件哈希变更检测
- 可选：跑全量遍历测试

用法：
  python3 daily_template_check.py          # 快速巡检（<5秒）
  python3 daily_template_check.py --full   # 含全量遍历测试（~2分钟）
"""
import json
import sys
import hashlib
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent
REGISTRY_FILE = ROOT / 'template_registry.json'
TYPE_MAPPINGS_FILE = ROOT / 'template_type_mappings.json'
SEMANTIC_MAPPINGS_FILE = ROOT / 'template_semantic_mappings.json'
HASH_FILE = ROOT / 'logs_x1' / 'template_config_hashes.json'
LOG_DIR = ROOT / 'logs_x1'

# 所有 14 个对象必须在 type_mappings 中有 default_template_key
REQUIRED_TYPE_IDS = [
    'operating_room', 'clean_function_room', 'negative_pressure',
    'bsl', 'animal_room', 'bsc', 'clean_bench', 'ivc',
    'food_workshop', 'laminar_hood', 'pass_box',
    'gmp_workshop', 'veterinary_gmp_workshop', 'electronics_workshop',
]

def sha256(path):
    if not path.exists():
        return ''
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_json_integrity():
    """校验三张配置表的 JSON 完整性"""
    results = []
    for label, path in [
        ('template_registry', REGISTRY_FILE),
        ('template_type_mappings', TYPE_MAPPINGS_FILE),
        ('template_semantic_mappings', SEMANTIC_MAPPINGS_FILE),
    ]:
        if not path.exists():
            results.append((label, 'WARN', '文件不存在'))
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                results.append((label, 'FAIL', f'顶层结构不是 dict，是 {type(data).__name__}'))
            else:
                results.append((label, 'PASS', f'{len(data)} 项'))
        except json.JSONDecodeError as e:
            results.append((label, 'CRITICAL', f'JSON 解析失败: {e}'))
    return results


def check_required_defaults():
    """校验所有对象的 default_template_key 不为空"""
    results = []
    try:
        mappings = json.loads(TYPE_MAPPINGS_FILE.read_text(encoding='utf-8'))
    except Exception:
        return [('type_mappings_defaults', 'SKIP', '无法读取 type_mappings')]

    for tid in REQUIRED_TYPE_IDS:
        entry = mappings.get(tid, {})
        default_key = entry.get('default_template_key', '')
        if not default_key:
            results.append((f'default:{tid}', 'FAIL', 'default_template_key 为空'))
        else:
            results.append((f'default:{tid}', 'PASS', default_key))
    return results


def check_registry_keys():
    """校验注册表中所有 key 对应的模板文件存在"""
    results = []
    try:
        registry = json.loads(REGISTRY_FILE.read_text(encoding='utf-8'))
    except Exception:
        return [('registry_files', 'SKIP', '无法读取 registry')]

    missing = 0
    for key, info in registry.items():
        tpath = info.get('template_path', '')
        if tpath and not Path(tpath).exists():
            results.append((f'file:{key}', 'FAIL', f'模板文件不存在: {tpath}'))
            missing += 1

    if not missing:
        results.append(('registry_files', 'PASS', f'{len(registry)} 个注册模板文件全部存在'))
    return results


def check_hash_changes():
    """检测文件哈希变更"""
    results = []
    if not HASH_FILE.exists():
        results.append(('hash_change', 'INFO', '无历史哈希记录，跳过变更检测'))
        return results

    try:
        prev = json.loads(HASH_FILE.read_text(encoding='utf-8'))
    except Exception:
        return [('hash_change', 'WARN', '哈希文件读取失败')]

    for label, path, key in [
        ('registry', REGISTRY_FILE, 'registry'),
        ('type_mappings', TYPE_MAPPINGS_FILE, 'type_mappings'),
        ('semantic_mappings', SEMANTIC_MAPPINGS_FILE, 'semantic_mappings'),
    ]:
        old = prev.get(key, '')
        new = sha256(path)
        if old and new and old != new:
            results.append((f'change:{label}', 'WARN', f'自 {prev.get("saved_at", "?")} 以来已变更'))
        elif old and new and old == new:
            results.append((f'change:{label}', 'OK', '未变更'))

    return results


def run_full_traverse():
    """跑全量遍历测试"""
    import subprocess
    result = subprocess.run(
        [sys.executable, str(ROOT / 'test_template_management_full_traverse.py')],
        capture_output=True, text=True, timeout=300, cwd=str(ROOT)
    )
    # 从输出提取 SUMMARY 行
    for line in result.stdout.split('\n'):
        if line.strip().startswith('SUMMARY'):
            return [('full_traverse', 'PASS' if result.returncode == 0 else 'FAIL', line.strip())]
    return [('full_traverse', 'PASS' if result.returncode == 0 else 'FAIL', f'returncode={result.returncode}')]


def main():
    full = '--full' in sys.argv
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f'\n{"=" * 60}')
    print(f'X1 模板管理每日巡检  {now}')
    print(f'{"=" * 60}')

    all_results = []
    all_results.extend(check_json_integrity())
    all_results.extend(check_required_defaults())
    all_results.extend(check_registry_keys())
    all_results.extend(check_hash_changes())

    if full:
        print('\n[全量遍历测试 运行中...]')
        all_results.extend(run_full_traverse())

    # 输出
    critical = 0
    fail = 0
    warn = 0
    for label, status, detail in all_results:
        icon = {'PASS': '✅', 'OK': '✅', 'FAIL': '❌', 'CRITICAL': '🔴', 'WARN': '⚠️', 'INFO': 'ℹ️', 'SKIP': '⏭️'}.get(status, '?')
        print(f'  {icon} {label}: {detail}')
        if status == 'CRITICAL':
            critical += 1
        elif status == 'FAIL':
            fail += 1
        elif status == 'WARN':
            warn += 1

    print(f'\n{"─" * 60}')
    if critical:
        print(f'🔴 严重问题: {critical} 项 — 需要立即修复')
        sys.exit(2)
    elif fail:
        print(f'❌ 失败: {fail} 项 — 需要关注')
        sys.exit(1)
    elif warn:
        print(f'⚠️ 警告: {warn} 项 — 建议检查')
        sys.exit(0)
    else:
        print(f'✅ 全部正常')
        sys.exit(0)

    # 写巡检日志
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f'daily_check_{datetime.now().strftime("%Y%m%d")}.json'
    log_file.write_text(json.dumps({
        'time': now,
        'results': [{'label': l, 'status': s, 'detail': d} for l, s, d in all_results],
        'critical': critical,
        'fail': fail,
        'warn': warn,
    }, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
