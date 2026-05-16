#!/usr/bin/env python3
"""
X1 全参数测试记录器（Batch 4）
覆盖：operating_room / clean_function_room / negative_pressure / bsl
本批继续补医院/生物安全方向的全参数正常样本与异常样本。
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
        'client_name': '全参数测试单位',
        'detection_date': '2026-05-03',
        'domain': domain,
        'rooms': [room]
    }


def run_case(case):
    print(f"RUN {case['case_id']}", flush=True)
    project = make_project(case['case_id'], case['domain'], case['room'])
    s.post(f'{BASE}/api/x/save_draft', json={'project': project}, timeout=30)
    r = s.post(f'{BASE}/api/x/submit_export', json={'project': project}, timeout=90)
    body = r.json()
    ep = body.get('export_payload') or {}
    room = ep.get('room') or {}
    summary = room.get('summary') or {}
    jr = ep.get('judgement_result') or {}
    abnormal_items = jr.get('abnormal_items') or []
    return {
        'case_id': case['case_id'],
        'type_id': room.get('type_id') or case['room']['type_id'],
        'template_key': (ep.get('template_rule') or {}).get('template_key', ''),
        'result_state': summary.get('result_state', ''),
        'judgement_engine': summary.get('judgement_engine', ''),
        'judgement_reason': summary.get('judgement_reason', ''),
        'abnormal_count': len(abnormal_items),
        'param_count': len(case['room'].get('params') or []),
        'expected_state': case['expected_state'],
        'export_id': body.get('export_id', ''),
        'ok': bool(body.get('export_id')) and summary.get('result_state') == case['expected_state'] and bool(summary.get('judgement_engine')),
    }


def main():
    assert login(), 'login failed'
    cases = [
        {
            'case_id': 'fullparam_operating_main_l2_good', 'domain': 'hospital', 'expected_state': '合格',
            'room': {
                'type_id':'operating_room','room_name':'千级手术室','level_name':'Ⅱ级','clean_class':'Ⅱ级',
                'context':{'room_type':'main-room','clean_class_code':'level2'},
                'params':[
                    {'key':'airchange','value':'24'},{'key':'pressure','value':'8'},{'key':'temperature','value':'23'},
                    {'key':'humidity','value':'50'},{'key':'noise','value':'48'},{'key':'illumination_min','value':'360'},
                    {'key':'illumination','value':'320'},{'key':'temp_diff','value':'1'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_operating_main_l2_bad_pressure', 'domain': 'hospital', 'expected_state': '不合格',
            'room': {
                'type_id':'operating_room','room_name':'千级手术室压差异常','level_name':'Ⅱ级','clean_class':'Ⅱ级',
                'context':{'room_type':'main-room','clean_class_code':'level2'},
                'params':[
                    {'key':'airchange','value':'24'},{'key':'pressure','value':'4'},{'key':'temperature','value':'23'},
                    {'key':'humidity','value':'50'},{'key':'noise','value':'48'},{'key':'illumination_min','value':'360'},
                    {'key':'illumination','value':'320'},{'key':'temp_diff','value':'1'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_clean_function_l3_good', 'domain': 'hospital', 'expected_state': '合格',
            'room': {
                'type_id':'clean_function_room','room_name':'通用洁净功能用房','level_name':'Ⅲ级（万级）','clean_class':'Ⅲ级（万级）',
                'context':{'clean_function_subroom':'通用洁净功能用房'},
                'params':[
                    {'key':'airchange','value':'12'},{'key':'pressure','value':'8'},{'key':'hepa_leak','value':'0.01'},
                    {'key':'temperature','value':'24'},{'key':'noise','value':'50'},{'key':'illumination','value':'100'},
                    {'key':'settling','value':'3'},{'key':'floating','value':'300'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_negative_pressure_good', 'domain': 'hospital', 'expected_state': '合格',
            'room': {
                'type_id':'negative_pressure','room_name':'负压病房','level_name':'负压病房','clean_class':'负压病房','context':{'negative_pressure_mode':'standard'},
                'params':[
                    {'key':'airchange','value':'12'},{'key':'airchange_clean','value':'8'},{'key':'pressure','value':'-7'},
                    {'key':'temperature','value':'23'},{'key':'humidity','value':'50'},{'key':'noise','value':'48'},
                    {'key':'illumination','value':'120'},{'key':'bacteria','value':'4'},{'key':'surface_bacteria','value':'6'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_bsl_p2_good', 'domain': 'biosafety', 'expected_state': '合格',
            'room': {
                'type_id':'bsl','room_name':'P2实验室','level_name':'BSL-2（P2）','clean_class':'BSL-2（P2）','context':{'bsl_level':'BSL-2（P2）'},
                'params':[
                    {'key':'airchange','value':'18'},{'key':'pressure','value':'-12'},{'key':'temperature','value':'23'},
                    {'key':'humidity','value':'55'},{'key':'noise','value':'55'},{'key':'illumination','value':'350'},
                    {'key':'settling','value':'2'},{'key':'floating','value':'80'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_bsl_p2_bad_pressure', 'domain': 'biosafety', 'expected_state': '不合格',
            'room': {
                'type_id':'bsl','room_name':'P2实验室压差异常','level_name':'BSL-2（P2）','clean_class':'BSL-2（P2）','context':{'bsl_level':'BSL-2（P2）'},
                'params':[
                    {'key':'airchange','value':'18'},{'key':'pressure','value':'-8'},{'key':'temperature','value':'23'},
                    {'key':'humidity','value':'55'},{'key':'noise','value':'55'},{'key':'illumination','value':'350'},
                    {'key':'settling','value':'2'},{'key':'floating','value':'80'}
                ], 'summary':{'result_state':'合格'}
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'fullparam_records_batch4_{ts}.json'
    out_md = REPORTS / f'fullparam_summary_batch4_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 全参数测试记录 Batch4', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
    lines.append('| case_id | type_id | param_count | expected | actual | abnormal_count | template_key | engine | export_id | ok |')
    lines.append('|---|---|---:|---|---|---:|---|---|---|---|')
    for r in results:
        lines.append(f"| {r['case_id']} | {r['type_id']} | {r['param_count']} | {r['expected_state']} | {r['result_state']} | {r['abnormal_count']} | {r['template_key']} | {r['judgement_engine']} | {r['export_id']} | {'PASS' if r['ok'] else 'FAIL'} |")
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    passed = sum(1 for r in results if r['ok'])
    print(out_json)
    print(out_md)
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
