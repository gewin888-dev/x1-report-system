#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def main(bundle_path: str):
    root = Path(bundle_path).expanduser().resolve()
    if root.is_file():
        raise SystemExit('请先解压模板包，再传入 bundle 根目录进行校验')
    manifest = load_json(root / 'manifest.json')
    registry = load_json(root / 'template_registry.json')
    missing = []
    checked = 0
    for key, item in registry.items():
        if not isinstance(item, dict):
            continue
        rel = str(item.get('template_relpath') or '').strip()
        project_rel = str(item.get('template_project_relpath') or '').strip()
        if rel:
            checked += 1
            p = root / 'template_base' / rel
            if not p.exists():
                missing.append({'key': key, 'expected': str(p.relative_to(root))})
        elif project_rel:
            checked += 1
            p = root / 'project_templates' / project_rel
            if not p.exists():
                missing.append({'key': key, 'expected': str(p.relative_to(root))})

    print(json.dumps({
        'success': len(missing) == 0,
        'bundle_root': str(root),
        'manifest_present': (root / 'manifest.json').exists(),
        'registry_entries': manifest.get('registry_entries'),
        'checked_entries': checked,
        'missing_count': len(missing),
        'missing': missing[:20],
    }, ensure_ascii=False, indent=2))
    raise SystemExit(1 if missing else 0)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 verify_x1_template_bundle.py <bundle_dir>')
        raise SystemExit(1)
    main(sys.argv[1])
