#!/usr/bin/env python3
"""模板管理业务闭环测试：注册/启停是否真正影响导出链命中"""
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
        'project_name': '模板管理闭环测试-兽药GMP A级',
        'report_number': 'TMPL-V2-CLOSELOOP-001',
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
            'summary': {
                'result_state': '合格',
                'judgement_active': ['GB 50457-2019'],
                'basis_primary': 'GB 50457-2019',
                'judgement_primary': 'GB 50457-2019'
            },
            'context': {
                'gmp_grade': 'A级'
            }
        }]
    }


def _submit_export(client, project):
    resp = client.post('/api/x/submit_export', data=json.dumps({'project': project}), content_type='application/json')
    assert resp.status_code == 200, resp.status_code
    data = resp.get_json()
    assert data.get('success') is True, data
    return data


def main():
    print('=' * 72)
    print('模板管理业务闭环测试：启停是否真正影响导出链')
    print('=' * 72)

    app_x1 = importlib.import_module('app_x1')
    tr = importlib.import_module('template_resources')

    with TemporaryDirectory() as td:
        temp_dir = Path(td)
        registry_path = temp_dir / 'template_registry.json'
        template_file = temp_dir / '制药工业兽药车间A级检测报告模板.docx'
        from docx import Document
        doc = Document()
        doc.add_paragraph('模板管理闭环测试模板')
        doc.save(str(template_file))

        original_registry = tr.REGISTRY_FILE
        tr.REGISTRY_FILE = registry_path
        try:
            seed = {
                'pharma/veterinary_gmp_workshop/grade/a': {
                    'type_id': 'veterinary_gmp_workshop',
                    'template_name': template_file.name,
                    'template_path': str(template_file),
                    'resource_status': 'confirmed',
                    'resource_note': '闭环测试模板',
                    'enabled': True,
                    'version': 'v2-test',
                    'last_verified_at': '2026-05-06 20:00:00',
                    'last_verify_result': 'success',
                    'last_verify_error': ''
                }
            }
            registry_path.write_text(json.dumps(seed, ensure_ascii=False, indent=2), encoding='utf-8')

            project = _build_vet_gmp_project()
            with app_x1.app.test_client() as client:
                assert _login(client), '登录失败'

                print('\n[CASE 1] 启用状态下，导出链应命中注册模板')
                data1 = _submit_export(client, project)
                ep1 = data1['export_payload']
                tr1 = ep1.get('template_resource', {})
                assert ep1.get('template_rule', {}).get('template_key') == 'pharma/veterinary_gmp_workshop/grade/a'
                assert tr1.get('template_key') == 'pharma/veterinary_gmp_workshop/grade/a'
                assert tr1.get('template_found') is True, tr1
                assert tr1.get('resource_status') == 'confirmed', tr1
                assert tr1.get('template_path') == str(template_file), tr1
                print('✅ 已命中注册模板，template_found=True，resource_status=confirmed')

                print('\n[CASE 2] 停用后，导出链应表现为 disabled / template_found=False')
                toggle_resp = client.post('/admin/api/template-registry/toggle', json={
                    'template_key': 'pharma/veterinary_gmp_workshop/grade/a',
                    'enabled': False
                })
                assert toggle_resp.status_code == 200, toggle_resp.status_code
                toggle_data = toggle_resp.get_json()
                assert toggle_data.get('success') is True
                assert toggle_data.get('enabled') is False

                data2 = _submit_export(client, project)
                ep2 = data2['export_payload']
                tr2 = ep2.get('template_resource', {})
                assert ep2.get('template_rule', {}).get('template_key') == 'pharma/veterinary_gmp_workshop/grade/a'
                assert tr2.get('template_key') == 'pharma/veterinary_gmp_workshop/grade/a'
                assert tr2.get('template_found') is False, tr2
                assert tr2.get('resource_status') == 'disabled', tr2
                print('✅ 停用后导出链已感知，resource_status=disabled，template_found=False')

                print('\n[CASE 3] 重新启用后，导出链应恢复命中')
                toggle_resp2 = client.post('/admin/api/template-registry/toggle', json={
                    'template_key': 'pharma/veterinary_gmp_workshop/grade/a',
                    'enabled': True
                })
                assert toggle_resp2.status_code == 200, toggle_resp2.status_code
                toggle_data2 = toggle_resp2.get_json()
                assert toggle_data2.get('success') is True
                assert toggle_data2.get('enabled') is True

                data3 = _submit_export(client, project)
                ep3 = data3['export_payload']
                tr3 = ep3.get('template_resource', {})
                assert tr3.get('template_found') is True, tr3
                assert tr3.get('resource_status') == 'confirmed', tr3
                print('✅ 重新启用后已恢复命中')

        finally:
            tr.REGISTRY_FILE = original_registry

    print('-' * 72)
    print('✅ ALL PASS：模板管理已真实影响导出链，而不只是按钮状态变化')


if __name__ == '__main__':
    main()
