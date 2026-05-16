#!/usr/bin/env python3
"""
X1 第一阶段深测：food_workshop + veterinary_gmp_workshop 判定专项
目标：把 food 4级与 veterinary_gmp 4级从“在线主链通过”推进到“后端判定显性化通过”。
"""
import json
import requests

BASE = 'http://localhost:8082'
s = requests.Session()


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def build_payload(domain, type_id, level, params, project_name, context=None):
    room = {
        'type_id': type_id,
        'type_name': type_id,
        'room_name': f'{level}样本01',
        'level_name': level,
        'clean_class': level,
        'params': params,
        'summary': {'result_state': '合格'}
    }
    if context:
        room['context'] = context
    return {
        'project_name': project_name,
        'report_number': f'TEST-{type_id}-{level}'.replace(' ', '').replace('/', '-'),
        'client_name': '测试单位',
        'detection_date': '2026-05-03',
        'domain': domain,
        'rooms': [room]
    }


def run_case(name, domain, type_id, level, params, expected_state, min_abnormal_items=0, context=None):
    payload = build_payload(domain, type_id, level, params, name, context=context)
    r = s.post(f'{BASE}/api/x/build_export', json={'project': payload}, timeout=60)
    body = r.json()
    data = body.get('export_payload') or {}
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
        'type_id': type_id,
        'level': level,
        'expected_state': expected_state,
        'actual_state': summary.get('result_state'),
        'judgement_engine': summary.get('judgement_engine', ''),
        'judgement_reason': summary.get('judgement_reason', ''),
        'abnormal_count': len(abnormal_items),
        'abnormal_items': abnormal_items,
        'matched_level': jr.get('matched_level', ''),
        'ok': ok,
    }


def main():
    assert login(), 'login failed'
    cases = [
        # food_workshop 4级
        ('food_grade_1_normal', 'food', 'food_workshop', 'Ⅰ级', {'temperature': {'values': ['22']}, 'humidity': {'values': ['55']}}, '合格', 0, None),
        ('food_grade_1_abnormal', 'food', 'food_workshop', 'Ⅰ级', {'temperature': {'values': ['40']}, 'humidity': {'values': ['85']}}, '不合格', 2, None),
        ('food_grade_2_normal', 'food', 'food_workshop', 'Ⅱ级', {'airchange': {'values': ['25']}, 'humidity': {'values': ['55']}}, '合格', 0, None),
        ('food_grade_2_abnormal', 'food', 'food_workshop', 'Ⅱ级', {'airchange': {'values': ['10']}, 'humidity': {'values': ['85']}}, '不合格', 2, None),
        ('food_grade_3_normal', 'food', 'food_workshop', 'Ⅲ级', {'airchange': {'values': ['15']}, 'temperature': {'values': ['22']}}, '合格', 0, None),
        ('food_grade_3_abnormal', 'food', 'food_workshop', 'Ⅲ级', {'airchange': {'values': ['5']}, 'temperature': {'values': ['40']}}, '不合格', 2, None),
        ('food_grade_4_normal', 'food', 'food_workshop', 'Ⅳ级', {'airchange': {'values': ['12']}, 'temperature': {'values': ['22']}}, '合格', 0, None),
        ('food_grade_4_abnormal', 'food', 'food_workshop', 'Ⅳ级', {'airchange': {'values': ['2']}, 'temperature': {'values': ['40']}}, '不合格', 2, None),

        # veterinary_gmp_workshop 4级
        ('vet_gmp_A_normal', 'pharma', 'veterinary_gmp_workshop', 'A级', {'wind_speed': {'values': ['0.45']}, 'temperature': {'values': ['22']}}, '合格', 0, None),
        ('vet_gmp_A_abnormal', 'pharma', 'veterinary_gmp_workshop', 'A级', {'wind_speed': {'values': ['0.20']}, 'temperature': {'values': ['40']}}, '不合格', 1, None),
        ('vet_gmp_B_normal', 'pharma', 'veterinary_gmp_workshop', 'B级', {'airchange': {'values': ['50']}, 'temperature': {'values': ['22']}}, '合格', 0, None),
        ('vet_gmp_B_abnormal', 'pharma', 'veterinary_gmp_workshop', 'B级', {'airchange': {'values': ['10']}, 'temperature': {'values': ['40']}}, '不合格', 1, None),
        ('vet_gmp_C_normal', 'pharma', 'veterinary_gmp_workshop', 'C级', {'airchange': {'values': ['25']}, 'temperature': {'values': ['22']}}, '合格', 0, None),
        ('vet_gmp_C_abnormal', 'pharma', 'veterinary_gmp_workshop', 'C级', {'airchange': {'values': ['5']}, 'temperature': {'values': ['40']}}, '不合格', 1, None),
        ('vet_gmp_D_normal', 'pharma', 'veterinary_gmp_workshop', 'D级', {'airchange': {'values': ['15']}, 'temperature': {'values': ['22']}}, '合格', 0, None),
        ('vet_gmp_D_abnormal', 'pharma', 'veterinary_gmp_workshop', 'D级', {'airchange': {'values': ['2']}, 'temperature': {'values': ['40']}}, '不合格', 1, None),
    ]
    results = [run_case(*case) for case in cases]
    passed = sum(1 for r in results if r['ok'])
    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
