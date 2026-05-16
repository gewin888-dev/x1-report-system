#!/usr/bin/env python3
"""
X1 第二批边界测试实跑记录器
覆盖：operating_room / bsl / electronics_workshop / gmp_workshop
在第一批基础上扩到更多参数，响应“全参数测试才有意义”的要求。
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


def make_project(case_id, domain, room):
    return {
        'project_name': case_id,
        'report_number': case_id[:40],
        'client_name': '边界测试单位',
        'detection_date': '2026-05-03',
        'domain': domain,
        'rooms': [room]
    }


def merge_params(base_params, key, value):
    params = [dict(p) for p in base_params]
    found = False
    for p in params:
        if p.get('key') == key:
            p['value'] = str(value)
            found = True
            break
    if not found:
        params.append({'key': key, 'value': str(value)})
    return params


def run_case(case):
    print(f"RUN {case['case_id']}", flush=True)
    project = make_project(case['case_id'], case['domain'], case['room'])
    s.post(f'{BASE}/api/x/save_draft', json={'project': project}, timeout=30)
    r = s.post(f'{BASE}/api/x/submit_export', json={'project': project}, timeout=90)
    body = r.json()
    ep = body.get('export_payload') or {}
    summary = ((ep.get('room') or {}).get('summary') or {})
    jr = ep.get('judgement_result') or {}
    abnormal_items = jr.get('abnormal_items') or []
    feishu = body.get('feishu') or {}
    return {
        'case_id': case['case_id'],
        'type_id': case['room']['type_id'],
        'parameter': case['parameter'],
        'input_value': case['input_value'],
        'expected_state': case['expected_state'],
        'actual_state': summary.get('result_state'),
        'judgement_engine': summary.get('judgement_engine', ''),
        'judgement_reason': summary.get('judgement_reason', ''),
        'abnormal_count': len(abnormal_items),
        'template_key': (ep.get('template_rule') or {}).get('template_key', ''),
        'draft_saved': True,
        'export_id': body.get('export_id', ''),
        'feishu_report_url': ((feishu.get('report') or {}).get('feishu_url', '')),
        'feishu_export_url': ((feishu.get('export') or {}).get('feishu_url', '')),
        'ok': summary.get('result_state') == case['expected_state'],
    }


def main():
    assert login(), 'login failed'
    cases = []

    base_or = {
        'type_id':'operating_room','room_name':'百级手术室','level_name':'Ⅰ级','clean_class':'Ⅰ级',
        'context':{'room_type':'main-room','clean_class_code':'level1'},
        'params':[
            {'key':'temperature','value':'23.0'},{'key':'humidity','value':'50.0'},{'key':'pressure','value':'10'},
            {'key':'noise','value':'50'},{'key':'illumination','value':'350'},{'key':'wind_speed','value':'0.22'}
        ],'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '29.9', '不合格'), ('low_eq', '30.0', '合格'), ('low_in', '30.1', '合格'), ('high_in', '59.9', '合格'), ('high_out', '60.1', '不合格')]:
        room = dict(base_or)
        room['params'] = merge_params(base_or['params'], 'humidity', value)
        cases.append({'case_id': f'or_humidity_{suffix}', 'domain': 'hospital', 'parameter': 'humidity', 'input_value': value, 'expected_state': expected, 'room': room})

    base_bsl = {
        'type_id':'bsl','room_name':'P2实验室','level_name':'BSL-2（P2）','clean_class':'BSL-2（P2）',
        'context':{'bsl_level':'BSL-2（P2）'},
        'params':[
            {'key':'temperature','value':'22.0'},{'key':'humidity','value':'55.0'},{'key':'pressure','value':'-12'},
            {'key':'noise','value':'55'},{'key':'illumination','value':'350'}
        ],'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '17.9', '不合格'), ('low_eq', '18.0', '合格'), ('low_in', '18.1', '合格'), ('high_in', '26.9', '合格'), ('high_out', '27.1', '不合格')]:
        room = dict(base_bsl)
        room['params'] = merge_params(base_bsl['params'], 'temperature', value)
        cases.append({'case_id': f'bsl_temp_{suffix}', 'domain': 'biosafety', 'parameter': 'temperature', 'input_value': value, 'expected_state': expected, 'room': room})

    base_elec = {
        'type_id':'electronics_workshop','room_name':'电子ISO5','level_name':'ISO 5','clean_class':'ISO 5',
        'context':{'iso_level':'ISO 5'},
        'params':[
            {'key':'wind_speed','value':'0.30'},{'key':'pressure','value':'8'},{'key':'noise','value':'60'},
            {'key':'illumination_main','value':'350'},{'key':'illumination_aux','value':'250'},{'key':'temperature','value':'23'},{'key':'humidity','value':'55'}
        ],'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '0.19', '不合格'), ('low_eq', '0.20', '合格'), ('low_in', '0.21', '合格'), ('high_in', '0.44', '合格'), ('high_out', '0.46', '不合格')]:
        room = dict(base_elec)
        room['params'] = merge_params(base_elec['params'], 'wind_speed', value)
        cases.append({'case_id': f'elec_iso5_wind_{suffix}', 'domain': 'electronics', 'parameter': 'wind_speed', 'input_value': value, 'expected_state': expected, 'room': room})

    base_gmp = {
        'type_id':'gmp_workshop','room_name':'GMP A级','level_name':'A级','clean_class':'A级',
        'context':{'gmp_grade':'A级'},
        'params':[
            {'key':'wind_speed','value':'0.45'},{'key':'pressure','value':'12'},{'key':'noise','value':'60'},
            {'key':'illumination_main_room','value':'350'},{'key':'illumination_aux_room','value':'250'}
        ],'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '0.35', '不合格'), ('low_eq', '0.36', '合格'), ('low_in', '0.37', '合格'), ('high_in', '0.53', '合格'), ('high_out', '0.55', '不合格')]:
        room = dict(base_gmp)
        room['params'] = merge_params(base_gmp['params'], 'wind_speed', value)
        cases.append({'case_id': f'gmp_a_wind_{suffix}', 'domain': 'pharma', 'parameter': 'wind_speed', 'input_value': value, 'expected_state': expected, 'room': room})

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'boundary_records_batch2_{ts}.json'
    out_md = REPORTS / f'boundary_summary_batch2_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 第二批边界测试记录', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
    lines.append('| case_id | type_id | parameter | input_value | expected | actual | engine | template_key | export_id | ok |')
    lines.append('|---|---|---|---:|---|---|---|---|---|---|')
    for r in results:
        lines.append(f"| {r['case_id']} | {r['type_id']} | {r['parameter']} | {r['input_value']} | {r['expected_state']} | {r['actual_state']} | {r['judgement_engine']} | {r['template_key']} | {r['export_id']} | {'PASS' if r['ok'] else 'FAIL'} |")
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    passed = sum(1 for r in results if r['ok'])
    print(out_json)
    print(out_md)
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
