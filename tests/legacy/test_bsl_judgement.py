#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, level, params, expected):
    payload={'project_name':name,'domain':'biosafety','rooms':[{
        'type_id':'bsl','room_name':'BSL01','level_name':level,'clean_class':level,
        'context':{'bsl_level':level},
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
        ('bsl_p2_换气正常','BSL-2（P2）', {'airchange':{'values':['20']}}, '合格'),
        ('bsl_p2_换气不足','BSL-2（P2）', {'airchange':{'values':['5']}}, '不合格'),
        ('bsl_p3_压差正常','BSL-3（P3）', {'pressure':{'values':['-12']}}, '合格'),
        ('bsl_p3_压差异常','BSL-3（P3）', {'pressure':{'values':['0']}}, '不合格'),
        ('bsl_p3_噪声正常','BSL-3（P3）', {'noise':{'values':['55']}}, '合格'),
        ('bsl_p3_噪声超标','BSL-3（P3）', {'noise':{'values':['80']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d) for a,b,c,d in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
