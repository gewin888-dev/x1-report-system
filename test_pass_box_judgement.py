#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, context, params, expected):
    payload={'project_name':name,'domain':'pharma','rooms':[{
        'type_id':'pass_box','room_name':'传递窗01','level_name':context.get('pass_box_type','默认'),'clean_class':context.get('pass_box_type','默认'),
        'context':context,
        'params':params,'summary':{'result_state':'合格'}
    }]}
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    ep=r.json()['export_payload']
    summary=ep['room']['summary']
    jr=ep.get('judgement_result') or {}
    actual=summary.get('result_state')
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'), name, 'actual=', actual, 'expected=', expected, 'engine=', summary.get('judgement_engine'), 'level=', jr.get('matched_level'), 'abnormal=', len(jr.get('abnormal_items',[])))
    return ok

if __name__=='__main__':
    assert login(), 'login failed'
    cases=[
        ('pass_box_噪声正常', {}, {'noise':{'values':['60']}}, '合格'),
        ('pass_box_噪声超标', {}, {'noise':{'values':['80']}}, '不合格'),
        ('pass_box_检漏正常', {}, {'hepa_leak':{'values':['0.005']}}, '合格'),
        ('pass_box_检漏超标', {}, {'hepa_leak':{'values':['0.05']}}, '不合格'),
        ('pass_box_B12_换气正常', {'pass_box_type':'B1/B2型'}, {'airchange_b12':{'values':['60']}}, '合格'),
        ('pass_box_B12_换气不足', {'pass_box_type':'B1/B2型'}, {'airchange_b12':{'values':['20']}}, '不合格'),
        ('pass_box_B3_换气正常', {'pass_box_type':'B3型'}, {'airchange_b3':{'values':['1200']}}, '合格'),
        ('pass_box_B3_换气不足', {'pass_box_type':'B3型'}, {'airchange_b3':{'values':['500']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d) for a,b,c,d in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
