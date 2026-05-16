#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BASE = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(BASE))

from app_x1 import app, _x_draft_path  # noqa: E402

DRAFT_ID = 'X1DRAFT_RESULT_SUMMARY_LOOP_TEST'

PAYLOAD = {
    'draft_id': DRAFT_ID,
    'project_name': '结果承接闭环验证',
    'report_number': 'RESULT-LOOP-001',
    'client_name': '测试单位',
    'detection_date': '2026-05-03',
    'domain': 'electronics',
    'rooms': [{
        'room_id': 'ROOM_1',
        'room_name': '电子车间1',
        'type_id': 'electronics_workshop',
        'type_name': '电子车间',
        'clean_class': 'ISO 7',
        'summary': {
            'result_state': '合格',
            'input_result_state': '不合格',
            'judgement_engine': 'backend-rule-engine',
            'judgement_reason': '测试原因',
            'judgement_overridden': True,
            'abnormal_items': [
                {'item_name': '温度', 'result': '不合格'},
                {'item_name': '湿度', 'result': '不合格'}
            ],
            'judgement_active': ['温度'],
            'basis_primary': 'GB 50073-2013',
            'judgement_primary': '温度'
        },
        'params': {}
    }]
}

EXPECT_SUMMARY = PAYLOAD['rooms'][0]['summary']


def extract_summary(obj: dict) -> dict:
    rooms = (obj.get('record') or {}).get('rooms') or []
    room = rooms[0] if rooms else {}
    return room.get('summary') or {}


def main():
    client = app.test_client()
    draft_path = _x_draft_path(DRAFT_ID)
    draft_path.unlink(missing_ok=True)

    try:
        save_res = client.post('/api/save', json=PAYLOAD)
        save_json = save_res.get_json(silent=True) or {}

        saved_file_summary = {}
        if draft_path.exists():
            data = json.loads(draft_path.read_text(encoding='utf-8'))
            saved_file_summary = (((data.get('project') or {}).get('rooms') or [{}])[0].get('summary') or {})

        load_res = client.get(f'/api/get/{DRAFT_ID}')
        load_json = load_res.get_json(silent=True) or {}
        loaded_summary = extract_summary(load_json)

        result = {
            'save_status': save_res.status_code,
            'save_success': save_json.get('success') is True,
            'file_exists': draft_path.exists(),
            'saved_file_summary': saved_file_summary,
            'loaded_summary': loaded_summary,
            'expect_summary': EXPECT_SUMMARY,
            'ok': (
                save_res.status_code == 200
                and save_json.get('success') is True
                and draft_path.exists()
                and saved_file_summary == EXPECT_SUMMARY
                and loaded_summary == EXPECT_SUMMARY
            )
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        draft_path.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
