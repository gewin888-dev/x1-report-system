#!/usr/bin/env python3
"""
X1 异常样本专项记录器（Batch 2）
目标：继续扩大异常样本覆盖面，把 batch1 未覆盖对象补进异常链。
覆盖：clean_function_room / gmp_workshop / veterinary_gmp_workshop / animal_room / pass_box / bsc / clean_bench / ivc
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
            'case_id': 'abnormal_cfr_multi', 'domain': 'hospital', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'clean_function_room','room_name':'ICU异常样本','level_name':'ICU病房','clean_class':'ICU病房','context':{'clean_function_subroom':'ICU病房'},
                'params':[
                    {'key':'airchange','value':'6'},{'key':'pressure','value':'2'},{'key':'hepa_leak','value':'0.20'},
                    {'key':'temperature','value':'30'},{'key':'noise','value':'70'},{'key':'illumination','value':'20'},
                    {'key':'settling','value':'9'},{'key':'floating','value':'900'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_gmp_multi', 'domain': 'pharma', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'gmp_workshop','room_name':'GMP C级异常样本','level_name':'C级','clean_class':'C级','context':{'gmp_grade':'C级'},
                'params':[
                    {'key':'particle','value':'9999999'},{'key':'airchange','value':'10'},{'key':'pressure','value':'2'},
                    {'key':'temperature','value':'28'},{'key':'humidity','value':'80'},{'key':'noise','value':'70'},
                    {'key':'illumination_main_room','value':'100'},{'key':'illumination_aux_room','value':'100'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_vgmp_multi', 'domain': 'pharma', 'expected_min_abnormal': 3,
            'room': {
                'type_id':'veterinary_gmp_workshop','room_name':'兽药GMP B级异常样本','level_name':'B级','clean_class':'B级','context':{'gmp_grade':'B级'},
                'params':[
                    {'key':'particle','value':'9999999'},{'key':'airchange','value':'20'},{'key':'pressure','value':'2'},
                    {'key':'noise','value':'70'},{'key':'illumination_main_room','value':'100'},{'key':'illumination_aux_room','value':'100'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_animal_multi', 'domain': 'animal', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'animal_room','room_name':'屏障环境主房间异常样本','level_name':'屏障环境主房间','clean_class':'屏障环境主房间','context':{'animal_room_type':'屏障环境主房间'},
                'params':[
                    {'key':'temperature','value':'30'},{'key':'humidity','value':'80'},{'key':'noise','value':'70'},
                    {'key':'illumination','value':'50'},{'key':'ammonia','value':'30'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_passbox_multi', 'domain': 'pharma', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'pass_box','room_name':'传递窗异常样本','level_name':'传递窗','clean_class':'传递窗',
                'params':[
                    {'key':'cleanliness','value':'不合格'},{'key':'interlock','value':'失效'},{'key':'uv_intensity','value':'0'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_bsc_multi', 'domain': 'biosafety', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'bsc','room_name':'生物安全柜异常样本','level_name':'Ⅱ级A2型','clean_class':'Ⅱ级A2型','context':{'bsc_model':'Ⅱ级A2型'},
                'params':[
                    {'key':'downflow_velocity','value':'0.10'},{'key':'inflow_velocity','value':'0.10'},{'key':'noise','value':'75'},
                    {'key':'illumination','value':'200'},{'key':'hepa_leak','value':'0.20'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_cleanbench_multi', 'domain': 'biosafety', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'clean_bench','room_name':'洁净工作台异常样本','level_name':'洁净工作台','clean_class':'洁净工作台',
                'params':[
                    {'key':'wind_speed','value':'0.10'},{'key':'noise','value':'75'},{'key':'illumination','value':'100'},
                    {'key':'hepa_leak','value':'0.20'}
                ], 'summary':{'result_state':'合格'}
            }
        },
        {
            'case_id': 'abnormal_ivc_multi', 'domain': 'biosafety', 'expected_min_abnormal': 2,
            'room': {
                'type_id':'ivc','room_name':'IVC笼具异常样本','level_name':'IVC笼具','clean_class':'IVC笼具',
                'params':[
                    {'key':'noise','value':'80'},{'key':'illumination','value':'50'},{'key':'temperature','value':'30'},
                    {'key':'humidity','value':'80'}
                ], 'summary':{'result_state':'合格'}
            }
        },
    ]

    results = [run_case(c) for c in cases]
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'abnormal_records_batch2_{ts}.json'
    out_md = REPORTS / f'abnormal_summary_batch2_{ts}.md'
    out_json.write_text(json.dumps({'generated_at': ts, 'total': len(results), 'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = ['# X1 异常样本专项记录 Batch2', '', f'- 生成时间：{ts}', f'- 总数：{len(results)}', '']
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
