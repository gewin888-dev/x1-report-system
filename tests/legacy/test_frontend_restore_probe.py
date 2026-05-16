#!/usr/bin/env python3
"""
X1 前台页面回填专项探针
目标：不依赖浏览器自动化，先验证 /api/get/<id> 返回的 record 是否携带前台 loadRecordForEdit 所需 summary 字段。
重点字段：result_state / input_result_state / judgement_reason / judgement_overridden / abnormal_items / judgement_engine
"""
import json
import requests
from pathlib import Path
from datetime import datetime

BASE = 'http://localhost:8082'
ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
RECORDS = ROOT / 'records_x1'
REPORTS = ROOT / 'reports_x1'
s = requests.Session()


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def save_probe_record():
    payload = {
        'project': {
            'project_name': 'front_restore_probe',
            'report_number': 'front_restore_probe',
            'client_name': '前台回填专项',
            'detection_date': '2026-05-03',
            'domain': 'pharma',
            'rooms': [{
                'room_id': 'r1',
                'room_name': '传递窗01',
                'type_id': 'pass_box',
                'level_name': '默认',
                'clean_class': '默认',
                'params': [
                    {'key': 'noise', 'value': '80'},
                    {'key': 'hepa_leak', 'value': '0.05'}
                ],
                'summary': {
                    'result_state': '不合格',
                    'input_result_state': '合格',
                    'judgement_engine': 'pass_box_v1',
                    'judgement_reason': '存在超出标准范围的检测项',
                    'judgement_overridden': True,
                    'abnormal_items': [
                        {'key': 'noise', 'value': 80, 'range': '≤68', 'passed': False},
                        {'key': 'hepa_leak', 'value': 0.05, 'range': '≤0.01%', 'passed': False}
                    ]
                },
                'pass_box_result_state': '不合格',
                'context': {}
            }]
        }
    }
    r = s.post(f'{BASE}/api/x/save_draft', json=payload, timeout=30)
    r.raise_for_status()
    body = r.json()
    return body['draft_id']


def main():
    assert login(), 'login failed'
    record_id = save_probe_record()
    res = s.get(f'{BASE}/api/get/{record_id}', timeout=30)
    res.raise_for_status()
    body = res.json()
    assert body.get('success') is True, body
    record = body.get('record') or {}
    room = (record.get('rooms') or [{}])[0]
    summary = room.get('summary') or {}

    checks = {
        'has_record_id': bool(record.get('record_id')),
        'has_room': bool(room.get('type_id')),
        'summary_result_state': summary.get('result_state') == '不合格',
        'summary_input_result_state': summary.get('input_result_state') == '合格',
        'summary_judgement_engine': summary.get('judgement_engine') == 'pass_box_v1',
        'summary_judgement_reason': summary.get('judgement_reason') == '存在超出标准范围的检测项',
        'summary_judgement_overridden': summary.get('judgement_overridden') is True,
        'summary_abnormal_items': isinstance(summary.get('abnormal_items'), list) and len(summary.get('abnormal_items')) == 2,
        'pass_box_result_state': room.get('pass_box_result_state') == '不合格',
    }

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out = REPORTS / f'frontend_restore_probe_{ts}.json'
    out.write_text(json.dumps({
        'generated_at': ts,
        'record_id': record_id,
        'checks': checks,
        'record_excerpt': {
            'record_id': record.get('record_id'),
            'type_id': room.get('type_id'),
            'summary': summary,
            'pass_box_result_state': room.get('pass_box_result_state'),
        }
    }, ensure_ascii=False, indent=2), encoding='utf-8')
    passed = sum(1 for v in checks.values() if v)
    print(out)
    print(f'SUMMARY {passed}/{len(checks)}')
    if passed != len(checks):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
