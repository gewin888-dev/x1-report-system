#!/usr/bin/env python3
import json
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from config_loader import load_x1_config

BASE_DIR = Path(__file__).resolve().parent
CFG = load_x1_config(BASE_DIR)
TEMPLATE_BASE = Path(CFG.get('template_base', '')).expanduser().resolve()
REGISTRY = BASE_DIR / 'template_registry.json'
TYPE_MAP = BASE_DIR / 'template_type_mappings.json'
SEMANTIC_MAP = BASE_DIR / 'template_semantic_mappings.json'


def load_json(path: Path):
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def copy_tree_files(src_root: Path, dst_root: Path):
    count = 0
    if not src_root.exists():
        return count
    for p in src_root.rglob('*'):
        if p.is_file():
            rel = p.relative_to(src_root)
            dst = dst_root / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(p, dst)
            count += 1
    return count


def main(bundle_input: str):
    source = Path(bundle_input).expanduser().resolve()
    temp_dir = None
    bundle_root = source

    if source.is_file():
        temp_dir = Path(tempfile.mkdtemp(prefix='x1_tpl_restore_'))
        with tarfile.open(source, 'r:gz') as tar:
            tar.extractall(temp_dir)
        manifest_candidates = list(temp_dir.rglob('manifest.json'))
        if not manifest_candidates:
            raise SystemExit('模板包解压后未发现 manifest.json')
        bundle_root = manifest_candidates[0].parent

    manifest = load_json(bundle_root / 'manifest.json')
    registry_src = bundle_root / 'template_registry.json'
    type_src = bundle_root / 'template_type_mappings.json'
    semantic_src = bundle_root / 'template_semantic_mappings.json'

    if not registry_src.exists():
        raise SystemExit('模板包缺少 template_registry.json')

    copied_template_base = copy_tree_files(bundle_root / 'template_base', TEMPLATE_BASE)
    copied_project_templates = copy_tree_files(bundle_root / 'project_templates', BASE_DIR)

    shutil.copy2(registry_src, REGISTRY)
    if type_src.exists():
        shutil.copy2(type_src, TYPE_MAP)
    if semantic_src.exists():
        shutil.copy2(semantic_src, SEMANTIC_MAP)

    print(json.dumps({
        'success': True,
        'bundle_root': str(bundle_root),
        'template_base': str(TEMPLATE_BASE),
        'copied_template_base_files': copied_template_base,
        'copied_project_template_files': copied_project_templates,
        'registry_entries': manifest.get('registry_entries'),
    }, ensure_ascii=False, indent=2))

    if temp_dir and temp_dir.exists():
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 restore_x1_template_bundle.py <bundle_dir_or_tar.gz>')
        raise SystemExit(1)
    main(sys.argv[1])
