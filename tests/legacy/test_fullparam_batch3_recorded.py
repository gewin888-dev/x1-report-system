#!/usr/bin/env python3
"""
X1 全参数测试记录器（Batch 3）
覆盖：gmp_workshop / veterinary_gmp_workshop / electronics_workshop / food_workshop
本批继续扩大“接近全参数”的有效样本覆盖，并增加 1 组异常样本验证。
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
            'case_id': 'fullparam_gmp_c_good', 'domain': 'pharma', 'expected_state': '合格',
            'room': {
                'type_id':'gmp_workshop','room_name':'GMP车间C级','level_name':'C级','clean_class':'C级','context':{'gmp_grade':'C级'},
                'params':[
                    {'key':'particle','value':'100000'},{'key':'airchange','value':'30'},{'key':'pressure','value':'12'},
                    {'key':'temperature','value':'22'},{'key':'humidity','value':'50'},{'key':'noise','value':'58'},
                    {'key':'illumination_main_room','value':'350'},{'key':'illumination_aux_room','value':'220'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_vet_gmp_b_good', 'domain': 'pharma', 'expected_state': '合格',
            'room': {
                'type_id':'veterinary_gmp_workshop','room_name':'兽药GMP车间B级','level_name':'B级','clean_class':'B级','context':{'gmp_grade':'B级'},
                'params':[
                    {'key':'particle','value':'20'},{'key':'airchange','value':'50'},{'key':'pressure','value':'12'},
                    {'key':'noise','value':'58'},{'key':'illumination_main_room','value':'350'},{'key':'illumination_aux_room','value':'220'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_electronics_iso6_good', 'domain': 'electronics', 'expected_state': '合格',
            'room': {
                'type_id':'electronics_workshop','room_name':'电子ISO6','level_name':'ISO 6','clean_class':'ISO 6','context':{'iso_level':'ISO 6'},
                'params':[
                    {'key':'particle','value':'20000'},{'key':'airchange','value':'55'},{'key':'pressure','value':'8'},
                    {'key':'noise','value':'58'},{'key':'illumination_main','value':'400'},{'key':'illumination_aux','value':'250'},
                    {'key':'temperature','value':'24'},{'key':'humidity','value':'55'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_food_grade2_good', 'domain': 'food', 'expected_state': '合格',
            'room': {
                'type_id':'food_workshop','room_name':'食品车间Ⅱ级','level_name':'Ⅱ级','clean_class':'Ⅱ级','context':{'food_grade':'Ⅱ级'},
                'params':[
                    {'key':'airchange','value':'22'},{'key':'pressure','value':'12'},{'key':'temperature','value':'23'},
                    {'key':'humidity','value':'55'},{'key':'noise','value':'58'},{'key':'illumination_general_processing','value':'220'},
                    {'key':'illumination_mixed_processing','value':'520'},{'key':'illumination_non_processing','value':'120'},
                    {'key':'settling','value':'1'},{'key':'floating','value':'40'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_food_grade2_bad_temp', 'domain': 'food', 'expected_state': '不合格',
            'room': {
                'type_id':'food_workshop','room_name':'食品车间Ⅱ级异常温度','level_name':'Ⅱ级','clean_class':'Ⅱ级','context':{'food_grade':'Ⅱ级'},
                'params':[
                    {'key':'airchange','value':'22'},{'key':'pressure','value':'12'},{'key':'temperature','value':'30'},
                    {'key':'humidity','value':'55'},{'key':'noise','value':'58'},{'key':'illumination_general_processing','value':'220'},
                    {'key':'illumination_mixed_processing','value':'520'},{'key':'illumination_non_processing','value':'120'},
                    {'key':'settling','value':'1'},{'key':'floating','value':'40'}
                ], 'summary':{'result_state':'合格'}
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'fullparam_records_batch3_{ts}.json'
    out_md = REPORTS / f'fullparam_summary_batch3_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 全参数测试记录 Batch3', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
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
