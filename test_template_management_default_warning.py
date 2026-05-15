#!/usr/bin/env python3
"""默认模板异常态治理测试：默认模板停用/缺失时，页面与导出链状态一致"""
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


def _build_vet_gmp_project():
    return {
        'project_name': '默认模板异常态测试-兽药GMP A级',
        'report_number': 'TMPL-DEFAULT-WARN-001',
        'client_name': '测试客户',
        'contact_info': '13800000000',
        'project_address': '上海市测试区',
        'inspection_area': 'A级洁净区',
        'detection_date': '2026-05-06',
        'domain': 'pharma',
        'domain_name': '制药工业',
        'rooms': [{
            'room_id': 'r1',
            'type_id': 'veterinary_gmp_workshop',
            'room_name': 'A级车间',
            'type_name': '兽药GMP车间',
            'level_name': 'A级',
            'clean_class': 'A级',
            'basis': ['GB 50457-2019'],
            'judgement': ['GB 50457-2019'],
            'params': [],
            'summary': {'result_state': '合格'},
            'context': {'gmp_grade': 'A级'}
        }]
    }


def _submit_export(client, project):
    resp = client.post('/api/x/submit_export', data=json.dumps({'project': project}), content_type='application/json')
    assert resp.status_code == 200, resp.status_code
    data = resp.get_json()
    assert data.get('success') is True, data
    return data


def main():
    print('=' * 76)
    print('默认模板异常态治理测试')
    print('=' * 76)

    app_x1 = importlib.import_module('app_x1')
    tr = importlib.import_module('template_resources')
    project = _build_vet_gmp_project()

    with TemporaryDirectory() as td:
        temp_dir = Path(td)
        registry_path = temp_dir / 'template_registry.json'
        mappings_path = temp_dir / 'template_type_mappings.json'
        from docx import Document

        file_a = temp_dir / '制药工业兽药车间A级检测报告模板.docx'
        doc = Document(); doc.add_paragraph('A 模板'); doc.save(str(file_a))

        original_registry = tr.REGISTRY_FILE
        original_mappings = tr.TYPE_MAPPINGS_FILE
        tr.REGISTRY_FILE = registry_path
        tr.TYPE_MAPPINGS_FILE = mappings_path
        try:
            with app_x1.app.test_client() as client:
                assert _login(client), '登录失败'

                print('\n[CASE 1] 默认模板已停用：一级页/二级页告警与导出链 disabled 应一致')
                registry_path.write_text(json.dumps({
                    'pharma/veterinary_gmp_workshop/grade/a': {
                        'type_id': 'veterinary_gmp_workshop',
                        'template_name': file_a.name,
                        'template_path': str(file_a),
                        'resource_status': 'confirmed',
                        'enabled': False,
                        'version': 'v1'
                    }
                }, ensure_ascii=False, indent=2), encoding='utf-8')
                mappings_path.write_text(json.dumps({
                    'veterinary_gmp_workshop': {
                        'allowed_template_keys': ['pharma/veterinary_gmp_workshop/grade/a'],
                        'default_template_key': 'pharma/veterinary_gmp_workshop/grade/a'
                    }
                }, ensure_ascii=False, indent=2), encoding='utf-8')

                list_data = client.get('/admin/api/templates').get_json()
                list_item = next(t for t in list_data['templates'] if t['id'] == 'veterinary_gmp_workshop')
                assert list_item['default_warning'] == 'disabled', list_item

                detail_data = client.get('/admin/api/templates/veterinary_gmp_workshop').get_json()
                assert detail_data['default_warning'] == 'disabled', detail_data

                export1 = _submit_export(client, project)
                res1 = export1['export_payload']['template_resource']
                assert res1['resource_status'] == 'disabled', res1
                assert res1['template_found'] is False, res1
                print('✅ 默认模板停用：页面与导出链状态一致')

                print('\n[CASE 2] 默认模板文件缺失：一级页/二级页告警与导出链 missing 应一致')
                missing_path = temp_dir / '不存在的默认模板.docx'
                registry_path.write_text(json.dumps({
                    'pharma/veterinary_gmp_workshop/grade/a': {
                        'type_id': 'veterinary_gmp_workshop',
                        'template_name': missing_path.name,
                        'template_path': str(missing_path),
                        'resource_status': 'missing',
                        'enabled': True,
                        'version': 'v1'
                    }
                }, ensure_ascii=False, indent=2), encoding='utf-8')

                list_data2 = client.get('/admin/api/templates').get_json()
                list_item2 = next(t for t in list_data2['templates'] if t['id'] == 'veterinary_gmp_workshop')
                assert list_item2['default_warning'] == 'missing', list_item2

                detail_data2 = client.get('/admin/api/templates/veterinary_gmp_workshop').get_json()
                assert detail_data2['default_warning'] == 'missing', detail_data2

                export2 = _submit_export(client, project)
                res2 = export2['export_payload']['template_resource']
                assert res2['resource_status'] == 'missing', res2
                assert res2['template_found'] is False, res2
                print('✅ 默认模板缺失：页面与导出链状态一致')

                print('\n[CASE 3] 未设置默认模板：页面应给出 unset 告警')
                mappings_path.write_text(json.dumps({'veterinary_gmp_workshop': {'allowed_template_keys': [], 'default_template_key': ''}}, ensure_ascii=False, indent=2), encoding='utf-8')
                list_data3 = client.get('/admin/api/templates').get_json()
                list_item3 = next(t for t in list_data3['templates'] if t['id'] == 'veterinary_gmp_workshop')
                assert list_item3['default_warning'] == 'unset', list_item3
                detail_data3 = client.get('/admin/api/templates/veterinary_gmp_workshop').get_json()
                assert detail_data3['default_warning'] == 'unset', detail_data3
                print('✅ 未设置默认模板：页面告警成立')

        finally:
            tr.REGISTRY_FILE = original_registry
            tr.TYPE_MAPPINGS_FILE = original_mappings

    print('-' * 76)
    print('✅ ALL PASS：默认模板异常态治理已打通')


if __name__ == '__main__':
    main()
