#!/usr/bin/env python3
"""X1 迁移体检（P0 雏形）"""
import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CFG = json.loads((BASE_DIR / 'x1_config.json').read_text(encoding='utf-8'))

checks = []

def ok(name, detail=''):
    checks.append(('OK', name, detail))

def fail(name, detail=''):
    checks.append(('FAIL', name, detail))

# 1. 单一配置源提醒
main_cfg = BASE_DIR / 'x1_config.json'
shadow_cfg = BASE_DIR / 'config' / 'x1_config.json'
if main_cfg.exists():
    ok('主配置存在', str(main_cfg))
else:
    fail('主配置缺失', str(main_cfg))
if shadow_cfg.exists():
    fail('存在历史配置副本', f'请改名/移除：{shadow_cfg}')
else:
    ok('无历史配置副本歧义')

# 2. 运行模式
host_mode = str(CFG.get('host_mode', 'desktop') or 'desktop').strip().lower()
if host_mode in ('desktop', 'server'):
    ok('运行模式有效', host_mode)
else:
    fail('运行模式非法', f'host_mode={host_mode}')

# 3. 模板根目录
base = Path(os.path.expanduser(CFG.get('template_base', ''))).resolve()
if base.exists():
    ok('模板根目录存在', str(base))
else:
    fail('模板根目录不存在', str(base))

# 4. 模板注册表相对路径检查
registry = BASE_DIR / 'template_registry.json'
if registry.exists():
    data = json.loads(registry.read_text(encoding='utf-8'))
    abs_count = 0
    rel_count = 0
    for item in data.values():
        if not isinstance(item, dict):
            continue
        rel = str(item.get('template_relpath') or '').strip()
        project_rel = str(item.get('template_project_relpath') or '').strip()
        if rel or project_rel:
            rel_count += 1
            continue
        tp = str(item.get('template_path') or '')
        if tp.startswith('/Users/'):
            abs_count += 1
    if rel_count > 0:
        ok('模板注册表已含相对路径字段', f'{rel_count} 项')
    if abs_count > 0:
        fail('模板注册表仍含旧主机绝对路径', f'{abs_count} 项')
    else:
        ok('模板注册表无旧主机绝对路径')
else:
    fail('模板注册表缺失', str(registry))

# 5. 正式归档目录
paths = CFG.get('paths', {})
archive = CFG.get('archive', {})
report_dir = Path(os.path.expanduser(str(archive.get('formal_report_archive') or paths.get('formal_report_archive') or '~/公司资料/检测部/检测报告'))).resolve()
raw_dir = Path(os.path.expanduser(str(archive.get('formal_raw_archive') or paths.get('formal_raw_archive') or '~/公司资料/检测部/原始记录'))).resolve()
for name, p in [('正式报告归档目录', report_dir), ('正式原始记录归档目录', raw_dir)]:
    if p.exists():
        ok(name, str(p))
    else:
        fail(name, f'不存在：{p}')

# 6. desktop 模式额外能力检查
if host_mode == 'desktop':
    has_open = os.system("command -v open >/dev/null 2>&1") == 0
    if has_open:
        ok('desktop 模式具备 open 命令')
    else:
        fail('desktop 模式缺少 open 命令')


print('\nX1 迁移体检结果')
print('=' * 60)
for status, name, detail in checks:
    print(f'[{status}] {name}' + (f' -> {detail}' if detail else ''))

fails = [x for x in checks if x[0] == 'FAIL']
print('=' * 60)
print(f'总计：{len(checks)} 项；失败：{len(fails)} 项')
raise SystemExit(1 if fails else 0)
