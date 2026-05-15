#!/usr/bin/env python3
"""模板管理 V2 接口测试：options / detail / toggle"""
import importlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).parent))


def _login(client):
    client.get('/login')
    resp = client.post('/login', data={'username': 'admin', 'password': 'pudi2026'}, follow_redirects=True)
    return resp.status_code == 200


def _load_app_module():
    return importlib.import_module('app_x1')


def case_options_endpoint_ok():
    app_x1 = _load_app_module()
    with app_x1.app.test_client() as client:
        assert _login(client), '登录失败'
        resp = client.get('/admin/api/template-registry/options')
        assert resp.status_code == 200, resp.status_code
        data = resp.get_json()
        assert data['success'] is True
        assert isinstance(data['objects'], dict)
        assert 'gmp_workshop' in data['objects']
        sample = data['objects']['gmp_workshop']
        assert sample.get('label')
        assert sample.get('keyBase')
    print('✅ CASE1 options 接口正常')


def case_detail_one_row_per_registered_template():
    app_x1 = _load_app_module()
    tr = importlib.import_module('template_resources')
    original = tr.list_registered_template_resources
    with TemporaryDirectory() as td:
        target_file = Path(td) / '制药工业兽药车间A级检测报告模板.docx'
        target_file.write_bytes(b'dummy-docx-content')
        overlay = {
            'pharma/veterinary_gmp_workshop/grade/a': {
                'type_id': 'veterinary_gmp_workshop',
                'template_name': '制药工业兽药车间A级检测报告模板.docx',
                'template_path': str(target_file),
                'enabled': True,
                'version': 'v1',
                'last_verified_at': '2026-05-06 18:00:00',
                'last_verify_result': 'success',
            },
            'pharma/veterinary_gmp_workshop/grade/a-v2': {
                'type_id': 'veterinary_gmp_workshop',
                'template_name': '制药工业兽药车间A级检测报告模板.docx',
                'template_path': str(target_file),
                'enabled': False,
                'version': 'v2',
                'last_verified_at': '2026-05-06 19:00:00',
                'last_verify_result': 'failed',
            },
        }
        tr.list_registered_template_resources = lambda: overlay
        try:
            with app_x1.app.test_client() as client:
                assert _login(client), '登录失败'
                resp = client.get('/admin/api/templates/veterinary_gmp_workshop')
                assert resp.status_code == 200, resp.status_code
                data = resp.get_json()
                files = data['files']
                matched = [f for f in files if f.get('template_key') in overlay]
                assert len(matched) == 2, matched
                keys = {f['template_key'] for f in matched}
                assert keys == set(overlay.keys())
                enabled_map = {f['template_key']: f['enabled'] for f in matched}
                assert enabled_map['pharma/veterinary_gmp_workshop/grade/a'] is True
                assert enabled_map['pharma/veterinary_gmp_workshop/grade/a-v2'] is False
        finally:
            tr.list_registered_template_resources = original
    print('✅ CASE2 detail 接口按注册项逐条返回')


def case_toggle_updates_only_target_key():
    app_x1 = _load_app_module()
    tr = importlib.import_module('template_resources')
    original_registry = tr.REGISTRY_FILE
    with TemporaryDirectory() as td:
        registry_path = Path(td) / 'template_registry.json'
        seed = {
            'alpha/key': {'type_id': 'veterinary_gmp_workshop', 'enabled': True},
            'beta/key': {'type_id': 'veterinary_gmp_workshop', 'enabled': False},
        }
        registry_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding='utf-8')
        tr.REGISTRY_FILE = registry_path
        try:
            with app_x1.app.test_client() as client:
                assert _login(client), '登录失败'
                resp = client.post('/admin/api/template-registry/toggle', json={'template_key': 'alpha/key', 'enabled': False})
                assert resp.status_code == 200, resp.status_code
                data = resp.get_json()
                assert data['success'] is True
                assert data['template_key'] == 'alpha/key'
                assert data['enabled'] is False
            updated = json.loads(registry_path.read_text(encoding='utf-8'))
            assert updated['alpha/key']['enabled'] is False
            assert updated['beta/key']['enabled'] is False
        finally:
            tr.REGISTRY_FILE = original_registry
    print('✅ CASE3 toggle 只更新目标 key')


def main():
    print('=' * 68)
    print('模板管理 V2 接口测试')
    print('=' * 68)
    case_options_endpoint_ok()
    case_detail_one_row_per_registered_template()
    case_toggle_updates_only_target_key()
    print('-' * 68)
    print('✅ ALL PASS')


if __name__ == '__main__':
    main()
