#!/usr/bin/env python3
"""
X1 异常样本专项记录器（Batch 1）
目标：验证多项异常叠加时，系统是否能稳定输出不合格、异常项数量、judgement_reason。
覆盖：operating_room / bsl / food_workshop / electronics_workshop / negative_pressure / laminar_hood
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
        'client_name': '异常样本测试单位',
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
        'expected_min_abnormal': case['expected_min_abnormal'],
        'export_id': body.get('export_id', ''),
        'ok': bool(body.get('export_id')) and summary.get('result_state') == '不合格' and len(abnormal_items) >= case['expected_min_abnormal'] and bool(summary.get('judgement_engine')),
    }


def main():
    assert login(), 'login failed'
    cases = [
        {
            'case_id': 'abnormal_or_multi', 'domain': 'hospital', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'operating_room','room_name':'千级手术室异常样本','level_name':'Ⅱ级','clean_class':'Ⅱ级',
                'context':{'room_type':'main-room','clean_class_code':'level2'},
                'params':[
                    {'key':'airchange','value':'20'},{'key':'pressure','value':'4'},{'key':'temperature','value':'26'},
                    {'key':'humidity','value':'70'},{'key':'noise','value':'52'},{'key':'illumination_min','value':'300'},
                    {'key':'illumination','value':'280'},{'key':'temp_diff','value':'3'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_bsl_multi', 'domain': 'biosafety', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'bsl','room_name':'P2实验室异常样本','level_name':'BSL-2（P2）','clean_class':'BSL-2（P2）','context':{'bsl_level':'BSL-2（P2）'},
                'params':[
                    {'key':'airchange','value':'10'},{'key':'pressure','value':'-8'},{'key':'temperature','value':'30'},
                    {'key':'humidity','value':'80'},{'key':'noise','value':'65'},{'key':'illumination','value':'200'},
                    {'key':'settling','value':'5'},{'key':'floating','value':'200'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_food_multi', 'domain': 'food', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'food_workshop','room_name':'食品车间Ⅲ级异常样本','level_name':'Ⅲ级','clean_class':'Ⅲ级','context':{'food_grade':'Ⅲ级'},
                'params':[
                    {'key':'airchange','value':'10'},{'key':'pressure','value':'3'},{'key':'temperature','value':'30'},
                    {'key':'humidity','value':'80'},{'key':'noise','value':'70'},{'key':'illumination_general_processing','value':'150'},
                    {'key':'illumination_mixed_processing','value':'300'},{'key':'illumination_non_processing','value':'50'},
                    {'key':'settling','value':'8'},{'key':'floating','value':'200'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_elec_multi', 'domain': 'electronics', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'electronics_workshop','room_name':'电子ISO6异常样本','level_name':'ISO 6','clean_class':'ISO 6','context':{'iso_level':'ISO 6'},
                'params':[
                    {'key':'particle','value':'999999'},{'key':'airchange','value':'40'},{'key':'pressure','value':'2'},
                    {'key':'noise','value':'70'},{'key':'illumination_main','value':'200'},{'key':'illumination_aux','value':'150'},
                    {'key':'temperature','value':'28'},{'key':'humidity','value':'80'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_np_multi', 'domain': 'hospital', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'negative_pressure','room_name':'负压病房异常样本','level_name':'负压病房','clean_class':'负压病房','context':{'negative_pressure_mode':'standard'},
                'params':[
                    {'key':'airchange','value':'8'},{'key':'airchange_clean','value':'4'},{'key':'pressure','value':'-3'},
                    {'key':'temperature','value':'28'},{'key':'humidity','value':'80'},{'key':'noise','value':'60'},
                    {'key':'illumination','value':'20'},{'key':'bacteria','value':'10'},{'key':'surface_bacteria','value':'20'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_laminar_multi', 'domain': 'pharma', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'laminar_hood','room_name':'层流罩异常样本','level_name':'层流罩','clean_class':'层流罩',
                'params':[
                    {'key':'avg_speed','value':'0.60'},{'key':'speed_uniformity','value':'0.30'},{'key':'hepa_leak','value':'0.20'},
                    {'key':'airflow_pattern','value':'紊流，有旋涡'}
                ], 'summary':{'result_state':'合格'}
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'abnormal_records_batch1_{ts}.json'
    out_md = REPORTS / f'abnormal_summary_batch1_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 异常样本专项记录 Batch1', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
    lines.append('| case_id | type_id | expected_min_abnormal | actual_abnormal | result_state | engine | export_id | ok |')
    lines.append('|---|---|---:|---:|---|---|---|---|')
    for r in results:
        lines.append(f"| {r['case_id']} | {r['type_id']} | {r['expected_min_abnormal']} | {r['abnormal_count']} | {r['result_state']} | {r['judgement_engine']} | {r['export_id']} | {'PASS' if r['ok'] else 'FAIL'} |")
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    passed = sum(1 for r in results if r['ok'])
    print(out_json)
    print(out_md)
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
