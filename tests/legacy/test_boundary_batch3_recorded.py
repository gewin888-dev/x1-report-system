#!/usr/bin/env python3
"""
X1 第三批边界测试实跑记录器
覆盖：negative_pressure / clean_function_room / food_workshop / electronics_workshop
继续扩大 5 点边界留痕对象面。
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
        'export_id': body.get('export_id', ''),
        'ok': summary.get('result_state') == case['expected_state'],
    }


def main():
    assert login(), 'login failed'
    cases = []

    base_np = {
        'type_id':'negative_pressure','room_name':'负压病房','level_name':'负压病房','clean_class':'负压病房','context':{'negative_pressure_mode':'standard'},
        'params':[
            {'key':'airchange','value':'12'},{'key':'airchange_clean','value':'8'},{'key':'pressure','value':'-7'},
            {'key':'temperature','value':'23'},{'key':'humidity','value':'50'},{'key':'noise','value':'48'},
            {'key':'illumination','value':'120'},{'key':'bacteria','value':'4'},{'key':'surface_bacteria','value':'6'}
        ], 'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '19.9', '不合格'), ('low_eq', '20.0', '合格'), ('low_in', '20.1', '合格'), ('high_in', '25.9', '合格'), ('high_out', '26.1', '不合格')]:
        room = dict(base_np)
        room['params'] = merge_params(base_np['params'], 'temperature', value)
        cases.append({'case_id': f'np_temp_{suffix}', 'domain': 'hospital', 'parameter': 'temperature', 'input_value': value, 'expected_state': expected, 'room': room})

    base_cfr = {
        'type_id':'clean_function_room','room_name':'通用洁净功能用房','level_name':'Ⅲ级（万级）','clean_class':'Ⅲ级（万级）','context':{'clean_function_subroom':'通用洁净功能用房'},
        'params':[
            {'key':'airchange','value':'12'},{'key':'pressure','value':'8'},{'key':'hepa_leak','value':'0.01'},
            {'key':'temperature','value':'24'},{'key':'noise','value':'50'},{'key':'illumination','value':'100'},
            {'key':'settling','value':'3'},{'key':'floating','value':'300'}
        ], 'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '4', '不合格'), ('low_eq', '5', '合格'), ('low_in', '6', '合格'), ('high_in', '9', '合格'), ('high_out', '11', '不合格')]:
        room = dict(base_cfr)
        room['params'] = merge_params(base_cfr['params'], 'pressure', value)
        cases.append({'case_id': f'cfr_pressure_{suffix}', 'domain': 'hospital', 'parameter': 'pressure', 'input_value': value, 'expected_state': expected, 'room': room})

    base_food = {
        'type_id':'food_workshop','room_name':'食品车间Ⅲ级','level_name':'Ⅲ级','clean_class':'Ⅲ级','context':{'food_grade':'Ⅲ级'},
        'params':[
            {'key':'airchange','value':'15'},{'key':'pressure','value':'6'},{'key':'temperature','value':'22'},
            {'key':'humidity','value':'50'},{'key':'noise','value':'55'},{'key':'illumination_general_processing','value':'220'},
            {'key':'illumination_mixed_processing','value':'520'},{'key':'illumination_non_processing','value':'120'},
            {'key':'settling','value':'3'},{'key':'floating','value':'80'}
        ], 'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '17.9', '不合格'), ('low_eq', '18.0', '合格'), ('low_in', '18.1', '合格'), ('high_in', '25.9', '合格'), ('high_out', '26.1', '不合格')]:
        room = dict(base_food)
        room['params'] = merge_params(base_food['params'], 'temperature', value)
        cases.append({'case_id': f'food3_temp_{suffix}', 'domain': 'food', 'parameter': 'temperature', 'input_value': value, 'expected_state': expected, 'room': room})

    base_elec = {
        'type_id':'electronics_workshop','room_name':'电子ISO6','level_name':'ISO 6','clean_class':'ISO 6','context':{'iso_level':'ISO 6'},
        'params':[
            {'key':'particle','value':'20000'},{'key':'airchange','value':'55'},{'key':'pressure','value':'8'},
            {'key':'noise','value':'58'},{'key':'illumination_main','value':'400'},{'key':'illumination_aux','value':'250'},
            {'key':'temperature','value':'24'},{'key':'humidity','value':'55'}
        ], 'summary':{'result_state':'合格'}
    }
    for suffix, value, expected in [('low_out', '49', '不合格'), ('low_eq', '50', '合格'), ('low_in', '51', '合格'), ('high_in', '59', '合格'), ('high_out', '61', '不合格')]:
        room = dict(base_elec)
        room['params'] = merge_params(base_elec['params'], 'airchange', value)
        cases.append({'case_id': f'elec6_airchange_{suffix}', 'domain': 'electronics', 'parameter': 'airchange', 'input_value': value, 'expected_state': expected, 'room': room})

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'boundary_records_batch3_{ts}.json'
    out_md = REPORTS / f'boundary_summary_batch3_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 第三批边界测试记录', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
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
