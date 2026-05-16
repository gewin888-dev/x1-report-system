#!/usr/bin/env python3
import json
import tarfile
from datetime import datetime
from pathlib import Path

from config_loader import load_x1_config

BASE_DIR = Path(__file__).resolve().parent
CFG = load_x1_config(BASE_DIR)
TEMPLATE_BASE = Path(CFG.get('template_base', '')).expanduser().resolve()
REGISTRY = BASE_DIR / 'template_registry.json'
TYPE_MAP = BASE_DIR / 'template_type_mappings.json'
SEMANTIC_MAP = BASE_DIR / 'template_semantic_mappings.json'
OUT_DIR = BASE_DIR / 'template_bundles'
OUT_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def main():
    data = load_json(REGISTRY)
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    bundle_root_name = f'x1_template_bundle_{ts}'
    bundle_dir = OUT_DIR / bundle_root_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        'created_at': ts,
        'template_base': str(TEMPLATE_BASE),
        'registry_entries': 0,
        'template_relpath_count': 0,
        'template_project_relpath_count': 0,
        'files': [],
        'missing': [],
    }

    # copy metadata
    for src in [REGISTRY, TYPE_MAP, SEMANTIC_MAP]:
        if src.exists():
            target = bundle_dir / src.name
            target.write_text(src.read_text(encoding='utf-8'), encoding='utf-8')

    # collect template files
    for key, item in data.items():
        if not isinstance(item, dict):
            continue
        manifest['registry_entries'] += 1
        rel = str(item.get('template_relpath') or '').strip()
        project_rel = str(item.get('template_project_relpath') or '').strip()
        src = None
        dst = None
        if rel:
            manifest['template_relpath_count'] += 1
            src = TEMPLATE_BASE / rel
            dst = bundle_dir / 'template_base' / rel
        elif project_rel:
            manifest['template_project_relpath_count'] += 1
            src = BASE_DIR / project_rel
            dst = bundle_dir / 'project_templates' / project_rel
        if src is None:
            continue
        if src.exists() and src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            manifest['files'].append({'key': key, 'source': str(src), 'bundle_path': str(dst.relative_to(bundle_dir))})
        else:
            manifest['missing'].append({'key': key, 'expected': str(src)})

    (bundle_dir / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')

    tar_path = OUT_DIR / f'{bundle_root_name}.tar.gz'
    with tarfile.open(tar_path, 'w:gz') as tar:
        tar.add(bundle_dir, arcname=bundle_dir.name)

    print(json.dumps({
        'success': True,
        'bundle_dir': str(bundle_dir),
        'tarball': str(tar_path),
        'registry_entries': manifest['registry_entries'],
        'files_packed': len(manifest['files']),
        'missing': len(manifest['missing']),
    }, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
