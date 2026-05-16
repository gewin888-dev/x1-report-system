#!/usr/bin/env python3
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def main(bundle_path: str, target_root: str = ''):
    source = Path(bundle_path).expanduser().resolve()
    target = Path(target_root).expanduser().resolve() if target_root else Path.cwd()
    if not source.exists():
        raise SystemExit(f'完整迁移包不存在: {source}')

    temp_dir = Path(tempfile.mkdtemp(prefix='x1_full_restore_'))
    try:
        with tarfile.open(source, 'r:gz') as tar:
            tar.extractall(temp_dir)
        manifest_candidates = list(temp_dir.rglob('manifest.json'))
        if not manifest_candidates:
            raise SystemExit('完整迁移包解压后未发现 manifest.json')
        bundle_root = manifest_candidates[0].parent
        app_src = bundle_root / 'app'
        if not app_src.exists():
            raise SystemExit('完整迁移包缺少 app 目录')

        target.mkdir(parents=True, exist_ok=True)
        copied = 0
        for p in app_src.rglob('*'):
            rel = p.relative_to(app_src)
            dst = target / rel
            if p.is_dir():
                dst.mkdir(parents=True, exist_ok=True)
            elif p.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)
                copied += 1

        print(json.dumps({
            'success': True,
            'bundle_root': str(bundle_root),
            'target_root': str(target),
            'files_restored': copied,
        }, ensure_ascii=False, indent=2))
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 restore_x1_full_bundle.py <full_bundle.tar.gz> [target_dir]')
        raise SystemExit(1)
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else '')
