#!/usr/bin/env python3
"""
X1 第一阶段深测：electronics_workshop 5级异常样本判定专项
目标：把 electronics ISO 5~9 从“在线主链通过”推进到“后端判定显性化通过”。
"""
import json
import requests

BASE = 'http://localhost:8082'
s = requests.Session()


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def build_payload(iso, params, project_name):
    return {
        'project_name': project_name,
        'report_number': f'TEST-{iso.replace(" ", "").replace("-", "")}',
        'client_name': '测试单位',
        'detection_date': '2026-05-03',
        'domain': 'electronics',
        'rooms': [{
            'type_id': 'electronics_workshop',
            'type_name': '电子洁净车间',
            'room_name': f'{iso}车间01',
            'level_name': iso,
            'clean_class': iso,
            'context': {'iso_level': iso},
            'params': params,
            'summary': {'result_state': '合格'}
        }]
    }


def run_case(name, iso, params, expected_state, min_abnormal_items):
    payload = build_payload(iso, params, name)
    r = s.post(f'{BASE}/api/x/build_export', json={'project': payload}, timeout=60)
    data = r.json().get('export_payload') or {}
    summary = ((data.get('room') or {}).get('summary') or {})
    jr = data.get('judgement_result') or {}
    abnormal_items = jr.get('abnormal_items') or []
    ok = (
        summary.get('result_state') == expected_state
        and bool(summary.get('judgement_engine', ''))
        and bool(summary.get('judgement_reason', ''))
        and len(abnormal_items) >= min_abnormal_items
    )
    return {
        'name': name,
        'iso': iso,
        'expected_state': expected_state,
        'actual_state': summary.get('result_state'),
        'judgement_engine': summary.get('judgement_engine', ''),
        'judgement_reason': summary.get('judgement_reason', ''),
        'abnormal_count': len(abnormal_items),
        'abnormal_items': abnormal_items,
        'ok': ok,
    }


def main():
    assert login(), 'login failed'
    cases = [
        ('electronics_iso5_normal', 'ISO 5', {'wind_speed': {'values': ['0.35']}, 'temperature': {'values': ['23']}, 'humidity': {'values': ['55']}}, '合格', 0),
        ('electronics_iso5_abnormal', 'ISO 5', {'wind_speed': {'values': ['0.10']}, 'temperature': {'values': ['40']}, 'humidity': {'values': ['80']}}, '不合格', 2),
        ('electronics_iso6_normal', 'ISO 6', {'airchange': {'values': ['55']}, 'temperature': {'values': ['23']}, 'humidity': {'values': ['55']}}, '合格', 0),

        ('electronics_iso6_abnormal', 'ISO 6', {'airchange': {'values': ['5']}, 'temperature': {'values': ['40']}, 'humidity': {'values': ['80']}}, '不合格', 2),
        ('electronics_iso7_normal', 'ISO 7', {'airchange': {'values': ['20']}, 'temperature': {'values': ['23']}, 'humidity': {'values': ['55']}}, '合格', 0),
        ('electronics_iso7_abnormal', 'ISO 7', {'airchange': {'values': ['4']}, 'temperature': {'values': ['40']}, 'humidity': {'values': ['80']}}, '不合格', 2),
        ('electronics_iso8_normal', 'ISO 8', {'airchange': {'values': ['12']}, 'temperature': {'values': ['23']}, 'humidity': {'values': ['55']}}, '合格', 0),

        ('electronics_iso8_abnormal', 'ISO 8', {'airchange': {'values': ['3']}, 'temperature': {'values': ['40']}, 'humidity': {'values': ['80']}}, '不合格', 2),
        ('electronics_iso9_normal', 'ISO 9', {'airchange': {'values': ['15']}, 'temperature': {'values': ['23']}, 'humidity': {'values': ['55']}}, '合格', 0),
        ('electronics_iso9_abnormal', 'ISO 9', {'airchange': {'values': ['2']}, 'temperature': {'values': ['40']}, 'humidity': {'values': ['80']}}, '不合格', 2),
    ]
    results = [run_case(*case) for case in cases]
    passed = sum(1 for r in results if r['ok'])
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
