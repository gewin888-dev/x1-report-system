#!/usr/bin/env python3
"""
X1 异常样本专项记录器（Batch 3）
目标：继续扩大异常样本覆盖面，并验证异常样本在更多对象上的 reason / abnormal_items 稳定返回。
覆盖：operating_room / clean_function_room / gmp_workshop / animal_room / bsc / pass_box
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


def norm_params(params):
    out = []
    for k, v in params.items():
        out.append({'key': k, 'value': str(v)})
    return out


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
        'abnormal_items': abnormal_items,
        'expected_min_abnormal': case['expected_min_abnormal'],
        'export_id': body.get('export_id', ''),
        'ok': (
            bool(body.get('export_id'))
            and summary.get('result_state') == '不合格'
            and len(abnormal_items) >= case['expected_min_abnormal']
            and bool(summary.get('judgement_engine'))
            and summary.get('judgement_engine') != 'unmatched_or_insufficient_params'
            and bool(summary.get('judgement_reason'))
        ),
    }


def main():
    assert login(), 'login failed'
    cases = [
        {
            'case_id': 'abnormal_or_pressure_temp_humidity', 'domain': 'hospital', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'operating_room','room_name':'百级手术室异常样本2','level_name':'I级','clean_class':'I级',
                'context':{'room_type':'main-room','clean_class_code':'level1'},
                'params': norm_params({
                    'airchange':'18','pressure':'4','temperature':'27','humidity':'72','noise':'54',
                    'illumination_min':'300','illumination':'260','temp_diff':'3'
                }),
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_cfr_pressure_noise_bacteria', 'domain': 'hospital', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'clean_function_room','room_name':'透析室异常样本','level_name':'透析室','clean_class':'透析室',
                'context':{'clean_function_subroom':'透析室'},
                'params': norm_params({
                    'pressure':'2','noise':'68','illumination':'50','temperature':'29','settling':'10','floating':'1200'
                }),
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_gmp_airchange_pressure_temp', 'domain': 'pharma', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'gmp_workshop','room_name':'GMP B级异常样本2','level_name':'B级','clean_class':'B级',
                'context':{'gmp_grade':'B级'},
                'params': norm_params({
                    'particle':'9999999','airchange':'20','pressure':'2','temperature':'29','humidity':'78',
                    'noise':'72','illumination_main_room':'120','illumination_aux_room':'80'
                }),
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_animal_temp_humidity_noise', 'domain': 'biosafety', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'animal_room','room_name':'普通环境动物房异常样本','level_name':'普通环境','clean_class':'普通环境',
                'context':{'animal_environment':'普通环境'},
                'params': norm_params({
                    'temperature':'31','humidity':'82','noise':'72','illumination':'40','ammonia':'25'
                }),
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_bsc_velocity_noise_leak', 'domain': 'biosafety', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'bsc','room_name':'生物安全柜异常样本2','level_name':'Ⅱ级A2型','clean_class':'Ⅱ级A2型',
                'context':{'bsc_model':'Ⅱ级A2型'},
                'params': norm_params({
                    'downflow_speed':'0.10','inflow_speed':'0.10','noise':'78','illumination':'180','hepa_leak':'0.20'
                }),
                'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_passbox_noise_leak_uv', 'domain': 'pharma', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'pass_box','room_name':'传递窗异常样本2','level_name':'默认','clean_class':'默认',
                'context':{},
                'params': norm_params({
                    'noise':'82','hepa_leak':'0.20','uv_intensity':'0'
                }),
                'summary':{'result_state':'合格'}
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'abnormal_records_batch3_{ts}.json'
    out_md = REPORTS / f'abnormal_summary_batch3_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 异常样本专项记录 Batch3', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
    lines.append('| case_id | type_id | expected_min_abnormal | actual_abnormal | result_state | engine | has_reason | export_id | ok |')
    lines.append('|---|---|---:|---:|---|---|---|---|---|')
    for r in results:
        lines.append(f"| {r['case_id']} | {r['type_id']} | {r['expected_min_abnormal']} | {r['abnormal_count']} | {r['result_state']} | {r['judgement_engine']} | {'Y' if r['judgement_reason'] else 'N'} | {r['export_id']} | {'PASS' if r['ok'] else 'FAIL'} |")
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    passed = sum(1 for r in results if r['ok'])
    print(out_json)
    print(out_md)
    print(f'SUMMARY {passed}/{len(results)}')
    if passed != len(results):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
