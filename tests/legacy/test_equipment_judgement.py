#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, type_id, params, expected):
    payload={'project_name':name,'domain':'biosafety','rooms':[{
        'type_id':type_id,'room_name':type_id.upper()+'01','level_name':'默认','clean_class':'默认',
        'params':params,'summary':{'result_state':'合格'}
    }]}
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    ep=r.json()['export_payload']
    summary=ep['room']['summary']
    jr=ep.get('judgement_result') or {}
    actual=summary.get('result_state')
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'), name, 'actual=', actual, 'expected=', expected, 'engine=', summary.get('judgement_engine'), 'abnormal=', len(jr.get('abnormal_items',[])))
    return ok

if __name__=='__main__':
    assert login(), 'login failed'
    cases=[
        ('clean_bench_风速正常','clean_bench', {'avg_speed':{'values':['0.30']}}, '合格'),
        ('clean_bench_风速超标','clean_bench', {'avg_speed':{'values':['0.10']}}, '不合格'),
        ('clean_bench_噪声正常','clean_bench', {'noise':{'values':['60']}}, '合格'),
        ('clean_bench_噪声超标','clean_bench', {'noise':{'values':['80']}}, '不合格'),
        ('ivc_风速正常','ivc', {'airflow_speed':{'values':['0.10']}}, '合格'),
        ('ivc_风速超标','ivc', {'airflow_speed':{'values':['0.30']}}, '不合格'),
        ('ivc_换气正常','ivc', {'airchange':{'values':['25']}}, '合格'),
        ('ivc_换气不足','ivc', {'airchange':{'values':['10']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d) for a,b,c,d in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
