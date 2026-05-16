#!/usr/bin/env python3
"""手动注册同步最小闭环测试：注册模板时自动加入候选集并可设为默认"""
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


def main():
    print('=' * 76)
    print('手动注册同步最小闭环测试')
    print('=' * 76)

    app_x1 = importlib.import_module('app_x1')
    tr = importlib.import_module('template_resources')

    with TemporaryDirectory() as td:
        temp_dir = Path(td)
        registry_path = temp_dir / 'template_registry.json'
        mappings_path = temp_dir / 'template_type_mappings.json'
        # 将测试模板放在 TEMPLATE_BASE 内以通过路径穿越防护
        import os as _os
        _tb = Path(_os.path.expanduser('~/公司资料/检测部/检测报告模板'))
        _test_tmpl_dir = _tb / 'test_tmp'
        _test_tmpl_dir.mkdir(parents=True, exist_ok=True)
        template_file = _test_tmpl_dir / '制药工业兽药车间A级检测报告模板-人工注册.docx'
        from docx import Document
        d = Document(); d.add_paragraph('manual register sync'); d.save(str(template_file))

        registry_path.write_text('{}', encoding='utf-8')
        mappings_path.write_text('{}', encoding='utf-8')

        original_registry = tr.REGISTRY_FILE
        original_mappings = tr.TYPE_MAPPINGS_FILE
        tr.REGISTRY_FILE = registry_path
        tr.TYPE_MAPPINGS_FILE = mappings_path
        try:
            with app_x1.app.test_client() as client:
                assert _login(client), '登录失败'

                print('\n[CASE 1] 注册模板时 attach_to_type=true，应自动加入候选集')
                resp1 = client.post('/admin/api/template-registry/register', json={
                    'type_id': 'veterinary_gmp_workshop',
                    'template_key': 'pharma/veterinary_gmp_workshop/grade/a-manual',
                    'template_name': template_file.name,
                    'path_mode': 'absolute',
                    'absolute_path': str(template_file),
                    'attach_to_type': True,
                    'set_as_default': False
                })
                assert resp1.status_code == 200, resp1.status_code
                data1 = resp1.get_json()
                assert data1.get('success') is True, data1
                current_map1 = json.loads(mappings_path.read_text(encoding='utf-8'))
                allowed1 = current_map1['veterinary_gmp_workshop']['allowed_template_keys']
                assert 'pharma/veterinary_gmp_workshop/grade/a-manual' in allowed1, current_map1
                print('✅ 注册后已自动加入候选集')

                print('\n[CASE 2] 注册模板时 set_as_default=true，应自动设为默认模板')
                resp2 = client.post('/admin/api/template-registry/register', json={
                    'type_id': 'veterinary_gmp_workshop',
                    'template_key': 'pharma/veterinary_gmp_workshop/grade/a-manual-v2',
                    'template_name': template_file.name,
                    'path_mode': 'absolute',
                    'absolute_path': str(template_file),
                    'attach_to_type': True,
                    'set_as_default': True
                })
                assert resp2.status_code == 200, resp2.status_code
                data2 = resp2.get_json()
                assert data2.get('success') is True, data2
                current_map2 = json.loads(mappings_path.read_text(encoding='utf-8'))
                mapping2 = current_map2['veterinary_gmp_workshop']
                assert 'pharma/veterinary_gmp_workshop/grade/a-manual-v2' in mapping2['allowed_template_keys'], mapping2
                assert mapping2['default_template_key'] == 'pharma/veterinary_gmp_workshop/grade/a-manual-v2', mapping2
                print('✅ 注册后已自动设为默认模板')

        finally:
            tr.REGISTRY_FILE = original_registry
            tr.TYPE_MAPPINGS_FILE = original_mappings
            # 清理测试临时模板文件
            try:
                template_file.unlink(missing_ok=True)
            except Exception:
                pass

    print('-' * 76)
    print('✅ ALL PASS：手动注册同步已接入候选/默认链')


if __name__ == '__main__':
    main()
