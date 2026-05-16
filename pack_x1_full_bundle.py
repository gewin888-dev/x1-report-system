#!/usr/bin/env python3
import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

from config_loader import load_x1_config

BASE_DIR = Path(__file__).resolve().parent
CFG = load_x1_config(BASE_DIR)
OUT_DIR = BASE_DIR / 'full_bundles'
OUT_DIR.mkdir(parents=True, exist_ok=True)

EXCLUDE_NAMES = {
    '.git', 'node_modules', '__pycache__', '.pytest_cache', '.DS_Store',
    'full_bundles'
}
EXCLUDE_SUFFIXES = {'.pyc', '.pyo', '.log'}


def should_skip(path: Path) -> bool:
    return any(part in EXCLUDE_NAMES for part in path.parts) or path.suffix in EXCLUDE_SUFFIXES


def copy_project(src_root: Path, dst_root: Path):
    count = 0
    for p in src_root.rglob('*'):
        if should_skip(p):
            continue
        rel = p.relative_to(src_root)
        dst = dst_root / rel
        if p.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
        elif p.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            count += 1
    return count


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    bundle_name = f'x1_full_bundle_{ts}'
    bundle_dir = OUT_DIR / bundle_name
    app_dir = bundle_dir / 'app'
    app_dir.mkdir(parents=True, exist_ok=True)

    files_copied = copy_project(BASE_DIR, app_dir)

    manifest = {
        'created_at': ts,
        'bundle_name': bundle_name,
        'app_dir': 'app',
        'files_copied': files_copied,
        'entrypoints': {
            'restore': 'app/run_x1_full_restore.sh',
            'doctor': 'app/doctor_x1_migration.py',
            'smoke': 'app/smoke_test_x1.py'
        }
    }
    (bundle_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    tar_path = OUT_DIR / f'{bundle_name}.tar.gz'
    with tarfile.open(tar_path, 'w:gz') as tar:
        tar.add(bundle_dir, arcname=bundle_dir.name)

    print(json.dumps({
        'success': True,
        'bundle_dir': str(bundle_dir),
        'tarball': str(tar_path),
        'files_copied': files_copied,
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
