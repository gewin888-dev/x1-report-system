#!/usr/bin/env python3
"""
X1 主矩阵第一批全参数深测记录器
目标：把 hospital + biosafety 主矩阵中的关键对象推进到：
- 正常样本
- 异常样本
- judgement_engine / judgement_reason
- abnormal_items
留下可审计记录。
"""
import json
import requests
from datetime import datetime
from pathlib import Path

BASE = 'http://localhost:8082'
ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
REPORTS = ROOT / 'reports_x1'
s = requests.Session()


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def run_case(case):
    r = s.post(f'{BASE}/api/x/build_export', json={'project': case['project']}, timeout=60)
    body = r.json()
    if r.status_code != 200:
        return {
            'name': case['name'],
            'type_id': case['type_id'],
            'expected_state': case['expected_state'],
            'actual_state': None,
            'judgement_engine': '',
            'judgement_reason': '',
            'matched_level': '',
            'abnormal_count': 0,
            'abnormal_items': [],
            'ok': False,
            'http_status': r.status_code,
            'error': body.get('error', body),
        }
    ep = body.get('export_payload') or {}
    summary = ((ep.get('room') or {}).get('summary') or {})
    jr = ep.get('judgement_result') or {}
    abnormal_items = jr.get('abnormal_items') or []
    ok = (
        summary.get('result_state') == case['expected_state']
        and bool(summary.get('judgement_engine', ''))
        and bool(summary.get('judgement_reason', ''))
        and len(abnormal_items) >= case.get('min_abnormal_items', 0)
    )
    return {
        'name': case['name'],
        'type_id': case['type_id'],
        'expected_state': case['expected_state'],
        'actual_state': summary.get('result_state'),
        'judgement_engine': summary.get('judgement_engine', ''),
        'judgement_reason': summary.get('judgement_reason', ''),
        'matched_level': jr.get('matched_level', ''),
        'abnormal_count': len(abnormal_items),
        'abnormal_items': abnormal_items,
        'ok': ok,
    }


def main():
    assert login(), 'login failed'
    cases = [
        {
            'name': 'operating_room_L1_normal',
            'type_id': 'operating_room',
            'expected_state': '合格',
            'min_abnormal_items': 0,
            'project': {
                'project_name': 'operating_room_L1_normal','report_number':'B1-001','client_name':'测试单位','detection_date':'2026-05-03','domain': 'hospital',
                'rooms': [{
                    'type_id': 'operating_room','room_name': '百级手术室','level_name': 'Ⅰ级','clean_class': 'Ⅰ级',
                    'context': {'room_type': 'main-room', 'clean_class_code': 'level1'},
                    'params': [{'key': 'temperature', 'value': '22'}, {'key': 'humidity', 'value': '55'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'operating_room_L1_abnormal',
            'type_id': 'operating_room',
            'expected_state': '不合格',
            'min_abnormal_items': 2,
            'project': {
                'project_name': 'operating_room_L1_abnormal','report_number':'B1-002','client_name':'测试单位','detection_date':'2026-05-03','domain': 'hospital',
                'rooms': [{
                    'type_id': 'operating_room','room_name': '百级手术室','level_name': 'Ⅰ级','clean_class': 'Ⅰ级',
                    'context': {'room_type': 'main-room', 'clean_class_code': 'level1'},
                    'params': [{'key': 'temperature', 'value': '40'}, {'key': 'humidity', 'value': '90'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'clean_function_icu_normal',
            'type_id': 'clean_function_room',
            'expected_state': '合格',
            'min_abnormal_items': 0,
            'project': {
                'project_name': 'clean_function_icu_normal','report_number':'B1-003','client_name':'测试单位','detection_date':'2026-05-03','domain': 'hospital',
                'rooms': [{
                    'type_id': 'clean_function_room','room_name': 'ICU病房','level_name': 'ICU病房','clean_class': 'ICU病房',
                    'context': {'clean_function_subroom': 'ICU病房'},
                    'params': [{'key': 'temperature', 'value': '23'}, {'key': 'humidity', 'value': '55'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'clean_function_icu_abnormal',
            'type_id': 'clean_function_room',
            'expected_state': '不合格',
            'min_abnormal_items': 2,
            'project': {
                'project_name': 'clean_function_icu_abnormal','report_number':'B1-004','client_name':'测试单位','detection_date':'2026-05-03','domain': 'hospital',
                'rooms': [{
                    'type_id': 'clean_function_room','room_name': 'ICU病房','level_name': 'ICU病房','clean_class': 'ICU病房',
                    'context': {'clean_function_subroom': 'ICU病房'},
                    'params': [{'key': 'temperature', 'value': '40'}, {'key': 'humidity', 'value': '90'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'negative_pressure_normal',
            'type_id': 'negative_pressure',
            'expected_state': '合格',
            'min_abnormal_items': 0,
            'project': {
                'project_name': 'negative_pressure_normal','report_number':'B1-005','client_name':'测试单位','detection_date':'2026-05-03','domain': 'hospital',
                'rooms': [{
                    'type_id': 'negative_pressure','room_name': '负压病房01','level_name': '负压病房','clean_class': '负压病房',
                    'context': {'negative_pressure_mode': 'ward-pressure-driven'},
                    'params': [{'key': 'humidity', 'value': '55'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'negative_pressure_abnormal',
            'type_id': 'negative_pressure',
            'expected_state': '不合格',
            'min_abnormal_items': 1,
            'project': {
                'project_name': 'negative_pressure_abnormal','report_number':'B1-006','client_name':'测试单位','detection_date':'2026-05-03','domain': 'hospital',
                'rooms': [{
                    'type_id': 'negative_pressure','room_name': '负压病房01','level_name': '负压病房','clean_class': '负压病房',
                    'context': {'negative_pressure_mode': 'ward-pressure-driven'},
                    'params': [{'key': 'humidity', 'value': '85'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'bsl_p2_normal',
            'type_id': 'bsl',
            'expected_state': '合格',
            'min_abnormal_items': 0,
            'project': {
                'project_name': 'bsl_p2_normal','report_number':'B1-007','client_name':'测试单位','detection_date':'2026-05-03','domain': 'biosafety',
                'rooms': [{
                    'type_id': 'bsl','room_name': 'P2实验室','level_name': 'BSL-2（P2）','clean_class': 'BSL-2（P2）',
                    'context': {'bsl_level': 'BSL-2（P2）'},
                    'params': [{'key': 'temperature', 'value': '22'}, {'key': 'humidity', 'value': '55'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'bsl_p2_abnormal',
            'type_id': 'bsl',
            'expected_state': '不合格',
            'min_abnormal_items': 2,
            'project': {
                'project_name': 'bsl_p2_abnormal','report_number':'B1-008','client_name':'测试单位','detection_date':'2026-05-03','domain': 'biosafety',
                'rooms': [{
                    'type_id': 'bsl','room_name': 'P2实验室','level_name': 'BSL-2（P2）','clean_class': 'BSL-2（P2）',
                    'context': {'bsl_level': 'BSL-2（P2）'},
                    'params': [{'key': 'temperature', 'value': '40'}, {'key': 'humidity', 'value': '90'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'animal_room_normal_env_normal',
            'type_id': 'animal_room',
            'expected_state': '合格',
            'min_abnormal_items': 0,
            'project': {
                'project_name': 'animal_room_normal_env_normal','report_number':'B1-009','client_name':'测试单位','detection_date':'2026-05-03','domain': 'biosafety',
                'rooms': [{
                    'type_id': 'animal_room','room_name': '普通环境饲养室','level_name': '普通环境','clean_class': '普通环境',
                    'context': {'animal_environment': '普通环境', 'barrier_room_class': '饲养室'},
                    'params': [{'key': 'temperature', 'value': '22'}, {'key': 'humidity', 'value': '55'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'animal_room_normal_env_abnormal',
            'type_id': 'animal_room',
            'expected_state': '不合格',
            'min_abnormal_items': 2,
            'project': {
                'project_name': 'animal_room_normal_env_abnormal','report_number':'B1-010','client_name':'测试单位','detection_date':'2026-05-03','domain': 'biosafety',
                'rooms': [{
                    'type_id': 'animal_room','room_name': '普通环境饲养室','level_name': '普通环境','clean_class': '普通环境',
                    'context': {'animal_environment': '普通环境', 'barrier_room_class': '饲养室'},
                    'params': [{'key': 'temperature', 'value': '40'}, {'key': 'humidity', 'value': '90'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'bsc_normal',
            'type_id': 'bsc',
            'expected_state': '合格',
            'min_abnormal_items': 0,
            'project': {
                'project_name': 'bsc_normal','report_number':'B1-011','client_name':'测试单位','detection_date':'2026-05-03','domain': 'biosafety',
                'rooms': [{
                    'type_id': 'bsc','room_name': 'BSC01','level_name': 'A2型','clean_class': 'A2型',
                    'params': [{'key': 'wind_speed_down', 'value': '0.35'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
        {
            'name': 'bsc_abnormal',
            'type_id': 'bsc',
            'expected_state': '不合格',
            'min_abnormal_items': 1,
            'project': {
                'project_name': 'bsc_abnormal','report_number':'B1-012','client_name':'测试单位','detection_date':'2026-05-03','domain': 'biosafety',
                'rooms': [{
                    'type_id': 'bsc','room_name': 'BSC01','level_name': 'A2型','clean_class': 'A2型',
                    'params': [{'key': 'wind_speed_down', 'value': '0.05'}],
                    'summary': {'result_state': '合格'}
                }]
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'matrix_batch1_deep_{ts}.json'
    out_md = REPORTS / f'matrix_batch1_deep_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = ['# X1 主矩阵第一批全参数深测记录', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
    lines.append('| name | type_id | actual_state | judgement_engine | abnormal_count | ok |')
    lines.append('|---|---|---|---|---:|---|')
    for r in results:
        lines.append(f"| {r['name']} | {r['type_id']} | {r['actual_state']} | {r['judgement_engine']} | {r['abnormal_count']} | {'PASS' if r['ok'] else 'FAIL'} |")
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    print(out_json)
    print(out_md)
    passed = sum(1 for r in results if r['ok'])
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
