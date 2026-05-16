#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, type_id, level, params, expected):
    payload={'project_name':name,'domain':'pharma','rooms':[{
        'type_id':type_id,'room_name':level+'01','level_name':level,'clean_class':level,
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
        ('gmp_C_温度正常','gmp_workshop','C级', {'temperature':{'values':['22']}}, '合格'),
        ('gmp_C_温度超标','gmp_workshop','C级', {'temperature':{'values':['30']}}, '不合格'),
        ('gmp_D_换气正常','gmp_workshop','D级', {'airchange':{'values':['15']}}, '合格'),
        ('gmp_D_换气超标','gmp_workshop','D级', {'airchange':{'values':['25']}}, '不合格'),
        ('vet_gmp_A_风速正常','veterinary_gmp_workshop','A级', {'wind_speed':{'values':['0.45']}}, '合格'),
        ('vet_gmp_A_风速超标','veterinary_gmp_workshop','A级', {'wind_speed':{'values':['0.20']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d,e) for a,b,c,d,e in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
