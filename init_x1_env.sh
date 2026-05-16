#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

python3 - <<'PY'
import json
from pathlib import Path

root = Path('.').resolve()
cfg_path = root / 'x1_config.json'
if not cfg_path.exists():
    raise SystemExit('[FAIL] 缺少 x1_config.json')

cfg = json.loads(cfg_path.read_text(encoding='utf-8'))
paths = cfg.setdefault('paths', {})
archive = cfg.setdefault('archive', {})

for key, default in {
    'records': 'records_x1',
    'reports': 'reports_x1',
    'logs': 'logs_x1',
    'cache': 'cache_x1',
    'temp': 'temp_x1',
    'uploads': 'uploads_x1',
}.items():
    path = root / paths.get(key, default)
    path.mkdir(parents=True, exist_ok=True)
    print(f'[OK] ensured: {path}')

for key, default in {
    'formal_report_archive': '~/公司资料/检测部/检测报告',
    'formal_raw_archive': '~/公司资料/检测部/原始记录',
}.items():
    value = archive.get(key) or default
    p = Path(value).expanduser()
    p.mkdir(parents=True, exist_ok=True)
    archive[key] = str(p)
    print(f'[OK] archive: {key} -> {p}')

cfg_path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')
print('[OK] x1_config.json 已补齐 archive 配置')
PY

echo "[OK] init_x1_env.sh 执行完成"
