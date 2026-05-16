#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, subroom, params, expected):
    payload={'project_name':name,'domain':'hospital','rooms':[{
        'type_id':'clean_function_room','room_name':subroom+'01','level_name':subroom,'clean_class':subroom,
        'context':{'clean_function_subroom':subroom},
        'params':params,'summary':{'result_state':'合格'}
    }]}
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    ep=r.json()['export_payload']
    summary=ep['room']['summary']
    jr=ep.get('judgement_result') or {}
    actual=summary.get('result_state')
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'), name, 'actual=', actual, 'expected=', expected, 'engine=', summary.get('judgement_engine'), 'level=', (jr.get('matched_level')), 'abnormal=', len(jr.get('abnormal_items',[])))
    return ok

if __name__=='__main__':
    assert login(), 'login failed'
    cases=[
        ('ICU_噪声正常','ICU病房', {'noise':{'values':['55']}}, '合格'),
        ('ICU_噪声超标','ICU病房', {'noise':{'values':['70']}}, '不合格'),
        ('CSSD_温度正常','消毒供应中心', {'temperature':{'values':['22']}}, '合格'),
        ('CSSD_温度超标','消毒供应中心', {'temperature':{'values':['30']}}, '不合格'),
        ('透析室_湿度正常','透析室', {'humidity':{'values':['50']}}, '合格'),
        ('透析室_湿度超标','透析室', {'humidity':{'values':['90']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d) for a,b,c,d in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
