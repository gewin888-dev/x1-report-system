#!/usr/bin/env python3
"""
X1 异常样本专项记录器（Batch 4b）
目标：纠偏 batch4 中 ivc 异常样本力度，验证其是否能稳定返回 2+ abnormal_items。
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
    return [{'key': k, 'value': str(v)} for k, v in params.items()]


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
            'case_id': 'abnormal_ivc_multi_2_fix', 'domain': 'biosafety', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'ivc','room_name':'IVC笼具异常样本2纠偏','level_name':'默认','clean_class':'默认',
                'context':{},
                'params': norm_params({
                    'airchange':'8','airflow_speed':'0.10','noise':'82','temperature':'31','humidity':'82','illumination':'40'
                }),
                'summary':{'result_state':'合格'}
            }
        }
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'abnormal_records_batch4b_{ts}.json'
    out_md = REPORTS / f'abnormal_summary_batch4b_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 异常样本专项记录 Batch4b', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
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
