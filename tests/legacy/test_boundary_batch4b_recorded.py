#!/usr/bin/env python3
"""
X1 第四批边界测试纠偏记录器（Batch 4b）
目标：按已核实的真实规则，纠正 animal_room / bsc / pass_box / laminar_hood 的边界预期。
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


def norm_params(params):
    out = []
    for k, v in params.items():
        if isinstance(v, dict):
            out.append({'key': k, 'value': str((v.get('values') or [''])[0])})
        else:
            out.append({'key': k, 'value': str(v)})
    return out


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

    # animal_room 屏障环境 pressure >=10
    for suffix, value, expected in [('low_out', '9', '不合格'), ('low_eq', '10', '合格'), ('low_in', '11', '合格')]:
        room = {
            'type_id':'animal_room','room_name':'屏障环境饲养室','level_name':'屏障环境','clean_class':'屏障环境',
            'context':{'animal_environment':'屏障环境','barrier_room_class':'饲养室'},
            'params': norm_params({'pressure': {'values':[value]}}), 'summary':{'result_state':'合格'}
        }
        cases.append({'case_id': f'animal_barrier_pressure_fix_{suffix}', 'domain': 'biosafety', 'parameter': 'pressure', 'input_value': value, 'expected_state': expected, 'room': room})

    # bsc downflow_speed 0.25~0.5
    for suffix, value, expected in [('low_out', '0.24', '不合格'), ('low_eq', '0.25', '合格'), ('low_in', '0.26', '合格')]:
        room = {
            'type_id':'bsc','room_name':'BSC01','level_name':'A2型','clean_class':'A2型',
            'params': norm_params({'wind_speed_down': {'values':[value]}}), 'summary':{'result_state':'合格'}
        }
        cases.append({'case_id': f'bsc_downspeed_fix_{suffix}', 'domain': 'biosafety', 'parameter': 'wind_speed_down', 'input_value': value, 'expected_state': expected, 'room': room})

    # pass_box noise <=68
    for suffix, value, expected in [('low_in', '68', '合格'), ('high_out', '69', '不合格')]:
        room = {
            'type_id':'pass_box','room_name':'传递窗01','level_name':'默认','clean_class':'默认','context':{},
            'params': norm_params({'noise': {'values':[value]}}), 'summary':{'result_state':'合格'}
        }
        cases.append({'case_id': f'passbox_noise_fix_{suffix}', 'domain': 'pharma', 'parameter': 'noise', 'input_value': value, 'expected_state': expected, 'room': room})

    # laminar_hood avg_speed 0.36~0.54
    for suffix, value, expected in [('low_out', '0.35', '不合格'), ('low_eq', '0.36', '合格')]:
        room = {
            'type_id':'laminar_hood','room_name':'层流罩01','level_name':'默认','clean_class':'默认',
            'params': norm_params({'avg_speed': {'values':[value]}}), 'summary':{'result_state':'合格'}
        }
        cases.append({'case_id': f'laminar_avgspeed_fix_{suffix}', 'domain': 'pharma', 'parameter': 'avg_speed', 'input_value': value, 'expected_state': expected, 'room': room})

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'boundary_records_batch4b_{ts}.json'
    out_md = REPORTS / f'boundary_summary_batch4b_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 第四批边界测试纠偏记录 Batch4b', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
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
