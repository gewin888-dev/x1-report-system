#!/usr/bin/env python3
"""
X1 全参数测试记录器（Batch 5）
覆盖：animal_room / bsc / clean_bench / ivc / laminar_hood / pass_box
继续补设备类与动物房方向的全参数正常/异常样本。
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
            'case_id': 'fullparam_animal_barrier_main_good', 'domain': 'biosafety', 'expected_state': '合格',
            'room': {
                'type_id':'animal_room','room_name':'屏障环境主房间','level_name':'屏障环境','clean_class':'屏障环境',
                'context':{'animal_environment':'屏障环境'},
                'params':[
                    {'key':'temperature','value':'23'},{'key':'humidity','value':'50'},{'key':'pressure','value':'15'},
                    {'key':'noise','value':'55'},{'key':'illumination','value':'180'},{'key':'airchange','value':'18'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_bsc_good', 'domain': 'biosafety', 'expected_state': '合格',
            'room': {
                'type_id':'bsc','room_name':'生物安全柜','level_name':'BSC','clean_class':'BSC',
                'params':[
                    {'key':'downflow_speed','value':'0.35'},{'key':'inflow_speed','value':'0.55'},{'key':'noise','value':'60'},
                    {'key':'illumination','value':'800'},{'key':'hepa_leak','value':'0.01'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_clean_bench_good', 'domain': 'pharma', 'expected_state': '合格',
            'room': {
                'type_id':'clean_bench','room_name':'洁净工作台','level_name':'clean_bench','clean_class':'clean_bench',
                'params':[
                    {'key':'wind_speed','value':'0.4'},{'key':'noise','value':'60'},{'key':'illumination','value':'320'},
                    {'key':'hepa_leak','value':'0.01'},{'key':'airflow_pattern','value':'垂直向下，无旋涡'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_ivc_good', 'domain': 'biosafety', 'expected_state': '合格',
            'room': {
                'type_id':'ivc','room_name':'IVC笼具','level_name':'ivc','clean_class':'ivc',
                'params':[
                    {'key':'temperature','value':'23'},{'key':'humidity','value':'50'},{'key':'noise','value':'55'},
                    {'key':'illumination','value':'180'},{'key':'airchange','value':'60'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_laminar_good', 'domain': 'pharma', 'expected_state': '合格',
            'room': {
                'type_id':'laminar_hood','room_name':'层流罩','level_name':'层流罩','clean_class':'层流罩',
                'params':[
                    {'key':'avg_speed','value':'0.45'},{'key':'speed_uniformity','value':'0.18'},{'key':'hepa_leak','value':'0.01'},
                    {'key':'airflow_pattern','value':'气流垂直向下，无旋涡'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_pass_box_good', 'domain': 'pharma', 'expected_state': '合格',
            'room': {
                'type_id':'pass_box','room_name':'传递窗','level_name':'default','clean_class':'default',
                'context':{'pass_box_mode':'_default'},
                'params':[
                    {'key':'airflow_speed','value':'0.25'},{'key':'hepa_leak','value':'0.01'},{'key':'noise','value':'58'},
                    {'key':'uv_intensity','value':'80'},{'key':'airtightness','value':'0.01'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'fullparam_laminar_bad_speed', 'domain': 'pharma', 'expected_state': '不合格',
            'room': {
                'type_id':'laminar_hood','room_name':'层流罩风速异常','level_name':'层流罩','clean_class':'层流罩',
                'params':[
                    {'key':'avg_speed','value':'0.60'},{'key':'speed_uniformity','value':'0.18'},{'key':'hepa_leak','value':'0.01'},
                    {'key':'airflow_pattern','value':'气流垂直向下，无旋涡'}
                ], 'summary':{'result_state':'合格'}
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'fullparam_records_batch5_{ts}.json'
    out_md = REPORTS / f'fullparam_summary_batch5_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 全参数测试记录 Batch5', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
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
