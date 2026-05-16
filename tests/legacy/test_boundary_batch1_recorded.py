#!/usr/bin/env python3
"""
X1 第一批边界测试实跑记录器
覆盖：operating_room / bsl / electronics_workshop / gmp_workshop
当前先跑一批高风险参数的 5 点边界值，并生成记录。
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


def run_case(case):
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
        'abnormal_items': abnormal_items,
        'draft_saved': True,
        'export_id': body.get('export_id', ''),
        'feishu_report_url': ((feishu.get('report') or {}).get('feishu_url', '')),
        'feishu_export_url': ((feishu.get('export') or {}).get('feishu_url', '')),
        'ok': summary.get('result_state') == case['expected_state'],
    }


def main():
    assert login(), 'login failed'
    cases = []
    # operating_room temperature 5点
    for suffix, value, expected in [('low_out', '21.9', '不合格'), ('low_eq', '22.0', '合格'), ('low_in', '22.1', '合格'), ('high_in', '23.9', '合格'), ('high_out', '24.1', '不合格')]:
        cases.append({
            'case_id': f'or_temp_{suffix}', 'domain': 'hospital', 'parameter': 'temperature', 'input_value': value, 'expected_state': expected,
            'room': {'type_id':'operating_room','room_name':'百级手术室','level_name':'Ⅰ级','clean_class':'Ⅰ级','context':{'room_type':'main-room','clean_class_code':'level1'},'params':[{'key':'temperature','value':value}],'summary':{'result_state':'合格'}}
        })
    # bsl humidity 5点
    for suffix, value, expected in [('low_out', '44.9', '不合格'), ('low_eq', '45.0', '合格'), ('low_in', '45.1', '合格'), ('high_in', '64.9', '合格'), ('high_out', '65.1', '不合格')]:
        cases.append({
            'case_id': f'bsl_humidity_{suffix}', 'domain': 'biosafety', 'parameter': 'humidity', 'input_value': value, 'expected_state': expected,
            'room': {'type_id':'bsl','room_name':'P2实验室','level_name':'BSL-2（P2）','clean_class':'BSL-2（P2）','context':{'bsl_level':'BSL-2（P2）'},'params':[{'key':'humidity','value':value}],'summary':{'result_state':'合格'}}
        })
    # electronics iso7 airchange 5点
    for suffix, value, expected in [('low_out', '14', '不合格'), ('low_eq', '15', '合格'), ('low_in', '16', '合格'), ('high_in', '24', '合格'), ('high_out', '26', '不合格')]:
        cases.append({
            'case_id': f'elec_iso7_airchange_{suffix}', 'domain': 'electronics', 'parameter': 'airchange', 'input_value': value, 'expected_state': expected,
            'room': {'type_id':'electronics_workshop','room_name':'电子ISO7','level_name':'ISO 7','clean_class':'ISO 7','context':{'iso_level':'ISO 7'},'params':[{'key':'airchange','value':value}],'summary':{'result_state':'合格'}}
        })
    # gmp D airchange 5点
    for suffix, value, expected in [('low_out', '9', '不合格'), ('low_eq', '10', '合格'), ('low_in', '11', '合格'), ('high_in', '19', '合格'), ('high_out', '21', '不合格')]:
        cases.append({
            'case_id': f'gmp_d_airchange_{suffix}', 'domain': 'pharma', 'parameter': 'airchange', 'input_value': value, 'expected_state': expected,
            'room': {'type_id':'gmp_workshop','room_name':'GMP D级','level_name':'D级','clean_class':'D级','params':[{'key':'airchange','value':value}],'summary':{'result_state':'合格'}}
        })

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'boundary_records_batch1_{ts}.json'
    out_md = REPORTS / f'boundary_summary_batch1_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 第一批边界测试记录', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
    lines.append('| case_id | type_id | parameter | input_value | expected | actual | engine | export_id | ok |')
    lines.append('|---|---|---|---:|---|---|---|---|---|')
    for r in results:
        lines.append(f"| {r['case_id']} | {r['type_id']} | {r['parameter']} | {r['input_value']} | {r['expected_state']} | {r['actual_state']} | {r['judgement_engine']} | {r['export_id']} | {'PASS' if r['ok'] else 'FAIL'} |")
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    passed = sum(1 for r in results if r['ok'])
    print(out_json)
    print(out_md)
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
