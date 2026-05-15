#!/usr/bin/env python3
"""
X1 全参数测试记录器（Batch 2 扩展版）
目标：把“全参数测试”从骨架推进到真实执行。
当前批次覆盖高价值代表对象：
- operating_room 辅房
- clean_function_room ICU
- negative_pressure
- food_workshop
- electronics_workshop
- veterinary_gmp_workshop

说明：
- 每个 case 尽量提供该对象一组“接近全参数”的输入，而不是单参数冒烟
- 输出 JSON + Markdown，可继续扩展到 51 对象全量
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
    project = make_project(case['case_id'], case['domain'], case['room'])
    s.post(f'{BASE}/api/x/save_draft', json={'project': project}, timeout=30)
    r = s.post(f'{BASE}/api/x/submit_export', json={'project': project}, timeout=90)
    body = r.json()
    ep = body.get('export_payload') or {}
    room = ep.get('room') or {}
    summary = room.get('summary') or {}
    return {
        'case_id': case['case_id'],
        'type_id': room.get('type_id') or case['room']['type_id'],
        'template_key': (ep.get('template_rule') or {}).get('template_key', ''),
        'result_state': summary.get('result_state', ''),
        'judgement_engine': summary.get('judgement_engine', ''),
        'judgement_reason': summary.get('judgement_reason', ''),
        'param_count': len(case['room'].get('params') or []),
        'export_id': body.get('export_id', ''),
        'ok': bool(body.get('export_id')) and bool(summary.get('result_state')) and bool(summary.get('judgement_engine')),
    }


def main():
    assert login(), 'login failed'
    cases = [
        {
            'case_id': 'fullparam_operating_aux_scrub', 'domain': 'hospital',
            'room': {
                'type_id':'operating_room','room_name':'刷手间','level_name':'Ⅱ级（7级）','clean_class':'Ⅱ级（7级）',
                'context':{'surgery_room_type':'辅房','surgery_aux_room':'刷手间'},
                'params':[
                    {'key':'airchange','value':'8'},{'key':'temperature','value':'24'},{'key':'humidity','value':'55'},
                    {'key':'noise','value':'54'},{'key':'work_illumination','value':'180'},{'key':'bacteria','value':'1'}
                ],
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_clean_function_icu', 'domain': 'hospital',
            'room': {
                'type_id':'clean_function_room','room_name':'ICU病房','level_name':'Ⅲ级（万级）','clean_class':'Ⅲ级（万级）',
                'context':{'clean_function_subroom':'ICU病房'},
                'params':[
                    {'key':'airchange','value':'12'},{'key':'pressure','value':'8'},{'key':'hepa_leak','value':'0.01'},
                    {'key':'temperature','value':'24'},{'key':'noise','value':'50'},{'key':'illumination','value':'200'},
                    {'key':'settling','value':'3'},{'key':'floating','value':'300'}
                ],
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_negative_pressure', 'domain': 'hospital',
            'room': {
                'type_id':'negative_pressure','room_name':'负压病房','level_name':'负压病房','clean_class':'负压病房',
                'context':{'negative_pressure_mode':'standard'},
                'params':[
                    {'key':'airchange','value':'12'},{'key':'airchange_clean','value':'8'},{'key':'pressure','value':'-7'},
                    {'key':'temperature','value':'23'},{'key':'humidity','value':'50'},{'key':'noise','value':'48'},
                    {'key':'illumination','value':'120'},{'key':'bacteria','value':'4'},{'key':'surface_bacteria','value':'6'}
                ],
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_food_grade3', 'domain': 'food',
            'room': {
                'type_id':'food_workshop','room_name':'食品车间Ⅲ级','level_name':'Ⅲ级','clean_class':'Ⅲ级','context':{'food_grade':'Ⅲ级'},
                'params':[
                    {'key':'airchange','value':'15'},{'key':'pressure','value':'6'},{'key':'temperature','value':'22'},
                    {'key':'humidity','value':'50'},{'key':'noise','value':'55'},{'key':'illumination_general_processing','value':'220'},
                    {'key':'illumination_mixed_processing','value':'520'},{'key':'illumination_non_processing','value':'120'},
                    {'key':'settling','value':'8'},{'key':'floating','value':'80'}
                ],
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_electronics_iso7', 'domain': 'electronics',
            'room': {
                'type_id':'electronics_workshop','room_name':'电子ISO7','level_name':'ISO 7','clean_class':'ISO 7','context':{'iso_level':'ISO 7'},
                'params':[
                    {'key':'airchange','value':'20'},{'key':'pressure','value':'8'},{'key':'temperature','value':'24'},
                    {'key':'humidity','value':'55'},{'key':'noise','value':'58'},{'key':'illumination_main','value':'400'},
                    {'key':'illumination_aux','value':'250'}
                ],
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_vet_gmp_c', 'domain': 'pharma',
            'room': {
                'type_id':'veterinary_gmp_workshop','room_name':'兽药GMP车间C级','level_name':'C级','clean_class':'C级','context':{'gmp_grade':'C级'},
                'params':[
                    {'key':'particle','value':'100000'},{'key':'airchange','value':'30'},{'key':'pressure','value':'12'},
                    {'key':'noise','value':'58'},{'key':'illumination_main_room','value':'350'},{'key':'illumination_aux_room','value':'220'}
                ],
                'summary':{'result_state':'合格'}
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'fullparam_records_batch2_{ts}.json'
    out_md = REPORTS / f'fullparam_summary_batch2_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 全参数测试记录 Batch2', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
    lines.append('| case_id | type_id | param_count | template_key | result_state | judgement_engine | export_id | ok |')
    lines.append('|---|---|---:|---|---|---|---|---|')
    for r in results:
        lines.append(f"| {r['case_id']} | {r['type_id']} | {r['param_count']} | {r['template_key']} | {r['result_state']} | {r['judgement_engine']} | {r['export_id']} | {'PASS' if r['ok'] else 'FAIL'} |")
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    passed = sum(1 for r in results if r['ok'])
    print(out_json)
    print(out_md)
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
