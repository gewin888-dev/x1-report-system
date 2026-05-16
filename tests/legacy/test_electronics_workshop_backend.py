#!/usr/bin/env python3
"""测试 electronics_workshop 后端接入（Canonical Payload + 登录态）"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app_x1 import app


def _login(client):
    client.get('/login')
    resp = client.post('/login', data={'username': 'admin', 'password': 'pudi2026'}, follow_redirects=True)
    return resp.status_code == 200


def test_electronics_workshop():
    print("=" * 60)
    print("测试场景: electronics_workshop 后端接入验证")
    print("=" * 60)

    payload = {
        'project_name': '某电子厂洁净车间检测',
        'report_number': 'TEST-ELEC-001',
        'client_name': '某电子科技有限公司',
        'contact_info': '测试联系人 13800000000',
        'project_address': '苏州市测试区',
        'inspection_area': '组装车间',
        'detection_date': '2026-05-02',
        'domain': 'electronics',
        'domain_name': '电子工业',
        'rooms': [{
            'room_id': 'r1',
            'type_id': 'electronics_workshop',
            'room_name': '组装车间-01',
            'type_name': '电子车间',
            'clean_class': 'ISO 7',
            'level_name': 'ISO 7',
            'basis': ['GB 50591-2010'],
            'judgement': ['GB 50472-2008', 'GB 50591-2010'],
            'params': [],
            'summary': {
                'result_state': '合格',
                'judgement_active': ['GB 50472-2008'],
                'basis_primary': 'GB 50591-2010',
                'judgement_primary': 'GB 50472-2008'
            },
            'context': {
                'iso_level': 'ISO 7'
            }
        }]
    }

    with app.test_client() as client:
        assert _login(client), '登录失败'

        resp = client.post('/api/x/save_draft', data=json.dumps({'project': payload}), content_type='application/json')
        draft_data = resp.get_json()
        print(f"1. 草稿保存: {draft_data.get('draft_id', 'FAILED')}")
        assert draft_data.get('success') is True

        resp = client.post('/api/x/submit_export', data=json.dumps({'project': payload}), content_type='application/json')
        export_data = resp.get_json()
        print(f"2. 导出提交: {export_data.get('export_id', '')}")
        assert export_data.get('success') is True, export_data

        export_payload = export_data.get('export_payload', {})
        room = export_payload.get('room', {})
        print(f"   export_type: {export_payload.get('export_type')}")
        print(f"   template_key: {(export_payload.get('template_rule') or {}).get('template_key', '')}")
        print(f"   room_context: {room.get('context', {})}")

        assert export_payload.get('export_type') == 'electronics_workshop'
        assert room.get('type_id') == 'electronics_workshop'
        assert room.get('context', {}).get('iso_level') == 'ISO 7'


if __name__ == '__main__':
    test_electronics_workshop()
